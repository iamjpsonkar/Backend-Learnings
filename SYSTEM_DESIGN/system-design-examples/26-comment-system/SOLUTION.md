# Complete Solution: Comment System

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Users create replies, edit/delete their comments, vote, report abuse, and read a
thread chronologically or ranked. Moderators hide/restore content. The service
supports deep discussions, stable cursor pagination, counts, and hot live-event
threads without leaking blocked or removed content.

Targets: read p99 below 200 ms, create/vote p99 below 300 ms, 99.99% read and 99.9%
write availability, and accepted comments visible to their author immediately and
to others within two seconds. Comment/vote ownership is strongly consistent;
counters, ranking, search, and caches are eventually consistent. Read-time policy is
authoritative.

## 2. Capacity estimation

Assume one billion retained comments, 100,000 peak mutations/s during major events,
20 reads/write, 500 bytes average body plus 300 bytes metadata, and 10 replies/page.

- Peak reads can reach two million/s, so ranked ID caches and batched hydration are
  essential.
- Raw comment rows consume about 800 GB before indexes, replication, edit history,
  and votes.
- A popular object may receive thousands of writes/s; no request should synchronously
  update one shared object counter row.
- Retain ranking indexes only for active windows and rebuild them from authoritative
  comments/votes when necessary.

## 3. APIs

```text
POST   /v1/objects/{objectId}/comments       Idempotency-Key
POST   /v1/comments/{commentId}/replies      Idempotency-Key
PATCH  /v1/comments/{commentId}              If-Match: version
DELETE /v1/comments/{commentId}              If-Match: version
PUT    /v1/comments/{commentId}/vote         {value: -1|0|1} Idempotency-Key
POST   /v1/comments/{commentId}/reports      Idempotency-Key
GET    /v1/objects/{objectId}/comments?sort=top|new&cursor=&limit=
GET    /v1/comments/{commentId}/replies?cursor=&limit=
POST   /v1/moderation/comments/{commentId}   {action, reason} If-Match
```

Bound body size, links/mentions, nesting depth, page size, report/vote rate, edit
window, and cursor age. Every cursor is opaque, signed, query-specific, and contains
an ordering tuple rather than a numeric offset.

## 4. Data model

```text
Comment(id, object_id, parent_id, root_id, author_id, depth, path_key,
        body, state, visibility, created_at, edited_at, version,
        moderation_version)
CommentRevision(comment_id, version, body, editor, created_at)
Vote(comment_id, user_id, value, version, updated_at)
VoteAggregate(comment_id, up_count, down_count, score, source_offset)
ThreadAggregate(object_id, comment_count, source_offset)
RankEntry(object_id, scope_parent, rank_version, score, created_at, comment_id)
Report(id, comment_id, reporter_id, reason, state, created_at)
ModerationDecision(comment_id, version, action, reason, moderator, created_at)
Block(user_id, blocked_user_id, version)
Outbox(id, aggregate_id, event_type, payload, published_at)
```

Partition authoritative comments and votes by `object_id` when bounded thread-local
transactions matter; a directory maps comment ID to object shard. Otherwise use
globally sortable IDs and route votes by comment shard. Deleted parents remain as
tombstones so reply structure and cursors remain stable.

## 5. Architecture

```text
clients -> API/auth -> comment service -> partitioned SQL/KV + outbox
                                         |
                                      event log
                              /           |           \
                       moderation     counters      ranking/search
                           |               |              |
                    policy store      aggregate DB   ranked ID store/cache

read API -> ranked/chronological IDs -> batch comment hydration -> policy filter
```

Primary rows are authoritative. Vote aggregates, ranks, counts, search documents,
and caches are versioned rebuildable projections. A fast synchronous rules engine
can quarantine obvious abuse; expensive classifiers and human review are async.

## 6. Step-by-step workflow

### Create

1. Authenticate; validate object existence, discussion state, body, rate limits,
   parent ownership/object, and maximum depth.
2. Generate comment ID and deterministic path/root metadata. Transactionally insert
   comment plus `CommentCreated` outbox event under idempotency key.
3. Return the committed comment. If synchronous safety policy is uncertain, expose
   it only to its author as `PENDING` until moderation accepts it.
