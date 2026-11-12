# Performance Testing and Optimization

This repository is a practical learning path for measuring, testing, and
improving software performance. It covers optimization strategy across the
backend, database, cache, frontend, network, and observability layers, followed
by runnable Python demonstrations and a complete Locust curriculum.

## Learning path

### 01 — Foundations

1. [Performance testing fundamentals](docs/01-foundations/01-performance-testing-fundamentals.md)
2. [Measurement-first optimization strategy](docs/01-foundations/02-measurement-first-optimization-strategy.md)

### 02 — Optimization strategies

1. [Backend and runtime optimization](docs/02-optimization-strategies/01-backend-and-runtime-optimization.md)
2. [Database and caching optimization](docs/02-optimization-strategies/02-database-and-caching-optimization.md)
3. [Frontend and network optimization](docs/02-optimization-strategies/03-frontend-and-network-optimization.md)
4. [Observability and capacity planning](docs/02-optimization-strategies/04-observability-and-capacity-planning.md)

### 03 — Locust

1. [Locust fundamentals](docs/03-locust/01-locust-fundamentals.md)
2. [Installing and running Locust](docs/03-locust/02-installing-and-running-locust.md)
3. [Testing HTTP methods](docs/03-locust/03-testing-http-methods.md)
4. [Organizing Locust tasks](docs/03-locust/04-organizing-tasks.md)
5. [Load models and custom shapes](docs/03-locust/05-load-models-and-custom-shapes.md)
6. [Advanced Locust patterns](docs/03-locust/06-advanced-patterns.md)
7. [Automation and distributed scaling](docs/03-locust/07-automation-and-distributed-scaling.md)

### 04 — Complex systems optimization

1. [Landscape and system laws](docs/04-complex-systems/01-optimization-landscape-and-system-laws.md)
2. [Measurement and experimentation](docs/04-complex-systems/02-measurement-profiling-and-experimentation.md)
3. [Algorithms, CPU, and compilers](docs/04-complex-systems/03-algorithms-cpu-and-compiler-optimization.md)
4. [Concurrency and backpressure](docs/04-complex-systems/04-concurrency-scheduling-and-backpressure.md)
5. [Memory, GC, and locality](docs/04-complex-systems/05-memory-garbage-collection-and-data-locality.md)
6. [Storage, filesystems, and I/O](docs/04-complex-systems/06-storage-filesystem-and-io-optimization.md)
7. [Relational databases](docs/04-complex-systems/07-relational-database-optimization.md)
8. [NoSQL, cache, and search](docs/04-complex-systems/08-nosql-cache-search-and-specialized-data-systems.md)
9. [Distributed systems](docs/04-complex-systems/09-distributed-systems-partitioning-and-consistency.md)
10. [Network, edge, API, and protocols](docs/04-complex-systems/10-network-edge-api-and-protocol-optimization.md)
11. [Messaging and data pipelines](docs/04-complex-systems/11-messaging-streaming-and-data-pipeline-optimization.md)
12. [Service architecture](docs/04-complex-systems/12-service-architecture-and-workload-shaping.md)
13. [Cloud, Kubernetes, and autoscaling](docs/04-complex-systems/13-cloud-containers-kubernetes-and-autoscaling.md)
14. [Resilience and tail latency](docs/04-complex-systems/14-resilience-overload-and-tail-latency.md)
15. [Observability and capacity](docs/04-complex-systems/15-observability-capacity-and-continuous-optimization.md)
16. [Frontend, mobile, and clients](docs/04-complex-systems/16-frontend-mobile-and-client-performance.md)
17. [Analytics, ML, AI, and GPU](docs/04-complex-systems/17-analytics-ml-ai-and-gpu-optimization.md)
18. [Security, cost, energy, and governance](docs/04-complex-systems/18-security-cost-energy-and-governance.md)
19. [Decision matrix and playbooks](docs/04-complex-systems/19-decision-matrix-and-optimization-playbooks.md)

The sequence numbers restart inside each topic so a reader can complete one
track at a time without losing the overall structure. The advanced track is a
cross-layer reference for large distributed and data-intensive systems.

## Unified Locust notebook

[Open the complete Locust test collection](all_locust_tests.ipynb) to browse all
24 locustfiles in one Jupyter notebook. Every test remains in its own labeled
code cell and links back to the canonical runnable source path.

## Optimization demonstrations

| Demonstration | Concept |
| --- | --- |
| `algorithmic_complexity.py` | Replace repeated linear scans with indexed lookup |
| `benchmarking.py` | Compare implementations with repeatable measurements |
| `ttl_cache.py` | Add bounded-lifetime caching with deterministic tests |
| `batching.py` | Reduce expensive boundary crossings through batching |
| `sqlite_index.py` | Compare SQLite query plans before and after an index |

Run every standalone demonstration:

```sh
for example in optimization_examples/*.py; do python "$example"; done
```

## Example index

| Example | Topic | Target service |
| --- | --- | --- |
| `locust_001` | First GET request | httpbin |
| `locust_002` | Weighted tasks | httpbin |
| `locust_003` | GET requests and query parameters | JSONPlaceholder |
| `locust_004` | POST requests | JSONPlaceholder |
| `locust_005` | Response validation | JSONPlaceholder |
| `locust_006` | PUT requests | JSONPlaceholder |
| `locust_007` | DELETE requests | JSONPlaceholder |
| `locust_008` | Direct weighted tasks | JSONPlaceholder |
| `locust_009` | Repeating ordered tasks | JSONPlaceholder |
| `locust_010` | Grouped random tasks | JSONPlaceholder |
| `locust_011` | A sequential user journey | JSONPlaceholder |
| `locust_012` | Nested task sets | JSONPlaceholder |
| `locust_013` | Constant concurrent-user load | JSONPlaceholder |
| `locust_014` | Constant task throughput | JSONPlaceholder |
| `locust_015` | Step load | JSONPlaceholder |
| `locust_016` | Spike load | JSONPlaceholder |
| `locust_017` | Fixed iteration pacing | JSONPlaceholder |
| `locust_018` | User lifecycle and state | JSONPlaceholder |
| `locust_019` | Response correlation | JSONPlaceholder |
| `locust_020` | Task tags and filtering | JSONPlaceholder |
| `locust_021` | Multiple user classes | JSONPlaceholder |
| `locust_022` | Automated thresholds | JSONPlaceholder |
| `locust_023` | Custom CLI arguments | JSONPlaceholder |
| `locust_024` | Faster HTTP client | JSONPlaceholder |

## Quick start

Create and activate a virtual environment:

```sh
python3 -m venv .locust_venv
source .locust_venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the first example:

```sh
locust -f locust_tests/locust_001/locustfile.py \
  --host=https://httpbin.org
```

Open <http://localhost:8089>, start with a small user count, and observe the
statistics. Stop the test with `Ctrl+C` when finished.

## Repository validation

Run the offline validator after changing a guide or example:

```sh
python scripts/validate_repository.py
```

It checks Markdown links and fences, code-block synchronization, Python syntax,
optimization demonstrations, Locust discovery, custom shape boundaries, and
screenshot integrity.

## Safety

Only load-test systems you own or have explicit permission to test. The public
demo services in these examples are for learning, so use a very small number of
users and a low spawn rate.

## References

- [Locust documentation](https://docs.locust.io/en/stable/)
- [JSONPlaceholder guide](https://jsonplaceholder.typicode.com/guide/)
- [httpbin](https://httpbin.org/)
