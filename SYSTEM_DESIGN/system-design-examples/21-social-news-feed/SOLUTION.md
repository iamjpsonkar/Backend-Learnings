# Complete Solution: Social News Feed

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Users create/delete posts, follow or mute accounts, and read a personalized,
cursor-paginated home feed. The feed enforces private-account, block, deletion, and
moderation rules and may combine fresh, relevant, sponsored, and recommended posts.

Targets: post creation p99 below 300 ms, first feed page p99 below 250 ms, 99.99%
feed-read availability, and ordinary-author posts visible to 99% of followers within
five seconds. Feed order is personalized and eventually consistent. Post ownership
and visibility changes are authoritative and must be rechecked at read time.

## 2. Capacity estimation

Assume 100 million daily active users, five posts and 200 feed reads/user/day, 300
followed accounts/user, 1 KB post metadata, 50 candidate IDs/page, and 3x peaks.

- Post writes average about 5,800/s and peak near 18,000/s.
- Feed reads average about 231,000/s and peak near 700,000/s.
- If each ordinary post fans out to 300 followers, it produces 150 billion entry
  writes/day, so compact IDs, batching, retention, and the hybrid model matter.
- Post metadata is about 500 GB/day before media, indexes, and replication.
- A 30-day inbox with 1,000 compact 24-byte entries/user is about 2.4 TB for 100
  million users before replication; cap by count and age.

## 3. APIs

```text
POST   /v1/posts                         Idempotency-Key
DELETE /v1/posts/{postId}                If-Match: version
PUT    /v1/users/{userId}/following/{targetId} Idempotency-Key
DELETE /v1/users/{userId}/following/{targetId}
GET    /v1/feed?limit=50&cursor=...
POST   /v1/feed/impressions              {items, requestId}
POST   /v1/feed/actions                  {postId, action, requestId}
```

The cursor is opaque and signed. It includes the feed request/session ID, model and
policy versions, candidate snapshot watermark, and last ordering tuple; it is not a
numeric page offset.

## 4. Data model

```text
User(id, account_visibility, state, profile_version)
Follow(follower_id, followee_id, state, version, created_at)
Block(blocker_id, blocked_id, version)
Post(id, author_id, body_ref, media_refs, visibility, state,
     created_at, version, moderation_version)
FeedEntry(user_id, bucket, source_time, post_id, author_id, reason, event_version)
AuthorPost(author_id, created_at, post_id)
Engagement(post_id, counters, version)
FeedSession(id, user_id, candidate_watermark, model_version, expires_at)
Outbox(id, aggregate_id, event_type, payload, published_at)
```

Posts and graph edges are sources of truth. `FeedEntry` is a disposable projection,
unique by `(user_id, post_id, reason)` and partitioned by user/time bucket. Keep
media in object storage/CDN and post metadata in a sharded durable store.

## 5. Architecture

```text
post client -> post service -> post store + outbox -> event log
                                                     |
graph store -> fan-out planner -> follower shards -> inbox writers -> feed store
     |                                                   |
     +---- celebrity/source lists -----------------------+

feed client -> feed API -> candidate service -> ranker -> policy filter -> hydrator
                               |              |                     |
                         feed cache/store  feature store      post/media stores
```

Fan out ordinary authors on write for cheap reads. Do not fan out celebrities with
very large follower counts; merge their recent author streams on read. The threshold
is dynamic based on follower count, post rate, fan-out backlog, and infrastructure
cost.

## 6. Step-by-step workflow

### Publish

1. Authenticate, validate content/media/visibility, and claim idempotency key.
2. Transactionally insert post plus `PostCreated` outbox record; return after this
   authoritative commit, not after fan-out.
3. Planner classifies the author. For an ordinary author, read follower IDs in
   bounded pages and emit batches keyed by follower shard. For a celebrity, only
   update the author's recent-post stream.
4. Inbox writers conditionally insert compact feed entries. Retries are harmless.
5. Consumers update search, moderation, counters, and cache invalidations from the
   same versioned event.

