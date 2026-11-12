← [Previous: FinOps Overview](./README.md) | [Home](../README.md) | [Next: Rightsizing →](./rightsizing.md)

---

# Cost Visibility

You cannot optimize what you cannot see. Cost visibility means getting granular, queryable data on cloud spending before attempting any optimization.

---

## Tagging Strategy

Tags are the foundation of cost allocation. Without consistent tags you cannot attribute spend to teams, services, or environments.

```bash
# ─── AWS: Enforce tags via AWS Config ────────────────────────────────────────
aws configservice put-config-rule --config-rule '{
    "ConfigRuleName": "required-tags",
    "Source": {
        "Owner": "AWS",
        "SourceIdentifier": "REQUIRED_TAGS"
    },
    "InputParameters": "{\"tag1Key\":\"team\",\"tag2Key\":\"service\",\"tag3Key\":\"environment\",\"tag4Key\":\"cost-center\"}"
}'

# Tag an existing resource
aws ec2 create-tags \
    --resources i-1234567890abcdef0 \
    --tags \
        Key=team,Value=backend \
        Key=service,Value=order-api \
        Key=environment,Value=production \
        Key=cost-center,Value=CC-1042

# ─── Find untagged resources ─────────────────────────────────────────────────
aws resourcegroupstaggingapi get-resources \
    --tag-filters 'Key=team,Values=[]' \
    --query 'ResourceTagMappingList[*].ResourceARN' \
    --output text

# ─── AWS: Activate cost allocation tags (must do before they appear in billing)
aws ce update-cost-allocation-tags-status \
    --cost-allocation-tags-status '[
        {"TagKey":"team","Status":"Active"},
        {"TagKey":"service","Status":"Active"},
        {"TagKey":"environment","Status":"Active"},
        {"TagKey":"cost-center","Status":"Active"}
    ]'
```

### Tag Taxonomy

```yaml
# Recommended tags for all cloud resources
required_tags:
  team: "backend | frontend | data | platform | security"
  service: "order-api | payment-api | inventory | user-service"
  environment: "production | staging | development"
  cost-center: "CC-1042 | CC-2001 | CC-3005"

optional_tags:
  project: "project-name (for cross-team initiatives)"
  managed-by: "terraform | helm | manual"
  created-by: "github-actions | deployment-pipeline"
  expires: "YYYY-MM-DD (for ephemeral resources)"
```

---

## AWS Cost Explorer

```bash
# Get daily costs grouped by service (last 30 days)
aws ce get-cost-and-usage \
    --time-period Start=$(date -v-30d +%Y-%m-%d 2>/dev/null || date -d '30 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
    --granularity DAILY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE \
    --query 'ResultsByTime[-7:].Groups[*].{Service:Keys[0],Cost:Metrics.BlendedCost.Amount}' \
    --output table

# Get monthly spend by team tag
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-02-01 \
    --granularity MONTHLY \
    --metrics BlendedCost UnblendedCost \
    --group-by Type=TAG,Key=team \
    --query 'ResultsByTime[0].Groups[*].{Team:Keys[0],Cost:Metrics.BlendedCost.Amount}' \
    --output table

# Forecast next 3 months
aws ce get-cost-forecast \
    --time-period Start=$(date +%Y-%m-%d),End=$(date -v+90d +%Y-%m-%d 2>/dev/null || date -d '+90 days' +%Y-%m-%d) \
    --granularity MONTHLY \
    --metric BLENDED_COST \
    --query 'ForecastResultsByTime[*].{Period:TimePeriod.Start,Mean:MeanValue,Upper:PredictionIntervalUpperBound}'
```

### Cost Anomaly Detection

```bash
# Create an anomaly monitor for EC2
aws ce create-anomaly-monitor \
    --anomaly-monitor '{
        "MonitorName": "EC2CostMonitor",
        "MonitorType": "DIMENSIONAL",
        "MonitorDimension": "SERVICE"
    }'

MONITOR_ARN=$(aws ce list-anomaly-monitors --query 'AnomalyMonitors[0].MonitorArn' --output text)

# Create subscription: alert on anomalies > $50
aws ce create-anomaly-subscription \
    --anomaly-subscription '{
        "SubscriptionName": "DailyAnomalyAlerts",
        "MonitorArnList": ["'"$MONITOR_ARN"'"],
        "Subscribers": [{
            "Address": "arn:aws:sns:us-east-1:123456789012:cost-alerts",
            "Type": "SNS"
        }],
        "Threshold": 50,
        "Frequency": "DAILY"
    }'
```

---

## Budget Alarms

