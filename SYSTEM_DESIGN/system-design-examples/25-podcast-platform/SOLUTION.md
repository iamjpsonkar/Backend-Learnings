# Complete Solution: Podcast Platform

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Listeners discover/subscribe to shows, browse episodes, stream/download audio, and
resume across devices. Publishers submit RSS/Atom feeds. The platform polls feeds,
deduplicates changing entries, indexes metadata, optionally mirrors media, honors
updates/takedowns, and produces privacy-safe analytics.

Targets: catalog/search p99 below 250 ms, progress update p99 below 200 ms, 99.99%
playback-control availability, new episodes discovered within five minutes for active
feeds, and 99.9% progress convergence. Feed ingestion/search/analytics are eventually
consistent; a takedown is authoritative and prevents new playback authorization.

## 2. Capacity estimation

Assume 10 million feeds, 100 million listens/day, 50 MB average episode, 2 million
new episodes/day, five progress updates/listen, and 5x peak.

- At a six-hour average poll interval, feed fetches average 463/s; active-feed
  adaptive polling can create several thousand/s.
- Listens average 1,160/s and peak near 6,000/s; audio egress averages about 4.6
  PB/day if entire episodes are served, so CDN hit rate is essential.
- Progress writes average 5,800/s and peak near 30,000/s, reduced with client batching.
- Mirroring all new media at 50 MB adds 100 TB/day before replication; use policy,
  popularity, and rights to decide what to proxy.

## 3. APIs

```text
POST /v1/shows                         {feedUrl} Idempotency-Key
GET  /v1/shows/{id}
GET  /v1/shows/{id}/episodes?cursor=
GET  /v1/search?q=&cursor=
PUT  /v1/users/me/subscriptions/{showId}
DELETE /v1/users/me/subscriptions/{showId}
POST /v1/episodes/{id}/playback-session {device, download}
PUT  /v1/episodes/{id}/progress        {positionMs, state, clientVersion}
POST /v1/listen-events                 {sessionId, events[]}
POST /v1/publishers/{id}/claim         {verification}
```

Bound feed response bytes, redirects, entries/feed, text lengths, artwork/audio size,
search complexity, progress frequency, and telemetry batch size. Cursors are signed
ordering tuples, not offsets.

## 4. Data model

```text
Show(id, canonical_feed_url, title, owner_id, state, etag, last_modified,
     poll_interval, next_poll_at, lease_until, consecutive_failures,
     content_hash, metadata_version)
FeedAlias(url_hash, show_id)
Episode(id, show_id, publisher_guid, canonical_guid, title, published_at,
        enclosure_url, enclosure_hash, duration_ms, state, metadata_version)
Media(episode_id, generation, source_url, object_key, checksum, bytes, state)
Subscription(user_id, show_id, created_at)
Progress(user_id, episode_id, position_ms, state, logical_time,
         device_id, updated_at)
ListenEvent(session_id, sequence, user_or_anon, episode_id, type, position_ms)
PollAttempt(show_id, started_at, status, http_status, content_hash, error)
Outbox(id, aggregate_id, event_type, payload, published_at)
```

Never rely on GUID alone: publishers sometimes reuse or change it. Use show identity,
normalized GUID, enclosure URL/hash, publication time, and guarded fuzzy matching;
ambiguous matches create a new record for later reconciliation instead of merging
unrelated episodes.

## 5. Architecture

```text
poll scheduler -> due queue -> SSRF-safe fetch proxy -> raw feed store
                                      |
                                sandbox parser/deduper -> metadata DB/outbox
                                             |          |          |
                                          search    notifications  media mirror
                                                                    |
                                                           object store/CDN

clients -> catalog/playback API -> entitlement/takedown -> CDN or publisher origin
clients -> progress API / event gateway -> progress store / analytics stream
```

Partition show/episode metadata by show ID, progress by user ID, and analytics by
episode/session. Preserve raw versioned feed bodies for debugging/reparse within a
short, privacy-conscious retention window.

## 6. Step-by-step workflow

1. Scheduler claims due shows with a lease and enqueues stable poll IDs. Priority is
   based on observed publishing cadence, subscribers, recent changes, and failures.
2. Controlled fetcher performs conditional GET with `If-None-Match` and
   `If-Modified-Since`, applying SSRF, redirect, byte, timeout, and content-type rules.
3. A 304 updates scheduling only. A changed response is stored by content hash and
   parsed in a sandbox with external entities/network disabled.