4. Event consumers update counts, ranking candidates, search, notifications, and
   caches idempotently.

### Read

1. Validate object access, sort mode, page bounds, and signed cursor.
2. Scan over-fetched IDs by stable ordering tuple from rank store or chronological
   primary index.
3. Batch hydrate comment, author, vote, and moderation state.
4. Apply current deletion, block, audience, and safety policy; preserve eligible
   tombstone placeholders where needed to hold visible children.
5. Continue a bounded refill if entries were filtered, and return a cursor based on
   the last consumed candidate—not only the last displayed row.

## 7. Core comment creation logic

```text
function createComment(actor, objectId, parentId, body, requestKey):
    sanitized = validateAndNormalize(body)
    transaction on shard(objectId):
        old = idempotency.get(actor.id, requestKey)
        if old exists: return comments.get(old.commentId)

        require objectPolicy.mayComment(actor, objectId)
        if parentId != null:
            parent = comments.getForShare(parentId)
            require parent.objectId == objectId
            require parent.depth < MAX_DEPTH
            depth = parent.depth + 1
            root = parent.rootId ?? parent.id
            path = parent.pathKey + sortableComponent(newId)
        else:
            depth = 0; root = null; path = sortableComponent(newId)

        state = fastSafetyCheck(sanitized).initialState
        comment = comments.insert(newId, objectId, parentId, root,
                                  depth, path, actor.id, sanitized, state)
        idempotency.insert(actor.id, requestKey, comment.id)
        outbox.insert(CommentCreated(comment.id, comment.version))
    return comment
```

Maximum nesting simplifies UX and query cost. If unlimited logical nesting is a
product requirement, materialize `path_key` or closure edges, but cap returned depth
and page work.

## 8. Vote correctness and derived counters

```text
function setVote(actor, commentId, requestedValue, requestKey):
    require requestedValue in [-1, 0, 1]
    transaction:
        if idempotency.exists(actor.id, requestKey): return priorResult
        comment = comments.get(commentId)
        require mayViewAndVote(actor, comment)
        vote = votes.getForUpdate(commentId, actor.id) or Vote(value=0, version=0)
        old = vote.value
        if old != requestedValue:
            votes.upsert(commentId, actor.id, requestedValue, vote.version + 1)
            outbox.insert(VoteChanged(commentId, actor.id, old,
                                      requestedValue, vote.version + 1))
        rememberIdempotency(requestKey)
    return requestedValue
```

Unique `(comment_id, user_id)` prevents double voting. Consumers apply only newer
vote versions and adjust sharded aggregates by `delta(new)-delta(old)`. Periodic jobs
recompute exact totals from vote rows. Do not serialize all votes through one hot
comment-counter row.

## 9. Ranking and stable pagination

A basic time-decayed score can be:

```text
quality = wilsonLowerBound(upVotes, upVotes + downVotes)
score = quality + log1p(replyCount) * replyWeight
        + authorTrust - moderationPenalty
        - ageHours / decayHalfLife
rankKey = (quantize(score), createdAt, commentId)
```

Rank workers periodically create immutable `rank_version` snapshots per hot object
or update a sorted index. A feed session pins a rank version for several minutes;
its cursor contains `(rank_version, last_score, last_created_at, last_id)`. This
avoids duplicates/skips caused by scores changing between pages. If the snapshot
expires, restart with an explicit cursor-expired response rather than silently mixing
orders. Chronological mode uses `(created_at, id)` directly.

## 10. Thread representation

For most products, page top-level comments first and page replies separately by
`parent_id`; return a small reply preview and count. This prevents one enormous
subtree from consuming a whole page. Index `(object_id, parent_id, created_at, id)`.

If a flattened tree is required, materialized path gives a depth-first range scan,
but inserting/moving trees and very long paths are costly. Comments should generally
be immutable in parent relationship—delete/repost instead of moving subtrees.

## 11. Edits, deletes, and moderation

Edit uses optimistic `version`, records a revision for audit/rollback, reruns safety
checks, and emits a versioned event. Product policy can display an edited marker and
limit the edit window.

