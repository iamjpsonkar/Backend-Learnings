# Complete Solution: Maps and Routing

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Ingest authoritative/community road edits, validate and compile a routable graph and
render tiles, accept closures/incidents/live traffic, snap coordinates, and return
legal routes, alternatives, distance, duration, geometry, and turn instructions for
car, bike, walk, truck, and accessibility profiles. Support route updates without
mixing incompatible map artifacts.

Targets: one billion routes/day, p99 below 500 ms for regional routes and two seconds
for continental routes, 99.99% serving availability, critical closure propagation
below one minute, routine map edits below hours, and calibrated ETA error. Each request
pins one base graph/profile version plus a compatible dynamic-overlay watermark.

## 2. Capacity estimation

One billion routes/day is about 11,600/s average and over 100,000/s commute peak.
Assume 500 million directed road edges, 100 bytes compact base edge, 10% preprocessing
overhead (usually much more depending algorithm), and 2 KB average response.

- Compact edges alone are about 50 GB; geometry, names, turn restrictions, spatial
  indexes, profiles, hierarchy shortcuts, and replicas make regional artifacts hundreds
  of GB globally.
- Peak response egress around 200 MB/s before compression/TLS is regionally cacheable.
- Millions of probe points/s should be map-matched, aggregated, privacy-filtered, and
  reduced to edge speed overlays—not queried raw on the route path.
- Route-cache key space is enormous; cache only popular/quantized origin-destination/
  profile/time buckets with short traffic-aware TTL.

## 3. APIs

```text
POST /v1/routes
{
  "origin": {"lat": ..., "lng": ...},
  "destination": {...},
  "waypoints": [],
  "profile": "car",
  "departureTime": "...",
  "avoid": ["tolls"],
  "alternatives": 2
}
GET /v1/tiles/{z}/{x}/{y}?style=&language=&version=
POST /internal/map-edits                     sourceEventId/version
POST /internal/incidents                     sourceEventId/version/expiry
POST /internal/traffic-probes                session/sequence/batch
```

Bound waypoints, geographic span, alternatives, avoid constraints, vehicle dimensions,
coordinate precision, future departure horizon, batch size, and per-key/user QPS.
Response declares graph/traffic/ETA versions, snapped points, route legs, confidence,
and warnings/partial dynamic-data status.

## 4. Graph model

```text
Node(id, lat_e7, lng_e7, elevation, tile_id, version)
Edge(id, from_node, to_node, geometry_ref, length_mm, road_class,
     access_mask, speed_limit, surface, grade, toll, ferry,
     height_weight_width_limits, conditional_rules, version)
TurnRestriction(from_edge, via_node_or_path, to_edge, type,
                vehicle_profile, time_condition, version)
Place(id, names, point_or_polygon, access_points, category, version)
GraphManifest(version, profile_version, tile_partitions, border_table,
              hierarchy_refs, checksums, built_at, state)
TrafficEdge(edge_id, time_bucket, observed_speed, confidence,
            incident_penalty, closure, source_watermark, expires_at)
```

Edges are directed: one physical road may create two edges with different access or
speed. Model turns by `(previous_edge,current_node)` state or expand turn restrictions
into graph arcs; node-only shortest paths can illegally U-turn or ignore turn bans.

## 5. Architecture

```text
authoritative/community edits -> staging/validation/conflation -> canonical map store
                                                        |
                                             graph/tile/hierarchy builders
                                                        |
                                             immutable object artifacts/manifest
                                                        |
                                          regional distributor/canary rollout

probe/incident/closure events -> map match/aggregate/policy -> dynamic edge overlays

client -> route gateway/cache -> snap service -> hierarchical router
                                               |       |
                                         base graph  overlay/profile costs
                                               |
                                      alternative/ETA/instruction builder
```

Serving nodes memory-map immutable regional graph/hierarchy partitions. A versioned
router table locates border/remote partitions. Tiles and graph derive from compatible
canonical snapshots but are independently CDN-distributed.

## 6. Step-by-step workflow

### Map build

1. Authenticate/source-version and stage edit; validate geometry, topology, attributes,
   temporal rules, provenance, duplicates and conflicts without changing active map.
2. Conflate with canonical entities and apply reviewed change into a snapshot/log.
3. Build directed nodes/edges, intersections, turn restrictions, access profiles,
   spatial indexes, border tables, hierarchy/landmarks, instructions metadata and tiles.
