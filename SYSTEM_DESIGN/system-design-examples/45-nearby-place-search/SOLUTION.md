# Complete Solution: Nearby-Place Search

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Find places inside a radius, map viewport, route corridor, or administrative area,
optionally matching text, category, attributes, price, accessibility and `open now`.
Return accurate distance, relevance-ranked stable pages, localized names/hours, and
current closure/availability indicators. Businesses/users/providers can add or edit
places through validation, conflation, moderation and versioned indexing.

Targets: 100,000 peak queries/s, p99 below 200 ms for ordinary radius/viewport, 99.99%
read availability, emergency closure below one minute, routine edit-to-index below
five minutes, and no place outside the exact requested geometry. Search is eventually
consistent, returns index/policy version and marks incomplete coverage when degraded.

## 2. Capacity estimation

Assume one billion canonical places, 100,000 peak QPS, 50 results/page, 500 candidates
examined/query, 2 KB compact search document, and 5 KB authoritative metadata.

- Search documents are about 2 TB before text/geo/filter index and replicas;
  authoritative records about 5 TB before media/history.
- Candidate processing can reach 50 million docs/s, requiring shard-local filtering/
  top K rather than shipping all matches to brokers.
- At 10 KB response, peak egress is about 1 GB/s before compression and edge caching.
- Urban cells contain millions of places while rural cells are sparse; adaptive cell
  resolution and dense-cell subshards are required.
- Write rate is modest relative to reads, but bulk provider imports and emergency
  closures burst and need separate priority lanes.

## 3. APIs

```text
GET /v1/places/nearby?lat=&lng=&radius=&q=&category=&filters=&openNow=&cursor=
GET /v1/places/in-viewport?north=&south=&east=&west=&zoom=&filters=&cursor=
GET /v1/places/{placeId}?locale=
POST /v1/places                              Idempotency-Key
PATCH /v1/places/{placeId}                   If-Match: version
POST /v1/places/{placeId}/closure             Idempotency-Key
POST /v1/place-edit-proposals                 Idempotency-Key
```

Bound radius/viewport area, filter clauses, query length, page size/depth, polygon
complexity, localization count and QPS. Validate latitude/longitude including
antimeridian/poles. Cursor is signed and binds normalized request, index/ranker/policy
versions, coverage set, and last ordering tuple.

## 4. Authoritative data model

```text
Place(id, canonical_name, location_point, footprint_ref, access_points,
      category_ids, address, timezone, state, confidence, version, updated_at)
PlaceName(place_id, locale, name, type, version)
PlaceAttribute(place_id, definition_id, typed_value, source, version)
OpeningHours(place_id, weekly_rules, special_dates, timezone, version)
PlaceSource(place_id, provider, external_id, source_version, confidence, raw_ref)
PlaceEdit(id, place_id_or_candidate, proposer, patch, evidence, state, version)
Closure(place_id, start_at, end_at, type, source, confidence, version)
ReviewAggregate(place_id, rating, count, quality_version)
Outbox(id, aggregate_id, source_version, event_type, payload, published_at)
```

Stable canonical place IDs survive name/ownership/provider changes. Preserve source
provenance and revision history. Sensitive owner/user data is not embedded in public
search documents.

## 5. Search document

```text
PlaceDocument(place_id, source_version, point, bounding_box, access_points,
              geo_cells_by_resolution, names_analyzed, categories,
              typed_filter_fields, hours_compiled, timezone,
              quality, popularity, state, policy_flags, dynamic_version)
```

The document is a rebuildable projection. Index only schema-approved typed/filterable
attributes to avoid dynamic-field explosion. Exact footprint/entrance geometry can be
fetched for final refinement; search point should represent useful entrance/centroid
according to place type, not blindly polygon centroid.

## 6. Architecture

```text
providers/owners/users -> staging -> normalize/conflate/moderate -> place DB/outbox
                                                          |
                                            document builder/change log
                                               /          |         \
                                          geo/text      tile cache  analytics
                                         index shards

client -> query gateway/cache -> region cover/router -> shard local filter/top K
                                                        |
                                              exact geo/hours/ranker -> hydrate

closures/availability -> high-priority dynamic overlay/policy cache
rebuild/reconciliation compares place versions with index documents
```

Partition index by region/cell group and replicate across zones. Text query may fan
out within the covered geo shards; each returns local top candidates to a broker.

## 7. Step-by-step workflow

### Write/index

1. Authenticate source, validate typed schema/geometry/hours/evidence and stage raw
   version. Normalize names/address/categories/coordinates without losing provenance.
2. Find nearby/text/address/provider candidates, score whether this is the same real
   place, and merge only above reviewed confidence; otherwise create separate candidate.
3. Transactionally update canonical place/revision/outbox under optimistic version.
   High-risk ownership/category/closure edits enter moderation.
4. Projector reads a consistent aggregate, generates analyzed text, typed filters,
   compiled hours and multi-resolution cells, then conditionally indexes source version.
5. Cache/tile/search consumers ignore older versions. Emergency closure overlay updates
   independently and is checked at response time.

### Query

