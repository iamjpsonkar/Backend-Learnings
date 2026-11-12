# Network, Edge, API, and Protocol Optimization

Network latency comes from distance, name resolution, connection setup,
encryption, congestion, loss, serialization, proxy queues, and server work.
Optimize round trips and bytes before low-level socket controls.

## Reduce round trips

- Co-locate chatty services and their state.
- Batch independent operations and expose bulk APIs.
- Reuse connections, channels, sessions, and authentication context.
- Use multiplexed protocols carefully; one saturated connection can queue work.
- Prefetch predictable dependencies without wasting scarce bandwidth.
- Use streaming for genuinely long-lived flows, not as a default replacement
  for simple requests.
- Collapse service hops and proxy layers that add no policy or ownership value.

## Reduce bytes

- Return only required fields with pagination and bounded responses.
- Use compact binary serialization for proven high-volume internal paths.
- Compress text and structured payloads above a measured threshold.
- Avoid compressing already compressed or tiny content.
- Delta-encode or transfer changes when clients have a valid base version.
- Deduplicate headers and metadata.
- Resize media to device and viewport requirements.

Compression trades CPU, memory, and latency for bandwidth. Benchmark both ends
and protect decompression against size amplification.

## Connection management

- Pool connections by destination, credentials, and protocol settings.
- Bound pool size and acquisition wait.
- Align idle timeouts across client, proxy, load balancer, and server.
- Rotate long-lived connections gradually to rebalance traffic.
- Use keepalive only with coordinated, safe intervals.
- Monitor handshake rate, reuse, resets, queueing, and connection age.

## API design

- Set explicit deadlines and propagate remaining time.
- Make retry-safe operations idempotent or use idempotency keys.
- Return clear overload and retryability signals.
- Support conditional requests with versions or entity tags.
- Use cursor pagination for changing large collections.
- Avoid APIs that require clients to perform N+1 requests.
- Version schemas compatibly to enable independent deployment.

## Load balancing

- Balance by active work or observed latency when requests have unequal cost.
- Use locality-aware routing without trapping traffic in an overloaded zone.
- Apply slow start to cold or newly recovered instances.
- Detect and eject unhealthy endpoints with hysteresis.
- Bound connection stickiness and account for long-lived streams.
- Preserve spare capacity so failover does not overload survivors.

## Edge and content delivery

- Cache immutable assets with content-addressed names and long lifetimes.
- Use surrogate keys or versioned invalidation for shared dynamic content.
- Vary cache keys only on dimensions that change the response.
- Shield origins and coalesce concurrent misses.
- Execute safe personalization or filtering near users when it reduces origin
  and network work.
- Test cold-cache, purge, and regional-origin failure behavior.

## Protocol selection

Choose HTTP request/response, HTTP/2 or HTTP/3 multiplexing, gRPC, WebSocket,
server-sent events, message brokers, or custom transports from semantics,
interoperability, observability, head-of-line behavior, and operational support.
Protocol replacement cannot repair an inefficient call graph.

## Sources

- [gRPC performance best practices](https://grpc.io/docs/guides/performance/)
- [gRPC keepalive](https://grpc.io/docs/guides/keepalive/)
- [HTTP caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)
