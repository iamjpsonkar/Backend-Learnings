# Complete Solution: API Gateway

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Provide one controlled external API entry point: TLS termination, routing,
authentication, coarse authorization, quotas, schema/size checks, versioning,
request/response transformations where necessary, consistent errors, and
observability. The gateway must remain stateless and add under 10 ms p99 regional
latency while sustaining 1 million requests/second globally.

Business rules, database transactions, and service-specific orchestration stay in
backend services. The gateway is not an enterprise service bus.

## 2. Capacity estimation

Assume 20 regions, busiest region at 150K requests/s, 25 KB average total payload,
and 20K routes across tenants/environments.

```text
peak payload throughput = 150K * 25 KB ~= 3.75 GB/s per busy region
```

Capacity must cover TLS CPU, JSON validation/transformation CPU, concurrent
streams, buffers, authentication cache misses, access-log volume, and loss of one
zone. Keep gateway utilization low enough that it can shed downstream overload
rather than become the first bottleneck.

## 3. Route and policy model

```text
Route(host, method, path_template, api_version, upstream,
      auth_policy, scopes, quota_policy, request_schema,
      timeout, retry_policy, transform_chain, max_body_bytes)
PolicySnapshot(version, routes, key_sets, schemas, checksums, signature)
```

Specific routes win over wildcards. Compilation rejects ambiguous matches,
missing upstreams/schemas, unsafe retries, excessive timeouts, and unbounded
transformations.

## 4. Architecture

```text
identity keys/policies ----+
service discovery ---------+--> control plane -> signed snapshots
schemas/routes ------------+                         |
                                                    v
client -> CDN/WAF -> regional gateway fleet -> backend services
                            |    |    |
                      Redis quota  logs/metrics/traces
```

Gateways cache authentication keys, policies, schemas, and service endpoints.
Control plane is never called in the request path. Use a maintained proxy/plugin
runtime rather than writing HTTP parsing and TLS from scratch.

## 5. Step-by-step workflow

1. Edge applies DDoS/WAF controls and forwards trusted client IP metadata.
2. Gateway terminates TLS, enforces protocol/header/body limits, and assigns a
   request/trace ID.
3. One immutable snapshot matches host, method, normalized path template, and API
   version.
4. Authentication verifies credential locally where possible (JWT signature,
   issuer, audience, expiry) or calls a tightly bounded introspection cache path.
5. Authorization checks route scopes/tenant; gateway does not decide object-level
   business ownership.
6. Quota policy consumes regional rate-limit budget.
7. Request schema and safe transformations run with CPU/size bounds.
8. Gateway resolves upstream, applies overall deadline, circuit breaker, and safe
   retry policy, then streams request/response with backpressure.
9. Response maps known platform failures into a consistent error envelope while
   preserving service-defined business status.
10. Metrics/traces/access logs emit asynchronously with sensitive fields redacted.

## 6. Core request pipeline

```text
function handle(request):
    ctx.requestId = validIncomingId(request) or randomId()
    ctx.snapshot = activeSnapshot.get()       // one version for entire request

    rejectIfProtocolUnsafe(request)
    route = ctx.snapshot.routeIndex.match(
        host=request.host, method=request.method, path=request.path)
    if route missing: return error(404, "route_not_found", ctx.requestId)

    if request.body.declaredSize > route.maxBodyBytes:
        return error(413, "payload_too_large", ctx.requestId)

    identity = authenticate(request.credentials, route.authPolicy, ctx.snapshot)
    if identity.invalid: return error(401, "unauthenticated", ctx.requestId)
    if not authorizeScopes(identity, route.requiredScopes):
        return error(403, "forbidden", ctx.requestId)

    quota = limiter.check(canonicalLimitKeys(identity, route), cost=route.cost)
    if not quota.allowed:
        return error(429, "rate_limited", retryAfter=quota.retryAfter)

    validated = validateStreaming(request.body, route.requestSchema,
                                  maxBytes=route.maxBodyBytes)
    transformed = runBoundedTransforms(validated, route.transformChain)

    deadline = deriveDeadline(request, route.timeout)
    result = proxyWithSafeRetry(route, transformed, identity, deadline)
    return normalizePlatformResult(result, ctx.requestId)
```

Order matters: cheap protocol and route rejection occurs before expensive auth and
body work; authorization occurs before forwarding; rate limiting occurs before
backend consumption. Streaming validation must still enforce a hard byte limit.

## 7. Authentication

For JWTs, cache rotating issuer key sets and verify signature, algorithm allowlist,
issuer, audience, expiry/not-before, token type, and required claims. Unknown key ID
triggers one bounded refresh; it must not cause one refresh per malicious token.

Opaque-token introspection uses a short cache keyed by token hash, strict timeout,
and policy-specific failure mode. Never log raw credentials. Revocation-sensitive
routes use shorter caches or push invalidation.

## 8. Authorization boundary

Gateway handles stable coarse policies such as tenant membership and OAuth scope.
Backend checks resource ownership and changing business policy. Otherwise every
new product rule requires a gateway rollout and creates inconsistent authorization
between internal and external calls.

