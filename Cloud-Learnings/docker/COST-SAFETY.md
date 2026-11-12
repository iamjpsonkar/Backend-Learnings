# Cost Safety Guide

## Default Mode: Free

In default mode, this platform costs **nothing** except your local machine's electricity and resources.

All services run entirely on your laptop/desktop:
- No cloud API calls
- No external services
- No SaaS dependencies
- No billing

The only external network calls are:
- Pulling Docker images on first run (from Docker Hub, GitHub Container Registry, etc.)
- That's it.

---

## Local Resource Cost

Running this platform uses **local compute resources**:

| Profile | Approximate CPU | Approximate RAM | Approximate Disk |
|---|---|---|---|
| core only | 0.1 CPU | 200 MB | 500 MB images |
| + data | +0.2 CPU | +800 MB | +2 GB images |
| + aws | +0.5 CPU | +600 MB | +1.5 GB images |
| + observability | +1 CPU | +2 GB | +3 GB images |
| + security | +1 CPU | +2 GB | +3 GB images |
| + cicd | +1 CPU | +2 GB | +3 GB images |
| all profiles | ~4 CPU | ~8-16 GB | ~15 GB images |

Volumes (database data, Vault data, etc.) grow as you use the platform but are capped by your disk.

---

## Real Cloud Extensions: These CAN Cost Money

The labs document optional "real cloud extensions" where you can practice against actual AWS/Azure/GCP. These extensions are:

- **Completely optional**
- **Not required for any lab**
- **Not used in default mode**
- **Never configured automatically**

If you choose to use real cloud services, follow these rules:

### Before you start

1. **Set a budget alert** — $5 or less for personal practice
2. **Use free tier** — but understand free tier has limits
3. **Create a dedicated practice account** — never use production
4. **Note what you create** — keep a list so you can delete everything

### AWS free tier traps

| Service | Free tier | What costs |
|---|---|---|
| EC2 | 750h/mo t2.micro (12 months) | Running > 750h, larger instances |
| S3 | 5 GB storage | Requests, data transfer out |
| RDS | 750h/mo db.t2.micro (12 months) | Multi-AZ, larger instances |
| Lambda | 1M requests/mo | Above that |
| CloudWatch | Basic metrics | Detailed metrics, custom metrics |
| Data transfer | 100 GB/mo out | Above that |

### Azure free tier traps

| Service | Free credits | What costs |
|---|---|---|
| New account | $200 for 30 days | After 30 days |
| App Service | B1 (1 year) | Scale up |
| Azure SQL | 250 GB/mo | Above that |
| Storage | 5 GB (12 months) | Above that |

### GCP free tier traps

| Service | Free tier | What costs |
|---|---|---|
| Compute | e2-micro (1/mo per region) | Additional VMs |
| Cloud Storage | 5 GB US region | Transfer, operations |
| BigQuery | 10 GB storage, 1 TB queries/mo | Above that |
| Cloud Run | 2M requests/mo | Above that |

---

## Free Tier Is Not Unlimited

Common misconception: "free tier means I can use as much as I want."

Wrong. Free tier has:
- Request limits
- Storage limits
- Bandwidth limits
- Time limits (12 months on some AWS/Azure services)
- Regional restrictions

Always check the current free tier limits in the official docs before testing.

---

## Budget Alarm Setup (Before Using Real Cloud)

### AWS

```bash
# Create a $5 budget alert via AWS CLI (real AWS)
aws budgets create-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget '{"BudgetName":"lab-budget","BudgetLimit":{"Amount":"5","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}' \
  --notifications-with-subscribers '[{"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80},"Subscribers":[{"SubscriptionType":"EMAIL","Address":"your@email.com"}]}]'
```

### Azure

1. Search "Cost Management + Billing" in Azure Portal
2. Budgets → Add
3. Set $5/month, 80% alert

### GCP

1. Billing → Budgets & alerts
2. Create budget → $5, 80% alert

---

## Cleanup Checklist for Real Cloud

After any real cloud practice session:

### AWS
```bash
# List and delete S3 buckets
aws s3 ls
aws s3 rb s3://my-practice-bucket --force

# List EC2 instances
aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,State.Name]'

# Terminate instances
aws ec2 terminate-instances --instance-ids i-xxxxxxxxx

# Delete CloudFormation stacks
aws cloudformation delete-stack --stack-name my-stack
```

### Azure
```bash
# Delete entire resource group (easiest cleanup)
az group delete --name my-practice-rg --yes
```

### GCP
```bash
# Delete entire project (nuclear option but thorough)
gcloud projects delete my-practice-project

# Or delete specific resources
gcloud compute instances delete my-instance
gcloud storage buckets delete gs://my-bucket
```

---

## Using LocalStack vs Real AWS

For the vast majority of learning goals, **LocalStack is sufficient and free**:

| Task | LocalStack | Real AWS needed? |
|---|---|---|
| S3 bucket CRUD | Yes | No |
| SQS queue | Yes | No |
| DynamoDB | Yes | No |
| Lambda (basic) | Yes (limited) | For production testing |
| IAM policies | Partial | For real permission testing |
| CloudFront | No | Yes |
| RDS | No | Yes |
| EKS | No | Yes |
| EC2 auto-scaling | Limited | Yes |

Use LocalStack for concept learning. Use real AWS only when you specifically need to test real behavior.

---

## Cost Summary

| Scenario | Cost |
|---|---|
| Using this platform in default mode | **$0** |
| Pulling Docker images (one-time) | $0 (internet bandwidth only) |
| Optional real AWS labs (careful) | ~$1-5/month with cleanup |
| Optional real Azure labs (careful) | $0-5 with cleanup |
| Optional real GCP labs (careful) | $0-5 with cleanup |
| Forgetting to clean up real cloud resources | **Could be expensive** |

When in doubt, use local emulators. They cover 80% of what you need to learn.
