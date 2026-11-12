# Complete Solution: Web Crawler

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Continuously discover and fetch permitted public web pages, respect robots and host
politeness, canonicalize/deduplicate URLs/content, detect traps, store fetch versions,
extract links, and schedule recrawls by importance and change probability. Support
removal requests and reproducible downstream parsing.

Targets: one billion successful page fetches/day, durable frontier admission,
important-page recrawl within minutes, long-tail within days/weeks, and no more than
the configured concurrency/rate for any host/site. Coverage and freshness are
eventually consistent. Politeness and network-safety rules override throughput.

## 2. Capacity estimation

Assume one billion pages/day, 100 KB average compressed response, 10 discovered links
per page, 100 billion known canonical URLs, and 3x traffic bursts.

- Fetch rate averages 11,600/s and may exceed 35,000/s; per-host delay creates many
  mostly idle independent queues.
- Ingress is about 100 TB/day before replicas and retained versions.
- Ten billion raw discovered links/day demand streaming normalization/deduplication;
  do not insert every duplicate into a transactional database.
- At 200 bytes/URL record, 100 billion URLs require about 20 TB before indexes and
  replication.
- A 30-second average network fetch at 35,000/s needs about one million concurrent
  sockets in a distributed, tightly bounded fleet.

## 3. Control interfaces

```text
POST /v1/seeds                         {urls, priority, scope} Idempotency-Key
POST /v1/recrawl                       {url, reason} Idempotency-Key
POST /v1/removals                      {urlOrPrefix, evidence} Idempotency-Key
GET  /v1/urls/{urlHash}
GET  /v1/hosts/{hostHash}/status
GET  /v1/fetches?state=&cursor=
```

These are operator/publisher-facing, not an unrestricted public fetch proxy. Bound
seed batches, scope, requested priority, query variants, redirects, response bytes,
content types, depth, and per-tenant submissions.

## 4. Data model

```text
UrlRecord(url_id, canonical_url, host_key, discovered_at, source_url_id,
          depth, priority, crawl_state, next_fetch_at, last_fetch_at,
          etag, last_modified, content_hash, change_score, failure_count,
          robots_version, fetch_version)
HostState(host_key, robots_ref, robots_version, robots_expires_at,
          crawl_delay, max_concurrency, active_leases, next_allowed_at,
          failure_score, dns_state)
FrontierEntry(host_key, priority_bucket, next_fetch_at, url_id, generation)
FetchLease(url_id, generation, worker_id, lease_until, state)
FetchResult(url_id, fetch_version, requested_url, final_url, status,
            headers_ref, body_ref, checksum, fetched_at, network_metadata)
ContentCluster(content_hash_or_simhash, canonical_doc_id, members)
RemovalRule(url_or_prefix_hash, version, reason, state)
Outbox(id, aggregate_id, event_type, payload, published_at)
```

Partition URL/frontier state by normalized site/host key to make politeness atomic.
Raw fetch bodies are immutable objects; records point to checksums and parser versions.

## 5. Architecture

```text
seeds + extracted links -> normalize/scope/trap filter -> URL dedupe -> host frontier
                                                                       |
                                     ready-host scheduler -> fetch leases
                                                                       |
                                           regional fetchers -> safe egress/DNS
                                                                       |
                                              raw object store + result log
                                                        |             |
                                               parser/link extractor  recrawl scorer
                                                        |
                                                newly discovered URLs

robots service/cache and removal policy gate scheduling and fetching
```

Use two frontier levels: durable per-host URL queues and a global/sharded ready-host
heap containing only each host's next eligible time. This prevents a large site from
dominating global scheduling and makes host limits explicit.

## 6. Step-by-step workflow

1. Normalize a seed/extracted link, enforce scheme/scope/depth/trap policy, and compute
   stable URL/host IDs. Probabilistic filter drops obvious duplicates; authoritative
   conditional insert admits unseen URLs.
2. Insert/update its per-host frontier entry with priority and next-fetch time. Ensure
   the ready-host scheduler knows the host's earliest eligible item.
3. Scheduler claims a ready host only when robots allow it, active count is below
   limit, and `next_allowed_at <= now`; it leases one/bounded URLs and advances the
   host token.
4. Fetcher resolves through safe DNS, pins an allowed IP, sends a conditional request
   with crawler identity, follows only validated redirects, and streams within limits.
5. Store response/checksum/metadata immutably and commit a versioned result. Parser
   later extracts canonical hints, visible content, metadata, and links in a sandbox.
6. Deduplicate content, emit downstream document events, normalize discovered links,
   and compute adaptive next fetch from importance/change/failure/cache hints.

## 7. URL normalization and identity

```text
function normalizeUrl(base, raw):
    parsed = resolveRelative(base, trim(raw))
    require parsed.scheme in [http, https]
    host = idnaToAscii(lowercase(parsed.host)).stripTrailingDot()
    port = dropDefaultPort(parsed.scheme, parsed.port)
    path = removeDotSegments(percentNormalize(parsed.path or "/"))
    query = normalizeQueryByPolicy(parsed.query)  // not arbitrary sorting/removal
    fragment = ""
    require withinLengthAndVariantLimits(host, path, query)
    return scheme + "://" + host + port + path + query
```

