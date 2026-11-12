# Complete Solution: Search Autocomplete

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Given a short typed prefix, return up to ten safe, relevant query suggestions for
the user's locale/language. Ranking combines long-term popularity, recent trends,
freshness, quality, and bounded personalization. Results update within minutes for
trends and support rapid removal of unsafe or sensitive terms.

Targets: regional p99 below 20 ms, 99.99% availability, one million peak lookups/s,
trend freshness below five minutes, and safety removal effective globally within one
minute. Suggestions are eventually consistent and need no cross-request ordering;
the response declares the index/policy version used.

## 2. Capacity estimation

Assume one million peak requests/s, 50 locales, average prefix length eight bytes,
ten results, 20 million eligible terms/large locale, and 100-byte average response
before protocol overhead.

- Peak response bandwidth is roughly 100 MB/s before TLS/headers and replication.
- Query events can match request rate; sample/batch them and never synchronously log
  on the serving path.
- Twenty million strings at 20 bytes plus scores/top-K metadata can yield several GB
  per major locale; compact FST/trie shards and replicate hot locales in memory.
- Storing top ten IDs at every raw trie node is expensive, so path-compress, prune
  low-frequency terms, quantize scores, and share suffix/string tables.

## 3. API

```text
GET /v1/autocomplete?q=iph&locale=en-US&limit=10&context=products
```

Example response:

```json
{
  "suggestions": [
    {"text": "iphone 18", "type": "query", "score": 0.91},
    {"text": "iphone charger", "type": "query", "score": 0.84}
  ],
  "indexVersion": "en-US-20260824T1200",
  "policyVersion": 143
}
```

Normalize/validate locale, context, Unicode length, token count, and limit. Empty or
one-character prefixes may return curated/trending items or nothing to prevent broad
enumeration. Do not expose internal raw scores or user identifiers.

## 4. Data and artifacts

```text
QueryEvent(event_id, anonymous_cohort, locale, normalized_query,
           result_count_bucket, action, event_time)
TermAggregate(locale, term, long_count, recent_count, unique_user_sketch,
              quality, last_seen, safety_state)
Suppression(term_hash_or_pattern, locale, reason, policy_version, expires_at)
IndexManifest(locale, version, shard_map, checksums, normalizer_version,
              policy_version, built_at, state)
TrieNode(edge_bytes, child_offsets, top_term_ids, top_scores)
TermTable(term_id, display_text, normalized_text, type, metadata)
TrendDelta(prefix_or_term, score_delta, expires_at, version)
```

The serving artifact is immutable and rebuildable. Keep an audited emergency
denylist as a small separately distributed layer so removals do not wait for a full
index rebuild.

## 5. Architecture

```text
search clients -> regional autocomplete LB -> in-memory serving nodes
                                              |          |
                                        base FST/trie  trend delta/cache

query/action events -> privacy gate -> durable stream -> window aggregators
                                                     -> candidate/safety pipeline
                                                     -> immutable index builder
                                                     -> object store/manifest
                                                     -> regional distributors
```

Shard primarily by locale/context, then by first normalized bytes for very large
locales. Replicate common one/two-character shards widely. Each server memory-maps
an immutable artifact and atomically swaps a pointer after verification.

## 6. Step-by-step workflow

### Build

1. Collect consented search/action events with stable event IDs; privacy gate removes
   prohibited fields, rejects sensitive queries, and batches to the stream.
2. Windowed aggregators deduplicate events and calculate long-term/recent counts,
   approximate distinct users, engagement quality, and abuse signals by locale.
3. Candidate pipeline applies minimum-user/count thresholds, policy classifiers,
   publisher/editorial rules, and normalization/deduplication.
4. Builder scores terms, constructs a compact prefix structure whose nodes retain
   top candidates, writes checksummed shards, and publishes a signed manifest.
5. Regional distributor downloads to a staging path, verifies schema/checksum/policy,
   warms representative prefixes, then servers atomically activate the version.

### Lookup

