← [Previous: Regions & Zones](./regions-zones-geography.md) | [Home](../README.md) | [Next: Account Safety Checklist →](./account-safety-checklist.md)

---

# Cloud Billing Basics

## The Pay-As-You-Go Model

Cloud computing replaces large upfront capital expenditure (CapEx) with ongoing operational expenditure (OpEx). You pay only for what you consume, when you consume it.

The fundamental billing unit varies by service:

| Service type | Billing unit |
|-------------|-------------|
| Virtual machines (EC2) | Per second or per hour |
| Serverless compute (Lambda) | Per invocation + per GB-second of memory used |
| Object storage (S3) | Per GB-month stored + per request |
| Data transfer | Per GB transferred (egress to internet) |
| Database (RDS) | Per vCPU-hour + per GB-month storage |
| Load balancer | Per hour + per LCU (Load Balancer Capacity Unit) |
| DNS queries (Route 53) | Per million queries |

---

## Pricing Models

### On-Demand (Pay-As-You-Go)

Pay the list price for resources as you use them. No commitment, no minimum spend.

**Best for:** Development, testing, short-lived workloads, unpredictable traffic.

**AWS example:** An EC2 `t3.medium` in `us-east-1` costs ~$0.0416/hour on-demand. A month of 24/7 usage ≈ $30.

**Trade-off:** Most expensive per unit. Highest flexibility.

---

### Reserved Instances / Committed Use

Commit to using a specific resource for 1 or 3 years in exchange for a significant discount (typically 30–72% off on-demand).

| Provider | Term | Name |
|---------|------|------|
| AWS | 1 or 3 years | Reserved Instances (EC2, RDS, ElastiCache) |
| AWS | 1 or 3 years | Savings Plans (flexible, covers EC2 + Fargate + Lambda) |
| Azure | 1 or 3 years | Reserved VM Instances |
| GCP | 1 or 3 years | Committed Use Discounts (CUDs) |

**Payment options (AWS RI):**
- **No Upfront**: Pay monthly, ~30–40% discount
- **Partial Upfront**: Pay some now, rest monthly, ~40–55% discount
- **All Upfront**: Pay everything now, ~55–72% discount

**Best for:** Stable, predictable workloads you know will run continuously (production databases, core API servers).

**Gotcha:** You pay for reserved capacity whether you use it or not. If your workload changes significantly, you may pay for unused reservations. AWS allows selling unused RIs on the Reserved Instance Marketplace.

---

### Spot / Preemptible Instances

Use spare cloud provider capacity at a steep discount. The provider can reclaim the instance with short notice.

| Provider | Name | Notice | Discount |
|---------|------|--------|---------|
| AWS | Spot Instances | 2 minutes | Up to 90% |
| Azure | Spot VMs | 30 seconds | Up to 90% |
| GCP | Preemptible / Spot VMs | 30 seconds | 60–91% |

**Best for:** Fault-tolerant workloads that can be interrupted — batch processing, CI/CD pipelines, ML training, rendering, big data.

**Not suitable for:** Databases, stateful services, anything where abrupt termination causes data loss or user impact.

---

### Savings Plans (AWS-specific)

AWS Savings Plans are a more flexible form of commitment than Reserved Instances. You commit to a dollar amount of spend per hour (e.g., $10/hour) rather than a specific instance type.

| Plan type | Coverage | Flexibility |
|----------|---------|------------|
| Compute Savings Plan | EC2, Fargate, Lambda | Any instance family, size, region, OS |
| EC2 Instance Savings Plan | EC2 only | Specific region + instance family, any size |

Savings Plans discount your bill automatically — no manual reservation management.

---

### Free Tier

All major providers offer a free tier for new accounts:

**AWS Free Tier (12-month trial):**
- EC2: 750 hours/month of `t2.micro` or `t3.micro`
- S3: 5GB storage, 20,000 GET, 2,000 PUT
- RDS: 750 hours/month `db.t2.micro` + 20GB storage
- Lambda: 1 million requests/month (free forever)