```bash
# AWS Budget: alert at 80% and 100% of monthly budget
aws budgets create-budget \
    --account-id 123456789012 \
    --budget '{
        "BudgetName": "monthly-total",
        "BudgetType": "COST",
        "TimeUnit": "MONTHLY",
        "BudgetLimit": {"Amount": "5000", "Unit": "USD"},
        "CostFilters": {}
    }' \
    --notifications-with-subscribers '[
        {
            "Notification": {
                "NotificationType": "ACTUAL",
                "ComparisonOperator": "GREATER_THAN",
                "Threshold": 80,
                "ThresholdType": "PERCENTAGE"
            },
            "Subscribers": [{"SubscriptionType": "EMAIL","Address":"finops@my-app.com"}]
        },
        {
            "Notification": {
                "NotificationType": "FORECASTED",
                "ComparisonOperator": "GREATER_THAN",
                "Threshold": 100,
                "ThresholdType": "PERCENTAGE"
            },
            "Subscribers": [{"SubscriptionType":"SNS","Address":"arn:aws:sns:us-east-1:123456789012:cost-alerts"}]
        }
    ]'

# Per-service budget (order-api)
aws budgets create-budget \
    --account-id 123456789012 \
    --budget '{
        "BudgetName": "order-api-monthly",
        "BudgetType": "COST",
        "TimeUnit": "MONTHLY",
        "BudgetLimit": {"Amount": "800", "Unit": "USD"},
        "CostFilters": {
            "TagKeyValue": ["user:service$order-api"]
        }
    }'
```

---

## Cost Reporting (Python)

```python
import boto3
import logging
from datetime import date, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)
ce = boto3.client("ce", region_name="us-east-1")


def get_weekly_cost_by_team() -> dict[str, float]:
    """Return last 7 days of costs grouped by 'team' tag."""
    end = date.today()
    start = end - timedelta(days=7)

    logger.info("Fetching weekly cost by team", extra={"start": str(start), "end": str(end)})

    response = ce.get_cost_and_usage(
        TimePeriod={"Start": str(start), "End": str(end)},
        Granularity="DAILY",
        Metrics=["BlendedCost"],
        GroupBy=[{"Type": "TAG", "Key": "team"}],
    )

    totals: dict[str, float] = defaultdict(float)
    for period in response["ResultsByTime"]:
        for group in period.get("Groups", []):
            team = group["Keys"][0].replace("team$", "") or "untagged"
            cost = float(group["Metrics"]["BlendedCost"]["Amount"])
            totals[team] += cost

    logger.info("Cost fetch complete", extra={"teams": len(totals), "total_usd": sum(totals.values())})
    return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))


def post_weekly_report_to_slack(webhook_url: str) -> None:
    """Post cost breakdown to Slack."""
    import httpx

    costs = get_weekly_cost_by_team()
    total = sum(costs.values())

    lines = [f"*Cloud Cost Report — Last 7 Days*", f"Total: *${total:,.2f}*", ""]
    for team, cost in costs.items():
        pct = cost / total * 100 if total > 0 else 0
        bar = "█" * int(pct / 5)
        lines.append(f"`{team:<20}` ${cost:>8.2f}  {bar} {pct:.1f}%")

    logger.info("Posting cost report to Slack", extra={"total_usd": total})
    httpx.post(webhook_url, json={"text": "\n".join(lines)}, timeout=10)
```

---

## GCP Billing

```bash
# Export billing to BigQuery (recommended for querying)
# Enable via Console: Billing → Billing export → BigQuery export

# Query daily costs by label (team)
bq query --use_legacy_sql=false '
    SELECT
        labels.value AS team,
        SUM(cost) AS total_cost,
        currency
    FROM `my-billing-project.my_billing_dataset.gcp_billing_export_v1_ABCDEF_123456_789012`
    CROSS JOIN UNNEST(labels) AS labels
    WHERE labels.key = "team"
      AND DATE(_PARTITIONTIME) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY 1, 3
    ORDER BY 2 DESC
'

# GCP Budget alert
gcloud billing budgets create \
    --billing-account=ABCDEF-123456-789012 \
    --display-name="Monthly Prod Budget" \
    --budget-amount=5000USD \
    --threshold-rule=percent=80,basis=current-spend \
    --threshold-rule=percent=100,basis=forecasted-spend \
    --notifications-rule-monitoring-notification-channels=projects/my-project/notificationChannels/12345
```

---

## References

- [AWS Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html)
- [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- [GCP Billing export to BigQuery](https://cloud.google.com/billing/docs/how-to/export-data-bigquery)
- [Azure Cost Management + Billing](https://learn.microsoft.com/en-us/azure/cost-management-billing/)

---

← [Previous: FinOps Overview](./README.md) | [Home](../README.md) | [Next: Rightsizing →](./rightsizing.md)
