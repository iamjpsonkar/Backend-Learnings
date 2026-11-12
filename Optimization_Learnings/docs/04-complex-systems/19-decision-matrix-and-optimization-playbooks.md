# Decision Matrix and Optimization Playbooks

Use this guide when symptoms are visible but the correct layer is not. Start
with evidence, choose the smallest intervention that addresses the bottleneck,
and predict the next constraint before rollout.

## Symptom-to-strategy matrix

| Symptom | First evidence | Common strategies |
| --- | --- | --- |
| High CPU | CPU profile, IPC, cache misses | Eliminate work, algorithm, batch, vectorize |
| High memory | Heap, allocation, RSS, faults | Bound, stream, compact, fix retention |
| High p99 | Traces, queues, saturation, skew | Deadlines, isolate, remove fan-out, headroom |
| Low throughput | Utilization and wait profile | Pipeline, batch, parallelize, remove contention |
| Rising queue age | Arrival/service rates | Backpressure, shed, add bounded consumers |
| Slow database | Query stats and actual plans | Query, index, schema, statistics, partition |
| Low cache value | Hit ratio, miss cost, evictions | Key/TTL policy, size, coalesce, remove cache |
| Network-heavy | Bytes, RTT, retransmits | Localize, compress, batch, cache, reuse |
| Hot shard | Per-key and partition load | Split, salt, replicate, isolate, rate-limit |
| GC pressure | Allocation profile, live set | Allocate less, compact, resize, collector choice |
| Slow startup | Startup trace and artifacts | Lazy init, smaller image, snapshots, warm pool |
| High cloud cost | Unit cost and utilization | Right-size, schedule, tier, locality, architecture |
| GPU idle | Device trace, input timeline | Feed pipeline, batch, fuse, overlap transfers |
| Retry storm | Attempts per request | Budget, jitter, single layer, shed, circuit break |

## Latency playbook

1. Separate client, queue, service, dependency, and network time.
2. Compare fast and slow traces by route, version, region, and input size.
3. Find serialized critical-path work and remove round trips.
4. Check saturation, lock contention, GC, storage, and hot partitions.
5. Add deadlines and cancellation so abandoned work stops.
6. Validate at p50, p95, p99, errors, and resource cost.

## Throughput playbook

1. Determine whether CPU, memory bandwidth, I/O, network, lock, or dependency
   capacity is limiting.
2. Reduce work per unit and improve data layout.
3. Batch fixed costs and pipeline stages.
4. Add concurrency until the limiting resource is efficiently utilized.
5. Partition state or work to remove contention.
6. Stop when extra workers reduce useful throughput or tail latency.

## Overload playbook

1. Stop retries and nonessential background work from amplifying demand.
2. Reject low-priority work early using the actual constrained dimension.
3. Degrade expensive optional features.
4. Protect healthy partitions, tenants, and dependencies with bulkheads.
5. Restore enough headroom for recovery before gradually returning traffic.
6. Capture the operating envelope and automate regression tests.

## Cost playbook

1. Rank recurring cost by service and successful business unit.
2. Find idle capacity, waste, and duplicated data movement.
3. Match resources and purchase model to workload shape.
4. Reduce storage, transfer, and observability retention safely.
5. Improve software efficiency on the dominant resource.
6. Verify SLO, resilience, and team-operating cost after the change.

## Scaling decision tree

- If one node is inefficient, optimize work and resource shape.
- If one node is efficient but saturated, scale vertically within safe limits.
- If the workload partitions cleanly, scale horizontally.
- If demand is variable, add autoscaling plus headroom and load shedding.
- If state is the bottleneck, improve access patterns before adding replicas or
  shards.
- If coordination dominates, reduce shared state and global operations.
- If geography dominates, move reads, content, and safe computation closer.

## Change checklist

- [ ] Correct baseline, workload, and environment recorded
- [ ] User-visible objective and budgets defined
- [ ] Dominant bottleneck demonstrated
- [ ] Correctness and security tests pass
- [ ] Tail latency, throughput, and resource cost compared
- [ ] Cold, peak, overload, and failure behavior tested
- [ ] Downstream and next bottleneck assessed
- [ ] Canary, rollback, and observability ready
- [ ] Regression guardrail added
- [ ] Documentation and ownership updated

## Track order

Read the advanced track sequentially once, then use this playbook as an index.
For a real incident, begin at the symptom matrix and follow the linked domain in
the repository navigation.
