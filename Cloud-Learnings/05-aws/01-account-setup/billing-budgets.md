← [Previous: Account Setup](./account-setup.md) | [Home](../../README.md) | [Next: CLI Setup →](./cli-setup.md)

---

# AWS Billing and Cost Management

Cloud costs can spiral without guardrails. Set up billing visibility and alerts before deploying anything significant. An unexpected $10,000 bill from an undeleted resource is a common and avoidable experience.

---

## Billing Concepts

| Term | Meaning |
|------|---------|
| **On-Demand** | Pay per hour/second with no commitment |
| **Reserved Instances (RI)** | 1–3 year commitment; up to 72% discount |
| **Savings Plans** | Flexible commitment ($/hour); up to 66% discount |
| **Spot Instances** | Spare capacity; up to 90% discount; can be interrupted |
| **Free Tier** | 12-month new-account limits + always-free services |
| **Data Transfer** | Often overlooked; egress to internet is charged per GB |

---

## Cost Explorer

Cost Explorer visualises and analyses your AWS spend over the past 13 months.

```bash
# Get total costs for the current month (by service)
aws ce get-cost-and-usage \
    --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE \
    --query 'ResultsByTime[0].Groups[*].{Service:Keys[0],Cost:Metrics.BlendedCost.Amount}' \
    --output table | sort -k3 -rn

# Get daily costs for the last 7 days
aws ce get-cost-and-usage \
    --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
    --granularity DAILY \
    --metrics UnblendedCost \
    --query 'ResultsByTime[*].{Date:TimePeriod.Start,Cost:Total.UnblendedCost.Amount}' \
    --output table

# Get cost by tag (requires tags to be activated as cost allocation tags first)
aws ce get-cost-and-usage \
    --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=TAG,Key=Project

# Get cost forecast for the rest of the month
aws ce get-cost-forecast \
    --time-period Start=$(date +%Y-%m-%d),End=$(date +%Y-%m-31) \
    --metric BLENDED_COST \
    --granularity MONTHLY \
    --query 'Total.{Amount:Amount,Unit:Unit}'
```

---

## Budgets

AWS Budgets sends alerts when your actual or forecasted costs exceed thresholds.

### Create a Budget Alert

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Monthly cost budget: alert at $80 actual + $100 forecasted
aws budgets create-budget \
    --account-id $ACCOUNT_ID \
    --budget '{
        "BudgetName": "monthly-cost-alert",
        "BudgetLimit": {"Amount": "100", "Unit": "USD"},
        "TimeUnit": "MONTHLY",
        "BudgetType": "COST"
    }' \
    --notifications-with-subscribers '[
        {
            "Notification": {
                "NotificationType": "ACTUAL",
                "ComparisonOperator": "GREATER_THAN",
                "Threshold": 80,
                "ThresholdType": "PERCENTAGE"
            },
            "Subscribers": [{
                "SubscriptionType": "EMAIL",
                "Address": "billing-alerts@example.com"
            }]
        },
        {
            "Notification": {
                "NotificationType": "FORECASTED",
                "ComparisonOperator": "GREATER_THAN",
                "Threshold": 100,
                "ThresholdType": "PERCENTAGE"
            },
            "Subscribers": [{
                "SubscriptionType": "EMAIL",
                "Address": "billing-alerts@example.com"
            }]
        }
    ]'

# List all budgets
aws budgets describe-budgets \
    --account-id $ACCOUNT_ID \
    --query 'Budgets[*].{Name:BudgetName,Limit:BudgetLimit.Amount,Actual:CalculatedSpend.ActualSpend.Amount}'
```

### Recommended Budget Set

| Budget name | Threshold | Alert type |
|-------------|-----------|-----------|
| `monthly-alert-50` | $50 | Actual ≥ 100% |
| `monthly-alert-100` | $100 | Actual ≥ 100% + Forecast ≥ 100% |
| `monthly-alert-500` | $500 | Actual ≥ 100% + Forecast ≥ 80% |
| `ec2-budget` | $50 | Actual ≥ 100% (EC2 only) |

---

## Billing Alerts via CloudWatch (Legacy — prefer Budgets)

```bash
# Note: CloudWatch billing metrics are only available in us-east-1
aws cloudwatch put-metric-alarm \
    --region us-east-1 \
    --alarm-name billing-alert-50 \
    --alarm-description "Alert when monthly bill exceeds $50" \
    --metric-name EstimatedCharges \
    --namespace AWS/Billing \
    --statistic Maximum \
    --period 86400 \
    --evaluation-periods 1 \
    --threshold 50 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=Currency,Value=USD \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:billing-alerts \
    --treat-missing-data notBreaching
