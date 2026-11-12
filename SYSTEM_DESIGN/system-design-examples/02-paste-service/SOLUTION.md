# Complete Solution: Paste Service

[Problem brief](README.md) | [All examples](../README.md)

This design stores text pastes, supports public/unlisted/private visibility and
expiration, and keeps large content out of the metadata database.

## 1. Requirements

### Functional

1. Create a UTF-8 text paste with optional title, language, visibility, and expiry.
2. Read a paste by an unguessable ID.
3. Let an authenticated owner delete a paste.
4. Return raw text as well as a browser-friendly representation.
5. Make creation idempotent so client retries do not create duplicates.

### Non-functional

- Reads: 99.99% availability, p99 below 200 ms excluding client download time.
- Creates: 99.9% availability, p99 below 500 ms for ordinary text.
- A successful create must be durable across a zone failure.
- Private paste revocation must become effective within 30 seconds.
- Maximum paste size: 1 MB initially; larger files belong in a file service.

### Out of scope

Collaborative editing, executable code, arbitrary binary uploads, full-text public
search, and permanent archival guarantees.

## 2. Capacity estimation

Assume 10 million new pastes/month, 20 reads per paste, 20 KB average body, 10x
peak traffic, and three object replicas or equivalent durability.

```text
creates/second average = 10,000,000 / (30 * 86,400) ~= 3.9
creates/second peak    ~= 40
reads/second average   ~= 77
reads/second peak      ~= 770

body storage/month     = 10,000,000 * 20 KB        = 200 GB
body storage/year      = 200 GB * 12                = 2.4 TB raw
```

Metadata is small; bodies dominate storage. Object storage is cheaper, durable,
and naturally supports lifecycle expiration. PostgreSQL is sufficient for
metadata at this scale and gives useful transactional/idempotency guarantees.

## 3. API contract

### Create

```http
POST /v1/pastes
Authorization: Bearer <token>        # optional for unowned public/unlisted paste
Idempotency-Key: e67f...
Content-Type: application/json

{
  "content": "SELECT * FROM orders WHERE id = $1;",
  "title": "Example query",
  "language": "sql",
  "visibility": "UNLISTED",
  "expires_in_seconds": 86400
}
```

```http
HTTP/1.1 201 Created
Location: /v1/pastes/7Qm2xL9pV4k

{
  "id": "7Qm2xL9pV4k",
  "url": "https://paste.example/7Qm2xL9pV4k",
  "expires_at": "2026-08-25T12:00:00Z",
  "version": 1
}
```

### Read

```http
GET /v1/pastes/7Qm2xL9pV4k
Accept: application/json
```

Raw clients use `Accept: text/plain`. Private reads require authentication and
return `404`, rather than revealing existence, when the caller is unauthorized.

### Delete

```http
DELETE /v1/pastes/7Qm2xL9pV4k
Authorization: Bearer <token>
If-Match: "1"
```

Deletion is idempotent and returns `204` after metadata becomes unreadable. Blob
removal may complete asynchronously.

## 4. Data model

```text
Paste
  id                 string primary key
  owner_id           string | null
  object_key         string
  content_hash       bytes
  size_bytes         integer
  title              string | null
  language           string | null
  visibility         PUBLIC | UNLISTED | PRIVATE
  status             PENDING | ACTIVE | DELETED | BLOCKED
  created_at         timestamp
  expires_at         timestamp | null
  version            integer
```

```text
IdempotencyRecord
  actor_scope + key  primary key
  request_hash
  paste_id
  response
  expires_at
```

Store bodies at immutable keys such as `pastes/{id}/v1/body.txt`. Never overwrite
an object in place; immutable keys make caches, checksums, and recovery simpler.

## 5. Architecture

```text
client -> edge/WAF -> paste API -> PostgreSQL metadata
                              |-> private object storage
                              |-> Redis metadata cache
                              +-> scan/moderation queue -> workers

public read -> CDN -> read API/origin -> object storage
private read --------> read API ------> signed object read or streamed body

expiry/deletion queue -> lifecycle worker -> metadata tombstone + object removal
```

- The API owns metadata and authorization.
- Object storage is the durable body store.
- Redis caches only metadata/authorization-safe results.
- CDN may cache only public immutable bodies.
- Scanning/moderation is asynchronous, but a paste remains `PENDING` until the
  required checks complete.

## 6. Create flow

1. Edge applies request-size and creation-rate limits.
2. API authenticates the optional owner and validates UTF-8, size, visibility,
   language identifier, and allowed expiry range.
3. API checks the idempotency key and returns the saved response on a matching
   retry.
