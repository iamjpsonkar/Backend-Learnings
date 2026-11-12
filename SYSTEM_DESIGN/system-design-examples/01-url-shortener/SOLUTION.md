# Complete Solution: URL Shortener

[Problem brief](README.md) | [All examples](../README.md)

This chapter designs a production URL-shortening service from requirements to
operation. Numbers are explicit assumptions, not universal constants; changing
them should change the capacity plan, not the correctness model.

## 1. Requirements

### Functional requirements

1. Create a short URL for a valid HTTP or HTTPS destination.
2. Redirect a short alias to its destination.
3. Support optional custom aliases and expiration.
4. Let an authenticated owner disable a link.
5. Make repeated create requests safe through an idempotency key.

### Non-functional requirements

- Redirect availability: 99.99% monthly.
- Redirect latency: p50 below 20 ms and p99 below 100 ms inside a region.
- Creation availability: 99.9%; creation can be slower than redirect.
- A successful create must not disappear after an acknowledged write.
- A disabled or expired link must stop redirecting within 60 seconds globally.
- The redirect path must remain usable when cache nodes fail.

### Out of scope for the first version

- A full analytics dashboard, advertisements, QR codes, and link previews.
- Arbitrary non-HTTP protocols.
- Guaranteed immediate global deletion; the stated bound is 60 seconds.

## 2. Capacity estimation

Assume:

- 100 million new links per month.
- 100 redirects for every link creation.
- 1 KB per stored link including metadata and index overhead.
- 10x peak-to-average traffic ratio.
- Three database replicas.

Calculations:

```text
writes/second average = 100,000,000 / (30 * 86,400) = 38.6
writes/second peak    = 38.6 * 10                 ~= 400

reads/second average  = 38.6 * 100               ~= 3,900
reads/second peak     = 3,900 * 10               ~= 39,000

new records/year      = 100,000,000 * 12          = 1.2 billion
raw storage/year      = 1.2 billion * 1 KB         = 1.2 TB
replicated storage    = 1.2 TB * 3                 = 3.6 TB/year
```

The traffic is read-heavy and small enough to begin with a managed database, but
the alias lookup access pattern makes a partitioned key-value store a natural
long-term source of truth. Bandwidth is modest compared with media systems; tail
latency and hot aliases are the important concerns.

## 3. API contract

### Create a link

```http
POST /v1/links
Authorization: Bearer <token>
Idempotency-Key: 972f3c22-...
Content-Type: application/json

{
  "destination": "https://example.com/articles/system-design?ref=course",
  "custom_alias": null,
  "expires_at": "2027-01-01T00:00:00Z"
}
```

```http
HTTP/1.1 201 Created
Location: /v1/links/aZ91KlmP2Qx

{
  "alias": "aZ91KlmP2Qx",
  "short_url": "https://sho.rt/aZ91KlmP2Qx",
  "destination": "https://example.com/articles/system-design?ref=course",
  "expires_at": "2027-01-01T00:00:00Z"
}
```

- Reusing the same idempotency key and request returns the original result.
- Reusing it with different input returns `409 Conflict`.
- An unavailable custom alias also returns `409 Conflict`.
- Invalid or forbidden destinations return `422 Unprocessable Entity`.

### Redirect

```http
GET /aZ91KlmP2Qx
```

```http
HTTP/1.1 302 Found
Location: https://example.com/articles/system-design?ref=course
Cache-Control: private, no-store
```

Use `302` by default because destinations may later be disabled or edited by a
future product version. A permanent `301` can be cached beyond the service's
control and makes revocation harder.

### Disable a link

```http
DELETE /v1/links/aZ91KlmP2Qx
Authorization: Bearer <token>
If-Match: "link-version-4"
```

The operation is idempotent. It writes `DISABLED`, increments the version, emits
an invalidation event, and returns `204 No Content`.

## 4. Data model

The primary table is addressed directly by alias; no secondary lookup is needed
on the redirect path.

