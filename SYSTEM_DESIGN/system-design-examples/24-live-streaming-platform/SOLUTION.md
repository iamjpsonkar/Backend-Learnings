# Complete Solution: Live-Streaming Platform

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Creators schedule/start/end streams and publish audio/video. Viewers discover,
authorize, and watch an adaptive low-latency stream, optionally chat, and later view
an archive. The system reports approximate concurrent viewers and supports content
moderation, recording, and regional failover.

Targets: 99.99% playback availability for active streams, glass-to-glass latency
below five seconds for standard low-latency mode, playback start p95 below two
seconds on warm edges, segment-gap rate below 0.01%, and ingest failover within five
seconds. Chat/count/archive are isolated and may degrade without stopping media.

## 2. Capacity estimation

Assume one million registered broadcasters, 100,000 concurrent live channels, 50
million peak viewers, 3 Mbps average selected bitrate, six rendition ladder, and
two-second segments split into 500 ms CMAF parts.

- Edge egress is about 150 Tbps; multi-CDN capacity and cache locality dominate.
- At 50 million viewers and two-second segments, naive segment traffic is 25 million
  requests/s, handled at CDN edges; part requests can be higher.
- If each source averages 6 Mbps, ingest is 600 Gbps for 100,000 channels, doubled
  only if simultaneously sending to redundant sites.
- Transcoding cost scales with channels/renditions, not viewers; reserve GPU/CPU by
  source resolution and codec cost.
- Ten chat messages/viewer/hour at peak is about 139,000 messages/s, on a separate
  system.

## 3. APIs and protocols

```text
POST /v1/streams                         Idempotency-Key
POST /v1/streams/{id}/publish-token      {protocol, region}
POST /v1/streams/{id}/start              If-Match: version
POST /v1/streams/{id}/end                If-Match: version
GET  /v1/streams/{id}
POST /v1/streams/{id}/playback-session   {device, capabilities}
GET  /v1/streams/{id}/viewer-count
GET  /v1/streams/{id}/chat?cursor=
POST /v1/streams/{id}/chat               {clientMessageId, body}
```

Broadcasters use RTMP/SRT/WebRTC ingest depending latency/reliability needs. Viewers
use low-latency HLS/DASH over HTTPS for massive fan-out; interactive sub-second use
cases require a different WebRTC SFU design.

## 4. Data model and stream state

```text
Stream(id, creator_id, state, visibility, home_region, generation,
       active_epoch, started_at, ended_at, version, archive_video_id)
IngestSession(id, stream_id, epoch, region, node, state, last_media_at)
Rendition(stream_id, epoch, name, codec, bitrate, width, state)
Segment(stream_id, epoch, rendition, media_sequence, part_sequence,
        start_pts, duration, object_key, checksum, state)
Manifest(stream_id, epoch, rendition, latest_sequence, generation, object_key)
PlaybackSession(id, viewer_id, stream_id, entitlement_version, expires_at)
ArchiveJob(stream_id, epoch, state, last_sequence, output_ref)
Outbox(id, aggregate_id, event_type, payload, published_at)
```

```text
SCHEDULED -> STARTING -> LIVE -> ENDING -> ENDED -> ARCHIVED
                        \-> INTERRUPTED -> LIVE (new epoch)
```

`epoch` is a fencing token assigned to the active ingest pipeline. Only the current
epoch may publish manifest progress, so a recovered old pipeline cannot overwrite a
new one.

## 5. Architecture

```text
broadcaster -> geo ingest A/B -> media bus -> real-time transcoders
                                              |
                                       CMAF packagers -> regional origin
                                                              |
                                                        origin shields
                                                              |
viewer -> playback auth -> manifest edge -> multi-CDN --------+

segment log/object events -> archive assembler -> VOD pipeline
chat service and viewer-count pipeline remain independent
control plane -> stream metadata/leases/health/failover coordinator
```

The media data plane uses preallocated regional capacity and avoids synchronous
control-database calls per frame. Control leases decide ownership; sequence/epoch
metadata travels with every media fragment.

## 6. Step-by-step workflow

1. Creator creates stream and receives short-lived, single-stream publish tokens
   plus primary/backup regional ingest endpoints.
2. Ingest authenticates token, validates stream state, acquires the active epoch,
   buffers a small GOP window, and forwards timestamped source media.
3. Transcoders decode once and produce aligned rendition layers with common keyframe
   boundaries. Audio can be encoded separately and reused.