4. It generates an 11-character random Base62 paste ID.
5. It writes a `PENDING` metadata row using a unique conditional insert.
6. It writes the body to its immutable private object key with checksum metadata.
7. It publishes a scan task through a transactional outbox.
8. Worker verifies checksum, scans policy/malware rules, and changes status to
   `ACTIVE` or `BLOCKED` using a versioned conditional update.
9. For small trusted text, the product may perform validation inline and activate
   before returning. Otherwise create returns `202 Processing` and a status URL.

## 7. Read flow

1. Validate ID format before any database work.
2. Read metadata from Redis, falling back to PostgreSQL.
3. Treat missing, deleted, blocked, or expired records as unavailable.
4. For `PRIVATE`, authenticate and verify owner/ACL. `UNLISTED` is accessible to
   anyone possessing the unguessable ID; it is not indexed or listed.
5. Fetch body by immutable `object_key` and verify the stored size/checksum when
   corruption is suspected.
6. Public content may redirect to a CDN URL. Private content is streamed by the
   API or served using a signed URL lasting only a few minutes.
7. Record view analytics asynchronously; it cannot block the read.

## 8. Delete and expiry flow

1. Authenticate owner/admin and conditionally update status to `DELETED`.
2. Commit an outbox event in the same metadata transaction.
3. Invalidate Redis and purge public CDN keys.
4. Reads reject the paste immediately from metadata even if the blob still exists.
5. Worker deletes the object after a short retention window and records outcome.
6. Reconciliation repeatedly finds deleted metadata with surviving objects and
   unreferenced objects without valid metadata.

Expiry uses the same path. Every read checks `expires_at`, so delayed cleanup does
not expose expired content.

## 9. Core application logic

### Idempotent creation

```text
function createPaste(actor, request, idempotencyKey):
    validated = validate(request, maxBytes = 1 MB)
    scope = actor.id if actor exists else hash(clientFingerprint())
    requestHash = sha256(canonicalJson(validated))

    old = idempotencyStore.get(scope, idempotencyKey)
    if old exists:
        require old.requestHash == requestHash else Conflict
        return old.response

    repeat up to 5 times:
        id = base62(secureRandomUnsigned64()).padLeft(11, "0")
        objectKey = "pastes/" + id + "/v1/body.txt"

        inserted = metadata.conditionalInsert(Paste(
            id=id, objectKey=objectKey, status=PENDING,
            owner=actor?.id, visibility=validated.visibility,
            expiresAt=validated.expiresAt, version=1
        ))
        if not inserted:
            continue

        try:
            objectStore.put(
                key=objectKey,
                body=validated.content,
                checksum=sha256(validated.content),
                contentType="text/plain; charset=utf-8"
            )
            metadata.transaction:
                outbox.insert(ScanRequested(id, objectKey))
                idempotencyStore.insert(scope, idempotencyKey, requestHash, id)
            return Accepted(id)
        catch error:
            metadata.markUploadFailed(id)
            enqueueOrphanCheck(objectKey)
            raise

    raise TemporarilyUnavailable("ID allocation failed")
```

A relational implementation can reserve metadata and outbox atomically, but the
object write cannot join that transaction. The explicit states and reconciler are
therefore required; pretending the two systems form one transaction creates leaks.

### Safe read

```text
function readPaste(id, actor, now):
    if not validId(id): return NotFound

    paste = metadataCache.get(id)
    if paste missing:
        paste = metadata.get(id)
        if paste missing:
            metadataCache.setNegative(id, ttl=15 seconds)
            return NotFound
        metadataCache.set(id, paste, ttl=min(10 minutes, timeToExpiry(paste)))

    if paste.status != ACTIVE: return NotFound
    if paste.expiresAt exists and now >= paste.expiresAt: return NotFound
    if paste.visibility == PRIVATE and paste.ownerId != actor?.id: return NotFound

    if paste.visibility == PUBLIC:
        return RedirectToCDN(versionedPublicUrl(paste.objectKey))

    body = objectStore.get(paste.objectKey)
    if sha256(body) != paste.contentHash:
        alertCorruption(id)
        return TemporarilyUnavailable
    return Text(body)
```

### Scan worker

```text
function handleScanRequested(event):
    paste = metadata.get(event.pasteId)
    if paste missing or paste.status != PENDING: return

    body = objectStore.get(event.objectKey)
    verdict = scanner.inspect(body)
    nextStatus = ACTIVE if verdict.allowed else BLOCKED

    metadata.compareAndSet(
        id=paste.id,
        expectedVersion=paste.version,
        values={status: nextStatus, contentHash: sha256(body),
                sizeBytes: length(body), version: paste.version + 1}
    )
    metadataCache.delete(paste.id)
```