```text
Link
  alias             string, partition key
  destination       string
  owner_id          string | null
  status            ACTIVE | DISABLED | BLOCKED
  created_at        timestamp
  expires_at        timestamp | null
  version           integer
  destination_hash  bytes
```

```text
IdempotencyRecord
  owner_id + idempotency_key   partition key
  request_hash
  alias
  response_code
  expires_at
```

Keep click events out of `Link`. The redirect path publishes a small event to a
buffer and never synchronously increments a shared counter, which would turn a
viral alias into a write hot spot.

## 5. Alias generation

Use a random unsigned 64-bit value encoded with Base62 (`0-9A-Za-z`). Eleven
Base62 characters cover the full space. Random aliases:

- do not reveal creation volume;
- require no global sequence service;
- distribute evenly when the database partitions by alias hash.

Creation uses a conditional insert (`put if absent`). The extremely rare collision
generates another value and retries. Custom aliases use the same conditional
insert, after reserved-word and policy checks.

Seven random Base62 characters provide about 3.5 trillion combinations, but the
birthday collision probability becomes material at billion-link scale. Eleven
characters are less pretty but make collisions negligible. If product requires
shorter codes, allocate unique numeric ranges and Base62-encode counters instead.

## 6. High-level architecture

```text
                         +----------------------+
                         | Link management API  |
                         +----------+-----------+
                                    |
                                    v
client -> DNS/CDN/WAF -> load balancer -> stateless redirect service
                                            |           |
                                            v           v
                                      Redis cluster   link store
                                            |           |
                                            +-----+-----+
                                                  |
                                                  v
                                           event buffer/log
                                                  |
                                      analytics and abuse workers

control plane: authentication, policy, invalidation, monitoring
```

### Component responsibilities

- **Edge/WAF:** TLS termination, basic bot filtering, IP reputation, and coarse
  rate limits.
- **Management API:** authentication, validation, alias allocation, custom-alias
  policy, idempotency, disable operations.
- **Redirect service:** a minimal read path with no synchronous analytics call.
- **Redis:** cache of active mappings and short-lived negative results.
- **Link store:** durable, replicated source of truth partitioned by alias hash.
- **Event log:** click, invalidation, abuse, and audit events processed outside the
  redirect response.

## 7. Step-by-step create flow

1. Edge authenticates the management request and applies tenant/IP limits.
2. API validates URL length, `http`/`https` scheme, expiry bounds, and blocked
   destinations. It does not fetch the destination synchronously.
3. API hashes the canonical request body and looks up the idempotency record.
4. For a generated alias, it creates an 11-character Base62 value. For a custom
   alias, it checks syntax, reserved words, and ownership policy.
5. API performs a conditional insert into the link store. A random collision
   retries; a custom collision returns `409`.
6. API stores the idempotency result. In a relational first version this can share
   the link transaction; in a key-value version use a small workflow plus repair.
7. The durable record is now authoritative. Cache population is best-effort and
   must never decide whether creation succeeded.
8. API returns `201` with the chosen alias.

## 8. Step-by-step redirect flow

1. Edge validates alias shape and blocks obvious abuse before application work.
2. Redirect service checks Redis using `link:{alias}`.
3. A positive hit contains destination, status, expiry, and version. The service
   verifies state and time before returning a redirect.
4. A miss reads the link store with a consistent single-key lookup.
5. Missing aliases receive a negative-cache entry for roughly 10-30 seconds. This
   protects the database from repeated scans without delaying newly created links
   for long.
6. Active mappings enter Redis with a TTL (for example 15 minutes) plus random
   jitter so many entries do not expire simultaneously.
7. Service returns `302` and non-blockingly emits a click event. If the event
   buffer is unavailable, the redirect still succeeds and a metric counts loss.

Popular aliases are hot keys. Redis replicas can serve reads, and the service can
keep a very small in-process cache for the hottest immutable version. Request
coalescing ensures that one expired hot key causes one database read rather than
thousands.