### Read

1. Authenticate and validate cursor/session ownership.
2. Load more candidates than needed from inbox, celebrity streams, followed topics,
   and recommendations up to one shared watermark.
3. Deduplicate post IDs and remove already served/impressed IDs.
4. Batch-fetch lightweight post/author features, rank candidates, and apply hard
   visibility/moderation checks.
5. Hydrate selected posts/media, return the page and a signed cursor based on the
   last stable ordering key.

## 7. Core hybrid fan-out logic

```text
function onPostCreated(event):
    post = event.post
    if shouldFanOut(post.authorId):
        cursor = null
        do:
            followers, cursor = graph.pageFollowers(post.authorId, cursor, BATCH)
            groupByShard(followers).forEach((shard, users) =>
                queue.publish(shard,
                    FanoutBatch(event.id, post.id, post.authorId,
                                post.createdAt, users, event.version)))
        while cursor != null
    else:
        celebrityStream.putIfNewer(post.authorId, post.createdAt,
                                   post.id, event.version)

function writeFanoutBatch(batch):
    for userId in batch.users:
        if graph.mightReceive(userId, batch.authorId):
            inbox.upsertUnique(userId, batch.postId,
                sourceTime=batch.createdAt, version=batch.version)
```

The writer may use a graph snapshot captured at post time. Read-time authorization
is final, so a delayed unfollow/block cannot leak content. A fan-out job has a stable
event/batch ID, checkpoints follower-page progress, and is replayable from the log.

## 8. Candidate merge and pagination logic

```text
function getFeed(user, cursor, limit):
    state = verifyOrCreateFeedSession(user, cursor)
    inbox = feedStore.scan(user.id, before=state.inboxKey, limit=limit*5)
    authors = graph.followedCelebrityIds(user.id)
    celeb = kWayMergeRecentAuthorStreams(authors, state.watermark, limit*3)
    recommended = recommendations.fetch(user.id, state.requestId, limit*2)

    candidates = dedupeByPostId(inbox + celeb + recommended)
    candidates = excludePreviouslyServed(candidates, state)
    features = featureStore.batchGet(candidates)
    scored = rankWithPinnedModel(candidates, features, state.modelVersion)

    output = []
    for candidate in scored:
        post = postStore.get(candidate.postId)
        if visibleNow(user, post) and policyAllows(user, post):
            output.add(hydrate(post))
        if output.size == limit: break

    return output, signedAdvanceCursor(state, consumedCandidates(scored))
```

Advance the candidate scan position even when items are filtered, or a client can
loop forever on deleted entries. Over-fetch and refill within a bounded CPU/read
budget. K-way merge uses `(created_at, post_id)` to break ties deterministically.

## 9. Ranking

A candidate generator should favor recall; the ranker chooses a small final page.
A typical score combines predicted engagement, relationship affinity, freshness,
content quality, diversity, and negative feedback:

```text
score = w1*P(meaningful_action) + w2*affinity + w3*freshness
        + w4*quality - w5*seen_penalty - w6*negative_feedback
```

Pin the model/feature-policy version per short feed session to reduce page reorder.
Apply business rules after scoring: author/topic diversity, ad spacing, age safety,
and dedupe. If ranking/feature services fail, serve a bounded reverse-chronological
feed rather than failing the request.

## 10. Visibility, deletion, and graph changes

`visibleNow` verifies post state, post audience, current follow for private authors,
both-direction blocks, mute, geographic/age policy, and moderation decision. Cache
these decisions only briefly with versions.

Delete commits a post tombstone and event, immediately makes authoritative reads
return unavailable, invalidates caches, then asynchronously removes inbox entries,
search documents, media references, and recommendations. Follow begins future
fan-out and may backfill a bounded recent window; unfollow stops future entries and
filters old ones immediately while cleanup runs.

## 11. Cache and storage strategy