4. Run structural/routing/golden/diff checks, sign checksummed manifest, distribute to
   staging, warm and canary against current version, then atomically activate.

### Route request

1. Validate/profile request and pin graph/profile/overlay/ETA versions.
2. Find plausible directed access-edge candidates for origin/destination using spatial
   index, heading/access/side-of-road and snap distance.
3. Run hierarchical/corridor search then detailed edge/turn-aware A* using live or
   historical time-dependent costs and hard closures/restrictions.
4. Generate sufficiently different alternatives, validate every edge/turn, reconstruct
   geometry/instructions, calculate ETA/confidence/tolls/elevation, and rank.
5. Cache briefly under quantized endpoints/profile/departure and dependency version/
   affected-overlay tokens; return exact snapped points and versions.

## 7. Build and validation logic

```text
function compileSnapshot(snapshot, profileVersions):
    graph = DirectedGraph()
    for road in validatedRoads(snapshot):
        splits = splitAtIntersectionsAndAttributeChanges(road)
        for segment in splits:
            if permitsForward(segment): graph.addEdge(encode(segment, FORWARD))
            if permitsBackward(segment): graph.addEdge(encode(segment, BACKWARD))
    for restriction in snapshot.turnRestrictions:
        require referenced edges connect and rule parses
        graph.addTurnRule(compileConditionalRule(restriction))
    graph.spatialIndex = buildEdgeRTreeOrCellIndex(graph.edges)
    for profile in profileVersions:
        graph.hierarchy[profile] = preprocessHierarchy(graph, profile.staticCosts)
    assertTopologyAndProfileInvariants(graph)
    writeImmutablePartitionsAndSignedManifest(graph)
```

Checks include dangling/unreachable components, impossible coordinates, duplicate
edges, one-way/turn contradictions, ferry/border connectivity, sudden reachability/
route-length changes and sample routes by profile. Human review handles high-impact diffs.

## 8. Snapping logic

```text
function snap(point, profile, optionalHeading):
    candidates = spatialIndex.edgesWithin(point, radius=adaptiveRadius(point))
    scored = []
    for edge in candidates:
        if !profile.mayAccess(edge, departureTime): continue
        projection = closestPointOnPolyline(point, edge.geometry)
        score = distance(point, projection)
                + roadClassPenalty(edge, profile)
                + headingMismatch(optionalHeading, edge.direction)
                + sideOfRoadPenalty(point, edge, profile)
        scored.add(edge, projection, score)
    return scored.sort().take(SNAP_CANDIDATES)
```

Keep multiple candidates near parallel roads/bridges and try candidate pairs in route
search. A coordinate under a flyover must not always snap to the closest planar line.
Return explicit no-routable-access when distance/confidence fails.

## 9. Edge cost function

```text
function edgeCost(edge, arrivalTime, profile, overlay):
    if !profile.mayAccess(edge, arrivalTime): return INFINITY
    if overlay.isHardClosed(edge, arrivalTime): return INFINITY
    speed = overlay.reliableSpeed(edge, arrivalTime)
            ?? historicalSpeed(edge, dayOfWeek(arrivalTime), timeBucket(arrivalTime))
            ?? profile.defaultSpeed(edge.roadClass, edge.speedLimit)
    travelSeconds = edge.lengthMeters / clamp(speed, MIN_SPEED, legalMax(edge))
    return travelSeconds
         + profile.turnCost(previousEdge, edge, arrivalTime)
         + profile.tollFerrySurfaceGradePenalty(edge)
         + overlay.incidentPenalty(edge)
```

For departure-time routing, edge cost is time-dependent; reaching an edge later can
change speed/restrictions. Ensure modeled costs satisfy FIFO (leaving later cannot
arrive earlier on an edge) or use an algorithm that handles non-FIFO waiting explicitly.
Hard constraints are not soft penalties.

## 10. A* core logic