1. Normalize prefix with the exact artifact normalizer and select locale/context
   shard; fall back through locale hierarchy if needed.
2. Traverse the in-memory trie/FST and retrieve over-fetched base candidates.
3. Merge a small fresh trend layer, deduplicate, and apply emergency suppression.
4. Optionally rerank with bounded user/cohort features under a strict time budget.
5. Recheck response safety, render locale-correct display strings, and return top K.

## 7. Normalization and identity

Normalization must be versioned and locale-aware: Unicode normalize, case-fold,
standardize whitespace/punctuation, optionally strip diacritics only where correct,
and tokenize using language-specific rules. Preserve a reviewed display form
separately. Do not conflate distinct scripts or meanings merely because aggressive
ASCII folding produces the same bytes.

The event pipeline and online service use the same normalizer version. During a
normalizer migration, build a new complete artifact; never query a trie with rules
different from those used to construct it.

## 8. Candidate scoring logic

```text
function scoreTerm(stats, now):
    longTerm = log1p(stats.weightedSearches30d)
    trend = log1p(stats.searches15m) - expected15m(stats.baseline)
    freshness = exp(-hours(now - stats.lastSeen) / 168)
    quality = stats.clickOrSuccessRateAdjusted
    abuse = stats.botRatio + stats.reportPenalty
    return 0.45*longTerm + 0.25*trend + 0.10*freshness
           + 0.20*quality - abuse

function eligible(stats):
    return stats.distinctUsers >= K_ANONYMITY_THRESHOLD
       and stats.totalCount >= MIN_COUNT
       and stats.safetyState == ALLOWED
       and !looksLikeSensitiveIdentifier(stats.term)
```

Use Bayesian/Wilson smoothing for quality so a term with one click does not outrank
popular terms. Clamp trend contribution to resist flash abuse. Scores and weights
are illustrative and should be trained/evaluated against offline relevance and
online safety/business metrics.

## 9. Building top-K trie nodes

```text
function buildIndex(sortedEligibleTerms):
    trie = new CompressedTrie()
    for term in sortedEligibleTerms:
        nodePath = trie.insert(term.normalizedBytes, term.id)
        for node in nodePath:
            node.heap.offer(term.id, term.globalScore, capacity=BUILD_TOP_N)

    for node in trie.nodesPostOrder():
        node.top = sortDescending(node.heap).dedupe().take(BUILD_TOP_N)
        compressSingleChildPaths(node)
    return encodeWithSharedTermTable(trie)
```

For huge datasets, map workers emit `(prefix, candidate)` pairs only up to a maximum
prefix length, reducers keep bounded heaps, and the builder joins compact top lists
into FST shards. Storing more than response K permits safety filtering and reranking.

## 10. Online lookup and merging

```text
function autocomplete(request):
    prefix = normalizer(request.locale, request.q)
    if !valid(prefix): return []
    snapshot = activeIndex.acquire(request.locale, request.context)

    base = snapshot.lookupTop(prefix, limit=50)
    trend = trendLayer.lookup(prefix, limit=30, maxVersion=snapshot.compatVersion)
    candidates = dedupeByNormalizedText(base + trend)

    candidates = candidates.filter(c =>
        !emergencyDenylist.matches(c) and policy.allows(c, request))
    if personalization.availableWithin(3ms):
        candidates = boundedRerank(candidates, request.userFeatures)
    return candidates.sort(stableScoreThenText).take(request.limit)
```

Base/trend scores must be calibrated before merge. Personalization may boost only
already eligible public candidates; never use one person's private history to create
a globally visible suggestion. On timeout, return global/locale ranking.

## 11. Fresh trends and index rollout

Immutable base builds (hourly/daily) provide compactness and deterministic rollback.
A small streaming delta updates every few minutes for eligible high-confidence terms
and expires entries automatically. Periodic builds absorb it.

