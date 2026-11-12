← [Previous: Kubernetes Costs](./kubernetes-costs.md) | [Home](../README.md) | [Next: Databases →](../18-databases/README.md)

---

# FinOps Culture

Technology changes are necessary but insufficient. Sustainable cloud cost management requires a culture where every engineer understands their service's cost, owns it, and has the tools to act on it.

---

## Unit Economics

Total cloud spend is a vanity metric. Unit economics connects cost to business outcomes.

| Service | Vanity metric | Unit metric | Why it matters |
|---------|--------------|-------------|---------------|
| Order API | $12,000/month EC2 | $0.08 per order | Stays constant as orders grow |
| Data Pipeline | $3,000/month EMR | $0.002 per event processed | Validates pipeline efficiency |
| ML Inference | $8,000/month GPU | $0.15 per inference call | Pricing model viability |
| Storage | $5,000/month S3 | $0.12 per active user | Storage efficiency per user |

```python
import boto3
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)
ce = boto3.client("ce")


def calculate_cost_per_order(
    month_start: date,
    total_orders: int,
) -> dict:
    """Calculate infrastructure cost per order for a given month."""
    month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

    logger.info(
        "Calculating cost per order",
        extra={"period": str(month_start), "orders": total_orders},
    )

    response = ce.get_cost_and_usage(
        TimePeriod={"Start": str(month_start), "End": str(month_end)},
        Granularity="MONTHLY",
        Metrics=["BlendedCost"],
        Filter={
            "Tags": {
                "Key": "service",
                "Values": ["order-api", "order-db", "order-queue"],
            }
        },
    )

    total_cost = float(response["ResultsByTime"][0]["Total"]["BlendedCost"]["Amount"])
    cost_per_order = total_cost / total_orders if total_orders > 0 else 0

    result = {
        "period": str(month_start),
        "total_infrastructure_cost_usd": round(total_cost, 2),
        "total_orders": total_orders,
        "cost_per_order_usd": round(cost_per_order, 4),
    }
    logger.info("Unit economics calculated", extra=result)
    return result
```

---

## Showback vs Chargeback

| Model | How it works | When to use |
|-------|-------------|-------------|
| **Showback** | Report cost per team, no internal billing | Starting out — builds awareness without friction |
| **Chargeback** | Deduct cloud costs from team budget | Mature orgs with clear team ownership |
| **Hybrid** | Showback + manual chargeback for large overruns | Most common in practice |

```python
# Weekly showback report (Slack)
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def send_weekly_showback_report(
    cost_by_team: dict[str, float],
    budget_by_team: dict[str, float],
    slack_webhook: str,
) -> None:
    """Post weekly cost showback with budget tracking to Slack."""
    total = sum(cost_by_team.values())
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Weekly Cloud Cost Showback"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Total last 7 days: ${total:,.2f}*"},
        },
    ]

    rows = []
    for team, cost in sorted(cost_by_team.items(), key=lambda x: -x[1]):
        budget = budget_by_team.get(team, 0)
        weekly_budget = budget / 4.33  # monthly → weekly
        pct = cost / weekly_budget * 100 if weekly_budget > 0 else 0
        status = "🔴" if pct > 110 else "🟡" if pct > 90 else "🟢"
        rows.append(f"{status} `{team:<18}` ${cost:>7,.2f}  ({pct:.0f}% of weekly budget)")

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "\n".join(rows)},
    })

    logger.info("Sending showback report", extra={"teams": len(cost_by_team), "total": total})
    async with httpx.AsyncClient() as client:
        await client.post(slack_webhook, json={"blocks": blocks}, timeout=10)
```

---

## FinOps Maturity Model

### Crawl (getting started)

- [ ] All resources tagged (team, service, environment)
- [ ] Cost Explorer enabled and shared with engineering leads
- [ ] Monthly cost review meeting on calendar
- [ ] Budget alerts configured ($, not just %)
- [ ] One person owns FinOps practice (even if part-time)

### Walk (building habits)

- [ ] Weekly automated cost reports per team (showback)
- [ ] Unit economics defined and tracked (cost/order, cost/user)
- [ ] Rightsizing review quarterly
- [ ] Savings Plans / RIs covering > 60% of stable compute
- [ ] Lifecycle policies on all S3 buckets
- [ ] Cost review in sprint planning: "does this feature change our cost curve?"

