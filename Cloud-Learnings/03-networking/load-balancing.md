← [Previous: Firewalls & VPN](./firewalls-vpn.md) | [Home](../README.md) | [Next: HTTP/HTTPS/TLS →](./http-https-tls.md)

---

# Load Balancing

A load balancer distributes incoming traffic across multiple backend servers, improving availability and scalability. It also provides health checking, SSL termination, and a stable single endpoint for clients.

---

## Why Load Balancing

Without a load balancer:
- One server → single point of failure
- Traffic spikes crash a single instance
- No ability to deploy without downtime

With a load balancer:
- Traffic distributed across multiple instances
- Unhealthy instances are automatically removed
- Rolling deployments without downtime
- Single DNS endpoint; backends can scale independently

---

## L4 vs L7 Load Balancing

### Layer 4 — Transport Load Balancing

Routes traffic based on **IP address and TCP/UDP port** only. Does not inspect the payload.

```
Client  →  L4 LB (sees: src_ip, dst_ip, dst_port=443)  →  Backend
```

- Fast: minimal processing per packet
- TCP pass-through: TLS is terminated at the backend
- Supports any TCP/UDP protocol (not just HTTP)
- Source IP preservation is natural (or via PROXY protocol)
- **AWS equivalent**: Network Load Balancer (NLB)

### Layer 7 — Application Load Balancing

Routes traffic based on **HTTP content**: URL path, host header, query strings, cookies, request method.

```
Client  →  L7 LB (reads: Host header, URL path, cookies)  →  Backend
```

- More CPU-intensive per request
- TLS termination happens at the LB (offloads crypto from backends)
- Can route different paths to different backends
- Can add/remove/modify headers
- Can rewrite URLs
- Enables A/B testing, canary deployments based on headers
- **AWS equivalent**: Application Load Balancer (ALB)

---

## Load Balancing Algorithms

| Algorithm | How it works | Best for |
|-----------|-------------|---------|
| **Round Robin** | Each backend in sequence: 1, 2, 3, 1, 2, 3... | Homogeneous backends, stateless apps |
| **Weighted Round Robin** | More requests to higher-weight backends | Mixed instance types, gradual deployments |
| **Least Connections** | Route to backend with fewest active connections | Long-lived connections (WebSocket, DB proxies) |
| **Weighted Least Connections** | Combine weight and connection count | Different-capacity backends |
| **IP Hash** | Hash client IP → consistent backend | Stateful apps without shared session store |
| **Random** | Pick randomly | Simple, avoids coordination overhead |
| **Least Response Time** | Route to fastest backend | Latency-sensitive APIs |

**AWS ALB uses round-robin** by default with optional sticky sessions (cookie-based).
**AWS NLB uses a flow hash** (based on protocol, source/destination IP and port, TCP sequence).

---

## Health Checks

The load balancer periodically checks backend health and removes unhealthy instances from rotation.

```
Health check types:
  HTTP(S)  — GET /health → expect 200 OK
  TCP      — successful TCP connect
  GRPC     — gRPC health check protocol

Health check parameters:
  Interval:             10s  (how often to check)
  Timeout:              5s   (time to wait for response)
  Healthy threshold:    2    (successes before marking healthy)
  Unhealthy threshold:  3    (failures before marking unhealthy)
```

