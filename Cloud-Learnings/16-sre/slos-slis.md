← [Previous: SRE Overview](./README.md) | [Home](../README.md) | [Next: Error Budgets →](./error-budgets.md)

---

# SLIs and SLOs

Service Level Indicators (SLIs) measure what matters to users. Service Level Objectives (SLOs) set the target. Service Level Agreements (SLAs) are the legal promise.

---

## Definitions

| Term | Definition | Example |
|------|-----------|---------|
| **SLI** | A quantitative measure of a service attribute | 95th-percentile latency over 30 days |
| **SLO** | The target value for an SLI | p95 latency < 300ms, 99.9% of the time |
| **SLA** | External contract with penalties for breach | 99.9% monthly uptime; credits if breached |
| **Error budget** | `1 - SLO` — the allowed "budget" for unreliability | 0.1% = 43.8 min/month downtime |

**Key insight**: SLOs should be set slightly tighter than SLAs so you have time to react before breaching SLAs.

---

## Choosing Good SLIs

SLIs should capture the user experience, not internal system behavior.

| Service type | Recommended SLIs |
|-------------|-----------------|
| Request/response (API) | Availability (% successful requests), latency (p95/p99) |
| Data pipeline | Freshness (age of newest data), completeness (% records processed) |
| Storage | Throughput (bytes/s), availability (successful reads), durability |
| Scheduled jobs | Job success rate, job completion time |

```python
# Availability SLI: fraction of requests that succeed
# Good event: HTTP 2xx or 3xx
# Total events: all requests

# Latency SLI: fraction of requests faster than threshold
# Good event: request completed in < 300ms
# Total events: all requests

# Example SLI definitions in YAML (used by SLO tooling)
slis:
  availability:
    events:
      good: 'sum(rate(http_requests_total{status_code!~"5.."}[window]))'
      total: 'sum(rate(http_requests_total[window]))'
  latency:
    events:
      good: 'sum(rate(http_request_duration_seconds_bucket{le="0.3"}[window]))'
      total: 'sum(rate(http_request_duration_seconds_count[window]))'
```

---

## Writing SLOs

```yaml
# SLO specification (YAML format used by Sloth / OpenSLO)
apiVersion: sloth.slok.dev/v1
kind: PrometheusServiceLevel
metadata:
  name: order-api
  namespace: monitoring
spec:
  service: "order-api"
  labels:
    team: backend
    tier: critical

  slos:
    - name: "availability"
      objective: 99.9      # 99.9% — 43.8 min/month error budget
      description: "99.9% of order API requests must succeed"
      sli:
        events:
          errorQuery: |
            sum(rate(http_requests_total{job="order-api",status_code=~"5.."}[{{.window}}]))
          totalQuery: |
            sum(rate(http_requests_total{job="order-api"}[{{.window}}]))
      alerting:
        name: OrderAPIAvailability
        labels:
          category: availability
        annotations:
          runbook: "https://wiki.my-app.com/runbooks/order-api-availability"
        pageAlert:
          labels:
            severity: critical
        ticketAlert:
          labels:
            severity: warning

    - name: "latency"
      objective: 99.0      # 99% of requests faster than 300ms
      description: "99% of order API requests complete in under 300ms"
      sli:
        events:
          errorQuery: |
            sum(rate(http_request_duration_seconds_bucket{job="order-api",le="0.3"}[{{.window}}]))
          totalQuery: |
            sum(rate(http_request_duration_seconds_count{job="order-api"}[{{.window}}]))
```

---

## SLO Windows

```
Short window  (1 hour):  Burn rate alert — catching fast-burning incidents
Medium window (6 hours): Burn rate alert — catching slow degradations
Long window   (30 days): SLO compliance — monthly reporting
```

---

## PromQL: Measure SLO Compliance

```promql
# Availability over last 30 days
(
  sum(increase(http_requests_total{job="order-api",status_code!~"5.."}[30d]))
  /
  sum(increase(http_requests_total{job="order-api"}[30d]))
) * 100

# Latency SLO compliance over 30 days (% of requests < 300ms)
(
  sum(increase(http_request_duration_seconds_bucket{job="order-api",le="0.3"}[30d]))
  /
  sum(increase(http_request_duration_seconds_count{job="order-api"}[30d]))
) * 100

# Current error budget remaining (availability SLO = 99.9%)
(
  1 - (
    sum(increase(http_requests_total{job="order-api",status_code=~"5.."}[30d]))
    /
    sum(increase(http_requests_total{job="order-api"}[30d]))
  )
) / 0.001   # 1 - SLO = 0.001 for 99.9%
# Result: 1.0 = 100% of budget remaining, 0.0 = budget exhausted
```

---

## SLO Tooling

```bash
# Sloth: generates Prometheus rules from SLO spec
brew install slok/sloth/sloth

sloth generate -i slo.yaml -o /tmp/rules.yaml
kubectl apply -f /tmp/rules.yaml

# pyrra: SLO dashboard + alerting
kubectl apply -f https://github.com/pyrra-dev/pyrra/releases/latest/download/kubernetes-monitoring.yaml

# OpenSLO: vendor-neutral SLO spec format
# Supported by: Datadog, Dynatrace, Grafana Cloud, and others
```

---

## Common SLO Targets by Service Tier

| Tier | Availability SLO | Latency SLO | Notes |
|------|-----------------|-------------|-------|
| Tier 0 (critical path) | 99.99% | p99 < 200ms | Payment, auth, order creation |
| Tier 1 (important) | 99.9% | p99 < 500ms | Product catalog, user profile |
| Tier 2 (best-effort) | 99.5% | p99 < 2s | Analytics, reports, search |
| Tier 3 (internal tools) | 99.0% | p99 < 5s | Admin dashboards, batch jobs |

---

## References

- [Google SRE — Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Sloth SLO generator](https://sloth.dev/)
- [OpenSLO specification](https://openslo.com/)
- [SLO Math (Alex Hidalgo)](https://www.alex-hidalgo.com/the-slo-book)

---

← [Previous: SRE Overview](./README.md) | [Home](../README.md) | [Next: Error Budgets →](./error-budgets.md)