4. Normalizer canonicalizes text, dates, GUIDs, URLs, namespaces, and enclosures;
   deduper conditionally upserts show/episodes and writes versioned outbox events.
5. Search/notification consumers update derived systems. Media worker optionally
   verifies and mirrors permitted enclosures into immutable storage/CDN.
6. Playback checks episode/show/takedown/rights state and returns a signed CDN URL or
   a validated publisher URL. Client sends versioned progress and batched events.

## 7. Adaptive poll scheduling logic

```text
function finishPoll(show, result):
    transaction:
        current = shows.getForUpdate(show.id)
        require current.leaseOwner == thisWorker

        if result.notModified:
            current.consecutiveFailures = 0
            interval = min(MAX_INTERVAL, current.pollInterval * 1.25)
        else if result.changed:
            current.consecutiveFailures = 0
            observed = max(MIN_INTERVAL, now - current.lastChangedAt)
            interval = clamp(0.5 * observed, MIN_INTERVAL, MAX_INTERVAL)
            current.lastChangedAt = now
        else:
            current.consecutiveFailures += 1
            interval = fullJitter(min(MAX_BACKOFF,
                BASE_BACKOFF * 2^current.consecutiveFailures))

        interval = adjustForSubscribersAndPublisherHints(interval, current)
        current.nextPollAt = now + jitter(interval, 10%)
        clearLease(current)
```

Cap per-origin concurrency and request rate so millions of feeds on one host cannot
overload it. Respect valid cache headers and `Retry-After`, but clamp publisher hints
to platform limits. Use scheduler shards by due-time bucket plus URL-host fairness.

## 8. Safe fetching and parsing

Require HTTP(S), normalize scheme/host/port, and reject credentials. Resolve through
a controlled resolver and block loopback, private, link-local, metadata, multicast,
and internal ranges for every A/AAAA result. Pin the validated IP for the connection;
revalidate each bounded redirect. Use TLS verification, decompressed-byte/time limits,
and no ambient cloud credentials.

Parse in a CPU/memory-limited process with DTD/external entity expansion disabled.
Sanitize HTML, reject dangerous schemes, normalize Unicode, and treat all feed fields
as untrusted. A malformed new version must not erase the last good catalog.

## 9. Episode identity and upsert logic

```text
function matchEpisode(showId, item):
    guidKey = normalizeGuid(item.guid)
    if guidKey and episodes.exists(showId, guidKey): return exactGuidMatch

    enclosureKey = normalizeUrl(item.enclosure.url)
    if episodes.existsByEnclosure(showId, enclosureKey): return enclosureMatch

    fingerprint = hash(normalize(item.title), roundedPublishTime(item),
                       item.enclosure.length, normalize(item.duration))
    candidates = episodes.lookupFingerprint(showId, fingerprint)
    if candidates.size == 1 and safeSimilarity(item, candidates[0]) > THRESHOLD:
        return candidates[0]
    return NEW_EPISODE

function upsertItem(show, item, pollVersion):
    episode = matchEpisode(show.id, item)
    transaction:
        if episode is new: insert with stable internal ID
        else if pollVersion > episode.metadataVersion: applyPublisherChanges()
        outbox.insertUnique(show.id, pollVersion, episode.id, changeType)
```

Internal episode ID never changes when title/audio URL changes. Keep prior enclosure
generations briefly so existing downloads do not break unexpectedly, subject to
takedown requirements.

## 10. Media mirroring and playback

Direct mode returns a validated publisher enclosure and minimizes platform storage/
rights exposure, but availability, seeking, range support, analytics, and privacy are
less controllable. Proxy mode downloads through safe egress, validates magic bytes,
duration/codec/size/checksum, optionally normalizes audio, stores immutable bytes,
and serves range requests through CDN.

Choose proxying by publisher agreement, region, popularity, reliability, and cost.
Playback authorization always checks the current show/episode state. CDN keys include
media generation; signed access expires quickly for private/paid shows. If mirroring
is incomplete, fall back to origin only when rights and safety policy permit.

## 11. Cross-device progress logic

```text
function updateProgress(user, episode, command):
    require 0 <= command.positionMs <= episode.durationMs + TOLERANCE
    incoming = (command.logicalTime, command.deviceId)
    transaction:
        row = progress.getForUpdate(user.id, episode.id)
        if command.eventId was applied: return row
        if incoming > (row.logicalTime, row.deviceId):
            if validTransition(row, command):
                row.positionMs = clamp(command.positionMs)
                row.state = deriveState(command.positionMs, command.state)
                row.logicalTime = command.logicalTime
                row.deviceId = command.deviceId
        remember command.eventId
    return row
```

