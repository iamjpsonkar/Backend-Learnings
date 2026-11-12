# Complete Solution: Web Search Engine

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Discover permitted public pages, fetch and parse them, canonicalize/deduplicate
content, build a searchable index, and answer text queries with relevant, fresh,
safe results and snippets. Support spelling, language/region, filters, and stable
next-page cursors. Publishers can remove or update pages.

Targets: query p99 below 300 ms, 99.99% query availability, 100,000 peak queries/s,
important-page freshness below minutes and long-tail freshness below days. Indexing
is eventually consistent. Each response uses one compatible index/ranker/policy
snapshot; legal/safety removals use a fast deny layer checked at response time.

## 2. Capacity estimation

Assume 100 billion known documents, 100 KB average compressed raw page, 10 KB parsed
text, 1 KB compressed postings/features, 10% recrawled/day, and 100,000 peak QPS.

- Compressed raw storage is roughly 10 PB before replication/version retention.
- Parsed text is about 1 PB and a 1 KB/document index baseline is 100 TB; real
  positional indexes, fields, link graph, and replicas multiply this.
- Recrawling ten billion pages/day averages 116,000 fetches/s, constrained chiefly
  by per-host politeness rather than aggregate bandwidth.
- With 1,000 document-sharded index partitions, each query would fan out 1,000 ways;
  use shard groups, replicas, pruning, caches, and strict deadlines.
- Returning each shard's top 100 compact candidates at 24 bytes is about 2.4 MB per
  uncached query before staged pruning, so hierarchical merging matters.

## 3. Query interface

```text
GET /v1/search?q=distributed+cache&locale=en-IN&safe=strict
    &filters=type:web&limit=10&cursor=...
```

Response includes results, corrected/rewritten query, opaque next cursor, snapshot
version, and an explicit partial-result flag when policy allows degraded coverage.
The signed cursor binds normalized query, filters, snapshot/ranker versions, and the
last ranking tuple; cap query length, clauses, wildcards, page depth, and cost.

## 4. Core data and index artifacts

```text
UrlRecord(url_id, canonical_url, host_id, crawl_state, next_fetch_at, robots_version)
Document(doc_id, canonical_url, fetch_version, content_hash, title, text_ref,
         language, published_at, fetched_at, state, metadata)
LinkEdge(source_doc, target_url_or_doc, anchor_text, version)
Posting(term_id -> blocks(doc_delta, term_frequency, field_bits,
                          positions_delta, block_max_score))
DocValues(doc_id -> length, language, region, freshness, quality, authority, flags)
IndexManifest(version, shard_map, segment_refs, checksums, schema,
              analyzer_version, built_at, state)
DeletionBitmap(index_version, shard_id, doc_ids, policy_version)
QueryLog(event_id, normalized_query, anonymous_cohort, result_actions, event_time)
```

Raw pages and parsed documents are durable sources. Inverted indexes are immutable,
versioned, replicated artifacts. A stable `doc_id` maps revisions of one canonical
page; new content increments its fetch version rather than creating duplicates.

## 5. Architecture

```text
URL frontier -> fetchers -> raw store -> parse/canonical/dedupe -> document store
                                      -> link graph / feature pipelines
                                      -> segment builders -> index object store
                                                             |
                                                      shard distributors

client -> edge/query cache -> query broker -> lexical shard replicas
                                      |              |
                                  rewrite         local top N
                                      |              |
                                      +-> global merge -> feature fetch/rerank
                                                           -> policy/snippet/result
```

Use document-partitioned index shards for balanced build/storage and independent
replicas. Every normal query reaches a replica for each active shard group, but
hierarchical brokers and local dynamic pruning keep network/CPU bounded.

## 6. Step-by-step workflow

### Indexing

1. Crawl scheduler selects allowed due URLs under per-host politeness. Fetcher stores
   response and immutable metadata/checksum.
2. Sandboxed parser extracts canonical URL, visible text, title, language, links,
   structured fields, and safety signals; duplicate/near-duplicate logic selects a
   canonical document.
3. Analyzer tokenizes each field with versioned language rules and emits term,
   document, frequency, position, and field signals.
4. Builders sort postings by `(term, doc_id)`, compress them into immutable segments,
   calculate block-max scores/doc values, and write checksummed artifacts.
5. Compactor merges small segments and applies newer document versions/tombstones.
   A verified manifest rolls out to replicas by canary then atomic activation.

### Query

1. Normalize, detect language/intent, spell-correct/rewrite, validate filters, and pin
   index/ranker/policy versions.
