# Complete Solution: Recommendation Service

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Given a user/session and placement, return relevant eligible items using recent and
historical behavior. Combine collaborative, content, following, trending, and
editorial candidates; rank and diversify them; enforce availability/safety/business
rules; experiment safely; and join exact exposures to later outcomes for learning.

Targets: 100,000 peak recommendation requests/s, p99 below 100 ms inside the caller's
page budget, 99.99% availability, feature freshness below minutes for important
actions, and a safe fallback within 20 ms. Recommendations are best-effort/eventually
consistent, but current item eligibility and hard policy are checked before return.

## 2. Capacity estimation

Assume 100,000 peak QPS, 1,000 raw candidates/request, 200 pre-ranked, 20 returned,
100 million daily users, 100 million items, and 20 interaction events/request.

- Candidate generation can touch 100 million IDs/s before dedupe; indexes and batch
  operations must remain local/in-memory to serving nodes or specialized services.
- Returning 20 IDs plus metadata at 500 bytes/item is about 1 GB/s at peak before
  protocol compression.
- Two million behavioral events/s require a partitioned durable stream and sampling/
  aggregation strategy.
- A 256-dimensional float embedding is 1 KB; 100 million item vectors are 100 GB
  raw, multiplied by ANN graph/quantization metadata and replicas.
- Online user/item feature stores require billions of key lookups/s if accessed
  naively; batch, colocate, cache, precombine, and reduce features before ranking.

## 3. API

```text
POST /v1/recommendations
{
  "userId": "optional",
  "sessionId": "...",
  "placement": "home",
  "context": {"locale": "en-IN", "device": "mobile"},
  "limit": 20,
  "excludeItemIds": []
}
```

Response contains request/exposure token, ordered item IDs/reasons, model/experiment
version (internally or debug-authorized), and fallback flag. Bound limit, exclusion
size, context fields, debug access, request rate, and per-stage cost. Item hydration
can remain with the caller when this service should return only ranked IDs.

## 4. Data and artifacts

```text
Interaction(event_id, user_or_session, item_id, type, value, event_time,
            receive_time, request_id, position, model_version)
Exposure(request_id, user_or_session, placement, item_id, position,
         model_version, experiment_assignments, served_at)
UserFeature(user_id, feature_vector, feature_time, schema_version)
ItemFeature(item_id, feature_vector, eligibility_version, schema_version)
Embedding(entity_id, vector, model_version, generated_at)
CandidateIndex(source, version, shard_map, artifact_refs, checksums)
ModelManifest(version, feature_schema, artifact_ref, checksum,
              calibration, policy_compatibility, state)
ExperimentAssignment(subject_key, experiment_id, variant, version)
RecommendationLog(request_id, candidates_ref, result_ids, versions, timestamps)
```

Offline feature definitions and online encodings share one versioned registry. Model,
feature schema, candidate-index, policy, and experiment versions form a compatible
serving bundle that can be reproduced and rolled back.

## 5. Architecture

```text
interaction/exposure events -> stream/lake -> feature + training pipelines
                                      |             |
                               online features  model/embedding artifacts
                                      |             |
request -> recommendation API -> candidate orchestrator -> source services/ANN
                                      |
                               dedupe + pre-rank
                                      |
                              batch feature join -> ranker
                                      |
                         hard policy -> diversity/business rules -> response
                                      |
                               exposure event/outbox
```

Candidate, feature, model, policy, and event services have independent deadlines and
circuit breakers. Artifact control planes publish immutable signed versions; serving
data planes load validated snapshots without per-request control-plane calls.

## 6. Step-by-step workflow

### Online request

1. Authenticate caller, normalize placement/context, assign stable experiments, pin
   a compatible serving bundle, and create request ID/deadline.
2. Invoke candidate sources concurrently under individual budgets: user/item ANN,
   recent history continuations, followed entities, similar items, trending, and
   editorial inventory.
3. Merge/deduplicate IDs while retaining source/reason features; remove seen/excluded
   and cheaply ineligible candidates; use a lightweight pre-ranker to keep about 200.
4. Batch-fetch fresh user/item/context/cross features and infer scores with the pinned
   model. Missing features use declared defaults plus missingness indicators.
5. Apply current hard eligibility/safety, then diversity, freshness, inventory, and
   pacing constraints. Fill deficits from safe fallbacks.
6. Durably enqueue/log exact ordered exposures with request/model/experiment versions,
   then return. Client outcomes reference request ID and item/position.

### Learning loop

1. Deduplicate interaction/exposure events and validate timestamps/schema.
2. Join outcomes only to items actually exposed, apply attribution windows, and create
   training examples with point-in-time feature values.
