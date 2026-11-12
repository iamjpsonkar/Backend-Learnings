← [Previous: DR Overview](./README.md) | [Home](../README.md) | [Next: Backup Strategies →](./backup-strategies.md)

---

# RPO & RTO

RPO and RTO are the two foundational DR metrics. Set them based on business impact — not on what is technically achievable.

---

## Definitions

| Metric | Full name | What it measures | Example |
|--------|-----------|-----------------|---------|
| **RPO** | Recovery Point Objective | Maximum acceptable data loss | RPO = 1h means you can lose at most 1h of data |
| **RTO** | Recovery Time Objective | Maximum acceptable downtime | RTO = 15min means service must be restored in 15 min |
| **MTTR** | Mean Time To Recover | Average time to restore service | Operational metric: track and reduce over time |
| **MTBF** | Mean Time Between Failures | How often failures occur | Availability = MTBF / (MTBF + MTTR) |

---

## Setting RPO and RTO

Start with the business question: **what does 1 hour of downtime actually cost?**

```
Revenue impact:     $X/hour (orders not processed, SLA penalties)
Reputational impact: Brand damage, churn risk
Regulatory impact:  Compliance fines, audit findings
Data loss impact:   Transaction data, customer data
```

```python
def calculate_dr_cost_justification(
    hourly_revenue_usd: float,
    data_loss_cost_per_hour_usd: float,
    replication_cost_monthly_usd: float,
    standby_cost_monthly_usd: float,
    outage_probability_per_year: float,
    average_outage_hours: float,
) -> dict:
    """
    Compare cost of downtime vs cost of DR solution.
    Returns break-even analysis.
    """
    expected_annual_cost_no_dr = (
        (hourly_revenue_usd + data_loss_cost_per_hour_usd)
        * average_outage_hours
        * outage_probability_per_year
    )
    annual_dr_cost = (replication_cost_monthly_usd + standby_cost_monthly_usd) * 12
    roi = expected_annual_cost_no_dr / annual_dr_cost if annual_dr_cost > 0 else float("inf")

    return {
        "expected_loss_without_dr_annual": round(expected_annual_cost_no_dr, 2),
        "dr_solution_annual_cost": round(annual_dr_cost, 2),
        "roi_ratio": round(roi, 2),
        "justified": roi > 1.0,
    }

# Example: payment processing service
result = calculate_dr_cost_justification(
    hourly_revenue_usd=50_000,
    data_loss_cost_per_hour_usd=10_000,
    replication_cost_monthly_usd=500,
    standby_cost_monthly_usd=3_000,
    outage_probability_per_year=0.2,  # 20% chance of significant outage per year
    average_outage_hours=4,
)
# result: expected_loss ~$48k/year, DR cost ~$42k/year, ROI ~1.14x → justified
```

---

## RPO/RTO by Service Tier

```yaml
# service-dr-requirements.yaml
services:
  payment-api:
    tier: critical
    rpo: 0s          # Zero data loss — synchronous replication required
    rto: 5m          # Must recover in 5 minutes
    strategy: active-active
    dr_region: us-west-2

  order-api:
    tier: high
    rpo: 1m          # Up to 1 minute of data loss acceptable
    rto: 15m
    strategy: warm-standby
    dr_region: us-west-2

  user-profile-api:
    tier: medium
    rpo: 1h
    rto: 1h
    strategy: pilot-light
    dr_region: us-west-2

  analytics-pipeline:
    tier: low
    rpo: 24h
    rto: 4h
    strategy: backup-restore
    dr_region: us-west-2
```

---

## Availability Targets

```
Five nines:  99.999%  →  5.26 min/year downtime    → Requires active-active
Four nines:  99.99%   →  52.6 min/year             → Requires warm standby
Three nines: 99.9%    →  8.77 hours/year           → Warm standby or pilot light
Two nines:   99%      →  87.7 hours/year (~3.6 days) → Pilot light or backup/restore

For reference:
  AWS SLA (EC2):  99.99%
  AWS SLA (S3):   99.9% (99.99% availability SLA for 99.999999999% durability)
  RDS Multi-AZ:  ~99.95% (failover ~1-2 min)
```

---

## Measuring Recovery Metrics

```bash
# Track MTTR per incident in your incident management system
# Calculate from: incident_declared → service_restored

# Prometheus: SLO compliance over time
# Record when service is unavailable (status = 0)
# Calculate availability = (total_time - downtime) / total_time

# CloudWatch: calculate availability for the month
aws cloudwatch get-metric-statistics \
    --namespace AWS/ApplicationELB \
    --metric-name HealthyHostCount \
    --dimensions Name=LoadBalancer,Value=$ALB_NAME \
    --start-time $(date -d 'first day of this month' +%Y-%m-%dT00:00:00Z 2>/dev/null || date -v1d +%Y-%m-%dT00:00:00Z) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Minimum \
    --query 'sort_by(Datapoints, &Timestamp)[-1:].[Timestamp,Minimum]'

# Availability calculation (Python)
def calculate_availability(
    total_seconds: int,
    downtime_seconds: int,
) -> dict:
    availability = (total_seconds - downtime_seconds) / total_seconds
    nines = -1  # count trailing nines
    val = availability
    while val >= 0.9:
        val = (val - 0.9) * 10
        nines += 1
    return {
        "availability_pct": round(availability * 100, 4),
        "downtime_seconds": downtime_seconds,
        "downtime_minutes": round(downtime_seconds / 60, 1),
        "approximate_nines": nines,
    }
```

---

## References

- [AWS Disaster Recovery whitepaper](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.html)
- [SRE — Measuring and Managing Reliability](https://sre.google/sre-book/service-level-objectives/)
- [AWS Well-Architected — Recovery objectives](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/recovery-objectives.html)

---

← [Previous: DR Overview](./README.md) | [Home](../README.md) | [Next: Backup Strategies →](./backup-strategies.md)
