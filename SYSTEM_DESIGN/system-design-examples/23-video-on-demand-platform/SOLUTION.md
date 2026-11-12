# Complete Solution: Video-on-Demand Platform

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Creators resumably upload video; the platform validates, scans, transcodes, packages,
publishes, searches, authorizes, and streams it. Viewers get adaptive playback,
subtitles, resume position, and compatible formats. Owners can replace, unpublish,
or delete a video without stale workflow jobs republishing it.

Targets: metadata/playback authorization p99 below 200 ms, 99.99% playback-control
availability, median playback start below two seconds on a warm CDN, rebuffer ratio
below 1%, and 99% of one-hour uploads processed within 20 minutes. Ingest and
publishing are eventually consistent; entitlement is checked before access issuance.

## 2. Capacity estimation

Assume one million uploads/day averaging 1 GB and 30 minutes, a 2x encoded-size
ladder, 10 million peak concurrent viewers, and 3 Mbps average selected bitrate.

- Source ingress is about 1 PB/day; renditions add roughly 2 PB/day before replicas.
- Peak streaming egress is about 30 Tbps, requiring multi-CDN edge delivery.
- Ingest averages 347 hours of video/minute. If encoding costs 5x real time across
  the ladder, the fleet needs about 1,735 concurrent-equivalent encoder hours per
  minute, with substantial burst headroom.
- With four-second segments, 10 million viewers can cause 2.5 million segment
  requests/s, almost all served from CDN.
- Watch telemetry must be sampled/batched; a heartbeat every 30 seconds at peak is
  about 333,000 events/s.

## 3. APIs

```text
POST   /v1/videos/uploads                 Idempotency-Key
POST   /v1/videos/{id}/complete           Idempotency-Key
GET    /v1/videos/{id}
PATCH  /v1/videos/{id}                    If-Match: version
POST   /v1/videos/{id}/publish            If-Match: version
DELETE /v1/videos/{id}                    If-Match: version
POST   /v1/videos/{id}/playback-session   {device, capabilities}
GET    /v1/search?q=&cursor=
POST   /v1/watch-events                   {sessionId, events[]}
```

Upload creation includes declared bytes, checksum, expected duration, and content
type. Bound file/part size, duration, resolution, frame rate, tracks, codecs, search
query cost, playback-session rate, and telemetry batch size.

## 4. Data model and lifecycle

```text
Video(id, owner_id, source_key, source_checksum, status, visibility,
      generation, duration_ms, width, height, metadata_version,
      moderation_state, published_at)
UploadSession(id, video_id, expected_bytes, checksum, state, expires_at)
Workflow(video_id, generation, state, dag_version, created_at)
Task(video_id, generation, task_type, shard, state, attempt, lease_until,
     input_checksums, output_checksums)
Rendition(video_id, generation, codec, width, bitrate, segment_prefix, state)
Manifest(video_id, generation, format, object_key, checksum, state)
Subtitle(video_id, generation, language, kind, object_key, state)
PlaybackSession(id, user_id, video_id, entitlement_version, expires_at)
WatchEvent(session_id, sequence, type, position_ms, client_time)
Outbox(id, aggregate_id, event_type, payload, published_at)
```

```text
UPLOADING -> UPLOADED -> VALIDATING -> PROCESSING -> READY -> PUBLISHED
                                \-> REJECTED/FAILED
any state -> UNPUBLISHED -> DELETED
```

Every derived object key includes video generation, codec/rendition, and content
hash. Manifests are immutable; publication changes only a metadata pointer.

## 5. Architecture

```text
creator -> upload API -> signed multipart upload -> quarantine object store
                    |                                  |
                 metadata/outbox -> workflow engine -> probe/scan
                                                      -> transcode fleet
                                                      -> package/QC
                                                            |
                                                immutable origin store
                                                            |
viewer -> catalog/search -> playback API -> signed manifest -> multi-CDN -> segments
                                               |
                                         entitlement/DRM

player telemetry -> event gateway -> stream -> QoE analytics/watch history
```

Separate control plane (metadata, entitlement, workflows) from data plane (large
uploads and CDN segments). Origin shields coalesce cache misses and protect object
storage during releases or CDN failures.

## 6. Step-by-step workflow

1. Issue a short-lived multipart upload restricted to one quarantine key, expected
   size, checksum, and owner quota. Client uploads directly and can resume parts.
2. Completion verifies storage metadata/checksum and transactionally changes the
   video to `UPLOADED` plus an outbox event.