## 9. Disable and expiration flow

1. Management API authenticates owner/admin and compares `If-Match` version.
2. It conditionally changes `ACTIVE` to `DISABLED` in the source of truth.
3. It publishes an invalidation containing alias and new version.
4. Redirect nodes delete older cached versions. Cache TTL provides the final
   safety bound if an invalidation is missed.
5. Expiration is also checked on every redirect; correctness does not depend on a
   cleanup job running on time.
6. A lifecycle worker eventually deletes or archives expired rows according to
   retention policy.

## 10. Caching and consistency

- The database is authoritative; Redis is disposable.
- Creation is read-after-write consistent from the source of truth. A cache miss
  immediately after creation loads the newly committed row.
- Disable is eventually visible in caches, bounded by invalidation plus TTL.
- Cache values include link version so an old invalidation cannot delete a newer
  mapping accidentally.
- Do not cache an active link beyond its expiry time.
- Negative-cache TTL must remain short because a missing alias could be created.

## 11. Partitioning and multi-region design

Partition the link table by a stable hash of alias. Random aliases distribute
evenly, while a single viral link remains a read hot key handled by cache replicas.

For the first production version, use one write region and asynchronous read
replicas. Redirects are served regionally; creation routes to the write region.
On regional failover, promote one region using database fencing so two writers
cannot both claim a custom alias.

At much larger scale, generated aliases can include region bits and be created in
their local region without collision. Custom aliases still require one globally
consistent namespace or a designated home region.

## 12. Core application logic

The following pseudocode shows where correctness lives. Database operations named
`conditionalPut` and `compareAndSet` must be atomic at the storage layer.

### Alias generation

```text
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

function encodeBase62(unsignedValue):
    if unsignedValue == 0:
        return "0"

    output = ""
    while unsignedValue > 0:
        remainder = unsignedValue mod 62
        output = ALPHABET[remainder] + output
        unsignedValue = unsignedValue div 62
    return output

function generateAlias():
    // Cryptographically secure randomness prevents easy enumeration.
    random64 = secureRandomUnsigned64()
    return leftPad(encodeBase62(random64), 11, "0")
```

The padding makes aliases a consistent length. It is not required for uniqueness.
Never use a process-local pseudo-random generator with a repeated startup seed.

### Idempotent link creation

```text
function createLink(actor, request, idempotencyKey):
    require idempotencyKey is present
    normalized = validateForStorage(request.destination)
    requestHash = sha256(actor.id + canonicalJson(request))

    previous = idempotencyStore.get(actor.id, idempotencyKey)
    if previous exists:
        if previous.requestHash != requestHash:
            raise Conflict("idempotency key reused with different request")
        return previous.savedResponse

    if request.customAlias exists:
        require validCustomAlias(request.customAlias)
        require allowedCustomAlias(actor, request.customAlias)
        candidates = [request.customAlias]
    else:
        candidates = lazySequence(generateAlias)

    for alias in candidates.take(MAX_ALIAS_ATTEMPTS):
        link = Link(
            alias = alias,
            destination = normalized.originalValue,
            ownerId = actor.id,
            status = ACTIVE,
            expiresAt = validateExpiry(request.expiresAt),
            version = 1
        )

        inserted = linkStore.conditionalPut(
            key = alias,
            value = link,
            condition = "alias does not exist"
        )

        if inserted:
            response = toCreateResponse(link)
            saved = idempotencyStore.conditionalPut(
                key = (actor.id, idempotencyKey),
                value = (requestHash, response),
                condition = "key does not exist"
            )

            if not saved:
                // A concurrent identical request won. Return its response and
                // enqueue this now-unreferenced alias for safe cleanup.
                winner = idempotencyStore.get(actor.id, idempotencyKey)
                enqueueOrphanCheck(alias)
                if winner.requestHash != requestHash:
                    raise Conflict()
                return winner.savedResponse

            cache.set(alias, link, ttlFor(link), onlyIfNewerVersion = true)
            return response

        if request.customAlias exists:
            raise Conflict("custom alias is unavailable")

    raise TemporarilyUnavailable("could not allocate alias")
```