4. Packagers turn each layer into numbered CMAF parts/segments, store immutable
   objects, and conditionally advance epoch manifests.
5. Playback API checks stream visibility/entitlement and returns a short-lived signed
   master manifest. Player repeatedly reloads media playlists/parts through CDN and
   selects bitrate based on throughput and buffer.
6. Segment events feed an archive assembler and moderation sampling. Chat and counts
   run independently.
7. End seals the current epoch after a grace period, writes end markers, finalizes
   archive, and moves metadata from LIVE to ENDED/ARCHIVED.

## 7. Core ingest ownership and failover logic

```text
function activateIngest(streamId, node, region):
    transaction:
        stream = streams.getForUpdate(streamId)
        require stream.state in [STARTING, LIVE, INTERRUPTED]
        require publishLeaseExpired(stream) or stream.activeNode == node
        newEpoch = stream.activeEpoch + 1
        stream.activeEpoch = newEpoch
        stream.activeNode = node
        stream.leaseUntil = now + 5s
        stream.state = LIVE
        ingestSessions.insert(streamId, newEpoch, node, region, ACTIVE)
    return newEpoch

function acceptMedia(streamId, epoch, frame):
    current = epochCache.get(streamId)
    if epoch != current: rejectFencedPublisher()
    require timestampsSane(frame) and withinBitrateLimits(frame)
    mediaBus.append(streamId, epoch, frame)
    renewLeaseConditionally(streamId, epoch)
```

The coordinator promotes backup only after lease expiry or explicit health failure.
On promotion it increments epoch and starts from the latest viable keyframe. A
discontinuity marker tells players that timestamps/codec state may reset; duplicated
old-epoch segments cannot advance the current manifest.

## 8. Segment and manifest publication

```text
function publishPart(part):
    require part.epoch == streams.currentEpoch(part.streamId)
    key = immutableKey(part.streamId, part.epoch, part.rendition,
                       part.mediaSequence, part.partSequence, checksum(part.bytes))
    origin.putIfAbsent(key, part.bytes, checksum(part.bytes))

    transaction:
        manifest = manifests.getForUpdate(part.streamId, part.rendition)
        require manifest.epoch <= part.epoch
        if manifest.epoch < part.epoch:
            manifest.resetForEpoch(part.epoch, discontinuity=true)
        require part.sequence == manifest.nextExpectedPart
        segments.insertUnique(part.metadata(key))
        manifest.append(part.reference)
        manifest.generation += 1
    manifestCache.publishIfNewer(manifest)
```

Objects are visible before being referenced. The playlist pointer advances only
after durable object upload, avoiding manifests that point to missing bytes. A gap
holds publication briefly for late parts, then emits a discontinuity rather than
stalling forever.

## 9. Low-latency delivery and player behavior

Use two-to-six-second segments made of smaller CMAF chunks. The CDN supports chunked
transfer, blocking playlist reload, request coalescing, and short manifest caching;
immutable media parts use long TTLs. Regional shields absorb channel fan-out and
protect origins from synchronized playlist/part misses.

```text
onPlaybackTick():
    liveEdge = manifest.latestPartTime
    latency = liveEdge - player.playhead
    if buffer < emergencyBuffer: choose lower rendition immediately
    else choose highest rendition below 0.75 * estimatedThroughput

    if latency > target + tolerance and bufferHealthy:
        playbackRate = 1.03
    else playbackRate = 1.0
    if latency is far behind: seek to a safe independent part near live edge
```

Shorter parts lower latency but increase request/manifest/encoding overhead and
leave less recovery buffer. Maintain standard-latency fallback for weak devices or
networks.

## 10. Transcoding and capacity allocation

Reserve encoder slots when a scheduled stream approaches start; admission control
may restrict maximum resolution/renditions when a region is saturated. Use source
quality and viewer/device distribution to choose the ladder. Keyframes are forced on
aligned boundaries so all rendition switches are valid.

If one optional rendition fails, remove it from the next master-manifest generation;
if the baseline rendition fails, restart that pipeline from the retained source GOP
or fail over the full pipeline. Do not let a 4K encoder failure stop 360p playback.

## 11. Multi-CDN and hot-event handling

- Route playback sessions by region, ISP, measured QoE, CDN capacity, and cost;
  return backup base URLs for player retry.
