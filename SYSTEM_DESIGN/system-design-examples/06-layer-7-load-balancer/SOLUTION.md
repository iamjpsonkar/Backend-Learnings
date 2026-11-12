# Complete Solution: Layer 7 Load Balancer

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Terminate TLS, route HTTP/1.1, HTTP/2, gRPC, and WebSocket traffic by host/path/
headers, select healthy upstreams, reuse connections, enforce deadlines, perform
safe retries, support weighted canaries, and drain endpoints without interruption.

Target 99.999% regional availability, under 5 ms p99 proxy overhead excluding TLS
handshake, and no single control-plane failure affecting already running traffic.

The balancer does not contain business logic or provide end-to-end exactly-once
requests. Application authorization may run at a gateway/service layer.

## 2. Capacity estimation

Assume 2 million requests/second globally, 20 regions, 10x busiest-to-average
regional skew, 20 KB average combined request/response, and 100K long-lived
connections in a large region.

```text
average/region             = 100,000 requests/s
planned busy-region peak   = 300,000 requests/s
payload throughput at peak = 300K * 20 KB ~= 6 GB/s each direction aggregate
```

Network bandwidth, TLS CPU, concurrent streams, memory buffers, and upstream
connections are separate capacity dimensions. Operate each zone with enough spare
capacity to absorb loss of one zone without exceeding safe utilization.

## 3. Configuration model

```text
Listener(id, address, protocol, tls_policy)
VirtualHost(hostnames, routes[])
Route(match, cluster, timeout, retry_policy, hash_policy, filters)
Cluster(id, protocol, load_policy, circuit_breaker, health_policy)
Endpoint(id, address, zone, weight, metadata, state)
ConfigSnapshot(version, checksum, created_at)
```

Configuration is immutable by version. Every accepted request uses one complete
snapshot; it must never observe half an update.

## 4. Architecture

```text
                         control plane
service discovery ---> config compiler/validator ---> signed snapshot stream
                                                       |
client -> anycast/DNS -> regional L7 balancer fleet ----+
                              |      |       |
                              +---- upstream service endpoints

telemetry pipeline <--- metrics, access logs, traces, health results
```

The data plane is stateless aside from connections, local health/circuit state,
and last-known-good configuration. The control plane is not called per request.

## 5. Step-by-step workflow

1. Listener accepts TCP/QUIC, applies connection limits, and negotiates TLS/ALPN.
2. Proxy parses bounded headers and assigns or validates a trace/request ID.
3. It reads exactly one active configuration snapshot.
4. Virtual host and route matcher select the target cluster and policies.
5. Request deadline is derived from route maximum and client deadline.
6. Circuit breaker checks pending requests, connections, and recent failures.
7. Load policy chooses a healthy endpoint, preferring the local zone.
8. Proxy forwards through a pooled connection and streams the body with
   backpressure instead of buffering it entirely.
9. It may retry a safe failure only if method/body are replayable, retry budget is
   available, and enough deadline remains.
10. Response streams to client; metrics/logs/traces record the final and attempted
    upstream outcomes separately.

## 6. Route matching logic

```text
function matchRoute(request, snapshot):
    host = normalizeHost(request.authority)
    virtualHost = snapshot.hostIndex.longestMatch(host)
    if missing: return NoRoute

    for route in virtualHost.routesInPriorityOrder:
        if route.method exists and route.method != request.method: continue
        if not prefixMatch(request.path, route.pathPrefix): continue
        if not allHeaderPredicatesMatch(request.headers, route.headers): continue
        return route
    return NoRoute
```

Reject ambiguous duplicate rules during configuration compilation. The hot path
uses precompiled host/path indexes, not a linear scan of all routes.

## 7. Endpoint selection

Use power of two choices with an effective-load score. It performs nearly as well
as global least-loaded without scanning every endpoint.

```text
function chooseEndpoint(cluster, request):
    candidates = cluster.healthyEndpoints(
        preferZone=request.ingressZone,
        excludeEjected=true,
        snapshotVersion=request.configVersion
    )
    if candidates empty:
        candidates = cluster.healthyEndpoints(anyZone=true)
    if candidates empty: return None

    a = weightedRandom(candidates)
    b = weightedRandom(candidates excluding a)
    return a if score(a) <= score(b) else b

function score(endpoint):
    return (endpoint.activeRequests + endpoint.pendingRequests * 2) /
           max(endpoint.configuredWeight, 1)
```

For sticky state, consistent hashing by a stable cookie/header may be configured,
but stickiness reduces balancing quality and must not replace shared session state.

## 8. Safe retry logic

```text
function proxyWithRetry(request, route):
    deadline = min(request.clientDeadline, now + route.timeout)
    maxAttempts = route.retry.maxAttempts

    for attempt from 1 to maxAttempts:
        endpoint = chooseEndpoint(route.cluster, request)
        if endpoint missing: return ServiceUnavailable

        result = send(endpoint, request, deadline)
        if result.success: return result.response

        if not retryable(result, request): return result.responseOrError
        if not globalRetryBudget.tryConsume(route.cluster): return result.error
        if timeRemaining(deadline) < route.retry.minimumAttemptTime: return Timeout
        if not request.body.isReplayable: return result.error

    return lastResult
```