Manifest publication follows `BUILDING -> VERIFIED -> CANARY -> ACTIVE`. Servers
download without replacing current data, validate checksums/schema/normalizer and
minimum policy version, memory-map, run probes, then atomically swap. Retain at least
two prior versions. Fleet rollout uses canary cohorts and halts on latency, safety,
zero-result, or relevance regressions.

## 12. Caching and partitioning

An L1 cache stores `(indexVersion, policyVersion, locale, context, normalizedPrefix,
cohortBucket)` results for hot prefixes. Short TTL and versioned keys avoid explicit
bulk invalidation. Avoid per-user cache keys except a tiny client/session layer.

Route by locale and leading normalized bytes. Replicate hot shards and split them by
additional bytes; maintain a small router table in the signed manifest. Empty/short
prefixes use dedicated curated tables, not a full scan.

## 13. Safety, privacy, and abuse controls

Drop raw queries that contain emails, phone/card/account numbers, credentials,
addresses, rare names plus identifiers, illegal/unsafe content, or policy-prohibited
terms. Require k-anonymity-like distinct-user thresholds and delay before publication.
Use bot/fraud detection, per-source contribution caps, trend velocity limits, and
human review for high-impact trends.

Log normalized/redacted prefixes sparingly, encrypt streams/artifacts, restrict raw
event access, audit suppression/editorial changes, and enforce consent, retention,
deletion, residency, and child-safety rules. An emergency denylist is authenticated,
signed, versioned, globally pushed, and checked after all candidate generation.

## 14. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Event stream/aggregator lags | Serve older base; trend freshness alert |
| Builder fails | Never publish incomplete manifest; keep active version |
| New index is corrupt | Checksum/probe rejects it before pointer swap |
| Trend store fails | Serve immutable base suggestions |
| Personalization fails | Serve locale-global ranking |
| Locale shard unavailable | Replica, then parent-locale curated fallback |
| Bad term is discovered | Emergency suppression layer removes it immediately |
| Rollout degrades metrics | Stop rollout and atomically revert prior manifest |
| Server restarts | Memory-map locally cached verified version before joining load balancer |

## 15. Consistency and correctness

Artifact and policy versions make each response internally consistent. Streaming
counts and trends are eventual and deduplicated by event ID/window. Builders pin
input offsets, policy version, model weights, and normalizer so output is reproducible.
After a successful swap, in-flight requests retain the prior memory map until their
reference releases; no request observes a half-loaded structure.

## 16. Observability

Measure lookup p50/p95/p99, QPS, CPU/memory, cache hit, shard skew, candidates before/
after filters, zero-result and abandonment rate, click/success/reformulation metrics,
event/window/index age, build duration/size, rollout coverage, trend churn, fallback,
personalization timeout, unsafe leakage reports, suppression propagation time, and
differences between expected and active versions.

Golden tests cover scripts/locales, Unicode confusables, punctuation, sensitive data,
and blocked terms. Property tests compare trie results with brute-force prefix top-K.
Load tests use short hot prefixes. Canary/shadow evaluation compares relevance and
safety; chaos tests remove trend, shard, distributor, and entire regions.

## 17. Implementation path

1. **MVP:** offline eligible term counts, locale-aware normalization, immutable trie,
   in-memory lookup, static safety list, and global popularity.
2. **Reliable builds:** event dedupe/windows, signed manifests/checksums, atomic
   rollout/rollback, caches, shard replication, and emergency suppression.
3. **Fresh/relevant:** streaming trend delta, quality signals, personalization rerank,
   multilocale models, abuse controls, and A/B evaluation.
4. **Hardening:** regional distribution, privacy lifecycle, adversarial Unicode/PII/
   trend tests, load/chaos drills, restores, SLOs, and review tooling.

## 18. Final design

Transform privacy-filtered aggregate query behavior into versioned immutable compact
tries whose nodes contain precomputed top candidates. Regional servers answer by one
in-memory prefix traversal, merge a small expiring trend layer, then reapply emergency
safety and optional bounded personalization. Atomic signed rollouts and retained
prior versions provide reliable rollback; strict eligibility and suppression ensure
freshness never outruns privacy or safety.