3. Workflow probes container/tracks safely, scans content, validates duration and
   decoder limits, and selects an encoding ladder based on source quality.
4. Independent transcoding tasks create audio/video shards. Packaging assembles
   aligned HLS/DASH segments, thumbnails, captions, and immutable manifests.
5. Quality control checks required renditions, A/V sync, segment decodability,
   duration, black/frozen frames, loudness, and checksums. Finalizer marks generation
   READY only when the required DAG is complete.
6. Publish transaction checks ownership/moderation/READY, points video metadata to
   the generation, and emits index/feed/cache events.
7. Playback API checks current visibility and entitlement, selects a compatible
   manifest/DRM policy, and returns short-lived signed access. Player fetches
   segments via CDN and adapts bitrate from measured throughput/buffer.

## 7. Core workflow scheduling logic

```text
function scheduleReadyTasks(videoId, generation):
    workflow = workflows.get(videoId, generation)
    if workflow.state is terminal: return

    for task in workflow.tasks:
        if task.state == PENDING and
           all(dependency.state == SUCCEEDED for dependency in task.dependencies):
            if tasks.transition(task.id, PENDING, QUEUED):
                queue.publish(task.resourceClass, task.id)

function executeTask(taskId, worker):
    task = tasks.claim(taskId, worker, lease=estimatedRuntime(taskId))
    if task == null: return
    video = videos.get(task.videoId)
    if video.generation != task.generation or video.status == DELETED:
        tasks.cancel(task); return

    output = runSandboxed(task.type, verifiedInputs(task), resourceLimits(task))
    for artifact in output:
        origin.putIfAbsent(artifact.immutableKey, artifact.bytes, artifact.checksum)
    tasks.completeConditionally(task, output.checksums)
    scheduleReadyTasks(task.videoId, task.generation)
```

Queue delivery is at least once. Conditional transitions and deterministic immutable
outputs make retries safe. A sweeper requeues expired leases and PENDING tasks whose
dependencies completed but queue notification was lost.

## 8. Adaptive encoding and packaging

Probe source resolution, frame rate, HDR/color, complexity, and codecs. Never upscale
above useful source quality. A representative ladder might include 240p through 4K,
but per-title encoding chooses bitrates from quality metrics rather than one global
number. Generate one audio track separately where packaging permits reuse.

Create aligned keyframes and equal-duration segments across all renditions so the
player can switch cleanly. HLS/DASH master manifests reference codec/device-compatible
variant playlists. Four-to-six-second segments balance request overhead, start/switch
latency, and encoding efficiency; low-latency live constraints do not apply to VOD.

## 9. Atomic finalization and publication

```text
function finalize(videoId, generation):
    transaction:
        video = videos.getForUpdate(videoId)
        require video.generation == generation
        required = requiredArtifacts(video, workflow.dagVersion)
        require every artifact is SUCCEEDED and checksumVerified
        require moderationAllows(video) and qualityControlPassed(video)
        manifests.insertImmutable(generation, builtManifestChecksums)
        video.status = READY
        outbox.insert(VideoReady(videoId, generation))

function publish(actor, videoId, expectedVersion):
    transaction:
        video = videos.getForUpdate(videoId)
        require owns(actor, video) and video.metadataVersion == expectedVersion
        require video.status == READY and moderationAllows(video)
        video.status = PUBLISHED
        video.publishedAt = now
        video.metadataVersion += 1
        outbox.insert(VideoPublished(video.id, video.generation))
```

Search/feed projections may lag, but the video read API is authoritative. Publishing
never exposes a partially written manifest because all objects are immutable and the
pointer changes only after validation.

## 10. Playback authorization and delivery

```text
function createPlaybackSession(viewer, videoId, device):
    video = videos.get(videoId)
    require video.status == PUBLISHED
    require visibilityAllows(viewer, video)
    entitlement = entitlementService.check(viewer, video)
    require entitlement.allowed
    manifest = chooseManifest(video.generation, device.capabilities)
    session = sessions.create(viewer, video, entitlement.version, ttl=10m)
    return signedCdnAccess(manifest, session, ttl=5m), drmLicenseInfo(session)
```

Use tokenized URLs/cookies validated at CDN edge, scoped to video generation/path
and short expiry. Premium content uses DRM license acquisition tied to the playback
session/device. Geo/age/concurrency/subscription checks belong in entitlement and
are rechecked on session renewal.

## 11. Player adaptive bitrate logic

