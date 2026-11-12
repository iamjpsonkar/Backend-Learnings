← [Previous: Cost Visibility](./cost-visibility.md) | [Home](../README.md) | [Next: Reserved & Savings Plans →](./reserved-savings.md)

---

# Rightsizing

Rightsizing matches resource capacity to actual workload needs. Over-provisioned resources are the single largest source of wasted cloud spend — typically 30–50% in organizations without an active FinOps practice.

---

## AWS Compute Optimizer

```bash
# Enable Compute Optimizer
aws compute-optimizer update-enrollment-status \
    --status Active \
    --include-member-accounts

# Get EC2 instance recommendations
aws compute-optimizer get-ec2-instance-recommendations \
    --query 'instanceRecommendations[*].{
        Instance:instanceArn,
        CurrentType:currentInstanceType,
        RecommendedType:recommendationOptions[0].instanceType,
        MonthlySavings:recommendationOptions[0].estimatedMonthlySavings.value,
        PerformanceRisk:recommendationOptions[0].performanceRisk,
        Reason:finding
    }' \
    --output table

# Get RDS recommendations
aws compute-optimizer get-rds-database-recommendations \
    --query 'rdsDBRecommendations[*].{
        DB:resourceArn,
        CurrentClass:currentDBInstanceClass,
        Recommended:recommendationOptions[0].dbInstanceClass,
        Savings:recommendationOptions[0].estimatedMonthlySavings.value
    }' \
    --output table

# Get Lambda function recommendations
aws compute-optimizer get-lambda-function-recommendations \
    --query 'lambdaFunctionRecommendations[*].{
        Function:functionArn,
        CurrentMemory:memorySizeRecommendationOptions[0].memorySize,
        Reason:finding
    }'

# Export all recommendations to S3 for analysis
aws compute-optimizer export-ec2-instance-recommendations \
    --s3-destination-config bucket=my-cost-reports,keyPrefix=compute-optimizer/
```

---

## Idle Resource Detection

```python
import boto3
import logging
from datetime import datetime, timedelta, timezone
from typing import Generator

logger = logging.getLogger(__name__)

ec2 = boto3.client("ec2")
cw = boto3.client("cloudwatch")


def get_idle_ec2_instances(
    cpu_threshold: float = 5.0,
    lookback_days: int = 14,
) -> Generator[dict, None, None]:
    """
    Yield EC2 instances with average CPU < threshold over lookback period.
    These are candidates for downsizing or termination.
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=lookback_days)

    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running"]}]):
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                instance_type = instance["InstanceType"]

                # Get average CPU utilization
                metrics = cw.get_metric_statistics(
                    Namespace="AWS/EC2",
                    MetricName="CPUUtilization",
                    Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,  # Daily
                    Statistics=["Average"],
                )

                if not metrics["Datapoints"]:
                    continue

                avg_cpu = sum(dp["Average"] for dp in metrics["Datapoints"]) / len(metrics["Datapoints"])

                if avg_cpu < cpu_threshold:
                    name = next(
                        (tag["Value"] for tag in instance.get("Tags", []) if tag["Key"] == "Name"),
                        "unnamed",
                    )
                    logger.info(
                        "Idle instance detected",
                        extra={"instance_id": instance_id, "type": instance_type,
                               "avg_cpu_pct": round(avg_cpu, 2), "name": name},
                    )
                    yield {
                        "instance_id": instance_id,
                        "instance_type": instance_type,
                        "name": name,
                        "avg_cpu_pct": round(avg_cpu, 2),
                        "lookback_days": lookback_days,
                    }


def get_idle_rds_instances(cpu_threshold: float = 5.0) -> list[dict]:
    """Find RDS instances with low CPU utilization."""
    rds = boto3.client("rds")
    idle = []
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=14)

    for db in rds.describe_db_instances()["DBInstances"]:
        db_id = db["DBInstanceIdentifier"]
        metrics = cw.get_metric_statistics(
            Namespace="AWS/RDS",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,
            Statistics=["Average"],
        )
        if metrics["Datapoints"]:
            avg_cpu = sum(dp["Average"] for dp in metrics["Datapoints"]) / len(metrics["Datapoints"])
            if avg_cpu < cpu_threshold:
                logger.info("Idle RDS instance", extra={"db_id": db_id, "avg_cpu": round(avg_cpu, 2)})
                idle.append({
                    "db_id": db_id,
                    "instance_class": db["DBInstanceClass"],
                    "avg_cpu_pct": round(avg_cpu, 2),
                    "multi_az": db["MultiAZ"],
                })
    return idle
```