2. Query broker sends analyzed terms to one healthy replica per document shard with
   a deadline and asks each for lexical top N.
3. Shards use compressed postings and dynamic pruning to score only competitive docs.
4. Broker merges candidates, deduplicates canonicals, fetches fresh features, and
   applies a more expensive learned reranker/diversity rules.
5. Recheck deletion/safety/region policy, generate safe highlighted snippets, and
   return top results with cursor and coverage metadata.

## 7. Index construction logic

```text
function indexDocument(document, analyzerVersion):
    fields = {TITLE: document.title, BODY: document.visibleText,
              ANCHOR: document.inboundAnchorSummary}
    byTerm = map()
    for (field, text) in fields:
        tokens = analyzer(analyzerVersion, document.language).tokenize(text)
        for token in tokens:
            if eligible(token):
                byTerm[token.term].add(field, token.position)

    for (term, occurrences) in byTerm:
        emit(term,
             PostingInput(document.docId,
                          termFrequency=occurrences.size,
                          fieldBits=occurrences.fields,
                          positions=deltaEncode(occurrences.positions),
                          document.fetchVersion))

function reduceTerm(term, postingsSortedByDoc):
    keep newest version for each docId; drop tombstoned versions
    split into blocks, delta-code doc IDs/positions, compress frequencies
    calculate each block's maximum possible lexical score
    write immutable posting list and dictionary offset
```

Builder pins document/log offsets, analyzer/schema, spam policy, and feature versions
so an artifact is reproducible. Publish only when every shard and checksum exists.

## 8. Lexical retrieval and pruning

A baseline BM25 score is:

```text
idf(term) = log(1 + (N - documentFrequency + 0.5) /
                    (documentFrequency + 0.5))
bm25(term, doc) = idf(term) *
    tf*(k1+1) / (tf + k1*(1-b+b*docLength/averageDocLength))
lexicalScore = sum(fieldBoost * bm25(term, doc))
```

```text
function shardTopK(queryTerms, filters, K):
    iterators = openPostingIterators(queryTerms)
    heap = minHeap(capacity=K)
    while some iterator remains:
        pivot = chooseWandPivot(iterators, heap.minimumScore)
        if sumUpperBoundsBefore(pivot) <= heap.minimumScore:
            advanceSmallestIteratorTo(pivot.docId); continue
        doc = alignCandidatesAt(pivot.docId)
        if doc exists and docValues.match(doc, filters):
            score = exactBM25AndStaticFeatures(doc, queryTerms)
            heap.offer(doc, score)
        advanceMatchedIterators(doc)
    return heap.descending()
```

WAND/block-max WAND skips posting blocks whose maximum cannot enter current top K.
Phrase queries additionally verify positions only for lexical candidates. Timeout
returns the best completed heap with a shard-timeout marker.

## 9. Global merge and ranking

```text
function mergeAndRank(shardResults, request, snapshot):
    candidates = topNByLexicalScore(flatten(shardResults), GLOBAL_N)
    candidates = dedupeCanonicalAndNearDuplicates(candidates)
    features = featureService.batchGet(candidates, snapshot.featureVersion)

    for candidate in candidates:
        candidate.finalScore = ranker(snapshot.modelVersion,
            lexical=candidate.score,
            authority=features.authority,
            freshness=features.freshness,
            quality=features.quality,
            intentMatch=features.intentMatch,
            spam=features.spamPenalty)
    ranked = diversifyByDomainAndIntent(stableSort(candidates))
    return ranked.filter(currentPolicyAllows)
```

Tier one maximizes recall cheaply; tier two applies hundreds of features to perhaps
1,000 candidates; an optional neural cross-encoder reranks the final tens under a
small budget. If feature/neural services fail, return lexical plus stored static
features. Learned signals never bypass hard policy/deletion checks.

## 10. Pagination and result stability

Offset pagination is expensive and unstable. The cursor stores the pinned snapshot,
normalized/re-written query hash, filter hash, and last `(final_score_bucket,
tie_break_doc_id)`. A subsequent request repeats deterministic retrieval/ranking and
returns items below that tuple, excluding a small served-ID set/session bloom filter.

Scores can be quantized and rank/model versions pinned for a short session. If the
snapshot expires, return `CURSOR_EXPIRED` and restart; do not combine generations.
Deep paging is capped because it multiplies shard work and has little relevance.

## 11. Freshness and incremental indexing

Maintain small frequent immutable delta segments for changed/deleted documents and
merge them with a larger base index at query time. A per-doc latest-version map and
deletion bitmap ensure an older base posting cannot resurrect replaced content.
Background compaction folds deltas into a new base and discards obsolete versions.