```text
function routeAStar(startStates, goalCandidates, request, graph, overlay):
    open = minHeap()
    best = map state -> INFINITY
    parent = map()
    for start in startStates:
        best[start] = start.snapCost
        open.push(start, start.snapCost + heuristic(start, goalCandidates))

    while !open.empty and withinBudget():
        current, queuedF = open.pop()
        if queuedF > best[current] + heuristic(current, goal): continue
        if isGoal(current, goalCandidates): return reconstruct(parent, current)

        for nextEdge in graph.outgoing(current.node):
            if turnForbidden(current.previousEdge, nextEdge, current.arrivalTime): continue
            cost = edgeCost(nextEdge, current.arrivalTime, request.profile, overlay)
            if cost == INFINITY: continue
            next = State(nextEdge.to, previousEdge=nextEdge.id,
                         arrivalTime=current.arrivalTime + cost)
            candidate = best[current] + cost
            if candidate < best[next]:
                best[next] = candidate
                parent[next] = current, nextEdge
                open.push(next, candidate + admissibleHeuristic(next, goal))
    return NO_ROUTE_OR_TIMEOUT
```

A safe heuristic is straight-line distance divided by maximum possible speed; landmarks
(ALT) tighten it while remaining admissible. State must include enough turn/time context.

## 11. Hierarchical routing

Plain A* explores too much continent-scale graph. Preprocessing options include
contraction hierarchies (CH), customizable CH, multi-level Dijkstra, and ALT landmarks.
Contract low-importance nodes and add shortcuts that preserve shortest distances; query
searches upward from both ends and unpacks shortcuts.

Pure CH handles static weights extremely fast but live traffic changes shortcut weights.
Customizable CH separates topology preprocessing from fast weight customization;
alternatively use hierarchy to identify a corridor, then detailed A* with overlay.
Hard closures must either invalidate affected shortcuts, customize weights, or force
fallback/corridor expansion—never route through a closed constituent edge.

## 12. Geographic partitioning

Partition graph by stable tiles/cells with boundary nodes and cross-partition edges.
Load local region plus neighbor borders in memory; long routes use overlay graph of
region portals/hierarchy and fetch detailed corridor partitions. Replicate dense hot
cities and split tiles without changing stable edge IDs.

A request pins one graph manifest. Remote partition responses include version/checksum;
never combine topology partitions from incompatible versions. If a partition misses
deadline, retry replica or return explicit degraded/no-route, not a route with a gap.

## 13. Traffic and incident overlay

Probe pipeline validates consent/device/session sequences, removes impossible points,
map-matches trajectories probabilistically, derives traversal time, aggregates robustly
by edge/time bucket, removes outliers/bots, applies k-anonymity/privacy thresholds, and
publishes speed/confidence with expiry. Historical baselines fill sparse edges.

Incident/closure inputs have provenance, severity, direction, geometry, validity window,
confidence and version. Authoritative closures override probe speeds. Events map to edge
IDs, update regional overlays and invalidate dependency-aware caches. Expired incidents
fall out automatically; contradictory sources are fused/reviewed by policy.

## 14. Alternative routes

Do not return the same path with one different turn. Generate alternatives using
penalized-edge reruns, k-shortest loopless paths, or corridor branch points, then filter:

```text
overlap(candidate, best) = sharedLength / min(candidateLength, bestLength)
accept if overlap < threshold
       and duration <= bestDuration * maxStretch
       and all hard constraints pass
```

Rank by time, reliability, distance, tolls, complexity, safety/profile preferences and
route diversity. Revalidate turn/access/closure for every candidate after unpacking.

## 15. ETA and instructions

Base ETA sums time-dependent edge/turn costs. A calibrated model corrects systematic
bias using departure time, region, road classes, traffic confidence, weather/events,
route length/turns and recent residuals. Train with point-in-time features; output median
and intervals, not false precision. Routing remains functional with historical speeds/
heuristic ETA if model fails.

Instruction builder groups edges by name/class/geometry and emits maneuvers at turn,
merge, exit, roundabout, ferry and destination. Validate lane/sign/name language and
avoid telling a user to perform an illegal maneuver. Geometry simplification preserves
critical junctions and endpoints.

## 16. Map tiles and offline packs

Build vector tiles from the same canonical snapshot: roads, land, water, buildings,
boundaries and labels with stable feature IDs. Immutable URL includes data/style/
language version and uses long CDN TTL. Style changes need not rebuild topology.

Offline pack manifest contains region/profile graph/tile shards, checksums, version,
expiry and incremental deltas. Client atomically swaps verified pack and uses local
routing/tiles; it clearly labels stale traffic/closures and can fetch emergency overlay
when connected.