3. Train/evaluate candidate and ranking models; compare offline relevance, calibration,
   fairness/safety, latency, and slice metrics against baseline.
4. Register immutable artifacts, shadow, canary, then experiment with guardrails.

## 7. Candidate orchestration logic

```text
function generateCandidates(request, deadline):
    plans = [
      (collaborativeANN, 20ms, 400),
      (contentSimilar, 15ms, 250),
      (recentContinuation, 10ms, 150),
      (socialFollowing, 15ms, 200),
      (regionalTrending, 5ms, 100),
      (editorial, 5ms, 50)
    ]
    results = invokeConcurrently(plans, until=deadline.candidateCutoff)
    merged = map itemId -> Candidate
    for result in successful(results):
        for item in result.items:
            c = merged.getOrCreate(item.id)
            c.sources.add(result.source)
            c.sourceScores[result.source] = calibrated(result.score)
            c.reasonFeatures.merge(item.reasonFeatures)

    return merged.values()
        .filter(notInRequestExclusions)
        .filter(cheapEligibilitySnapshotAllows)
        .sortBy(preRankScore)
        .take(PRE_RANK_LIMIT)
```

Source scores are calibrated before comparison. Every source has a timeout, maximum
candidates, circuit breaker, and minimum reserved contribution so one noisy source
cannot consume the whole set. Trending/editorial double as cold-start and outage
fallbacks.

## 8. ANN candidate retrieval

Train user and item embeddings so relevant pairs have high dot-product/cosine score.
Build a versioned HNSW/IVF-like approximate nearest-neighbor index, sharded by item
class/region and replicated in memory. Filter inactive/unsafe items during build and
again at serve time because the artifact can lag.

```text
function annCandidates(userVector, context, K):
    shards = routeByEligibleCatalog(context)
    local = parallel(shards, s =>
        s.approximateTopK(userVector, K=K*2,
                          filters=coarseContextFilters))
    return topK(merge(local), K, by=dot(userVector, item.vector))
```

New items use content embeddings and exploration before interaction data exists. New
or anonymous users use session actions, locale/context, onboarding interests, and
popular-diverse lists.

## 9. Feature retrieval and training-serving consistency

Define each feature once with computation, key, event-time semantics, TTL, default,
and privacy classification. Offline jobs perform point-in-time joins (no future
events); streaming/batch jobs write the same schema to online stores. Store feature
timestamp and schema version alongside value.

```text
function assembleFeatures(request, candidates, bundle):
    user = featureStore.multiGetUser(request.userId, bundle.schema)
    items = featureStore.multiGetItems(candidates.ids, bundle.schema)
    now = request.receivedAt
    for candidate in candidates:
        f = combine(user, items[candidate.id], request.context,
                    crossFeatures(user, items[candidate.id]))
        for feature in bundle.requiredFeatures:
            if missing(f[feature]) or tooOld(f[feature], feature.maxAge):
                f[feature] = feature.default
                f[feature + "_missing"] = 1
        yield f
```

Validate online/offline distributions, freshness, null/default rate, range, and schema
at rollout. Feature failures must not silently feed nonsense into a model.

## 10. Ranking and post-processing

```text
function rank(request, candidates, bundle):
    features = assembleFeatures(request, candidates, bundle)
    predictions = bundle.model.batchInfer(features)
    scored = []
    for (candidate, p) in zip(candidates, predictions):
        utility = w1*p.meaningfulAction + w2*p.longTermValue
                  - w3*p.negativeFeedback - w4*p.churnRisk
        scored.add(candidate.withScore(calibrate(utility, bundle.calibration)))

    eligible = scored.filter(c => currentPolicyAndInventoryAllows(request, c))
    ordered = stableSortDescending(eligible, scoreThenItemId)
    return constrainedSelect(ordered, request.limit,
        maxPerCreator, categoryDiversity, freshnessFloor,
        sponsoredSpacingAndBudget, explorationSlots)
```

Hard safety, block, entitlement, age/region, availability, and already-consumed rules
are never model weights. They filter after scoring using sufficiently fresh state.
Constraint selection may use greedy maximal-marginal-relevance: relevance minus
similarity to already selected items.

## 11. Exposure and outcome correctness

Log what was actually served, not merely generated. The service writes/queues the
ordered result with `(request_id, item_id, position, model, experiments)` before or
atomically with returning an exposure token. The client sends impression only when
visible if that is the metric definition; ingestion deduplicates `(request, item,
event_type)`.

Outcome joins require matching subject/session, request, item, and attribution window.
Use negative examples from exposed-but-not-acted items, not arbitrary catalog items,
to reduce selection bias. Account for position propensity and exploration policy.
Late/offline events update bounded windows and never mutate already frozen training
datasets without a new dataset version.

