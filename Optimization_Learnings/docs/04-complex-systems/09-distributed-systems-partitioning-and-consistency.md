# Distributed Systems, Partitioning, and Consistency

Distribution adds capacity and locality but also communication, partial
failure, skew, coordination, and consistency cost. Do not distribute a
component until the scaling or failure-domain benefit exceeds that cost.

## Partitioning strategies

- **Hash partitioning:** Good average balance; weak for range scans.
- **Range partitioning:** Efficient ranges; vulnerable to moving hot ranges.
- **Directory partitioning:** Flexible placement; directory is critical state.
- **Consistent hashing:** Reduces movement during membership changes.
- **Tenant partitioning:** Isolation and locality; large tenants need splitting.
- **Time partitioning:** Natural retention; current partitions can become hot.
- **Composite partitioning:** Combines dimensions to balance access patterns.

Use virtual partitions so physical placement can change independently. Measure
request, byte, storage, and compute skew—not only record count.

## Hot-key and skew controls

- Add write sharding and aggregate on read.
- Replicate immutable or read-heavy hot keys.
- Split large tenants or ranges independently.
- Isolate exceptional workloads into dedicated partitions.
- Use adaptive routing and dynamic partition splitting.
- Cache popular results near consumers.
- Rate-limit single principals or keys before they exhaust a partition.

## Replication choices

- Synchronous replication improves acknowledged durability but adds latency and
  depends on quorum availability.
- Asynchronous replication reduces foreground latency but permits lag and loss
  during failover.
- Leader-based systems simplify ordering but concentrate writes.
- Multi-leader systems improve regional writes but require conflict handling.
- Leaderless quorum systems trade tunable consistency against repair and
  reconciliation complexity.

Measure replication lag in time and business meaning, not only log offsets.

## Consistency optimization

Select guarantees per invariant rather than globally:

- Linearizability for coordination and strict real-time state
- Serializability for multi-operation transactional invariants
- Causal consistency for causally ordered collaboration
- Read-your-writes and monotonic reads for user sessions
- Bounded staleness for replicated serving
- Eventual consistency for commutative or reconcilable state

Weaker consistency can reduce coordination but moves complexity to clients,
conflict resolution, product behavior, and support operations.

## Coordination reduction

- Partition ownership so most writes are single-shard.
- Use commutative, associative, or idempotent operations.
- Allocate ID ranges or use decentralized identifiers.
- Replace global counters with local counters plus aggregation.
- Use leases with fencing tokens when stale owners could write.
- Keep consensus groups small and isolate unrelated state.
- Move cross-shard workflows to sagas with explicit compensation only when
  invariants permit it.

## Geo-distribution

- Serve reads and static content close to users.
- Choose a home region for strongly coordinated writes.
- Route users or tenants consistently to preserve locality.
- Avoid synchronous intercontinental dependencies on latency-critical paths.
- Test partitions, region loss, failback, and divergent-state repair.
- Budget replication bandwidth, egress, and recovery time.

## Distributed correctness tools

Use idempotency keys, deduplication windows, monotonic versions, logical clocks,
checksums, transactional outbox/inbox patterns, and reconciliation jobs. Test
with delayed, duplicated, reordered, and lost messages.

## Sources

- [Google SRE: distributed periodic scheduling](https://sre.google/sre-book/distributed-periodic-scheduling/)
- [Kafka concepts and partitioning](https://kafka.apache.org/42/getting-started/introduction/)
- [Azure partitioning guidance](https://learn.microsoft.com/en-us/azure/architecture/best-practices/data-partitioning)
