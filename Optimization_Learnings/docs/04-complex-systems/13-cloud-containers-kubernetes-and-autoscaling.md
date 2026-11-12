# Cloud, Containers, Kubernetes, and Autoscaling

Infrastructure optimization matches resource shape, placement, and elasticity
to measured workload behavior. Autoscaling is a delayed feedback loop, not a
substitute for capacity planning or overload protection.

## Resource selection

- Benchmark compute families against unit cost and tail latency.
- Match CPU, memory, storage, network, and accelerator ratios to the workload.
- Use local storage only for reconstructable or replicated state.
- Select burstable capacity only when credit depletion is acceptable.
- Use preemptible or spot capacity for checkpointable, replicated, or deferrable
  work.
- Avoid architectures tied to peak-size instances when horizontal partitioning
  is practical.

## Container optimization

- Use small images and remove unused tools and package metadata.
- Order layers to maximize build and distribution cache reuse.
- Minimize startup initialization and dependency discovery.
- Set requests from observed normal demand and limits from safe tested behavior.
- Include runtime, native, page-cache, and sidecar memory.
- Handle termination, draining, and in-flight completion.
- Avoid CPU limits that create throttling for latency-sensitive workloads unless
  isolation requires them and behavior is measured.

## Kubernetes placement

- Use topology spread for availability without excessive cross-zone traffic.
- Apply affinity for data or accelerator locality and anti-affinity for failure
  isolation.
- Keep requests accurate so scheduling and node autoscaling work correctly.
- Use priority and disruption budgets for critical workloads.
- Separate incompatible workload classes into suitable node pools.
- Account for daemon, system, and eviction headroom.

## Autoscaling signals

| Signal | Useful for | Risk |
| --- | --- | --- |
| CPU utilization | CPU-bound steady work | Misses waiting and queue pressure |
| Memory | Memory-scaled workers | Slow, unsafe scale-down signal |
| Request rate | Similar-cost requests | Ignores operation cost |
| In-flight work | Concurrency-bound service | Needs correct limit |
| Queue depth or age | Async consumers | Can move overload downstream |
| Latency | User-visible pressure | Lagging and unstable alone |
| Custom work units | Heterogeneous workload | Requires accurate cost model |

Use leading signals when startup is slow. Combine minimum capacity, maximum
capacity, stabilization windows, step limits, and predictive scaling for known
cycles. Scale on queue age rather than depth when processing costs vary.

## Coordinating scaling layers

- Horizontal scaling changes replicas.
- Vertical scaling changes per-instance resources.
- Node scaling changes cluster capacity.
- Database and dependency limits remain separate constraints.

Avoid control loops that fight each other. Ensure pods can be scheduled before
replica targets rise, and ensure downstream capacity can accept the new
parallelism. Test scale from zero, rapid spikes, scale-down, and zone loss.

## Capacity pools

Maintain warm capacity for startup delay, failover, deployments, and load
variance. Reserve capacity for recovery and control traffic. Use separate pools
for latency-sensitive, batch, GPU, and interruptible work.

## Multi-region and edge

- Route to healthy nearby capacity while preserving data semantics.
- Avoid active-active complexity when active-passive meets objectives.
- Pre-position immutable content and model artifacts.
- Include cross-region bandwidth and replication in unit economics.
- Verify each region can handle its failover share without cascading overload.

## Sources

- [Kubernetes workload autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/)
- [Kubernetes node autoscaling](https://kubernetes.io/docs/concepts/cluster-administration/node-autoscaling/)
- [Google Cloud resource optimization](https://docs.cloud.google.com/architecture/framework/cost-optimization/optimize-resource-usage)
