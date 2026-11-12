# Complete Solution: Navigation ETA Service

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Given an ordered route (directed road edges), departure time, travel profile and
context, predict travel duration/arrival interval using live traffic, historical
patterns, incidents, weather/events and route characteristics. Continuously update ETA
during navigation, provide confidence/freshness, support batch matrix/dispatch calls,
and learn from consented completed trips without leaking future information.

Targets: 100,000 peak online predictions/s, single-route p99 below 100 ms after routing,
99.99% availability, live-edge freshness below two minutes, and calibrated p50/p90
error by region/time/profile. Prediction pins route graph, feature snapshot and model/
calibration versions. Missing live data degrades to historical/free-flow baselines with
wider uncertainty, never to an invented precise ETA.

## 2. Capacity estimation

Assume 100 million active navigators sampled every ten seconds, 100,000 ETA QPS, 200
edges/route, one million directed road edges with live traffic, and 5x commute peaks.

- Raw devices could produce ten million points/s; map-match and aggregate in stream,
  then retain privacy-filtered edge summaries rather than every point indefinitely.
- Naively reading 200 edge features × 100,000 QPS is 20 million lookups/s; batch by
  edge, colocate route feature blocks, cache and multi-get.
- One million edges × 288 five-minute buckets/day × multiple weekday/season cohorts
  can be billions of historical cells; compress/hierarchically back off sparse data.
- At 2 KB result, peak response egress is 200 MB/s before protocol overhead.
- Labels arrive after trips and are heavily censored/biased; dataset versioning and
  point-in-time joins are more important than raw storage volume.

## 3. API

```text
POST /v1/eta
{
  "routeId": "optional versioned route",
  "edges": [{"edgeId": "...", "fraction": 1.0}],
  "departureTime": "...",
  "profile": "car",
  "context": {"vehicleClass": "..."}
}

POST /v1/eta:batch                       bounded routes/origin-destination matrix
POST /v1/navigation-sessions/{id}/progress {routeVersion, edge, offset, eventTime}
POST /v1/trip-outcomes                   {sessionId, arrivalTime, traversals[]}
```

Return median duration/arrival, interval/quantiles, feature/source ages, confidence,
model/features/graph versions and degradation flags. Bound edges/route, routes/batch,
distance/time horizon, waypoints, QPS and context fields. Validate edges connect and
match graph/profile; do not accept arbitrary client speed as trusted truth.

## 4. Data and artifacts

```text
Probe(device_session, sequence, event_time, receive_time, point, accuracy,
      speed, heading, consent_cohort, integrity_flags)
Traversal(edge_id, entry_time, exit_time, duration, distance_fraction,
          source_class, confidence, observation_id)
EdgeSpeed(edge_id, window_start, median_speed, lower_speed, upper_speed,
          sample_count_bucket, confidence, source_watermark, expires_at)
HistoricalProfile(edge_or_cluster, day_type, time_bucket, season,
                  median_speed, quantiles, sample_support, version)
Incident(edge_ids, type, severity, start, end, confidence, source_version)
RouteFeature(route_hash, graph_version, static_features, edge_block_refs)
ModelManifest(version, feature_schema, artifact_ref, checksum,
              regions, calibration_version, state)
PredictionLog(request_id, route_hash, versions, generated_at, quantiles, features_ref)
Outcome(session_id, route_version, actual_duration, traversals_ref, quality, event_time)
```

Raw telemetry access/retention is separate and restricted. Serving artifacts are
immutable/versioned; online features carry event-time and processing watermark.

## 5. Architecture

```text
consented telemetry -> integrity filter/map matcher -> vehicle-partitioned stream
                                                       |
                                                edge traversal aggregator
                                                  /             \
                                         live edge store    history/lake
                                               |                |
incidents/weather/events ----------------> feature join      training pipeline
                                               |                |
route service -> ETA gateway/cache -> route feature assembler  model registry
                                               |                |
                                               +-> model serving/calibration

navigation progress -> remaining-route ETA / reroute policy
trip outcomes -> label/quality pipeline -> evaluation/drift/retraining
```

Regionalize live aggregation/serving by graph partitions and replicate historical/
model artifacts. Separate traffic estimation (what is happening on edges) from ETA
model (how edge/route/context turns into trip duration).

