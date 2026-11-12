← [Previous: Rightsizing](./rightsizing.md) | [Home](../README.md) | [Next: Storage Optimization →](./storage-optimization.md)

---

# Reserved Instances & Savings Plans

Commitments (Reserved Instances, Savings Plans, Committed Use Discounts) offer 30–72% discounts on cloud compute in exchange for 1- or 3-year commitments. They are the highest-ROI FinOps action after rightsizing.

---

## Discount Comparison

| Commitment type | Discount | Flexibility |
|----------------|---------|------------|
| **On-Demand** | 0% | Unlimited — no commitment |
| **Savings Plans (Compute)** | ~66% | Any EC2/Lambda/Fargate, any region |
| **Savings Plans (EC2 Instance)** | ~72% | Locked to instance family + region |
| **Reserved Instances (Standard)** | ~72% | Locked to instance type + AZ |
| **Reserved Instances (Convertible)** | ~54% | Can exchange for different type |
| **Spot Instances** | ~90% | Interruptible — only for fault-tolerant work |
| **GCP Committed Use (Resource)** | ~55% | Locked to resource type + region |
| **GCP Committed Use (Flexible)** | ~28% | Any machine type |
| **Azure Reserved VM Instances** | ~72% | Locked to VM size + region |

---

## AWS Savings Plans

Savings Plans are the recommended commitment type — more flexible than RIs.

```bash
# Check your current Savings Plans coverage
aws savingsplans describe-savings-plans \
    --query 'savingsPlans[*].{Type:savingsPlanType,Term:termDurationInSeconds,Rate:commitment,State:state,End:end}'

# Get coverage report: what % of your spend is covered by commitments?
aws ce get-savings-plans-coverage \
    --time-period Start=2024-01-01,End=2024-02-01 \
    --granularity MONTHLY \
    --group-by '[{"Type":"DIMENSION","Key":"SERVICE"}]' \
    --query 'SavingsPlansCoverages[*].Groups[*].{Service:Attributes.SERVICE,Coverage:Coverage.CoveragePercentage}' \
    --output table

# Get utilization: are your existing commitments being used?
aws ce get-savings-plans-utilization \
    --time-period Start=2024-01-01,End=2024-02-01 \
    --granularity MONTHLY \
    --query 'SavingsPlansUtilizationsByTime[*].Utilization'

# Get recommendations for new Savings Plans
aws ce get-savings-plans-purchase-recommendation \
    --savings-plans-type COMPUTE_SP \
    --term-in-years ONE_YEAR \
    --payment-option NO_UPFRONT \
    --lookback-period-in-days SIXTY_DAYS \
    --query 'SavingsPlansPurchaseRecommendation.SavingsPlansPurchaseRecommendationDetails[0]'
```

### Savings Plans Decision Framework

```
Step 1: Rightsize first
  └── Commitments on over-sized resources waste money

Step 2: Identify stable baseline load
  └── Use 14-day minimum, 60-day recommended
  └── Only commit to the p10 of your usage (the floor)

Step 3: Choose commitment type
  ├── Compute SP (recommended for most)
  │   └── Flexible across EC2/Fargate/Lambda, all instance types and regions
  │   └── Best if: you change instance types or regions frequently
  └── EC2 Instance SP
      └── Higher discount, locked to family (e.g., m5) + region
      └── Best if: stable, predictable workload on a specific instance family

Step 4: Choose payment option
  ├── No Upfront:    lowest risk, ~66% discount
  ├── Partial Upfront: ~69% discount
  └── All Upfront:  highest discount (~72%), requires cash

Step 5: 1-year vs 3-year
  └── Start with 1-year if uncertain
  └── 3-year only for workloads you're confident will run 3+ years
```

---

## AWS Reserved Instances

```bash
# Purchase a 1-year No Upfront m5.xlarge RI
aws ec2 purchase-reserved-instances-offering \
    --reserved-instances-offering-id <offering-id> \
    --instance-count 5

# Find available RI offerings
aws ec2 describe-reserved-instances-offerings \
    --instance-type m5.xlarge \
    --offering-type "No Upfront" \
    --product-description "Linux/UNIX" \
    --offering-class standard \
    --query 'ReservedInstancesOfferings[?Duration==`31536000`].{
        Id:ReservedInstancesOfferingId,
        Price:FixedPrice,
        Upfront:RecurringCharges[0].Amount,
        AZ:AvailabilityZone
    }' \
    --output table

# Check RI utilization (< 90% = wasted commitment)
aws ce get-reservation-utilization \
    --time-period Start=2024-01-01,End=2024-02-01 \
    --granularity MONTHLY \
    --query 'UtilizationsByTime[0].Total.UtilizationPercentage'

# RI Marketplace: sell unused RIs
aws ec2 create-reserved-instances-listing \
    --reserved-instances-id <ri-id> \
    --instance-count 2 \
    --price-schedules '[{"CurrencyCode":"USD","Price":500,"Term":12}]' \
    --client-token $(uuidgen)
```

---

## GCP Committed Use Discounts

```bash
# Purchase a resource-based CUD (CPU + memory)
gcloud compute commitments create my-app-commitment \
    --project=my-project \
    --region=us-central1 \
    --plan=12-month \
    --resources=vcpu=32,memory=128GB

# List existing commitments
gcloud compute commitments list --project=my-project

# Check CUD coverage via BigQuery billing export
bq query --use_legacy_sql=false '
    SELECT
        SUM(cost) AS total_cost,
        SUM(CASE WHEN cost_type = "committed use discount" THEN ABS(cost) ELSE 0 END) AS discount_amount,
        SAFE_DIVIDE(
            SUM(CASE WHEN cost_type = "committed use discount" THEN ABS(cost) ELSE 0 END),
            SUM(CASE WHEN cost_type = "usage" THEN cost ELSE 0 END)
        ) * 100 AS discount_percentage
    FROM `my-billing-project.my_billing_dataset.gcp_billing_export_v1_*`
    WHERE DATE(_PARTITIONTIME) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
'
```

---

## Spot / Preemptible Instances (Best Discount)

```bash
# AWS Spot: use for fault-tolerant workloads (batch jobs, CI workers, ML training)
# Average 60–90% discount vs On-Demand

# EKS: Spot node group
aws eks create-nodegroup \
    --cluster-name my-cluster \
    --nodegroup-name spot-workers \
    --capacity-type SPOT \
    --instance-types t3.large t3.xlarge t3a.large m5.large \   # Multiple families = more availability
    --scaling-config minSize=0,maxSize=20,desiredSize=5 \
    --ami-type AL2_x86_64

# Kubernetes: only schedule fault-tolerant pods on Spot
# Spot nodes are tainted so regular pods don't land there
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      tolerations:
        - key: "node.kubernetes.io/spot"
          operator: "Equal"
          value: "true"
          effect: "NoSchedule"
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: "eks.amazonaws.com/capacityType"
                    operator: In
                    values: ["SPOT"]
```

---

## References

- [AWS Savings Plans](https://docs.aws.amazon.com/savingsplans/latest/userguide/)
- [AWS Reserved Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-reserved-instances.html)
- [GCP Committed Use Discounts](https://cloud.google.com/compute/docs/instances/signing-up-committed-use-discounts)
- [Azure Reserved VM Instances](https://learn.microsoft.com/en-us/azure/cost-management-billing/reservations/save-compute-costs-reservations)

---

← [Previous: Rightsizing](./rightsizing.md) | [Home](../README.md) | [Next: Storage Optimization →](./storage-optimization.md)