Retry only connection failure before headers, reset codes explicitly declared
safe, and selected 5xx responses. POST is retried only with application-supported
idempotency. Hedged requests are limited to idempotent reads and a tiny budget.

## 9. Health and circuit breaking

- Active probes detect startup/readiness and total failure.
- Passive health uses real request outcomes to eject an endpoint temporarily.
- Ejection requires minimum volume and bounded percentage to avoid removing an
  entire cluster because of a shared downstream failure.
- Circuit breakers cap active/pending requests, connections, retries, and memory.
- Load shedding rejects early with `503` when proxy capacity is unsafe rather than
  queueing until all requests time out.

Health is not binary truth. An endpoint may be healthy for one route/dependency and
failing for another; track outcome by cluster and endpoint.

## 10. Connection management

Pool upstream connections per endpoint/protocol. Bound idle time, maximum age,
requests per connection, concurrent HTTP/2 streams, pending handshakes, and buffer
bytes. Apply backpressure from slow clients so they cannot force unbounded response
buffers.

For WebSockets/streams, choose endpoint once and keep the connection. Rebalancing
new traffic does not migrate an active stream.

## 11. Draining and deployment

1. Endpoint enters `DRAINING`; discovery stops assigning new requests.
2. Proxy sends HTTP/2 GOAWAY where applicable and closes idle connections.
3. Existing requests/streams receive a bounded grace period.
4. At deadline, remaining connections close and clients reconnect elsewhere.
5. Only then is the process terminated.

Canary traffic uses deterministic hashing to a weighted cluster so one user does
not oscillate versions. Automated rollback watches error/latency/SLO guardrails.

## 12. Configuration rollout

1. Compiler validates references, duplicate routes, certificates, timeouts,
   retry safety, and resource limits.
2. It signs immutable snapshot and distributes to a small balancer cohort.
3. Data plane validates checksum and resources before atomic activation.
4. Control plane compares health and expands rollout.
5. On rejection or regression, retain/revert last-known-good version.

An unavailable control plane cannot erase active configuration.

## 13. Failure handling

| Failure | Behavior |
| --- | --- |
| One balancer fails | Anycast/L4/DNS removes it; clients reconnect to another |
| One zone fails | Traffic shifts within region only if remaining capacity is safe |
| Endpoint fails | Passive/active health ejects it; safe in-flight requests may retry |
| Discovery/control plane fails | Continue last-known-good endpoints/config with staleness alert |
| Bad config | Compiler rejects or canary rollback; snapshots activate atomically |
| Retry storm | Per-cluster retry budget and circuit breaker stop amplification |
| Slow upstream | Deadline, pending limit, backpressure, and load shedding bound resources |
| Certificate update fails | Keep previous valid certificate until alert/expiry deadline |

## 14. Security

- Modern TLS policy, automated certificate rotation, and private-key isolation.
- Mutual TLS to internal services where identity boundaries require it.
- Strict parser limits prevent request smuggling, oversized headers, and slowloris.
- Sanitize hop-by-hop and forwarded headers; trust them only from known hops.
- Restrict admin/config/debug interfaces to a separate authenticated network.
- Access logs redact credentials and sensitive query/header values.
- Tenant/route connection and bandwidth quotas prevent noisy-neighbor exhaustion.

## 15. Observability

Measure request and connection rate, active streams, TLS handshake latency/errors,
per-route and per-endpoint p50/p99, status codes, resets, retries and retry success,
retry-budget exhaustion, circuit ejections, pending queues, load shedding, buffer
bytes, config version/age/rejection, health flaps, zone spillover, and saturation.

Trace each attempt under one client span. Access logs record chosen route, cluster,
endpoint, config version, attempts, bytes, and total/upstream duration.

## 16. Implementation path

1. **Adopt proven data plane:** Envoy, HAProxy, or managed equivalent with static
   routes, TLS, round robin, deadlines, and metrics.
2. **Dynamic fleet:** service discovery, connection pools, active/passive health,
   graceful drain, and zone awareness.
3. **Safe resilience:** circuit breakers, explicit retry policies/budgets,
   backpressure, load shedding, and fault injection.
4. **Control plane:** compiled signed snapshots, canaries, last-known-good state,
   certificate automation, and regional disaster drills.

## 17. Final design

Use a proven stateless L7 proxy fleet with an independent versioned control plane,
power-of-two load selection, zone-aware health, bounded circuit resources, and
deadline-aware idempotency-safe retries. The central invariant is that each request
uses one coherent config version and all retry attempts remain inside the original
deadline and retry budget; the balancer must reduce overload, never amplify it.