---

## Kubernetes Rightsizing

```bash
# View actual resource usage vs requests
kubectl top pods -n production --containers | sort -k4 -rn

# Find pods with >2x difference between request and actual usage
kubectl get pod -n production -o json | \
    jq -r '.items[] | .metadata.name as $name |
    .spec.containers[] |
    [$name, .name, .resources.requests.cpu // "none", .resources.requests.memory // "none"] |
    @tsv'

# VPA recommendations (install VPA first)
kubectl get vpa -n production -o json | \
    jq -r '.items[] | {
        name: .metadata.name,
        target_cpu: .status.recommendation.containerRecommendations[0].target.cpu,
        target_mem: .status.recommendation.containerRecommendations[0].target.memory
    }'
```

### VPA for Automated Recommendations

```yaml
# Install VPA in recommendation-only mode
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: order-api-vpa
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-api
  updatePolicy:
    updateMode: "Off"    # Recommendations only — review before applying
  resourcePolicy:
    containerPolicies:
      - containerName: order-api
        controlledResources: ["cpu", "memory"]
        minAllowed: { cpu: "50m", memory: "64Mi" }
        maxAllowed: { cpu: "2", memory: "2Gi" }
```

```bash
# Review VPA recommendations and apply to deployment
RECOMMENDED_CPU=$(kubectl get vpa order-api-vpa -n production -o jsonpath='{.status.recommendation.containerRecommendations[0].target.cpu}')
RECOMMENDED_MEM=$(kubectl get vpa order-api-vpa -n production -o jsonpath='{.status.recommendation.containerRecommendations[0].target.memory}')
echo "Recommended: CPU=$RECOMMENDED_CPU Memory=$RECOMMENDED_MEM"

# Apply after review
kubectl patch deployment order-api -n production \
    --type json \
    -p "[
        {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/resources/requests/cpu\",\"value\":\"$RECOMMENDED_CPU\"},
        {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/resources/requests/memory\",\"value\":\"$RECOMMENDED_MEM\"}
    ]"
```

---

## Rightsizing Workflow

```
1. Baseline (2 weeks minimum)
   └── Collect CPU, memory, network, disk I/O metrics

2. Analyze
   └── P95 CPU < 20% → downsize candidate
   └── P95 memory < 40% → downsize candidate
   └── Consider: does this service have traffic spikes?

3. Test
   └── Downsize in staging first
   └── Run load test at P95 traffic
   └── Verify SLO compliance

4. Apply in production
   └── Blue/green deployment
   └── Monitor for 24 hours post-change
   └── Set 7-day rollback window

5. Document
   └── Update Terraform resource definitions
   └── Record savings in cost tracking spreadsheet
```

---

## References

- [AWS Compute Optimizer](https://docs.aws.amazon.com/compute-optimizer/latest/ug/)
- [Kubernetes VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
- [GCP Recommender](https://cloud.google.com/recommender/docs)
- [Azure Advisor](https://learn.microsoft.com/en-us/azure/advisor/advisor-overview)

---

← [Previous: Cost Visibility](./cost-visibility.md) | [Home](../README.md) | [Next: Reserved & Savings Plans →](./reserved-savings.md)