Normalization removes syntactic aliases but must not assume arbitrary query parameter
order or tracking-looking parameters are semantically irrelevant. HTTP and HTTPS may
serve different content. Publisher canonical tags and redirects are signals, not
blind commands; validate they remain permitted before clustering or transfer.

## 8. Frontier scheduling and politeness logic

```text
function leaseNext(hostKey, worker):
    transaction on host shard:
        host = hosts.getForUpdate(hostKey)
        require host.nextAllowedAt <= now
        require host.activeLeases < host.maxConcurrency
        require robotsStateAllows(host)

        entry = frontier.firstDueForHost(hostKey, now)
        if entry == null: return NONE
        url = urls.getForUpdate(entry.urlId)
        require entry.generation == url.frontierGeneration

        lease = leases.insert(url.id, entry.generation, worker, now + FETCH_TIMEOUT)
        url.crawlState = FETCHING
        host.activeLeases += 1
        host.nextAllowedAt = now + host.crawlDelayWithJitter
        readyHosts.upsert(hostKey, host.nextEligibleEntryTime())
    return lease, url
```

On completion/expiry, decrement the host lease count exactly once using lease state.
Partition scheduler ownership by host hash and fence owners with epochs. Obey the
stricter of robots crawl delay, host health adaptation, and platform minimum delay.

## 9. Robots handling

Fetch `/robots.txt` with the same SSRF/size/redirect controls, cache by host and
user-agent with HTTP freshness bounded by policy, and store the exact rules version
used for each decision. Match paths according to the supported robots standard.

If robots is temporarily unavailable, conservative policy delays new hosts and may
use a recent still-valid cached version for known hosts. A clear disallow cancels
queued URLs and prevents redirects into forbidden paths. `noindex` affects indexing,
not necessarily crawling; `nofollow` affects link scheduling according to product
policy.

## 10. SSRF-safe fetching

```text
function safeFetch(url, priorMetadata):
    for redirectCount in 0..MAX_REDIRECTS:
        answers = controlledDns.resolve(url.host)
        require everySelectedAddressIsPublic(answers)
        ip = chooseAndPin(answers)
        response = egressProxy.request(url, pinnedIp=ip,
            headers=conditionalHeaders(priorMetadata),
            connectTimeout=2s, totalTimeout=30s,
            maxCompressedBytes=MAX_BODY, maxDecodedBytes=MAX_DECODED)
        if !response.isRedirect: return response
        url = normalizeUrl(url, response.location)
        require robotsAndScopeAllow(url)
    fail TOO_MANY_REDIRECTS
```

Block loopback, RFC1918/ULA, link-local, multicast, metadata, internal service, and
platform-owned ranges for IPv4/IPv6. Revalidate every redirect and DNS resolution,
pin the connection to stop rebinding, verify TLS/SNI, and run fetchers without cloud
credentials or access to internal networks.

## 11. Fetch result and parser idempotency

```text
function commitFetch(lease, response):
    bodyKey = rawStore.putByChecksum(response.body)
    transaction:
        current = leases.getForUpdate(lease.id)
        require current.state == ACTIVE and current.worker == thisWorker
        result = results.insertUnique(lease.urlId, lease.generation,
                   response.metadata, bodyKey, checksum(response.body))
        current.state = COMPLETED
        updateUrlHttpMetadataAndVersion(result)
        decrementHostActiveLeaseOnce(current.hostKey)
        outbox.insert(FetchCompleted(result.id, result.fetchVersion))

function parseResult(result, parserVersion):
    if parseOutputs.exists(result.id, parserVersion): return
    page = sandboxParser.parse(rawStore.getVerified(result.bodyRef), LIMITS)
    persistUniqueParseOutput(result.id, parserVersion, page)
    emitDocumentAndDiscoveredLinkEvents(page)
```

If object upload succeeds but commit fails, content-addressed storage makes retry
cheap. Retaining raw bodies lets fixed parsers replay without refetching publishers.

## 12. URL and content deduplication

URL dedupe uses a sharded authoritative key/value unique index, fronted by a Bloom/
cuckoo filter to reduce lookups; false positives must still be checked when missing
important pages. Redirect and canonical relationships form guarded alias clusters.

Exact content hash catches byte/normalized-text duplicates. SimHash/MinHash finds
near duplicates; choose a canonical based on publisher hints, HTTPS, quality,
freshness, and link authority. Keep URL-level fetch metadata for recrawl and removal
even when multiple URLs share one indexed document.

## 13. Adaptive recrawl logic