**AWS Always-Free (no expiry):**
- Lambda: 1 million requests + 400,000 GB-seconds compute
- DynamoDB: 25GB storage + 25 RCU + 25 WCU
- CloudWatch: 10 custom metrics + 10 alarms

**GCP Free Tier (always free):**
- Compute Engine: 1 `e2-micro` instance (US regions only)
- Cloud Storage: 5GB
- Cloud Functions: 2 million invocations/month

---

## Key Cost Drivers to Watch

### 1. Data Transfer (Egress)

Data leaving the cloud (to the internet or to another region) is typically charged. Ingress is usually free.

```
Internet → Cloud (ingress): FREE
Cloud → Internet (egress): $0.09/GB (AWS, first 10TB, us-east-1)
Cloud Region A → Cloud Region B: ~$0.02/GB
Within same AZ: FREE
Between AZs, same region: ~$0.01/GB
```

**Action:** Keep services that communicate frequently in the same AZ. Use CloudFront to reduce origin egress.

### 2. Storage (Not Deleting Old Data)

Storage bills accumulate silently. Unused EBS volumes, forgotten S3 buckets, old AMI snapshots, stale ECR images.

**Action:** Set S3 lifecycle policies, use AWS Cost Explorer to find large storage resources, clean up unused EBS volumes.

### 3. Idle Resources

EC2 instances running 24/7 even when not needed (dev environments left on overnight, staging environments not shut down).

**Action:** Use AWS Instance Scheduler, Lambda to stop/start dev instances on a schedule.

### 4. Unoptimized Instance Sizing

Using a large instance when a small one would suffice. Over-provisioning to "play it safe."

**Action:** Use AWS Compute Optimizer, Azure Advisor, or GCP Recommender to identify right-sizing opportunities.

### 5. NAT Gateway

NAT Gateways charge per hour + per GB processed. High-throughput workloads can make NAT Gateway surprisingly expensive.

**Action:** Consider VPC endpoints for AWS services (S3, DynamoDB) to bypass NAT Gateway entirely.

---

## Understanding Your Bill

### AWS Cost and Usage Report (CUR)

The most granular billing data available from AWS. Line items for every resource, every hour. Export to S3 and analyze with Athena or QuickSight.

### AWS Cost Explorer

Visual cost analysis tool. Filter by service, region, account, tag. Shows trends and provides forecasts.

### AWS Budgets

Set spending thresholds with email/SNS alerts when you approach or exceed them.

```
Budget example:
  Monthly spend > $100 → alert at 80% and 100%
  EC2 spend > $50 → alert when exceeded
```

### AWS Cost Allocation Tags

Tag every resource with `Environment`, `Team`, `Project`, `CostCenter`. Then filter Cost Explorer and CUR by tag to see spend by team or project.

```
aws ec2 create-tags \
  --resources i-1234567890abcdef0 \
  --tags Key=Environment,Value=production \
         Key=Team,Value=platform \
         Key=Project,Value=api-gateway
```

---

## Cost Optimization Hierarchy

1. **Right-size first** — ensure you're not running more capacity than needed
2. **Turn off what you don't use** — dev environments, idle resources
3. **Use Savings Plans / Reserved Instances** — for stable, predictable workloads
4. **Use Spot where possible** — batch, CI/CD, training jobs
5. **Architect to reduce data transfer** — minimize cross-AZ and cross-region traffic
6. **Monitor and alert** — set budgets, review Cost Explorer weekly

---

## References

- [AWS Pricing Calculator](https://calculator.aws/pricing/2/home)
- [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- [Cloud Pricing Comparison (Infracost)](https://www.infracost.io/docs/)
---

← [Previous: Regions & Zones](./regions-zones-geography.md) | [Home](../README.md) | [Next: Account Safety Checklist →](./account-safety-checklist.md)