1. Normalize text/locale/categories/filters and pin compatible index/ranker/policy.
2. Compute conservative S2/H3/geohash cover for exact circle/viewport/corridor and
   route covered cells to shards.
3. Shards apply cell, text, category, typed attributes, state and coarse hours filters,
   oversample local top candidates, and return compact features.
4. Broker deduplicates place IDs, computes exact geometry distance/containment, evaluates
   hours/special closures, fetches dynamic policy/availability, ranks and diversifies.
5. Batch hydrate top results, recheck current removal/privacy, return page and cursor
   based on last consumed candidate.

## 8. Place conflation logic

```text
function matchCandidate(sourcePlace):
    nearby = canonicalIndex.within(sourcePlace.point, categoryRadius(sourcePlace))
    best = null
    for place in nearby:
        score = w1*nameSimilarity(normalize(sourcePlace.name), place.names)
              + w2*addressSimilarity(sourcePlace.address, place.address)
              + w3*phoneWebsiteIdentity(sourcePlace, place)
              + w4*categoryCompatibility(sourcePlace.categories, place.categories)
              + w5*distanceLikelihood(sourcePlace.point, place.point)
              + w6*providerCrossReference(sourcePlace, place)
        if incompatibleFootprintsOrKnownDistinctUnits(sourcePlace, place): continue
        best = max(best, place, score)
    if best.score >= AUTO_MERGE_HIGH: return MERGE(best.place)
    if best.score >= REVIEW_LOW: return HUMAN_REVIEW(best.candidates)
    return CREATE_NEW
```

Thresholds vary by category/density; two shops meters apart may be distinct while a
park spans kilometers. False merge is difficult to undo, so ambiguous records remain
separate and later cluster with reversible alias history.

## 9. Geographic covering

```text
function coverCircle(center, radius, targetCandidates):
    resolution = chooseResolution(radius, localDensity(center), targetCandidates)
    cells = geo.cover(capOrCircle(center, radius), resolution,
                      maxCells=MAX_CELLS, includeBoundary=true)
    if cells.size > MAX_CELLS:
        cells = geo.coarsen(cells, MAX_CELLS)
    return cells
```

Cover must be a superset: false-positive boundary cells are fine because exact filter
removes them; missing boundary cells lose valid results. For a viewport crossing the
antimeridian, split into valid regions. Multi-resolution document cells or spatial
tree terms reduce fan-out. Dense cells can be subsharded by place ID/category while
sparse neighbors combine.

## 10. Exact distance and containment

For small distances, library geodesic/Haversine is sufficient; for large/precision
requirements use ellipsoidal geodesic library. Do not use raw latitude/longitude
Euclidean distance.

```text
function exactEligible(candidate, query):
    representative = nearestAuthorizedAccessPointOrGeometry(candidate, query.center)
    distance = geodesicDistance(query.center, representative)
    if query.type == RADIUS and distance > query.radius: return false
    if query.type == VIEWPORT and !exactGeometryIntersects(candidate, query.viewport):
        return false
    return hardAttributeAndPolicyFilters(candidate, query), distance
```

Return straight-line distance unless specifically requesting walking/driving distance;
route distance requires a routing service and should only run for a small final set.

## 11. Opening-hours evaluation

Store structured weekly intervals, overnight spans, special openings/closures, holidays,
appointment-only/24h/unknown, and the place IANA timezone. Compile to an evaluated
artifact but retain source rule/version.

```text
function openAt(place, instant):
    local = convert(instant, place.timezone)
    if specialDateRule exists for local.date: return specialDateRule.contains(local.time)
    intervals = weeklyRulesFor(local.dayOfWeek)
    include carry-over interval from previous day when it crosses midnight
    return any interval contains local.time
```

DST gap/fold uses timezone library instants, not fixed UTC offset. Unknown hours are
not equivalent to closed. “Open now” excludes unknown unless product offers an explicit
include-unknown option. Current emergency closure overrides schedule.

## 12. Ranking logic

```text
function rank(place, query, distance, features):
    text = bm25OrSemanticMatch(query.text, place.names, place.categories)
    distanceScore = exp(-distance / scaleFor(query.intent, place.category))
    quality = bayesianSmoothedRating(place.rating, place.reviewCount)
    return w1*text + w2*distanceScore + w3*quality
           + w4*popularityByLocalTime + w5*queryIntentMatch
           + w6*freshnessConfidence - spamPenalty - closurePenalty
```

Weights depend on intent: “coffee” balances relevance/quality/distance; explicit exact
business name favors text/entity match. Apply category/brand diversity and avoid a
chain monopolizing pages. Personalization reranks only already policy-eligible candidates.

## 13. Stable cursor pagination

Pin a short search session to index/model/policy and region-cover versions. Stable sort
uses `(quantized_score DESC, exact_distance ASC, place_id ASC)`. Cursor stores request
hash, coverage shard state/search-after tuple, last consumed key and expiration.

On next page, shards use search-after under the same snapshot where supported; broker
over-fetches, dedupes and filters. Advance by consumed candidates, including newly
closed/removed rows, to avoid loops. If snapshot expires, return cursor-expired and
restart rather than mixing generations. Cap deep pagination.