## 6. Step-by-step workflow

### Traffic features

1. Authenticate/consent-check telemetry, deduplicate device session/sequence, reject or
   downweight bad accuracy, stale clocks, impossible movement, spoofing and bots.
2. Probabilistic map matcher maps point sequences to directed edges and derives traversal
   entry/exit/duration with confidence; ambiguous samples are dropped/downweighted.
3. Windowed aggregator groups traversals by edge/event-time, computes robust speed/
   quantiles/support, applies privacy thresholds and publishes versioned live features.
4. Batch jobs build hierarchical historical profiles from validated traversals and
   calendar/season cohorts; incident/weather streams enrich online feature snapshots.

### Prediction

1. Validate/pin connected route graph version and model-compatible feature schema.
2. Batch-fetch live/historical/incident/static features for unique edges; select source
   by freshness/confidence and propagate expected arrival time edge by edge.
3. Model predicts edge/segment/route residual or quantiles; apply regional/profile/
   horizon calibration and return interval/fallback flags.
4. During navigation, consume map-matched progress, remove traversed path, refresh live
   features and ETA; reroute only under improvement/incident/hysteresis policy.
5. Completed high-quality outcomes join point-in-time features to predictions, evaluate
   error/calibration slices and feed versioned retraining/canary.

## 7. Probe map matching

```text
function matchProbeSequence(points, graphVersion):
    for point in points:
        candidates[point] = nearbyDirectedEdges(point, point.accuracy)
        emission(edge) = probability(distance/accuracy, headingDifference)
    path = viterbi(
      states=candidates,
      transition=(edgeA, edgeB, dt) =>
        probability(routedDistance(edgeA, edgeB), observedDisplacement, dt))
    if path.confidence < MIN_CONFIDENCE: return DROP
    traversals = inferEdgeEntryExit(path, points)
    return traversals.filter(plausibleDurationAndCoverage)
```

One noisy point near parallel roads should not set edge traffic. Use sequences, road
connectivity and direction. Do not use phone-reported speed alone; compare distance/time
and device quality. Tunnel/missing-GPS segments need explicit lower confidence.

## 8. Robust live edge aggregation

```text
function closeWindow(edgeId, traversals, window):
    valid = traversals.filter(confidence, minimumCoverage, plausibleSpeed)
    valid = capContributionPerDeviceAndFleet(valid)
    if distinctContributors(valid) < PRIVACY_AND_QUALITY_K:
        return no live estimate
    speeds = valid.map(distance / duration)
    center = weightedMedian(speeds, weights=confidence * coverage)
    spread = weightedQuantiles(speeds, [0.1, 0.9])
    center = robustClamp(center, priorFor(edgeId, window), maxChangeByRoadClass)
    publish EdgeSpeed(center, spread, supportBucket, confidenceFrom(valid), watermark)
```

Weight/threshold by source quality, but avoid one fleet dominating. Exponential smoothing
may reduce noise while detecting genuine incidents via change-point logic. Preserve
event-time watermark and expire live values quickly; an old “live” speed is worse than
an honest historical fallback.

## 9. Historical backoff

Sparse edge/time buckets back off hierarchically:

```text
exact edge + 5-minute + day type + season
-> edge + 15-minute + weekday/weekend
-> similar edge cluster + time bucket
-> road class + region + time bucket
-> legal/free-flow/default profile speed
```

Blend levels by sample support instead of hard switching. Store median and quantiles,
holiday/event regimes and version. Historical calculations use traversal event time and
local road timezone. A future departure uses predicted/historical traffic by future
arrival bucket, not current speed for every edge.

## 10. Time-dependent route baseline

```text
function baselineETA(route, departure, featureSnapshot):
    t = departure
    total = 0
    edgeFeatures = []
    for edgeSegment in route.orderedEdges:
        live = featureSnapshot.live(edgeSegment.edgeId)
        source = live if freshAndConfident(live, t)
                      else historical(edgeSegment.edgeId, t)
        speed = clamp(source.expectedSpeed, MIN_PROFILE_SPEED,
                      maxAllowedFor(edgeSegment.edgeId))
        duration = edgeSegment.lengthFractionMeters / speed
                   + turnAndIntersectionDelay(previous, edgeSegment, t)
        edgeFeatures.add(source, t, duration)
        t += duration
        total += duration
    return total, edgeFeatures
```

