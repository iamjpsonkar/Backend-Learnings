# Hints — Monitoring Dashboard

---

## Hint 1 — PromQL for request rate

```promql
# Requests per second (5m window)
rate(http_requests_total{job="sample-api"}[5m])

# By status code
rate(http_requests_total{job="sample-api"}[5m]) by (status_code)
```

---

## Hint 2 — Error rate calculation

```promql
# Error rate as ratio (0.0 to 1.0)
sum(rate(http_requests_total{job="sample-api", status_code=~"5.."}[5m]))
/
sum(rate(http_requests_total{job="sample-api"}[5m]))
```

Multiply by 100 for percentage:
```promql
100 * (
  sum(rate(http_requests_total{job="sample-api", status_code=~"5.."}[5m]))
  /
  sum(rate(http_requests_total{job="sample-api"}[5m]))
)
```

---

## Hint 3 — P95 latency

```promql
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{job="sample-api"}[5m]))
  by (le)
)
```

---

## Hint 4 — Grafana panel types

| Metric | Best panel type |
|---|---|
| Request rate over time | Time series |
| Current error rate | Stat (with threshold coloring) |
| P95 latency over time | Time series |
| Active connections | Gauge |
| Cache hit ratio | Bar gauge |

---

## Hint 5 — Grafana alert query

In Alert Rules, the query must return a single number:
```promql
# Scalar value: current error rate
(
  sum(rate(http_requests_total{job="sample-api", status_code=~"5.."}[5m]))
  /
  sum(rate(http_requests_total{job="sample-api"}[5m]))
) * 100
```

Condition: `IS ABOVE 5` (5% error rate threshold)