```

---

## Cost Allocation Tags

Tags that are activated as cost allocation tags appear in Cost Explorer and billing reports, allowing you to split costs by team, project, or environment.

```bash
# Activate cost allocation tags (one-time setup in Billing console)
# Billing → Cost allocation tags → User-defined → Activate

# Recommended tag keys:
#   Environment  (production, staging, development)
#   Project      (auth-service, data-pipeline)
#   Owner        (alice, platform-team)
#   CostCenter   (engineering, marketing)

# Tag an existing resource
aws ec2 create-tags \
    --resources i-0abc1234 \
    --tags \
        Key=Environment,Value=production \
        Key=Project,Value=api-service \
        Key=Owner,Value=alice

# Apply tags at creation time (example: EC2 launch)
aws ec2 run-instances \
    --image-id ami-0abcdef1234567890 \
    --instance-type t3.micro \
    --tag-specifications \
        'ResourceType=instance,Tags=[{Key=Environment,Value=production},{Key=Project,Value=api}]'

# Find untagged resources (requires AWS Config or Tag Editor)
aws resourcegroupstaggingapi get-resources \
    --tag-filters 'Key=Environment' \
    --query 'ResourceTagMappingList[?Tags[?Key==`Environment`]==`[]`]'
```

---

## Cost Optimisation Fundamentals

### Rightsizing

Identify EC2 instances with low utilisation using Cost Explorer Rightsizing Recommendations:

```bash
aws ce get-rightsizing-recommendation \
    --service EC2 \
    --query 'RightsizingRecommendations[*].{
        Instance:CurrentInstance.ResourceId,
        Type:CurrentInstance.InstanceType,
        Recommendation:RightsizingType,
        Savings:RightsizingSavings.EstimatedMonthlySavingsAmount
    }' \
    --output table
```

### Savings Plans

Commitment-based discounts that apply automatically to EC2, Fargate, and Lambda:

```bash
# Get Savings Plans purchase recommendations
aws ce get-savings-plans-purchase-recommendation \
    --savings-plans-type COMPUTE_SP \
    --term-in-years ONE_YEAR \
    --payment-option NO_UPFRONT \
    --query 'SavingsPlansPurchaseRecommendation.SavingsPlansPurchaseRecommendationDetails[0]'
```

### Common Cost Traps

| Trap | Prevention |
|------|-----------|
| Forgotten NAT Gateway | Tag with team; review monthly |
| EBS snapshots accumulating | Lifecycle policies on all volumes |
| Old AMIs and associated snapshots | Regular cleanup automation |
| Idle load balancers | Alert on zero healthy targets |
| Data transfer between AZs | Deploy services to same AZ where possible; use VPC endpoints for AWS services |
| CloudWatch Logs never expiring | Set retention on every log group |
| S3 incomplete multipart uploads | Lifecycle rule: abort after 7 days |

```bash
# Set CloudWatch Logs retention to 30 days on all log groups
aws logs describe-log-groups \
    --query 'logGroups[?!retentionInDays].logGroupName' \
    --output text | tr '\t' '\n' | while read -r lg; do
    echo "Setting 30d retention on: $lg"
    aws logs put-retention-policy --log-group-name "$lg" --retention-in-days 30
done

# S3 lifecycle rule: abort incomplete multipart uploads
aws s3api put-bucket-lifecycle-configuration \
    --bucket my-bucket \
    --lifecycle-configuration '{
        "Rules": [{
            "ID": "abort-incomplete-multipart",
            "Status": "Enabled",
            "Filter": {"Prefix": ""},
            "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
        }]
    }'
```

---

## Free Tier Monitoring

AWS Free Tier limits are per service and per region. Enable alerts before you exceed them.

```bash
# Enable Free Tier usage alerts
# Billing → Billing preferences → Receive Free Tier Usage Alerts
# (console only — no CLI equivalent)

# Check current Free Tier usage via API
aws ce get-dimension-values \
    --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
    --dimension USAGE_TYPE \
    --context COST_AND_USAGE

# Common Free Tier limits:
#   EC2:       750 hours/month t2.micro or t3.micro (Linux/Windows)
#   S3:        5 GB storage, 20,000 GET requests, 2,000 PUT requests
#   Lambda:    1M requests/month, 400,000 GB-seconds compute
#   RDS:       750 hours/month db.t2.micro (single AZ)
#   DynamoDB:  25 GB storage, 25 RCU, 25 WCU
#   CloudFront: 1 TB data transfer out, 10M HTTP requests
```

---

## References

- [AWS Cost Explorer documentation](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html)
- [AWS Budgets documentation](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [Savings Plans documentation](https://docs.aws.amazon.com/savingsplans/latest/userguide/)
---

← [Previous: Account Setup](./account-setup.md) | [Home](../../README.md) | [Next: CLI Setup →](./cli-setup.md)