Because time advances, later edges use their expected arrival bucket. Iterate once or
twice if time-bucket changes materially. Routing edge costs should satisfy FIFO or use
appropriate time-dependent algorithms.

## 11. Model and feature design

Static features: edge length/class/speed limit/lanes/intersection/turn/toll/grade,
route distance/classes/turns/urbanity. Dynamic: live/historical speed/confidence/age,
incident severity, weather/event, departure calendar and upstream/downstream congestion.
Context: travel profile and privacy-safe vehicle class—not protected/user identity unless
lawful, necessary and evaluated.

A robust design predicts a positive correction/residual/quantiles over physics baseline:

```text
finalMedian = max(MIN_DURATION, baselineDuration + modelResidual(features))
[p10,p50,p90] = calibratedQuantileModel(route/segment features)
```

Tree/linear models offer fast inference and explanation; sequence/graph models may
improve correlations but increase cost/rollback complexity. Version every feature
definition/default/max-age and include missingness indicators.

## 12. Uncertainty and calibration

Edge errors are correlated by corridor/incident, so summing independent variances
understates route uncertainty. Predict route/segment quantiles directly or model
correlation groups, then calibrate per region, time, route length, traffic regime,
profile and prediction horizon. A 90% interval should contain actual arrival near 90%
of the time in each important slice.

Widen interval for stale/missing live data, sparse region, active incidents, long future
horizon or off-route uncertainty. Return reason/confidence internally and avoid precise
minute claims when interval is broad.

## 13. Online serving logic

```text
function predictETA(request, deadline):
    route = routeService.resolveAndPin(request.route, request.graphVersion)
    bundle = modelRegistry.activeCompatible(route.region, route.profile)
    cacheKey = hash(route.edges/fractions, departureBucket, route.graphVersion,
                    trafficGeneration(route.corridor), bundle.version)
    if safe cache hit: return cached

    features = featureStore.batchGet(unique(route.edgeIds), deadline.featureCutoff)
    baseline, assembled = baselineETA(route, request.departureTime, features)
    if bundle and requiredFeaturesValid(assembled):
        prediction = bundle.infer(baseline, route, assembled)
        prediction = calibrate(prediction, bundle.calibration)
    else:
        prediction = historicalFallback(baseline, assembled, widerInterval=true)
    log versions/features asynchronously and cache under short versioned key
    return prediction
```

Strict stage budgets and circuit breakers prevent feature/model outage from exceeding
caller deadline. Never silently substitute graph-incompatible edge features/model.

## 14. Navigation updates and rerouting

Map-match progress to current route edge/offset with session sequence. ETA uses remaining
fraction plus updated traffic and observed trip delay. Smooth display updates to avoid
jitter, but immediately reflect hard closure/major delay. Do not carry already incurred
delay twice.

Reroute compares current-route predicted arrival with candidate alternative including
turnaround/route-switch cost and uncertainty. Require material improvement, persistence
and cooldown (hysteresis), unless current path is closed/illegal. Frequent oscillation
confuses users and can create traffic feedback loops; diversify routes and cap network-
wide concentration where appropriate.

## 15. Caching and scaling

- Cache static route features by `(route_hash, graph_version)` long; live result by
  route/corridor traffic generation and departure bucket briefly.
- Quantize common origins/destinations for dispatch matrix cache, but final route/ETA
  uses exact snapped points and access.
- Multi-get unique edges and reuse feature blocks across batch routes; microbatch model
  inference only within latency budget.
- Partition live edge store by graph tile/edge hash and replicate hot commute regions.
- Regional serving pins local graph/model/historical artifacts; traffic overlays stream
  nearby. Admission caps giant batch matrices and adversarial looping routes.

## 16. Training labels and leakage prevention

A valid outcome requires coherent navigation session/route version, reliable start/
arrival/traversals, no privacy opt-out, and explicit handling of stops, reroutes and
abandonment. Train each prediction horizon on information available at prediction time.
Use point-in-time feature join keyed by source watermark/version—never today's finalized
traffic aggregate to train a prediction made before those observations existed.