## 12. Experiment assignment and rollout

Deterministically assign with a stable hash of `(experiment_id, randomization_unit,
salt)` so retries/devices remain in one variant. Persist assignment/version for
long-lived experiments and make variants mutually exclusive where interference is a
risk. Log assignment on every exposure.

Artifact flow is `REGISTERED -> VALIDATED -> SHADOW -> CANARY -> EXPERIMENT -> ACTIVE`.
Automatic rollback watches error/latency/fallback plus safety, diversity, inventory,
complaint, and core business guardrails—not only click-through rate. Keep a kill
switch and last known-good compatible bundle.

## 13. Caching and scaling

- Cache anonymous/low-personalization results by placement, locale, device, time
  bucket, policy, and bundle version; apply live eligibility after cache read.
- Cache user embeddings/features briefly and invalidate via version/TTL, not massive
  deletion broadcasts.
- Batch feature reads/inference, colocate model and hot features, quantize embeddings,
  and use GPU/CPU microbatches only within latency budget.
- Shard ANN by item domain/region and user features by user ID; replicate hot catalog
  and trending lists regionally.
- Use admission control and per-caller quotas; degrade sources/model complexity before
  exceeding page deadline.

## 14. Failure handling

| Failure | Correct behavior |
| --- | --- |
| One candidate source times out | Merge remaining sources and report source health |
| ANN index unavailable | Use history/content/social/trending candidates |
| User features missing | Session/context/cold-start model with missing indicators |
| Item feature batch partially fails | Drop unsafe unknowns; defaults only for allowed features |
| Main ranker fails/overruns | Lightweight pre-ranker, then cached safe trending |
| Policy/inventory uncertainty | Fail closed for affected item |
| Exposure stream is unavailable | Durable local/outbox buffer; avoid untraceable experiment data |
| New model degrades | Stop canary and atomically activate prior bundle |
| Region fails | Route to replicated regional service with local fallback lists |

The explicit ladder is: full personalized -> fewer sources -> lightweight model ->
contextual popular/diverse -> curated safe list. Always meet hard policy.

## 15. Security, privacy, fairness, and abuse

Authorize callers/placements and isolate tenants. Encrypt features/events/artifacts,
sign model manifests, restrict training/raw-event access, audit model/experiment/
policy/admin changes, and avoid sensitive values in traces. Enforce consent, purpose
limitation, retention, deletion, residency, and user controls for personalization.

Detect event poisoning, bots, shilling, seller/creator collusion, feedback loops, and
model extraction. Cap one actor's contribution, use robust aggregates, protect
exploration, and review anomalous trends. Measure exposure/quality by relevant cohorts,
constrain harmful concentration, and provide explainable high-level reasons without
leaking private features.

## 16. Observability

Track total and stage p50/p95/p99, QPS/errors/deadline exhaustion, candidates/source,
source timeout/overlap/coverage, feature latency/freshness/defaults, inference batch/
latency, filter reasons, returned count, diversity/novelty/catalog coverage, cache
hit, fallback level, artifact/version skew, exposure loss/duplicates/join rate, model
drift/calibration, and cost/request. Monitor online outcomes with guardrails and
confidence intervals by experiment/cohort.

Offline replay verifies deterministic features/ranking for pinned versions. Golden
users cover cold-start, sparse, power, blocked, age/region, and deleted-item cases.
Shadow and canary compare old/new bundles. Chaos tests remove sources/features/model/
stream/regions; reconciliation proves returned request IDs have exposure records and
active manifests reference verified compatible artifacts.

## 17. Implementation path

1. **MVP:** eligible regional popularity, subscriptions/history rules, exact exposure
   log, outcome definitions, safe fallback, and offline evaluation.
2. **Personalized candidates:** batch collaborative/content embeddings, ANN index,
   streaming recent features, source orchestration, dedupe, and pre-ranking.
3. **Learned ranking:** feature registry/point-in-time joins, online store, multi-task
   model, constrained diversity, experiments, canary/rollback, and monitoring.
4. **Hardening:** regional serving, artifact compatibility control, privacy/fairness/
   abuse lifecycle, load/chaos/drift tests, restores, and SLOs.

## 18. Final design

Use multiple bounded candidate sources for recall, a versioned online feature join
and model for relevance, then current hard policy and constrained selection for a
safe diverse final list. Every request pins a compatible model/feature/index bundle
and records exact ordered exposure for unbiased learning. Strict deadlines and an
explicit fallback ladder preserve availability, while point-in-time features,
deterministic experiments, signed rollouts, and guardrails keep learning reproducible
and safe.