In a relational MVP, the link and idempotency row should be inserted in one
transaction, which removes the orphan-cleanup branch. The more general workflow
above also works when they live in separately partitioned key-value tables.

### Redirect resolution

```text
function resolveRedirect(alias, now):
    if not syntacticallyValidAlias(alias):
        return NotFound

    cached = localHotCache.get(alias) or redis.get(alias)

    if cached is NEGATIVE:
        return NotFound

    if cached exists:
        return resultFromLink(cached, now)

    // Coalesce concurrent misses for this alias inside one service instance.
    return singleFlight.do(alias, function():
        cachedAgain = redis.get(alias)
        if cachedAgain exists:
            return resultFromLink(cachedAgain, now)

        link = linkStore.get(alias)
        if link does not exist:
            redis.set(alias, NEGATIVE, ttl = randomBetween(10s, 30s))
            return NotFound

        ttl = min(randomBetween(10m, 20m), durationUntil(link.expiresAt))
        if ttl > 0:
            redis.set(alias, link, ttl, onlyIfNewerVersion = true)

        return resultFromLink(link, now)
    )

function resultFromLink(link, now):
    if link.status != ACTIVE:
        return Gone
    if link.expiresAt exists and now >= link.expiresAt:
        return Gone

    clickEvents.tryPublish(
        alias = link.alias,
        occurredAt = now,
        requestId = currentRequestId()
    )
    return Redirect(status = 302, location = link.destination)
```

`tryPublish` is deliberately non-blocking. Analytics failure must not turn a
healthy redirect into a user-visible error.

### Disable and invalidate

```text
function disableLink(actor, alias, expectedVersion):
    current = linkStore.get(alias)
    if current does not exist:
        return NoContent                 // idempotent delete semantics
    require actor owns current or actor is administrator

    if current.status == DISABLED:
        return NoContent

    updated = current.copy(
        status = DISABLED,
        version = current.version + 1
    )

    changed = linkStore.compareAndSet(
        key = alias,
        expectedVersion = expectedVersion,
        newValue = updated
    )
    if not changed:
        raise PreconditionFailed("link changed; read latest version")

    // A transactional outbox is preferred when the database supports it.
    invalidationLog.publish(alias, updated.version)
    cache.deleteIfVersionOlderThan(alias, updated.version)
    return NoContent

function consumeInvalidation(event):
    cached = cache.get(event.alias)
    if cached exists and cached.version < event.version:
        cache.delete(event.alias)
    localHotCache.deleteIfVersionOlderThan(event.alias, event.version)
```

Version comparison is essential. Without it, a delayed invalidation for version 3
could incorrectly delete a freshly cached version 4.

### Expiration cleanup

```text
function expirationWorker(timeBucket):
    for link in expiryIndex.scan(timeBucket, pageSize = 1000):
        if link.expiresAt <= clock.now():
            linkStore.compareAndSetStatus(link.alias, ACTIVE, DISABLED)
            invalidationLog.publish(link.alias, link.version + 1)
            enqueuePhysicalDeletion(link.alias, after = RETENTION_WINDOW)
```

The worker saves storage but is not on the correctness path: every redirect checks
`expiresAt`. A delayed worker therefore cannot serve an expired link.

### Complexity

| Operation | Expected time | Network/storage work |
| --- | --- | --- |
| Generate alias | O(1) | Secure random generation only |
| Create link | O(1) expected | One conditional write plus idempotency write |
| Redirect, cache hit | O(1) | One local/Redis lookup |
| Redirect, cache miss | O(1) | Redis plus one primary-key database read |
| Disable | O(1) | Read, conditional write, invalidation append |
| Expiry cleanup | O(n) for expiring bucket | Paginated background scan |

## 13. Failure scenarios