```text
function nextFetch(url, result, signals):
    if result.permanentGone:
        return now + longVerificationInterval
    observedChange = result.contentHash != url.previousContentHash
    url.changeScore = ewma(url.changeScore, observedChange ? 1 : 0)

    base = interpolate(MAX_INTERVAL, MIN_INTERVAL, url.changeScore)
    base /= importanceMultiplier(signals.authority, traffic, sitemapPriority)
    if result.status in [429, 503] or result.networkFailure:
        base = max(base, exponentialHostBackoff(url.failureCount))
    if result.cacheMaxAge exists: base = max(base, bounded(result.cacheMaxAge))
    return now + jitter(clamp(base, MIN_INTERVAL, MAX_INTERVAL))
```

Allocate crawl budget by predicted information gain: likelihood of change times
importance divided by fetch cost and site constraints. Conditional GET saves bytes,
but a 304 still consumes host capacity and should inform interval adaptation.

## 14. Trap and abuse control

Detect calendars/session IDs/faceted navigation/infinite pagination, repeated path
components, query permutations, soft-404s, low unique-content ratios, redirect loops,
and hosts generating unbounded variants. Enforce per-site URL, depth, path-pattern,
query-parameter, bytes/day, and error budgets. Learn trap signatures but keep audited
allow/deny overrides for legitimate large sites.

Sandbox parsers/decompressors, cap DOM nodes, nesting, CPU, memory, decoded bytes,
links, and media. Do not execute arbitrary JavaScript in the bulk crawler; use a
small isolated rendering tier only for high-value pages with stricter budgets.

## 15. Partitioning and fairness

Hash by registrable domain/host to one logical frontier shard so politeness state has
one owner. Split overloaded host shards by moving whole hosts, not individual URLs.
The ready scheduler uses weighted fair selection among priority classes and sites;
new/high-value URLs get reserved capacity without starving recrawl or small sites.

Fetch region selection respects publisher geography, network cost, legal policy, and
host affinity. Never fetch the same host concurrently from many regions merely to
increase speed; the global host lease remains authoritative.

## 16. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Scheduler dies | Fenced replacement rebuilds ready heap from durable frontier |
| Fetcher dies | Lease expires, host count reconciles, URL retries with jitter |
| Fetch completed twice | URL generation/result unique key accepts one version |
| Parser fails | Raw page remains; retry or replay with fixed parser |
| Robots service unavailable | Use valid cache or conservatively delay |
| Host returns 429/503 | Honor bounded Retry-After and increase host backoff |
| DNS changes private | Every fetch/redirect revalidates and blocks it |
| Frontier shard fails | Promote fenced replica; no two active schedulers per host |
| Raw store is unavailable | Stop committing fetch success; backpressure new leases |

## 17. Security, privacy, and compliance

Use an identifiable user-agent and contact URL, honor robots/terms/legal constraints,
publisher removal and copyright policy. Encrypt control data, sign internal events,
restrict raw content access, audit seed/priority/override/removal/admin actions, and
avoid credentials/cookies. Treat fetched personal/malicious content as untrusted;
apply retention, deletion, legal hold, regional restrictions, malware handling, and
safe analyst tooling to raw pages, links, logs, indexes, and backups.

## 18. Observability

Track URLs known/queued/due/fetching by priority, discovery-to-fetch and recrawl age,
fetch rate/bytes/status/latency, conditional 304 rate, redirects, DNS/TLS failures,
robots cache/denials, per-host concurrency/delay/fairness, expired leases, parser lag/
errors, exact/near duplicate rate, new useful documents, trap rejections, private-IP
blocks, shard skew, raw-storage growth, and information gain per crawl byte.

Synthetic sites exercise robots changes, redirects, 304, 429, traps, DNS rebinding,
huge compression, malformed HTML, and slow bodies. Property-test normalization and
lease transitions. Chaos tests kill each scheduler/fetch/parse stage. Reconciliation
checks leases versus host counts, due URLs versus ready hosts, and committed results
versus raw checksummed objects.

## 19. Implementation path

1. **MVP:** durable URL set/priority queue, one polite fetcher pool, robots cache,
   basic normalization, raw store, parser, and extracted-link loop.
2. **Distributed correctness:** host-partitioned frontier, leases/fencing, safe egress,
   idempotent results/parser, URL/content dedupe, checkpoints, and reconciliation.
3. **Efficiency:** adaptive recrawl, conditional GET, trap detection, priority/fair
   scheduling, selective rendering, compaction, and regional fetch capacity.
4. **Hardening:** removal/compliance lifecycle, adversarial parser/network tests,
   load/chaos/restore drills, dashboards, runbooks, and freshness/politeness SLOs.

## 20. Final design

Build a durable two-level frontier: URLs are owned by per-host queues and the global
scheduler contains only hosts that may be contacted now. A fenced lease transaction
enforces delay and concurrency before safe egress fetches immutable raw content.
Versioned, replayable parsing discovers normalized links and exact/near duplicates;
adaptive information-gain scheduling controls recrawl. This design scales globally
without sacrificing robots compliance, publisher fairness, network isolation, or
recoverability.