- Cache only the hottest head of each inbox; durable feed-store entries allow cache
  rebuild. Never make Redis the only copy of fan-out work.
- Store compact entry IDs separately from post bodies, then batch hydrate to avoid
  duplicating edited post data across millions of inboxes.
- Partition inboxes by user ID and time bucket. Split celebrity/hot users and salt
  read-heavy author streams across replicas.
- Cap per-user inbox by time/count. Older content can fall back to read-time source
  generation when the product requires deep history.

## 12. Backpressure and overload behavior

Prioritize post durability and active feed reads over derived fan-out. If lag rises,
increase batch sizes/workers, temporarily classify large authors as read-time, shed
low-value recommendation sources, and fall back to chronological ranking. Per-author
and tenant quotas stop a spammer from consuming fan-out capacity. Never allow a hot
author partition to block unrelated authors.

## 13. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client repeats create | Idempotency key returns same post |
| Outbox/log duplicates | Feed-entry unique key makes write harmless |
| Fan-out worker dies | Resume follower-page checkpoint/replay event |
| Fan-out is delayed | Read-time author merge can fill recent gaps |
| Feed cache fails | Read durable inbox and refill cache |
| Ranker/features fail | Serve chronological candidates with hard filtering |
| Post deleted during hydration | Omit it and continue bounded refill |
| Graph store is uncertain | Fail closed for private content; cached public policy may degrade |
| Region fails | Serve replicated feed/post data; fence home-region writers on promotion |

## 14. Consistency and rebuild

Post create/update/delete and graph commands are strongly consistent per entity.
Fan-out, counts, ranking features, and cleanup are eventually consistent. Every
projection records source event version and ignores older events. Rebuild an inbox
from retained post and graph logs into a new generation, compare counts/checksums,
then atomically switch its generation pointer.

Periodic reconciliation samples posts/followers and proves expected entries exist
or are safely supplied on read. It also removes entries whose source post no longer
exists.

## 15. Security and privacy

Authorize all post, graph, feed, media, and impression access. Protect private and
blocked content at hydration, use short authorized media URLs, encrypt data, audit
privacy/moderation/admin actions, and rate-limit scraping and graph enumeration.
Treat ranking features as personal data. Apply deletion, retention, legal hold,
residency, and account deactivation across primary stores, projections, caches,
logs, models, media, and backups.

## 16. Observability

Measure feed/post latency and errors, time-to-first-follower visibility, fan-out lag
and amplification, oldest batch, inbox/cache hit rate, candidates per source,
filter/drop/refill rates, ranking/fallback latency, cursor errors, duplicate rate,
stale/deleted item exposure, hot authors, shard skew, graph/policy failures, and
rebuild divergence. Break down health by cohort without exposing user IDs in metric
labels.

Load tests include celebrity posts, high-fan-out bursts, and deep pagination. Chaos
tests kill fan-out workers, cache, graph, ranker, and a region. Privacy tests race
block/delete with reads and assert no content appears after authoritative revocation.

## 17. Implementation path

1. **MVP:** durable posts/graph, chronological fan-out-on-read, visibility checks,
   signed cursor, and media hydration.
2. **Efficient reads:** ordinary-author fan-out, durable inbox store, cache, outbox,
   idempotent replay, and cleanup.
3. **Personalization:** candidate sources, feature service, ranker, feed sessions,
   diversity rules, impressions, and chronological fallback.
4. **Scale/hardening:** dynamic celebrity threshold, fair queues, partition repair,
   regional failover, privacy lifecycle, chaos/load tests, and rebuild tooling.

## 18. Final design

Use posts and follow edges as authoritative data and inbox entries as rebuildable
derived candidates. Hybrid fan-out writes ordinary-author posts into follower
inboxes while merging celebrity streams at read time. Ranking is allowed to be
eventually consistent, but every returned item passes current visibility and policy
checks. Stable sessions/cursors, versioned idempotent fan-out, and read-time merge
give low latency without sacrificing privacy or letting hot authors dominate writes.