### Run (continuous optimization)

- [ ] Cost anomaly detection with automated Slack alerts
- [ ] Engineers have self-service cost dashboards
- [ ] Cost is part of architecture review (estimated spend in design docs)
- [ ] Chargeback implemented for large teams
- [ ] Unit economics tracked in engineering OKRs
- [ ] Spot/preemptible > 40% of compute spend
- [ ] Automated idle resource cleanup

---

## Anomaly Detection

```python
import boto3
import logging
import os
from datetime import date, timedelta

logger = logging.getLogger(__name__)
ce = boto3.client("ce")
sns = boto3.client("sns")

ALERT_TOPIC = os.environ["COST_ALERT_SNS_TOPIC"]
THRESHOLD_PCT = 25.0  # Alert if cost increased > 25% day-over-day


def check_daily_cost_anomaly() -> None:
    """Compare today's cost forecast to yesterday's actual. Alert on large increases."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    # Yesterday actual
    resp_yesterday = ce.get_cost_and_usage(
        TimePeriod={"Start": str(two_days_ago), "End": str(yesterday)},
        Granularity="DAILY",
        Metrics=["BlendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    # Today actual (so far)
    resp_today = ce.get_cost_and_usage(
        TimePeriod={"Start": str(yesterday), "End": str(today)},
        Granularity="DAILY",
        Metrics=["BlendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    def extract_costs(resp) -> dict[str, float]:
        costs = {}
        for group in resp["ResultsByTime"][0].get("Groups", []):
            service = group["Keys"][0]
            costs[service] = float(group["Metrics"]["BlendedCost"]["Amount"])
        return costs

    yesterday_costs = extract_costs(resp_yesterday)
    today_costs = extract_costs(resp_today)

    anomalies = []
    for service, today_cost in today_costs.items():
        yesterday_cost = yesterday_costs.get(service, 0)
        if yesterday_cost < 1.0:
            continue  # Ignore very small amounts
        change_pct = (today_cost - yesterday_cost) / yesterday_cost * 100
        if change_pct > THRESHOLD_PCT:
            anomalies.append((service, yesterday_cost, today_cost, change_pct))
            logger.warning(
                "Cost anomaly detected",
                extra={"service": service, "yesterday": yesterday_cost,
                       "today": today_cost, "change_pct": round(change_pct, 1)},
            )

    if anomalies:
        lines = [f"Cost anomalies detected on {today}:"]
        for service, prev, curr, pct in sorted(anomalies, key=lambda x: -x[3]):
            lines.append(f"  {service}: ${prev:.2f} → ${curr:.2f} (+{pct:.0f}%)")

        sns.publish(
            TopicArn=ALERT_TOPIC,
            Subject=f"Cost Anomaly Alert — {today}",
            Message="\n".join(lines),
        )
    else:
        logger.info("No cost anomalies detected", extra={"date": str(today)})
```

---

## FinOps Checklist for New Services

```markdown
## FinOps Checklist — New Service Launch

Before launching a new service or feature, complete this checklist:

### Tagging
- [ ] All cloud resources tagged: team, service, environment, cost-center
- [ ] Tags applied in Terraform/IaC (not manually)

### Estimation
- [ ] Monthly cost estimated in design doc
- [ ] Per-unit cost defined (cost/request, cost/user, etc.)
- [ ] Cost reviewed and approved by team lead

### Optimization
- [ ] Instance type right-sized for expected load (not over-provisioned)
- [ ] Storage tiering configured (S3 lifecycle, EBS type)
- [ ] Auto-scaling configured (scale to zero where possible)

### Visibility
- [ ] Service included in team cost dashboard
- [ ] Budget alert set for service-level spend

### Review
- [ ] Cost spike scenario considered: what if traffic 10x?
- [ ] Estimated added cost shared with FinOps/finance stakeholder
```

---

## References

- [FinOps Foundation — Framework](https://www.finops.org/framework/)
- [Cloud FinOps (O'Reilly book)](https://www.oreilly.com/library/view/cloud-finops/9781492054610/)
- [AWS Cloud Financial Management](https://aws.amazon.com/aws-cost-management/)
- [Unit Economics for Cloud](https://www.finops.org/framework/capabilities/unit-economics/)

---

← [Previous: Kubernetes Costs](./kubernetes-costs.md) | [Home](../README.md) | [Next: Databases →](../18-databases/README.md)