```text
onSegmentDownloaded(bytes, duration, downloadTime):
    throughputEstimate = ewma(bytes * 8 / downloadTime)
    safeBandwidth = throughputEstimate * 0.75
    candidates = renditionsCompatibleWithDevice()

    if bufferSeconds < 5:
        next = highestBitrateBelow(candidates, safeBandwidth * 0.7)
    else:
        next = highestBitrateBelow(candidates, safeBandwidth)
        if next > current and bufferSeconds < 15: next = current
    request(next, nextSegmentNumber)
```

The player starts conservatively, prioritizes avoiding stalls, switches only at
aligned boundaries, and falls back quickly after throughput drops. It retries an
alternate CDN/rendition for segment errors without skipping sequence integrity.

## 12. CDN and origin strategy

Use long-lived cache headers for immutable segments/manifests and a multi-CDN router
based on geography, health, cost, and real-user QoE. Regional origin shields collapse
misses and use request coalescing. Popular releases can be pre-warmed selectively;
avoid global pre-warm waste. Signed authorization must survive cache hits at the
edge without forwarding every request to the playback API.

## 13. Watch events and resume state

Clients batch session start, first frame, rendition, pause, seek, rebuffer, progress,
error, and end events with monotonically increasing session sequence IDs. Gateway
deduplicates `(session, sequence)` and appends to a stream. A stateful consumer keeps
the highest valid progress per user/video, excluding previews, suspicious jumps, and
completed credits threshold. QoE aggregation is separate and can tolerate sampling.

Telemetry loss must never interrupt playback. Treat client timestamps as untrusted
and attach server receive time/session/device metadata.

## 14. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Upload resumes/repeats completion | Part list and idempotency return same state |
| Encoder dies | Lease expires; deterministic task retries |
| One rendition permanently fails | Retry/fallback ladder policy; never reference missing artifact |
| Queue event lost | Workflow sweeper discovers runnable task |
| Packaging/QC fails | Generation remains non-READY; previous published generation stays live |
| CDN fails | Multi-CDN reroute; origin shield protects storage |
| Entitlement dependency fails | Fail closed for protected video; documented grace token if policy allows |
| Metadata region fails | Read replica serves public metadata; fenced promotion for writes |
| Delete races old workflow | Generation/tombstone check cancels task and blocks publication |

## 15. Security and privacy

Restrict signed uploads by key/size/checksum/expiry and decode/transcode in sandboxed
workers with no broad network/storage credentials. Validate container/codec/parser
inputs, scan malware, encrypt media and queues, protect DRM keys in HSM/KMS, audit
publish/entitlement/admin/delete actions, watermark where required, and rate-limit
credential sharing/scraping. Apply copyright/moderation, retention, deletion, legal
hold, and residency policy across origins, CDN, indexes, telemetry, and backups.

## 16. Observability

Track upload success/abandonment, workflow age and critical-path duration, queued/
leased/stuck tasks, encode real-time factor and cost/minute, rejection/QC failures,
artifact checksum gaps, publish/index lag, authorization latency/denials, playback
start time, video-start failure, rebuffer ratio, bitrate, segment errors, CDN hit/
origin/multi-CDN performance, DRM failures, and watch-event lag. Break QoE down by
ISP, region, device, codec, CDN, and rendition.

Golden videos cover codecs, HDR, rotation, variable frame rate, subtitles, multiple
audio, corrupt input, and long duration. Chaos tests kill every DAG stage and CDN/
origin dependencies. Reconciliation proves each PUBLISHED generation has a valid
manifest whose referenced checksummed segments all exist.

## 17. Implementation path

1. **MVP:** resumable upload, safe probe, one rendition, immutable segments, metadata
   publish, signed HLS playback, and one CDN.
2. **Reliable adaptive VOD:** leased DAG, ladder/package/QC, sweepers, watch history,
   entitlement, outbox, search, and reconciliation.
3. **Scale:** per-title encoding, distributed resource pools, origin shields,
   multi-CDN routing, telemetry pipeline, quotas, DRM, and cost controls.
4. **Hardening:** regional failover, privacy/copyright lifecycle, sandbox fuzzing,
   load/chaos/QoE tests, restore drills, and customer-facing SLOs.

## 18. Final design

Treat each video generation as an immutable artifact graph. A recoverable, idempotent
DAG transforms a verified quarantine source into aligned checksummed renditions and
publishes only after required artifacts pass quality control. The control plane
authorizes short playback sessions; CDN and origin shields carry the data plane.
Generation fencing means retries, replacement, unpublish, and deletion cannot expose
partial or obsolete video, while adaptive bitrate logic keeps playback smooth.
