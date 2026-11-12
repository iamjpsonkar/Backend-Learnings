# System Design Interview Template

Use this worksheet to keep a design discussion structured. Adapt the depth to the
time available; do not treat every prompt as mandatory.

## 1. Frame the problem

- Users and stakeholders:
- Three core use cases:
- Out of scope:
- Main constraints and assumptions:

## 2. Define measurable requirements

### Functional requirements

1.
2.
3.

### Non-functional requirements

| Quality | Target | Why it matters |
| --- | --- | --- |
| Availability | | |
| Latency (p50/p95/p99) | | |
| Consistency | | |
| Durability | | |
| Recovery time / recovery point | | |
| Data retention | | |
| Privacy and compliance | | |

## 3. Estimate scale

Record assumptions and use ranges when the input is uncertain.

```text
daily active users =
actions per active user per day =
average requests/second = daily actions / 86,400
peak requests/second = average requests/second * peak factor

writes/second =
average record size =
retention period =
replication factor =
storage = writes/second * record size * retention * replication factor

egress bandwidth = responses/second * average response size
concurrent requests = requests/second * average latency in seconds
```

Check whether reads or writes dominate and whether a small set of keys, users, or
regions creates hot spots.

## 4. Define the contract and data

- APIs: method, path, request, response, pagination, and idempotency behavior.
- Events: producer, topic, schema, ordering key, delivery semantics, and consumer.
- Entities: identifiers, relationships, lifecycle, indexes, and retention.
- Consistency boundary: which operations must be atomic or immediately visible?

## 5. Draw the high-level design

Start with the critical path:

```text
client -> edge/load balancer -> stateless service -> cache/database
                                      |
                                      +-> queue -> worker -> object store/search
```

Label synchronous and asynchronous calls, sources of truth, cache ownership,
partition keys, replication, and external dependencies.

## 6. Test the design

Walk through:

- one normal read and write;
- a retry or duplicate request;
- a dependency timeout;
- a server, zone, or region failure;
- a hot partition or traffic spike;
- stale cache data and cache loss;
- schema/API evolution and rollback;
- abuse, unauthorized access, and sensitive-data exposure.

For each critical failure, state the detection signal, user-visible behavior,
recovery mechanism, and acceptable data loss.

## 7. Deep dive and trade-offs

Spend remaining time on the riskiest requirement rather than naming more
technologies. Compare at least two options and state why the chosen one fits the
requirements. Typical deep dives include partitioning, consistency, ranking,
search, media delivery, stream processing, multi-region writes, and cost.

## 8. Operate and evolve

- Service-level indicators: traffic, errors, latency, saturation, freshness, and
  correctness.
- Logs, metrics, traces, dashboards, alerts, and audit records.
- Capacity limits, load shedding, backpressure, and rate limiting.
- Deployment, migration, rollback, disaster recovery, and data repair.
- The first simplification for launch and the next bottleneck at 10x scale.

## Final review

- [ ] Requirements are measurable and assumptions are explicit.
- [ ] Capacity estimates are dimensionally correct.
- [ ] APIs and data ownership are clear.
- [ ] The critical path has no unexplained component.
- [ ] Consistency, failure, security, and operations are addressed.
- [ ] Major trade-offs and rejected alternatives are stated.