Correct for selection bias: probes overrepresent certain phones/fleets/regions/routes,
and navigation choices respond to prior ETAs. Evaluate non-navigation/held-out fleets
where permitted, weight cohorts, and monitor feedback-loop effects.

## 17. Model rollout and rollback

Artifact bundle includes model, feature schema/defaults, supported graph/profile,
training dataset/offsets, calibration and signature. Flow:

```text
REGISTERED -> OFFLINE_VALIDATED -> SHADOW -> REGIONAL_CANARY -> EXPERIMENT -> ACTIVE
```

Gates include MAE/median/percentiles, interval coverage, bias by slice, tail incidents,
latency/resources, reroute behavior and business guardrails. Automatically stop/rollback
on segmented regression or version/default anomalies. Retain known-good model and
historical-only fallback.

## 18. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Live traffic stream lags | Expire values, use historical prior, widen interval |
| Map matching confidence low | Drop/downweight observation; do not poison edge |
| Feature shard times out | Partial historical/static assembly with missing indicators |
| Model server fails | Physics/historical baseline plus calibrated fallback |
| New model regresses region | Halt canary/rollback compatible previous bundle |
| Incident feed fails | Continue live/historical and declare source age; routing handles known closures |
| Graph/model versions mismatch | Reject model and use compatible fallback |
| Cache stale after closure | Closure/traffic generation and hard route validation bypass it |
| Region fails | Route to replica with same graph/model and available overlay freshness |

## 19. Security and privacy

Authenticate probe/source/caller services, sign model/artifact manifests, use mTLS,
field encryption, role/region access, sandbox input decoders, audit feature/model/
incident changes and rate-limit expensive routes/batches. Prevent fake GPS/probe farms,
traffic/incident poisoning, model/artifact tampering, route enumeration, membership
inference, raw trace access, malicious geometries and insider home/work lookup.

Collect probes only with clear purpose/consent, rotate pseudonyms, aggregate with minimum
cohorts, cap contributor influence, minimize precision/retention and enforce deletion/
residency/legal hold. Avoid logging route endpoints/raw traces. Measure geographic/
device/community bias and provide safe behavior for emergency/accessibility/truck routes.

## 20. Observability

Track serving/stage p50/p95/p99, QPS/errors/fallback/cache hit, edges/route/batch size,
feature multi-get age/missing/default/confidence, traffic event-time/processing lag and
coverage, traversal contributors/outliers/map-match confidence, historical backoff level,
model inference/version skew, ETA MAE/MAPE/median/p90/p99, signed bias and p10/p90 coverage
by region/time/profile/horizon/length/traffic, reroute frequency/regret/oscillation,
incident response, drift and cost/prediction.

Golden routes/outcomes cover free-flow, commute, incidents, sparse regions, DST, long
routes and reroutes. Property-test baseline nonnegative/time propagation and fallback.
Shadow/canary replay exact point-in-time features. Load-test batch/hot corridors, kill
stream/feature/model/cache/region, poison probes, and reconcile prediction logs/versions
with outcomes and evaluation completeness.

## 21. Implementation path

1. **MVP:** route edges, free-flow/historical speed profiles, time-dependent sum,
   fixed uncertainty, versioned API/cache and outcome logging.
2. **Live traffic:** consented sequence probes, map matching, robust window aggregates,
   live feature store/expiry, historical backoff and incident inputs.
3. **Learned ETA:** point-in-time feature pipeline, route quantile/residual model,
   calibration, shadow/canary/rollback, navigation updates and reroute hysteresis.
4. **Hardening:** regional scale, poisoning/privacy/bias controls, golden/property/
   batch-load/chaos tests, artifact/restore drills, runbooks, dashboards, and SLOs.

## 22. Final design

Turn consented location sequences into confidence-weighted directed-edge traversals,
then robust event-time live speeds with privacy thresholds and expiring freshness.
For a pinned route, select live or hierarchical historical features and propagate time
edge by edge; a versioned calibrated model predicts residual/quantiles and falls back
cleanly to the physical baseline. Progress updates recompute only the remaining path,
while reroute hysteresis prevents oscillation. Point-in-time labels, segmented interval
calibration, canary rollout and explicit source/model versions make ETA measurable,
explainable and resilient instead of a single opaque timestamp.
