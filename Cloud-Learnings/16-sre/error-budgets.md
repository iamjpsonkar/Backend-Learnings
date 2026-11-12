← [Previous: SLIs & SLOs](./slos-slis.md) | [Home](../README.md) | [Next: Toil Reduction →](./toil-reduction.md)

---

# Error Budgets

An error budget is the acceptable amount of unreliability for a given period, derived from your SLO. It aligns engineering and operations: when the budget is healthy, move fast; when it's exhausted, stop feature work and fix reliability.

---

## Error Budget Math

```
SLO: 99.9% availability
Error budget: 100% - 99.9% = 0.1%

Over 30 days (2,592,000 seconds):
  Allowed downtime:    2,592,000 × 0.001 = 2,592 seconds ≈ 43 minutes

Over 7 days:
  Allowed downtime:    604,800 × 0.001 = 604 seconds ≈ 10 minutes

For request-based SLOs (1,000 requests/min × 60 min × 24 hr × 30 days = 43.2M requests/month):
  Allowed failures:    43,200,000 × 0.001 = 43,200 failed requests
```

| SLO | Monthly downtime | Weekly downtime |
|-----|-----------------|-----------------|
| 99.0% | 7h 18m | 1h 41m |
| 99.5% | 3h 39m | 50m |
| 99.9% | 43m 48s | 10m 4s |
| 99.95% | 21m 54s | 5m 2s |
| 99.99% | 4m 22s | 1m 0s |

---

## Burn Rate

Burn rate measures how fast you are consuming your error budget relative to the expected rate.

```
Burn rate = (current error rate) / (error budget rate)

Budget rate for 99.9% SLO = 0.001 (0.1% errors allowed)

If current error rate = 5%:
  Burn rate = 5% / 0.1% = 50x
  At this rate, 30-day budget exhausted in: 30 days / 50 = 14.4 hours
```

### Multi-Window Burn Rate Alerts

```yaml
# PrometheusRule: multi-window burn rate alerts (Google SRE Workbook pattern)
# Fast burn: catches incidents consuming budget quickly
# Slow burn: catches low-grade degradations that exhaust budget over days

groups:
  - name: order-api-error-budget
    rules:
      # Pre-compute error ratios for multiple windows
      - record: job:slo_error_ratio:5m
        expr: |
          sum(rate(http_requests_total{job="order-api",status_code=~"5.."}[5m]))
          /
          sum(rate(http_requests_total{job="order-api"}[5m]))

      - record: job:slo_error_ratio:1h
        expr: |
          sum(rate(http_requests_total{job="order-api",status_code=~"5.."}[1h]))
          /
          sum(rate(http_requests_total{job="order-api"}[1h]))

      - record: job:slo_error_ratio:6h
        expr: |
          sum(rate(http_requests_total{job="order-api",status_code=~"5.."}[6h]))
          /
          sum(rate(http_requests_total{job="order-api"}[6h]))

      - record: job:slo_error_ratio:3d
        expr: |
          sum(rate(http_requests_total{job="order-api",status_code=~"5.."}[3d]))
          /
          sum(rate(http_requests_total{job="order-api"}[3d]))

      # ── Page alert: fast burn (consumes 5% of 30d budget in 1h) ────────────
      # Burn rate > 14.4x for 2min in both 1h and 5m windows
      - alert: OrderAPIBudgetBurnFast
        expr: |
          job:slo_error_ratio:1h{job="order-api"} > (14.4 * 0.001)
          AND
          job:slo_error_ratio:5m{job="order-api"} > (14.4 * 0.001)
        for: 2m
        labels:
          severity: critical
          slo: availability
        annotations:
          summary: "Order API burning error budget at 14.4x rate (page)"
          description: |
            Current 1h error ratio: {{ $value | humanizePercentage }}.
            At this rate, 30-day error budget exhausted in ~2 hours.
          runbook: "https://wiki.my-app.com/runbooks/error-budget-burn"

      # ── Ticket alert: slow burn (consumes 10% of 30d budget in 6h) ─────────
      # Burn rate > 6x for 15min in both 6h and 1h windows
      - alert: OrderAPIBudgetBurnSlow
        expr: |
          job:slo_error_ratio:6h{job="order-api"} > (6 * 0.001)
          AND
          job:slo_error_ratio:1h{job="order-api"} > (6 * 0.001)
        for: 15m
        labels:
          severity: warning
          slo: availability
        annotations:
          summary: "Order API burning error budget at 6x rate (ticket)"
          description: "Slow degradation — 30-day budget will exhaust in ~5 days at this rate."
          runbook: "https://wiki.my-app.com/runbooks/error-budget-burn"
```

---

## Error Budget Dashboard

```promql
# Error budget remaining (percentage, 30-day window)
(
  1 -
  sum(increase(http_requests_total{job="order-api",status_code=~"5.."}[30d]))
  /
  sum(increase(http_requests_total{job="order-api"}[30d]))
  /
  0.001   # 1 - SLO target
) * 100

# Error budget consumed this week
(
  sum(increase(http_requests_total{job="order-api",status_code=~"5.."}[7d]))
  /
  sum(increase(http_requests_total{job="order-api"}[7d]))
)
/
(7 / 30 * 0.001)   # Weekly proportion of monthly budget

# Projected budget exhaustion date (days remaining)
(
  (0.001 -
    sum(rate(http_requests_total{job="order-api",status_code=~"5.."}[24h]))
    /
    sum(rate(http_requests_total{job="order-api"}[24h]))
  )
  /
  (
    sum(rate(http_requests_total{job="order-api",status_code=~"5.."}[24h]))
    /
    sum(rate(http_requests_total{job="order-api"}[24h]))
  )
) * (24 / 720)   # Convert to days (720 hours = 30 days)
```

---

## Error Budget Policy

An error budget policy defines how the organization responds when the budget is healthy or exhausted.

```markdown
## Error Budget Policy: Order API

**SLO:** 99.9% availability, 30-day rolling window
**Error budget:** 43 min 48 sec per month

### When budget is > 50% remaining
- Normal development velocity
- Feature deployments proceed per standard process
- On-call load is acceptable — proceed with planned work

### When budget is 25–50% remaining
- Reliability review required before new feature deployments
- Increase deployment monitoring duration from 5 min to 15 min
- Weekly error budget report shared with engineering leadership

### When budget is 10–25% remaining
- Feature freeze — no new features deployed until budget recovers
- Dedicated reliability sprint: fix top error sources
- Daily standups focused on reliability work
- Incident review for any new errors

### When budget is < 10% remaining (or exhausted)
- Feature work halted — all hands on reliability
- On-call engineer empowered to roll back any recent change without approval
- Escalate to engineering director
- Postmortem required for all incidents
- Deploy frequency reduced to once per week maximum

### Budget recovery
- Budget resets on a rolling 30-day basis
- Once budget recovers to > 50%, return to normal velocity
```

---

## References

- [Google SRE Workbook — Error Budget Policy](https://sre.google/workbook/error-budget-policy/)
- [Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
- [Multi-window, multi-burn-rate alerts](https://www.slok.dev/posts/sloth/)

---

← [Previous: SLIs & SLOs](./slos-slis.md) | [Home](../README.md) | [Next: Toil Reduction →](./toil-reduction.md)
