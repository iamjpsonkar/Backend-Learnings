# Complete Solution: Photo-Sharing Platform

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Users upload photos, publish one or more photos as posts/albums, follow accounts,
view feeds/profiles, like/comment, and change visibility or delete content. The
platform validates media, removes unsafe metadata, produces display variants, and
serves bytes efficiently through a CDN.

Targets: upload-session creation and metadata reads p99 below 200 ms, 99% of normal
photos ready within 30 seconds, image delivery 99.99% available, and privacy/delete
changes effective at authorization immediately. Processing and feed appearance are
eventually consistent; a photo cannot be published until its required variants and
moderation state are ready.

## 2. Capacity estimation

Assume 10 million uploads/day, 5 MB average original, five generated variants whose
combined size is 2 MB, 50 photo views/upload/day, and 5x peak traffic.

- Uploads average 116/s and peak around 600/s; direct multipart upload avoids API
  bandwidth bottlenecks.
- Originals add 50 TB/day; variants add about 20 TB/day before replication.
- Views average roughly 5,800/s and can peak near 30,000/s, overwhelmingly served
  by CDN.
- Metadata at 2 KB/photo adds about 20 GB/day before indexes and replicas.

Lifecycle old originals/variants according to product and legal requirements; do
not promise unlimited retention without budgeting it.

## 3. APIs

```text
POST   /v1/photos/uploads             {size, mime, checksum, parts} Idempotency-Key
POST   /v1/photos/{id}/complete       {uploadId, parts, checksum} Idempotency-Key
GET    /v1/photos/{id}
POST   /v1/posts                      {photoIds, caption, visibility} Idempotency-Key
PATCH  /v1/posts/{id}                 If-Match: version
DELETE /v1/photos/{id}                If-Match: version
GET    /v1/users/{id}/posts?cursor=
GET    /v1/feed?cursor=&limit=
POST   /v1/photos/{id}/download-token {variant}
```

Validate declared byte size, part count, MIME allowlist, checksum algorithm, photo
count/post, caption length, visibility, cursor, and request quotas. A download
response is a short-lived authorized CDN URL or signed cookie, never a storage
credential.

## 4. Data model and states

```text
Photo(id, owner_id, upload_id, source_key, source_checksum, media_type,
      width, height, status, visibility_version, moderation_state,
      object_generation, created_at, version)
Variant(photo_id, generation, kind, width, height, format, object_key,
        checksum, bytes, status)
Post(id, owner_id, caption, visibility, state, created_at, version)
PostPhoto(post_id, position, photo_id)
Album(id, owner_id, title, visibility, version)
UploadSession(id, owner_id, expected_bytes, checksum, state, expires_at)
ProcessingJob(photo_id, generation, step, state, attempt, lease_until)
Outbox(id, aggregate_id, event_type, payload, published_at)
```

```text
UPLOADING -> UPLOADED -> SCANNING -> PROCESSING -> READY
                              \-> REJECTED
                   any nonterminal -> FAILED or DELETED
```

Keys are immutable and generation-scoped, for example
`photos/{photo_id}/{generation}/medium.webp`. Never overwrite cached bytes in place.

## 5. Architecture

```text
client -> metadata API -> SQL metadata/outbox -> processing event log
   |                                              |
   +-> signed multipart upload -> quarantine store -> scan/metadata worker
                                                      |
                                               transform workers
                                                      |
                                             immutable media store -> CDN

feed/profile API -> post store/cache -> authorization -> signed CDN delivery
```

Metadata is partitioned by owner or photo ID. Binary media bypasses application
servers. Quarantine and published media use separate buckets/credentials so
unscanned uploads cannot be delivered accidentally.

## 6. Step-by-step workflow

1. Client requests an upload session. Service checks quota, allocates photo ID and
   quarantine key, records expected size/checksum, and returns short-lived signed
   multipart URLs restricted to that exact key and size.
2. Client uploads parts directly and calls complete. Service verifies ownership,
   storage-reported size/parts/checksum, marks `UPLOADED`, and emits an outbox event.