## 14. Dynamic data and freshness

Separate slow canonical fields from high-churn open/closed busy/availability signals.
Emergency closure has authenticated source, direction/scope, start/end, confidence,
version and TTL; a small replicated overlay is checked after index retrieval. Business-
reported temporary closure may be immediate but fraud-monitored/reviewable.

Crowd “busy now” uses consented aggregated observations with minimum cohort/privacy
thresholds, confidence and expiry. Do not expose individual visits. Booking/inventory
availability belongs to source service and is fetched only for final candidates with
deadline/fallback.

## 15. Caching and tile browsing

- Cache normalized common queries by quantized center/geocell, radius/viewport bucket,
  filters, locale and index/policy version; short TTL for open/dynamic filters.
- Cache static place details and vector place tiles under immutable version keys/CDN.
- Map browsing returns clustered cells/place IDs appropriate to zoom, not thousands
  of full documents; expand as user zooms.
- Request coalescing protects hot tourist/stadium cells. Admission avoids cache pollution
  by one-off arbitrary coordinate/filter keys.
- Response-time closure/removal filter still applies to cached IDs.

## 16. Sharding and partial results

Route cell cover to region shards with replicas; one shard can own several sparse cells
or a salted slice of dense cell. Broker sends deadlines and merges local top K. Retry/
hedge replica sparingly. If a nonessential shard fails and product permits, return
`incomplete=true` plus coverage metadata; never claim complete nearest K when a nearer
covered cell is missing. Safety/removal overlay uncertainty fails closed for affected data.

## 17. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Projection event duplicates/reorders | Source-version conditional index prevents regression |
| Search shard misses deadline | Retry replica or explicit incomplete coverage |
| Dense cell overloads | Subshard, local top K, cache/coalesce, bound query |
| Dynamic availability fails | Return place without optional signal, labeled unknown |
| Closure arrives before reindex | Response overlay suppresses/labels immediately |
| Cache is stale after deletion | Current removal policy filters cached IDs |
| New index generation is bad | Canary stops/rolls back prior manifest |
| Cursor snapshot expires | Explicit restart; never silently mix orderings |
| Rebuild misses documents | Version reconciliation detects and replays them |

## 18. Security, moderation, and privacy

Authorize provider/owner/editor/moderator roles, verify business claims, protect edit/
closure endpoints with strong auth, sign source files/events, encrypt data, audit every
merge/split/edit/closure/admin action, and require dual review for high-impact places.
Prevent fake listings/closures/reviews, map spam, SEO stuffing, duplicate businesses,
malicious URLs/media, XSS, IDOR, bulk scraping, expensive geo-query abuse, owner takeover,
and insider search of sensitive locations.

Suppress or generalize sensitive places (shelters, homes, protected sites) by policy.
Minimize precise query/location logs, consent for personalization/crowd signals, rotate
pseudonyms, and enforce retention/deletion/residency/legal hold. Provide correction/
appeal and safety/emergency removal with provenance and rollback.

## 19. Observability

Track query/stage p50/p95/p99, QPS/errors/cache hit, cover cells/resolution/fan-out,
candidates scanned/returned, exact-boundary removals, shard skew/timeouts/incomplete
coverage, empty/zero-result, text/distance/rank distributions, cursor expiry/duplicates,
open-now unknown/error, source-to-index/closure lag, index version skew, place merge/
split confidence/errors, freshness/coverage by region/category, edit moderation age,
fraud reports, and cost/query.

Golden queries cover dense/rural, cell boundaries, poles/antimeridian, exact geometry,
multilingual names, overnight/DST hours, closures and typed filters. Property-test cover
superset and exact distance against brute force on samples. Shadow/canary indexes,
load-test dense hot viewports, kill shards/overlays, and reconcile authoritative source
versions/place states with index/cache/tile generations.

## 20. Implementation path

1. **MVP:** authoritative places, one geo index, radius query, exact distance, category,
   details, structured hours, simple score and cursor.
2. **Search quality:** text/localization, H3/S2 multi-resolution cover, typed filters,
   dense-cell shards, stable snapshots, caches/tiles, rating/popularity ranking.
3. **Fresh/large:** versioned change pipeline/rebuild, conflation/moderation, dynamic
   closure/availability, route corridors, personalization, global replication.
4. **Hardening:** fraud/security/privacy/sensitive-place controls, property/golden/
   dense-load/chaos tests, rollout/restore drills, runbooks, dashboards, and SLOs.

## 21. Final design

Keep canonical place/provenance/history in an authoritative versioned store and build
replayable geo/text documents. A query covers the requested geometry conservatively
with adaptive cells, runs shard-local text/category/filter top K, then applies exact
geodesic/geometry, timezone-correct hours, dynamic closures, ranking and stable cursor.
Multi-resolution cells, dense subshards and caches scale reads; current response-time
policy prevents eventual indexes from leaking removed or closed places. Conflation,
versioned rollout and reconciliation preserve identity and freshness end to end.