Identity is forwarded in a signed internal assertion or mutually authenticated
channel; strip client-supplied identity headers before adding trusted ones.

## 9. Routing and versioning

- Prefer explicit version in URL/header negotiated by API contract.
- Route templates use normalized path, not raw user-controlled strings.
- Weighted canary uses deterministic hash of tenant/user/request key.
- Discovery provides healthy endpoints; gateway applies zone-aware balancing.
- Configuration activation is atomic and last-known-good survives control-plane
  outage.

## 10. Retry and idempotency

```text
function mayRetry(request, failure, route):
    if deadlineRemaining() < route.minimumAttemptTime: return false
    if not route.retryBudget.tryConsume(): return false
    if failure occurred after response headers: return false
    if request.method in [GET, HEAD, OPTIONS]: return request.body.replayable
    if request.hasValidatedIdempotencyKey and route.supportsIdempotency: return true
    return false
```

The gateway forwards the same idempotency key; the backend owns deduplication and
business result. The gateway cannot guarantee exactly once by itself.

## 11. Transformations and aggregation

Allow declarative bounded transformations: header rename, field projection,
version translation, compression, and standard error mapping. Sandbox plugins,
limit CPU/memory, and version them in snapshots.

Avoid general fan-out aggregation. If a public endpoint requires durable business
orchestration, implement a dedicated backend-for-frontend/service with tests and
ownership. A small read-only aggregation may use parallel calls with one deadline
and explicit partial-result semantics.

## 12. Error model

```json
{
  "error": {
    "code": "rate_limited",
    "message": "Request quota exceeded",
    "request_id": "req_...",
    "retryable": true
  }
}
```

Do not convert every backend error to `500`. Preserve documented business 4xx,
translate platform timeout to `504`, unavailable/circuit-open to `503`, and never
expose stack traces or internal hostnames.

## 13. Configuration rollout

1. Compile and validate all route/policy references.
2. Sign immutable snapshot and canary to a gateway cohort.
3. Gateway validates resources/checksum then atomically swaps snapshot.
4. Compare route-level errors/latency/auth/quota changes.
5. Expand or roll back. Keep previous valid snapshot and key sets.

## 14. Failure handling

| Failure | Behavior |
| --- | --- |
| Gateway instance/zone fails | Edge shifts to healthy capacity; clients retry within their policy |
| Control plane fails | Continue last-known-good routes, schemas, and key sets |
| Identity key refresh fails | Known keys continue; unknown-key tokens follow secure failure policy |
| Rate limiter fails | Per-route explicit fail-open/closed/local fallback |
| Backend fails/slow | Circuit, deadline, safe retry budget, and load shedding bound damage |
| Logging pipeline fails | Bounded buffer/sample/drop access logs; never block request indefinitely |
| Bad transform/config | Canary rollback; sandbox/resource limits contain plugin failure |
| Request body is slow/huge | Header/body deadlines, streaming byte cap, backpressure, connection limits |

## 15. Security

- Modern TLS externally and workload identity/mTLS internally.
- Strict HTTP parsing to prevent smuggling, header confusion, and path traversal.
- WAF and quotas complement, not replace, application validation.
- Separate authenticated admin interface; no public debug/config endpoints.
- Redact credentials, cookies, PII, and sensitive query/body fields.
- Schema/plugin supply chain is signed, reviewed, scanned, and version pinned.
- Per-tenant QPS, bandwidth, connections, and transform CPU prevent noisy neighbors.

## 16. Observability

Measure per-route traffic, p50/p99 and overhead, auth reason codes, key-set age,
authorization rejects, quota rejects/fallbacks, schema failures, upstream status/
latency, retries and amplification, circuit state, transform CPU/errors, request/
response bytes, active connections, config version/age, log drops, and saturation.

Trace gateway filters and upstream attempts under one request trace. Synthetic
tests cover valid/invalid tokens, quota, body limits, timeouts, safe/unsafe retries,
config rollback, control-plane loss, and zone failure.

## 17. Implementation path

1. **MVP:** maintained gateway, TLS, static routing, local JWT verification,
   deadlines, request IDs, consistent errors, and metrics.
2. **Policy:** scopes, regional rate limiting, schemas/size limits, discovery,
   circuits, safe retries, and redacted audit/access logs.
3. **Control plane:** compiled signed snapshots, atomic activation, canaries,
   last-known-good, key rotation, and certificate automation.
4. **Scale and hardening:** regional fleets, tenant isolation, plugin sandboxing,
   chaos/load testing, overload drills, and API lifecycle governance.

## 18. Final design

Use a stateless regional gateway fleet built on a proven proxy, driven by immutable
signed policy snapshots and local caches. The core invariant is that one request is
evaluated against one coherent policy version and forwarded only after protocol,
identity, scope, quota, and bounded validation succeed. Retries never exceed the
original deadline or idempotency/retry budget, so the gateway contains failure
instead of multiplying it.