- Pre-warm manifests and first segments for scheduled high-profile events.
- Use hierarchical origin shields, cache-key normalization, and collapsed forwarding
  so millions of viewers create one origin fill per object/region.
- Replicate live parts to multiple origins when the event risk justifies the cost.
- Shed expensive telemetry, thumbnails, and chat before media; never redirect more
  traffic into an already saturated alternate CDN.

## 12. Chat and viewer counts

Chat is a separate WebSocket service partitioned by channel, with per-user/channel
rate limits, moderation, slow mode, and replayable sequence log. Chat loss or lag
must not affect stream manifests.

Playback edges/session gateways emit sampled join/heartbeat/leave events. Stream
processors maintain expiring session sketches/counts and aggregate per region; do
not update one SQL row per viewer. Counts are approximate, monotonicity is not
guaranteed, and bots/duplicate sessions are filtered asynchronously.

## 13. Archiving

Archive workers consume the durable segment index, track highest contiguous sequence
per epoch/rendition, and compose a VOD timeline including discontinuities. Missing
segments are retried from origin/replicas and recorded explicitly if unrecoverable.
After stream end and grace period, finalize checksums, captions/thumbnails, then send
the output through the ordinary VOD publish/moderation workflow. Live retention can
expire only after archive verification or policy deadline.

## 14. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Broadcaster disconnects briefly | Retain session/grace buffer; resume same or new epoch |
| Primary ingest fails | Fence it, promote backup, increment epoch, emit discontinuity |
| Transcoder dies | Restart from retained GOP; keep independent renditions live |
| Packager dies after object put | Retry sees immutable object and conditionally advances manifest |
| Segment is missing | Brief reorder wait, then discontinuity; never reference absent object |
| Origin/shield fails | Alternate origin/CDN; cached immutable parts continue |
| Control database fails | Existing epoch runs on leases/cache; reject unsafe new ownership |
| Chat/count service fails | Media playback remains unaffected |
| Archive falls behind | Retain segment log/objects, scale workers, reconcile sequence gaps |

## 15. Security and privacy

Use short publish tokens bound to creator/stream/protocol/region and rotate leaked
keys. Validate bitrates, codecs, timestamps, frame sizes, and parser inputs; sandbox
media processing. Playback tokens are short, path-scoped, and edge-verified; premium
content uses DRM/concurrency policy. Encrypt transport/storage, protect signing/DRM
keys in KMS/HSM, moderate media/chat, audit publish/access/admin/delete, and enforce
geo/age/copyright, retention, deletion, legal hold, and residency rules.

## 16. Observability

Measure glass-to-glass latency by embedded timestamps, ingest RTT/loss/bitrate,
active lease/epoch changes, dropped frames, encoder real-time factor, keyframe
alignment, part/segment production lateness and gaps, manifest age, origin/shield/CDN
hit and error rate, playback start/rebuffer/bitrate/live-edge distance, failover time,
chat lag, viewer-count freshness, and archive completeness/cost.

Synthetic broadcasters/viewers run in every region. Load-test instant audience
surges and scheduled events. Chaos tests kill ingest, rendition, packager, shield,
CDN, and coordinator at frame/part boundaries. Reconciliation proves current
manifests reference existing checksummed objects and archive sequence coverage is
complete or explicitly marked.

## 17. Implementation path

1. **MVP:** one-region RTMP ingest, baseline transcoder, HLS segments, one origin/CDN,
   signed playback, stream state, and basic archive.
2. **Reliability:** redundant ingest epochs, leases/fencing, immutable CMAF parts,
   packager recovery, origin shield, telemetry, and reconciliation.
3. **Low-latency scale:** aligned ladder, LL-HLS/DASH, multi-CDN, hot-event prewarm,
   independent chat/counts, adaptive capacity, and VOD archive handoff.
4. **Hardening:** global failover, DRM/moderation/privacy lifecycle, load/chaos/QoE
   testing, restore drills, and event-level SLO/runbooks.

## 18. Final design

Use redundant authenticated ingest and a fenced stream epoch to guarantee only one
pipeline advances live state. Real-time transcoders create aligned layers; packagers
publish immutable parts before atomically advancing manifests. Shields and multi-CDN
provide massive fan-out, while the player controls bitrate and live-edge latency.
Media, chat, counts, and archive have independent failure domains. Epoch fencing and
discontinuities make failover recoverable without allowing a stale pipeline to
corrupt the live timeline.