Delete transaction checks owner/moderator, changes state to `DELETED`, clears or
encrypts body according to retention, increments version, and emits a tombstone.
Children remain attached. Reads show “[deleted]” only when needed for visible replies;
otherwise omit the node. Moderation decisions are versioned, audited, appealable,
and immediately enforced from the policy store while cache/search/feed cleanup is
asynchronous.

## 12. Hot-thread protection

- Partition/salt event consumers and vote-counter deltas while keeping individual
  comment/vote ownership consistent.
- Cache ranked ID pages and comment hydration; use request coalescing and short
  negative caching.
- Apply per-user, IP, object, and author token buckets plus slow mode.
- Isolate extremely hot objects into dedicated partitions and fair queues.
- Shed reply previews, exact live counts, search updates, and expensive reranking
  before rejecting authoritative writes or basic chronological reads.
- Batch WebSocket/live updates; clients reconcile from cursored reads after gaps.

## 13. Consistency and rebuilding

Comment and vote commands are strongly consistent per row/entity. Counts, ranks,
notifications, and search are eventual and carry source versions/offsets. Projection
consumers ignore duplicate/older events. Rebuild into a new generation from comment
and vote tables/event log, compare counts/checksums, then swap pointers atomically.

Reconciliation samples aggregate totals, checks every visible rank entry references
a live comment, and removes orphan cache/search rows. A stale aggregate never grants
authorization or resurrects deleted content.

## 14. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client retries mutation | Idempotency key/version returns same effect |
| Outbox event duplicates | Projection source version/unique key suppresses it |
| Ranking unavailable | Serve chronological primary-index results |
| Cache fails | Read ranked store/primary rows and refill |
| Counter consumer lags | Display stale/approximate value; votes remain correct |
| Moderation classifier fails | Quarantine uncertain new content or apply documented fallback |
| Parent deleted during reply | Transaction/policy decides reject or attach to tombstone |
| Shard/region fails | Promote fenced replica; keep derived systems rebuildable |
| Rank changes during pagination | Pinned rank-version cursor preserves the page snapshot |

## 15. Security and privacy

Authorize object audience, comment ownership, votes, reports, moderation, and revision
history. Sanitize/render text safely; defend against XSS, malicious links, mention
spam, Unicode abuse, scraping, vote manipulation, brigading, and account farming.
Encrypt data, audit moderation/admin/export/delete, separate moderator roles, and
minimize bodies in logs. Apply block/mute, age/region policy, retention, erasure,
legal hold, and residency across primary data, revisions, indexes, caches, models,
events, and backups.

## 16. Observability

Measure create/edit/delete/vote/read latency and errors, idempotency conflicts,
comments/votes per object, shard skew, hot threads, event/rank/count/search lag,
cache hit/refill, candidates scanned versus displayed, cursor expiry, duplicate/missing
pages, moderation queue age/actions/appeals, report abuse, stale deleted exposure,
rebuild divergence, and rate-limit decisions.

Property tests apply duplicate/reordered vote events and compare aggregates with the
vote table. Pagination tests mutate ranks between requests and assert pinned snapshots
do not duplicate or skip candidates. Chaos tests kill write/event/rank/cache services;
privacy tests race block/delete/moderation with reads and require immediate denial.

## 17. Implementation path

1. **MVP:** transactional chronological comments/replies, max depth, ownership edits/
   tombstone deletes, cursor pagination, and basic authorization.
2. **Interactions/safety:** idempotent votes, derived counters, reports, moderation,
   outbox, revisions, rate limits, and reconciliation.
3. **Ranking/scale:** rank snapshots/cursors, ID caches, hot-thread isolation, sharded
   aggregates, live update batching, search, and rebuild tooling.
4. **Hardening:** regional failover, abuse/privacy lifecycle, load/chaos/property
   tests, restore drills, dashboards, alerts, and SLOs.

## 18. Final design

Keep comments and one vote per user/comment authoritative in a partitioned
transactional store. Everything expensive—counts, rank, search, notifications, and
caches—is a versioned rebuildable projection. Rank-version cursors stabilize pages,
while read-time policy prevents stale projections from leaking deleted or blocked
content. Idempotent commands/events, tombstones, salted aggregates, and graceful
chronological fallback provide correctness and scale even on extremely hot threads.