**Health check endpoint best practices:**
- Use a dedicated `/health` or `/healthz` path
- Check actual dependencies (DB connection, cache) — not just HTTP 200 from a static file
- Return 200 for healthy, 5xx for unhealthy
- Respond within 2 seconds to avoid false positives
- Do not authenticate the health check endpoint (the LB doesn't send auth)

```python
# Example: proper health check endpoint
@app.get("/health")
def health():
    checks = {}
    # Check database
    try:
        db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    is_healthy = all(v == "ok" for v in checks.values())
    status = 200 if is_healthy else 503
    return JSONResponse(content={"status": "healthy" if is_healthy else "unhealthy", "checks": checks}, status_code=status)
```

---

## AWS Load Balancers

AWS offers three types of managed load balancers under the **Elastic Load Balancing (ELB)** service:

### Application Load Balancer (ALB) — Layer 7

```
Internet  →  ALB (port 80/443)  →  Target Groups (HTTP/HTTPS/gRPC)
```

**Features:**
- HTTP/HTTPS/gRPC (HTTP/2 and HTTP/3 supported)
- Routing rules: host header, path, query strings, HTTP method, source IP
- Target types: EC2 instances, IP addresses, Lambda functions, Containers (ECS)
- WebSocket support
- TLS termination with ACM certificates
- Sticky sessions (AWSALB cookie)
- WAF integration
- Access logs to S3
- Request tracing (X-Amzn-Trace-Id header)

**Listener rules order:**
```
Rule 1: If host == api.example.com AND path == /v2/* → forward to tg-api-v2
Rule 2: If host == api.example.com → forward to tg-api-v1
Rule 3: If path == /static/* → forward to tg-cdn
Rule * (default): forward to tg-web
```

```bash
# Create an ALB
aws elbv2 create-load-balancer \
    --name my-alb \
    --subnets subnet-az-a subnet-az-b \
    --security-groups sg-alb \
    --type application

# Create a target group
aws elbv2 create-target-group \
    --name web-tg \
    --protocol HTTP \
    --port 8080 \
    --vpc-id vpc-0def5678 \
    --health-check-path /health \
    --health-check-interval-seconds 10 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3

# Register targets
aws elbv2 register-targets \
    --target-group-arn arn:aws:elasticloadbalancing:...:targetgroup/web-tg/... \
    --targets Id=i-0abc1234,Port=8080 Id=i-0def5678,Port=8080

# Create HTTPS listener
aws elbv2 create-listener \
    --load-balancer-arn arn:...:loadbalancer/app/my-alb/... \
    --protocol HTTPS --port 443 \
    --certificates CertificateArn=arn:aws:acm:...:certificate/... \
    --default-actions Type=forward,TargetGroupArn=arn:...:targetgroup/web-tg/...

# Add a routing rule
aws elbv2 create-rule \
    --listener-arn arn:...:listener/... \
    --priority 10 \
    --conditions Field=path-pattern,Values=/api/* \
    --actions Type=forward,TargetGroupArn=arn:...:targetgroup/api-tg/...
```

### Network Load Balancer (NLB) — Layer 4

```
Internet  →  NLB (TCP/UDP port)  →  Target Groups (TCP/UDP/TLS)
```

**Features:**
- Handles millions of requests per second with ultra-low latency
- Static IP addresses per AZ (or Elastic IPs) — useful for IP allowlisting
- TCP, UDP, TLS, TCP_UDP protocols
- Preserves source IP by default (client IP visible to backend)
- TLS termination at NLB (optional)
- Target types: EC2 instances, IP addresses, ALB (!)
- Used for: non-HTTP protocols, strict firewall rules by IP, gaming, IoT, real-time comms

```bash
# Create an NLB
aws elbv2 create-load-balancer \
    --name my-nlb \
    --subnets subnet-az-a subnet-az-b \
    --type network

# Create TCP target group
aws elbv2 create-target-group \
    --name tcp-tg \
    --protocol TCP \
    --port 8080 \
    --vpc-id vpc-0def5678

# Create listener on port 5432 (e.g., proxying PostgreSQL)
aws elbv2 create-listener \
    --load-balancer-arn arn:...:loadbalancer/net/my-nlb/... \
    --protocol TCP --port 5432 \
    --default-actions Type=forward,TargetGroupArn=arn:...:targetgroup/tcp-tg/...
```

### Classic Load Balancer (CLB) — Legacy

The original AWS load balancer. Operates at both L4 and L7 but with much less flexibility than ALB/NLB. **Do not use for new deployments** — use ALB or NLB instead. AWS has announced CLB end-of-life.

---

## Comparison: ALB vs NLB

| Feature | ALB | NLB |
|---------|-----|-----|
| Layer | 7 (HTTP/gRPC) | 4 (TCP/UDP/TLS) |
| Protocols | HTTP, HTTPS, gRPC | TCP, UDP, TLS |
| Static IP | No (DNS name only) | Yes (one per AZ) |
| Preserve client IP | Via X-Forwarded-For header | Natively (source IP unchanged) |
| WebSocket | Yes | Yes |
| TLS termination | Yes | Yes |
| Content-based routing | Yes (path, host, headers) | No |
| WAF support | Yes | No |
| Lambda targets | Yes | No |
| Extreme throughput | Good | Better |
| Latency | ~1ms extra | Sub-1ms |
| Use when | HTTP API, microservices, content routing | TCP/UDP, static IP, ultra-low latency |

---

## Sticky Sessions

Sticky sessions (session affinity) ensure a client is always routed to the same backend — useful when session state is stored locally (not recommended; prefer shared session stores).

```bash
# Enable sticky sessions on a target group (ALB only)
aws elbv2 modify-target-group-attributes \
    --target-group-arn arn:...:targetgroup/web-tg/... \
    --attributes \
        Key=stickiness.enabled,Value=true \
        Key=stickiness.type,Value=lb_cookie \
        Key=stickiness.lb_cookie.duration_seconds,Value=86400
```

The ALB sets an `AWSALB` cookie on the first response. Subsequent requests with that cookie go to the same target.

---

## Connection Draining / Deregistration Delay

When removing a target (rolling deploy, scale-in), the LB stops sending new requests but keeps existing connections alive for a configurable period.

```bash
aws elbv2 modify-target-group-attributes \
    --target-group-arn arn:...:targetgroup/web-tg/... \
    --attributes Key=deregistration_delay.timeout_seconds,Value=30
```

Set this to match your application's maximum request duration. If requests typically complete in 2 seconds, 30 seconds is safe. If you have long-running jobs (uploads, streaming), increase accordingly.

---

## ALB Access Logs

```bash
# Enable access logs to S3
aws elbv2 modify-load-balancer-attributes \
    --load-balancer-arn arn:...:loadbalancer/app/my-alb/... \
    --attributes \
        Key=access_logs.s3.enabled,Value=true \
        Key=access_logs.s3.bucket,Value=my-access-logs-bucket \
        Key=access_logs.s3.prefix,Value=alb-logs/

# Log format includes: time, client:port, target:port, request_processing_time,
# target_processing_time, response_processing_time, elb_status_code,
# target_status_code, received_bytes, sent_bytes, request, user_agent, ssl_cipher,
# ssl_protocol, target_group_arn, trace_id, domain_name, chosen_cert_arn
```

---

## References

- [AWS ALB documentation](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)
- [AWS NLB documentation](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/introduction.html)
- [ELB comparison](https://aws.amazon.com/elasticloadbalancing/features/)
- [NGINX load balancing guide](https://docs.nginx.com/nginx/admin-guide/load-balancer/http-load-balancer/)
---

← [Previous: Firewalls & VPN](./firewalls-vpn.md) | [Home](../README.md) | [Next: HTTP/HTTPS/TLS →](./http-https-tls.md)
