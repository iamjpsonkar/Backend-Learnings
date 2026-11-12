# Production Observability — Advanced

**Difficulty**: Advanced
**Profile**: `apps observability`
**Time estimate**: 3–4 hours

---

## Scenario

Build production-grade observability: structured logging, distributed tracing, custom metrics, SLO-based alerting, and runbooks. The goal: achieve observability that would satisfy an SRE team.

---

## Setup

```bash
./run.sh start apps observability
./run.sh status
```

---

## Tasks

### Task 1 — Define SLOs

Write SLOs for sample-api in `SLO.md`:

```markdown
# SLOs — sample-api

## Availability SLO
- Target: 99.5% over 30 days
- Measurement: % of successful requests (2xx/3xx)

## Latency SLO
- Target: 95% of requests complete within 200ms
- Target: 99% of requests complete within 500ms

## Error SLO
- Target: Error rate < 0.5%
```

### Task 2 — SLO-based Prometheus alerts

Write alert rules in `configs/prometheus/rules/slo-alerts.yml`:

```yaml
# Burn rate alert (fast burn: 1h window)
- alert: APIHighErrorBurnRate
  expr: |
    (
      rate(http_requests_total{job="sample-api", status_code=~"5.."}[1h])
      /
      rate(http_requests_total{job="sample-api"}[1h])
    ) > 0.14  # 14x burn rate = using 1.4% error budget per hour
  for: 2m
  labels:
    severity: page
    slo: error_rate
```

Create alerts for:
- Fast burn (1h window, severe)
- Slow burn (6h window, warning)
- Latency P95 > 200ms
- Latency P99 > 500ms

### Task 3 — Structured logging verification

Verify sample-api logs are structured JSON:

```bash
docker logs cloud-learnings-lab-sample-api-1 2>&1 | head -20 | jq .
```

Each log line should have: `timestamp`, `level`, `message`, `logger`, `request_id` (for request logs).

If not structured, modify `apps/sample-api/app.py` to use JSON logging.

Check that Loki can parse the fields:
```logql
{container="sample-api"} | json | level="ERROR"
```

### Task 4 — Custom business metrics

Add custom Prometheus metrics to sample-api:

```python
# Business metrics (not just HTTP metrics)
orders_created = Counter("orders_created_total", "Total orders created",
                         ["customer_tier", "status"])
order_value = Histogram("order_value_dollars", "Order value in dollars",
                        buckets=[10, 25, 50, 100, 250, 500, 1000])
active_carts = Gauge("active_carts", "Number of active shopping carts")
```

Expose them at `/metrics` and verify in Prometheus.

### Task 5 — Trace-based alerting

Create a Grafana alert that fires on high error trace count:

1. Go to Explore → Tempo
2. Query: `{status=error}` (all errored traces)
3. Create alert: > 10 error traces per minute

### Task 6 — Runbook automation

Write a `runbooks/high-error-rate.md`:

```markdown
# Runbook: High Error Rate Alert

## Alert: APIHighErrorBurnRate

### Step 1 — Severity assessment
...

### Step 2 — Identify affected endpoints
```promql
topk(5, rate(http_requests_total{job="sample-api", status_code=~"5.."}[5m]) by (path))
```

### Step 3 — Check recent logs
...

### Step 4 — Escalation path
...
```

### Task 7 — SLO dashboard in Grafana

Build a Grafana dashboard with:
- Error budget remaining (last 30 days)
- Burn rate (1h and 6h)
- P50/P95/P99 latency trends
- Request volume
- Availability over time

This dashboard should be the first thing you open during an incident.

---

## Success criteria

- [ ] SLOs defined with measurable targets in SLO.md
- [ ] SLO burn rate alerts written and loaded in Prometheus
- [ ] Structured JSON logs verified and queryable in Loki with field parsing
- [ ] Custom business metrics exposed and visible in Prometheus
- [ ] Trace-based alert configured in Grafana
- [ ] Runbook written for high error rate alert
- [ ] SLO Grafana dashboard built