3. Scanner verifies magic bytes/decoder limits, malware, decompression ratio, image
   dimensions, and policy. It decodes safely, normalizes orientation, strips EXIF/
   GPS, and records canonical dimensions.
4. Transform workers generate required immutable variants, upload each with a
   checksum, and conditionally mark its job complete.
5. Finalizer verifies every required variant and moderation result, transitions the
   same generation to `READY`, and emits `PhotoReady`.
6. User publishes a post referencing only owned/authorized READY photos. Post and
   outbox commit atomically; feed/search/notification projections consume the event.

## 7. Core upload finalization logic

```text
function completeUpload(actor, photoId, request):
    transaction:
        photo = photos.getForUpdate(photoId)
        session = uploads.getForUpdate(photo.uploadId)
        require session.ownerId == actor.id
        if session.state == COMPLETED: return photo.status
        require session.state == OPEN and now < session.expiresAt

        object = quarantineStore.head(session.objectKey)
        require object.bytes == session.expectedBytes
        require object.checksum == session.expectedChecksum
        require request.parts == object.completedParts

        session.state = COMPLETED
        photo.status = UPLOADED
        outbox.insert(PhotoUploaded(photo.id, photo.objectGeneration))
    return PROCESSING_ACCEPTED
```

Do not trust client MIME, dimensions, filenames, or an ETag as a cryptographic
checksum. Completion is idempotent and only the metadata transaction starts work;
storage event notifications may be duplicated or missing.

## 8. Idempotent processing pipeline

```text
function runVariantJob(photoId, generation, kind):
    job = jobs.claim(photoId, generation, kind, lease=5m)
    if job == null: return
    photo = photos.get(photoId)
    if photo.status in [DELETED, REJECTED] or
       photo.objectGeneration != generation: cancel(job); return

    decoded = safeDecode(quarantineStore.get(photo.sourceKey), LIMITS)
    pixels = normalizeOrientationAndColor(decoded)
    output = encode(resizeCrop(pixels, variantSpec(kind)))
    key = immutableVariantKey(photoId, generation, kind, output.format)
    mediaStore.putIfAbsent(key, output.bytes, checksum(output.bytes))

    transaction:
        variants.upsertCompleted(photoId, generation, kind, key, checksum)
        jobs.completeIfOwned(job)
        if allRequiredVariantsReady(photoId, generation):
            photos.markReadyIfGenerationMatches(photoId, generation)
            outbox.insert(PhotoReady(photoId, generation))
```

Workers retry transient storage/compute failures with jitter; corrupt/unsafe input
is a permanent rejection. Conditional generation checks prevent an old retry from
publishing bytes after reprocessing or deletion.

## 9. Variant strategy

Pre-generate common thumbnail, feed, profile, and full-screen sizes in modern and
fallback formats because these dominate traffic and need predictable latency. Use
an authenticated, rate-limited image proxy for rare sizes, with strict dimensions,
pixel/CPU limits and a canonical transform key. Promote popular on-demand results
to persistent variants.

Serve a manifest containing dimensions, aspect ratio, dominant color/blur hash,
variant URLs, checksums, and generation. Clients can reserve layout space and show
a safe placeholder while loading.

## 10. Publish and feed behavior

```text
function createPost(actor, command):
    transaction:
        claimIdempotency(actor, command.key)
        photos = photoStore.lock(command.photoIds)
        require all(p.ownerId == actor.id and p.status == READY for p in photos)
        post = posts.insert(actor, command.caption, command.visibility)
        postPhotos.insertOrdered(post.id, photos)
        outbox.insert(PostPublished(post.id, post.version))
    return post
```

Feed entries contain post IDs, not duplicated captions/media metadata. The read path
loads candidates, applies current post/photo/account/block/moderation policy, batch
hydrates manifests, and returns signed CDN access. A not-yet-ready, deleted, or
newly private object fails closed even if a stale feed entry exists.

## 11. CDN caching and privacy

Public immutable variants can use long cache TTLs and content-generation URLs.
Private content uses non-guessable keys plus short signed URLs/cookies and an origin
that rechecks authorization where necessary. A privacy change increments visibility
version, immediately denies new token issuance, invalidates authorization caches,
and purges CDN keys when the threat model requires already issued URLs to stop.