Client maintains a per-device logical clock, sends on pause/background/periodically,
and retries the same event ID. Explicit rewind/restart has a new logical version and
must not be rejected merely because position is lower. Completion is a product
threshold (for example final 90 seconds), not exactly duration.

## 12. Search, subscriptions, and notifications

Search documents are rebuildable projections of show/episode versions. Index title,
publisher, description, language, category, and safe transcript where permitted;
rank by text relevance, quality/popularity, recency, and personalization. A new
episode event fans out notifications to subscribers through a rate-limited service.
Unique `(episode, user, notification_type)` prevents duplicates; publisher edits do
not resend unless policy explicitly says so.

## 13. Analytics correctness

Player batches start, first audio, progress, seek, pause, completion, download, and
error events with `(session_id, sequence)`. Gateway authenticates where available,
adds receive time, and appends to a log. Stream processing deduplicates, filters
bots/impossible playback, sessionizes, and writes aggregated daily metrics.

Advertiser/publisher metrics define what counts as a start/listen/completion and how
downloads/offline events are attributed. Late events update bounded windows. Raw IP,
device, and listening behavior follow consent, minimization, aggregation, and
retention rules; telemetry failure never blocks audio.

## 14. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Poll worker dies | Lease expires and stable poll retries |
| Publisher returns 304 | Retain catalog and extend adaptive interval |
| Feed becomes malformed | Keep last good version; store error/back off |
| Feed URL redirects permanently | Verify safe target, retain alias, update canonical conditionally |
| Parser/outbox duplicates | Version and unique keys make upsert idempotent |
| Media mirror fails | Retry; policy-controlled safe origin fallback |
| CDN fails | Alternate CDN/origin for authorized immutable media |
| Concurrent device progress | Logical-time/device tie-break converges deterministically |
| Search/analytics lag | Catalog/playback remain available; expose freshness metrics |
| Takedown arrives | Authoritative state denies access; purge cache/media asynchronously |

## 15. Security and privacy

Enforce tenant/publisher/listener roles, ownership claims, paid/private entitlements,
and takedowns. Use SSRF-controlled fetch/media egress, sandbox parsers/decoders,
sanitize descriptions, encrypt secrets/data, audit feed ownership/metadata/takedown/
admin actions, and rate-limit scraping and fraudulent analytics. Apply copyright,
consent, child safety, retention, deletion, legal hold, and residency across media,
indexes, progress, analytics, caches, raw feeds, and backups.

## 16. Observability

Track due-to-fetch/discovery lag, polls by HTTP/error class, conditional-hit rate,
per-host throttling, redirect/SSRF blocks, parse time/failures, changed/duplicate/new
episodes, stale feeds, media mirror lag/failures/bytes, CDN hit/origin/range errors,
playback start/failure, progress conflicts/staleness, search/index lag, notification
age, analytics late/duplicate/bot rate, and cost per listening hour.

Golden feeds cover namespaces, date/GUID mutations, redirects, malformed XML, huge
content, and enclosure replacement. Chaos tests kill poll/parser/mirror workers and
CDN/origin. Reconciliation compares recent raw feed versions to metadata and proves
active mirrored media exists with the recorded checksum.

## 17. Implementation path

1. **MVP:** safe conditional feed poller/parser, show/episode SQL, direct enclosure
   playback, subscriptions, basic search, and manual takedown.
2. **Reliability:** adaptive leases, raw-feed replay, robust identity/upsert, outbox,
   progress versions, notification dedupe, and reconciliation.
3. **Scale/product:** selective media mirror/CDN, sharded scheduling, host fairness,
   analytics, offline downloads, publisher claims, and ranking.
4. **Hardening:** multi-region catalog/playback, privacy/copyright lifecycle,
   adversarial parser/SSRF tests, load/chaos tests, restores, and SLOs.

## 18. Final design

Treat publisher feeds as untrusted, mutable input and internal show/episode IDs as
stable canonical state. Adaptive conditional polling, safe fetch/parse, and guarded
multi-signal deduplication make ingestion efficient without merging unrelated
episodes. Selective immutable media proxying improves playback while retaining an
explicit rights/cost trade-off. Versioned progress converges across devices, and
isolated analytics never compromises catalog or playback availability.