## 17. Rollout and cache consistency

Manifest lifecycle is `BUILDING -> VALIDATED -> CANARY -> ACTIVE -> RETIRED`. Distribute
all artifacts before activation, verify signatures/checksums/schema, warm representative
routes, shadow compare with current, and canary by traffic cohort/region. Retain prior
generation for rollback. In-flight requests hold snapshot reference.

Route cache key includes quantized origin/destination/waypoints, profile/vehicle/avoid,
departure bucket, base graph, traffic/closure generation and ETA model. Closures can
invalidate by edge-to-cache reverse dependency or short TTL/regional generation. Always
recheck hard closure/policy before serving a cached route.

## 18. Failure handling

| Failure | Correct behavior |
| --- | --- |
| New graph artifact corrupt | Checksum/probes reject before activation; keep prior |
| One routing partition fails | Use replica/hedge; never return disconnected geometry |
| Traffic pipeline lags | Fall back by confidence to historical speeds and flag version |
| Closure event arrives | Hard overlay blocks edge and invalidates affected cache |
| ETA model fails | Return summed historical/live cost with wider confidence |
| Cache fails | Route underlying graph with admission control |
| Snap is ambiguous | Evaluate multiple directed candidate pairs |
| Search exceeds deadline | Return best proven route/degraded result per contract |
| Region fails | Route to replicated fleet holding same manifest |

## 19. Security, safety, and privacy

Authenticate edit/incident/probe sources, sign manifests, use mTLS/service roles,
sandbox parsers/builders, encrypt sensitive telemetry, audit edits/closures/admin and
restrict raw traces. Prevent SSRF through external sources, malformed geometries,
artifact poisoning, fake closures/traffic, GPS spoofing, bot route scraping, denial via
expensive constraints, and insider movement lookup.

Minimize/aggregate probe histories, rotate pseudonyms, enforce consent/retention/
deletion/residency, and protect home/work in logs. Apply road/accessibility/truck/
hazmat/legal rules, but state that navigation is advisory and use safety guardrails.
High-impact map edits/closures require stronger provenance/review and rapid rollback.

## 20. Observability

Track route/step/snap latency, QPS/errors/timeouts/cache hit, nodes/edges/partitions
visited, hierarchy fallback, no-route/unreachable rate, path length/time/turn/toll,
alternative diversity, graph/profile/overlay/model version skew, build/validation/
rollout age, closure propagation/cache invalidation, traffic coverage/confidence/age,
ETA absolute/percentage/calibration error by cohort, instruction errors, partition hot
spots, and cost/route.

Golden routes cover one-ways, turn bans, time restrictions, ferries, borders, tunnels/
bridges, truck limits, bike/walk/accessibility and closures. Property-test A* against
Dijkstra on sampled subgraphs and CH/customized results against base search. Fuzz map
inputs, shadow graph/model versions, load-test hot commutes, kill partitions/overlays,
and replay incident/traffic streams. Route-quality field reports feed reviewed fixes.

## 21. Implementation path

1. **MVP:** static regional directed graph, spatial snap, profile access, turn-aware
   Dijkstra/A*, route geometry/distance/static ETA, immutable manifest, and basic tiles.
2. **Fast/reliable:** CH/ALT hierarchy, graph partitions/replicas, route cache, atomic
   artifact rollout/rollback, alternatives, instructions, and golden correctness tests.
3. **Dynamic/global:** probe aggregation, historical/live traffic and closures,
   customizable/corridor routing, ETA model, continental borders, offline packs.
4. **Hardening:** provenance/security/privacy/safety lifecycle, property/fuzz/shadow/
   hot-load/chaos tests, restore/build drills, runbooks, dashboards, and SLOs.

## 22. Final design

Compile validated map sources into immutable compatible directed-graph, turn-rule,
hierarchy, spatial-index, border and tile artifacts. A request pins one manifest, snaps
to several plausible directed edges, uses hierarchy to bound search, and runs detailed
turn-aware time-dependent A* with fresh closures/traffic. Alternatives are diversity-
filtered and ETA-calibrated. Atomic signed rollout and historical fallback keep routing
available, while versioned overlays deliver minute-level change without rebuilding the
entire base graph.