Short token lifetime bounds leakage; CDN purge is defense in depth, not the only
authorization mechanism. Never expose quarantine/source keys through public CDN.

## 12. Deletion and lifecycle

1. Transactionally mark photo/post deleted, increment generation/version, and emit
   tombstone events. Reads and token issuance stop immediately.
2. Consumers remove feed/search/cache references and enqueue CDN purge.
3. Storage eraser deletes every known generation/variant and quarantined original
   after retention/legal-hold checks.
4. Reconciler lists metadata-to-object and object-to-metadata discrepancies,
   retrying erasure and aging orphan uploads after session expiry.
5. Backup expiry and derived model/data deletion follow the published policy.

Keep deletion tombstones long enough that delayed processing events cannot recreate
the object.

## 13. Partitioning and overload

Partition metadata by photo/owner, jobs by photo ID, and feed projections by viewer.
Autoscale scan/transform pools independently by media type and job cost. Admission
control uses per-user byte, pixel, concurrent-upload, daily-processing, and storage
quotas. Under overload, preserve accepted-upload durability, slow new session
issuance, delay nonessential variants, and keep mandatory safe variants prioritized.

## 14. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client retries create/complete | Idempotency returns same session/state |
| Storage notification is lost | Outbox and UPLOADED-state sweeper enqueue work |
| Worker dies | Lease expires; deterministic job retries |
| Variant upload succeeds but DB fails | Retry sees immutable object/checksum and commits metadata |
| One variant fails permanently | Photo remains non-publishable or uses documented required subset |
| CDN has old public bytes | Generation changes; purge old key and deny manifests |
| Queue is unavailable | Metadata state retains recoverable work |
| Database region fails | Promote fenced replica; object bytes remain durable |
| Orphan multipart upload | Expiry job aborts it and refunds quota |

## 15. Security and privacy

Use least-privilege signed uploads bound to exact key/size/type and short expiry.
Decode in sandboxed workers without network credentials; defend against polyglots,
decompression bombs, huge dimensions, malformed codecs, malware, EXIF/GPS leakage,
and abusive transforms. Encrypt storage and transport, audit access/privacy/delete/
moderation/admin actions, rate-limit enumeration and scraping, and protect face/
location-derived data under explicit consent and retention policy.

## 16. Observability

Track upload initiation/completion/abandonment, bytes and checksum mismatches,
state-age by pipeline step, queue/oldest-job lag, scan/rejection reasons, transform
latency/CPU/failures, ready SLO, storage growth, CDN hit/origin/error rates, signed
URL failures, feed hydration omissions, purge latency, orphan count, and deletion
completion. Use photo IDs in traces, not raw image content or private URLs in logs.

Golden-image tests verify orientation, color, dimensions, animation policy, and
encoder compatibility. Fuzz hostile decoders. Chaos tests kill workers between
object upload and metadata commit. Reconciliation asserts every READY photo has all
checksummed required variants and no DELETED generation is publicly retrievable.

## 17. Implementation path

1. **MVP:** signed single-part upload, safe decode, one feed variant, SQL metadata,
   private serving, and deletion tombstone.
2. **Reliable pipeline:** multipart completion, outbox, leased jobs, required variant
   finalizer, moderation, checksums, orphan reconciliation, and CDN.
3. **Product scale:** posts/albums/feed, several formats, on-demand rare transforms,
   quotas, cache/privacy invalidation, and regional reads.
4. **Hardening:** sandbox/fuzzing, global storage policy, failover, lifecycle/privacy
   erasure, load/chaos tests, restore drills, and processing/delivery SLOs.

## 18. Final design

Upload bytes directly into quarantine, then move a versioned metadata state machine
through verification, safe decode, immutable transformation, moderation, and READY.
Only READY generations can be published. Posts reference metadata while CDN serves
immutable variant keys, keeping feeds small and caches efficient. Generation checks,
read-time authorization, tombstones, and reconciliation ensure retries cannot expose
unscanned, stale-private, or deleted media.