| Failure | Expected behavior | Recovery |
| --- | --- | --- |
| Redis node/cluster unavailable | Redirect service falls back to link store with stricter rate limits | Replace cache nodes and warm only from real traffic |
| Cache stampede | Request coalescing permits one loader per alias | Add TTL jitter and monitor loader concurrency |
| Link-store replica fails | Client routes to healthy replica/quorum | Repair replica from peers; alert on reduced redundancy |
| Whole write region fails | Existing cached/replicated redirects continue; creation may pause briefly | Fence old primary and promote designated region |
| Event log unavailable | Redirect still succeeds; analytics may be sampled/lost | Buffer a bounded amount locally and alert |
| Invalidation missed | Old mapping can live only until bounded TTL | Replay invalidation stream and repair caches |
| Viral alias | Cache replicas/in-process hot cache absorb reads | Rate-limit abusive clients and scale edge/cache capacity |
| Bad destination discovered | Set status `BLOCKED`, invalidate, retain audit record | Abuse worker continually rescans reported domains |

## 14. Security and abuse controls

- Accept only `http` and `https`; reject credentials in URLs and dangerous
  control characters.
- Normalize for policy comparison carefully, but preserve the intended destination
  string. URL normalization can change semantics.
- Rate-limit creation more aggressively than redirects.
- Check phishing/malware blocklists asynchronously and support rapid blocking.
- Prevent open-redirect chains within the shortener by limiting nested aliases or
  detecting loops at creation.
- Encrypt storage and transport; restrict raw destination/audit access.
- Do not place full destinations containing sensitive query strings in logs.
- Protect custom aliases against impersonation, reserved words, and squatting.

## 15. Observability and SLOs

Track:

- redirect QPS, p50/p95/p99, status codes, and regional availability;
- cache hit, miss, negative-hit, eviction, and loader-coalescing rates;
- link-store latency, throttling, errors, replication lag, and hot partitions;
- create success, idempotent replay, collision, custom-conflict, and validation
  rates;
- invalidation propagation time and redirects served after disable;
- event loss/backlog, blocked destinations, abuse reports, and rate limiting.

Alert on user symptoms and SLO burn rate, not every transient node failure. A
useful synthetic probe creates a link, redirects it from several regions, disables
it, and confirms the global revocation bound.

## 16. Implementation plan

### Phase 1: correct MVP

- One region, stateless service, managed SQL table with unique alias index.
- Random Base62 aliases, create/redirect/disable APIs, authentication, validation,
  and basic metrics.
- No cache until measurements show the database read path needs it.

### Phase 2: read scaling

- Add Redis cache, negative caching, TTL jitter, and request coalescing.
- Separate management and redirect deployments so creation incidents cannot
  consume redirect capacity.
- Add replicated link store and asynchronous click-event log.

### Phase 3: regional resilience

- Regional redirect fleets and read replicas.
- Versioned invalidation events, tested regional failover, abuse automation, and
  disaster-recovery drills.
- Move from SQL to a partitioned key-value store only if measured scale or
  operational needs justify migration.

## 17. Final design decisions

| Decision | Choice | Reason |
| --- | --- | --- |
| Alias | Random 64-bit Base62 | No central allocator; even partition distribution |
| Redirect code | 302 by default | Keeps revocation and future updates under service control |
| Source of truth | Replicated key-value store | Direct single-key lookup and horizontal partitioning |
| Cache | Redis cache-aside | Low read latency without making cache authoritative |
| Analytics | Asynchronous event log | Viral links cannot create synchronous counter contention |
| Multi-region writes | Single writer initially | Simpler custom-alias uniqueness and failover correctness |
| Consistency | Strong per-alias write; bounded cache staleness | Correct creation with highly available fast redirects |

This design keeps the redirect path intentionally small: validate alias, read a
cache or one durable key, verify state/expiry, and return. Everything that does not
need to block the user—analytics, scanning, cleanup, and reporting—runs outside
that path.