Prioritize recrawl/indexing using page change rate, authority, traffic, sitemap/feed
hints, and publisher pushes. Emergency removal writes a globally replicated deny
record immediately, then tombstones document/index/cache asynchronously.

## 12. Caching and hot queries

- Edge/result cache key includes normalized query, locale, filters, safe mode,
  index/model/policy version, and first-page cursor state.
- Broker caches analyzed/rewrite plans and popular merged lexical candidate sets.
- Shards rely on OS page cache and pin hot dictionaries/posting blocks in memory.
- Use request coalescing for identical misses and admission policies that prevent
  one-off queries from evicting hot entries.
- Invalidate through versioned keys; short TTL handles rapidly changing news queries.

## 13. Sharding, replicas, and rollout

Hash/range documents into many logical shards, then assign shard replicas across
zones. A broker chooses the least-loaded healthy replica with hedging only near its
deadline. Split oversized shards and update the versioned routing manifest.

Build a complete generation or compatible base/delta set, verify checksums and query
goldens, distribute in staging, warm caches, canary a small query cohort, then
atomically switch fleet pointers. Retain previous generations for rollback. In-flight
requests hold their pinned snapshot until completion.

## 14. Safety, abuse, and security

Crawl only allowed public content, honor robots/legal policy, sandbox HTML/media
parsers, scan malware, and isolate fetched bytes from internal networks. Detect spam,
cloaking, link farms, keyword stuffing, malicious redirects, and adversarial markup;
keep human/legal review and appeals.

Sanitize snippets/highlights and URLs against XSS/open redirects. Rate-limit bots and
expensive query syntax; encrypt data/transport, sign manifests, restrict index/raw-log
access, audit policy/legal/admin operations, and minimize query logs. Apply consent,
retention, deletion, copyright, child safety, regional removal, and residency policy
to raw pages, indexes, caches, models, logs, and backups.

## 15. Failure handling

| Failure | Correct behavior |
| --- | --- |
| One shard replica fails | Retry/hedge healthy replica within deadline |
| Entire shard misses deadline | Return labeled partial result if allowed; never pretend full coverage |
| Rewrite/ranker fails | Use analyzed original query and lexical/static ranking |
| Fresh delta fails | Serve previous verified delta/base and alert on age |
| New index is corrupt | Verification/canary rejects it; prior generation stays active |
| Cache fails | Query underlying brokers/shards with admission control |
| Feature store is stale | Version mismatch falls back to stored static features |
| Removal races stale cache/index | Response-time deny layer filters it |
| Region fails | Route to another regional replicated query fleet |

## 16. Observability

Track end-to-end and per-stage query latency, QPS/errors/timeouts, shard fan-out and
coverage, replica hedges, candidates/scored/pruned, cache hit/coalescing, zero-result,
partial-result and fallback rate, index/delta age, crawl-to-search latency, artifact
size/rollout/version skew, policy removals, and cost/query. Relevance metrics include
NDCG/MRR offline plus click, reformulation, abandonment, and long-click guardrails.

Golden queries cover languages, phrases, filters, freshness, duplicates, spam, and
removals. Property tests compare pruned top K with exhaustive scoring. Shadow/canary
new indexes/models, load-test hot and adversarial queries, kill shards/regions, and
reconcile published manifests, document latest versions, and referenced artifacts.

## 17. Implementation path

1. **MVP:** small crawler/document store, batch tokenizer/inverted index, BM25, one
   query node, snippets, and simple policy removal.
2. **Distributed retrieval:** document shards/replicas, broker/merge, WAND, caches,
   immutable manifests, canary rollout, cursor, and partial-result semantics.
3. **Fresh/relevant:** delta indexes, link/static features, spell/rewrite, learned
   reranking, dedupe/diversity, multilanguage analyzers, and event evaluation.
4. **Hardening:** regional fleets, spam/legal/privacy controls, adversarial parsing,
   load/chaos/relevance tests, rebuild/restore drills, and SLOs.

## 18. Final design

Convert versioned parsed documents into replicated immutable document-sharded
inverted-index generations. Query brokers pin a snapshot, fan out analyzed terms,
use block-max pruning for local top candidates, then merge, rerank, diversify, apply
current policy, and create snippets. Base-plus-delta segments give freshness without
unsafe in-place mutation. Versioned atomic rollout, lexical fallback, and emergency
deletion filtering keep search available, reproducible, and safe.