Workers are at-least-once. Checking current state and using compare-and-set makes
duplicate delivery harmless.

### Reconciliation

```text
function reconcilePending(cutoff):
    for paste in metadata.find(status=PENDING, createdBefore=cutoff):
        if objectStore.exists(paste.objectKey):
            outbox.ensureScanRequested(paste.id, paste.objectKey)
        else:
            metadata.compareAndSetStatus(paste.id, PENDING, DELETED)

function reconcileDeleted():
    for paste in metadata.find(status in [DELETED, BLOCKED], olderThan=retention):
        objectStore.delete(paste.objectKey)   // idempotent
```

## 10. Consistency and caching

- PostgreSQL metadata is authoritative for visibility and status.
- Object keys are immutable; content never changes under a cached URL.
- Cache values carry metadata version. Deletes invalidate, while TTL bounds missed
  invalidations.
- Never put private content behind a shared public CDN cache key.
- Public CDN URLs include object version and may have long TTLs; deletion requires
  purge plus origin authorization/tombstone defense.
- Creation becomes readable only after the state reaches `ACTIVE`.

## 11. Security and abuse prevention

- Strict 1 MB limit, UTF-8 validation, request timeouts, and decompression limits.
- Render text escaped; syntax highlighting must never interpret HTML/script.
- Scan links/content for malware, phishing, secrets, and prohibited material.
- Use cryptographically random IDs to make unlisted pastes difficult to enumerate.
- Encrypt objects and database at rest; use short-lived credentials and signed URLs.
- Log paste IDs and decisions, not raw private content.
- Apply owner/IP creation limits and a takedown/audit process.
- Object storage bucket remains private; CDN origin access is restricted.

## 12. Failure handling

| Failure | User behavior | Recovery |
| --- | --- | --- |
| Metadata DB unavailable | Reads may serve only safe cached public data; creates fail | Fail over database and verify replication |
| Object write fails | Paste remains `PENDING`/becomes failed; no broken active paste | Retry or mark deleted; reconciler cleans metadata |
| Metadata commit fails after object write | Create fails safely | Orphan scanner deletes unreferenced object |
| Scan queue/worker fails | Paste remains processing, not public | Replay outbox and scale workers |
| Redis fails | Read metadata from database under rate limits | Replace/warm cache from traffic |
| CDN purge fails | Origin/tombstone still denies; edge may be stale until bound | Retry purge and alert on revocation SLO |
| Expiry worker delayed | Reads still reject by timestamp | Catch up lifecycle asynchronously |
| One viral public paste | CDN absorbs body traffic | Origin shield, per-key request coalescing, abuse limits |

## 13. Observability

Measure create/read/delete latency and errors, pending age, scan verdicts and queue
lag, cache/CDN hit ratios, database/object-store latency, orphan count, lifecycle
backlog, bytes stored, signed-URL issuance, unauthorized reads, and revocation time.

Run a synthetic journey that creates a paste, waits for activation, reads it as the
right and wrong user, deletes it, and verifies global unavailability.

## 14. Implementation plan

1. **MVP:** one region, PostgreSQL, private object storage, create/read/delete,
   random IDs, escaped rendering, and metadata-based expiry.
2. **Safety:** idempotency, explicit upload states, transactional outbox, scanning,
   deletion workflow, orphan reconciliation, and audit.
3. **Read scaling:** Redis metadata cache, CDN for public content, immutable
   versioned keys, negative caching, and request coalescing.
4. **Resilience:** multi-zone database/object storage, tested restore, regional read
   replicas, purge monitoring, and disaster-recovery exercises.

## 15. Final choices

| Concern | Choice | Reason |
| --- | --- | --- |
| Body storage | Object storage | Cheap, durable, lifecycle-aware large-value storage |
| Metadata | PostgreSQL initially | Transactions, uniqueness, idempotency, operational simplicity |
| ID | Random 64-bit Base62 | Unguessable, decentralized, evenly distributed |
| Publish state | `PENDING` then `ACTIVE` | Never expose an incomplete or unscanned body |
| Public delivery | Versioned CDN URL | Efficient viral reads with immutable caching |
| Private delivery | Authorized API or short signed URL | Prevent shared-cache information leaks |
| Cross-store correctness | Explicit states, outbox, reconciliation | Object storage and SQL cannot share a transaction |

The central invariant is simple: a paste is readable only when authoritative
metadata is `ACTIVE`, unexpired, and authorized, and that metadata points to a
complete immutable object. Every workflow and repair job preserves that invariant.
