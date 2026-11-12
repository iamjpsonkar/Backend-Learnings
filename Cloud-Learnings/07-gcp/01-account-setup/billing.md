← [Previous: Projects](./projects.md) | [Home](../../README.md) | [Next: GCP IAM →](../02-iam/README.md)

---

# GCP Billing and Cost Management

GCP billing is linked to a billing account. Projects are linked to billing accounts. Budgets, cost allocation labels, and the Cloud Billing API provide cost visibility and control.

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Billing Account** | Pays for resource usage across linked projects |
| **Invoice** | Monthly bill generated per billing account |
| **Budget** | Alert when spend reaches a threshold |
| **Cost Table** | Per-resource, per-service breakdown |
| **Committed Use Discounts (CUD)** | 1 or 3-year commitments for VMs/databases at 20–57% discount |
| **Sustained Use Discounts (SUD)** | Automatic discount for VMs running >25% of the month |
| **Free Tier** | Always-free quotas: 1 f1-micro VM, 5 GB Cloud Storage, 10 GB BigQuery queries/month |

---

## Viewing Costs

```bash
# View billing account linked to current project
gcloud billing projects describe $(gcloud config get-value project) \
    --format="table(billingAccountName,billingEnabled)"

# List all billing accounts
gcloud billing accounts list \
    --format="table(name,displayName,open,masterBillingAccount)"

# List projects under a billing account
gcloud billing projects list \
    --billing-account=BILLING_ACCOUNT_ID \
    --format="table(projectId,billingEnabled)"

# Export billing data to BigQuery (recommended for detailed analysis)
# Setup in Console: Billing → Billing export → BigQuery export
# Once set up, query via BigQuery:
# SELECT service.description, SUM(cost) as total_cost
# FROM `billing-export-project.billing_dataset.gcp_billing_export_v1_*`
# WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
# GROUP BY 1 ORDER BY 2 DESC LIMIT 20
```

---

## Budgets and Alerts

```bash
# Create a budget programmatically using the Cloud Billing Budgets API
# Easiest via Terraform:

# Terraform budget (in your Terraform config)
# resource "google_billing_budget" "monthly_alert" {
#   billing_account = "BILLING_ACCOUNT_ID"
#   display_name    = "monthly-production-budget"
#   amount {
#     specified_amount {
#       currency_code = "USD"
#       units         = "500"
#     }
#   }
#   threshold_rules { threshold_percent = 0.5 }
#   threshold_rules { threshold_percent = 0.8 }
#   threshold_rules { threshold_percent = 1.0 }
#   all_updates_rule {
#     pubsub_topic                 = google_pubsub_topic.budget_alerts.id
#     schema_version               = "1.0"
#     monitoring_notification_channels = [google_monitoring_notification_channel.email.name]
#   }
# }

# Via gcloud (alpha)
gcloud billing budgets create \
    --billing-account=BILLING_ACCOUNT_ID \
    --display-name="monthly-production-budget" \
    --budget-amount=500USD \
    --threshold-rule=percent=50,basis=CURRENT_SPEND \
    --threshold-rule=percent=80,basis=CURRENT_SPEND \
    --threshold-rule=percent=100,basis=CURRENT_SPEND

# List budgets
gcloud billing budgets list \
    --billing-account=BILLING_ACCOUNT_ID \
    --format="table(name,displayName,amount.specifiedAmount.units)"
```

---

## Cost Allocation with Labels

```bash
# Tag all resources with cost allocation labels
# Best done at project creation and enforced via org policies

# Label a project
gcloud projects update PROJECT_ID \
    --update-labels=cost-center=cc-1234,team=platform,environment=production

# Label a VM
gcloud compute instances add-labels my-vm \
    --zone=us-central1-a \
    --labels=cost-center=cc-1234,service=api

# Label a Cloud Storage bucket
gcloud storage buckets update gs://my-bucket \
    --update-labels=cost-center=cc-1234

# After billing export to BigQuery, query by label:
# SELECT labels.value as cost_center, SUM(cost) as total
# FROM `proj.dataset.gcp_billing_export_v1_*`, UNNEST(labels) as labels
# WHERE labels.key = "cost-center"
# GROUP BY 1 ORDER BY 2 DESC
```

---

## Committed Use Discounts (CUD)

CUDs apply to Compute Engine VM instances and Cloud SQL.

```bash
# Purchase a Compute Engine CUD (1 year, $100/month equivalent in a region)
gcloud compute commitments create my-commitment \
    --plan=12-month \
    --region=us-central1 \
    --resources=vcpu=8,memory=32GB

# List existing commitments
gcloud compute commitments list \
    --format="table(name,region,plan,status,endTimestamp)"

# CUD discount amounts:
# Compute Engine N2 1-year: 28% off on-demand
# Compute Engine N2 3-year: 46% off on-demand
# Cloud SQL 1-year: 25% off
# Cloud SQL 3-year: 52% off
```

---

## Cloud Billing Export to BigQuery

```bash
# One-time setup (do in Console or Terraform):
# Billing → Billing export → BigQuery export

# After export is configured, useful BigQuery queries:

# Top services by spend last 30 days
# SELECT
#   service.description AS service,
#   SUM(cost) + SUM(credits.amount) AS net_cost
# FROM `billing.dataset.gcp_billing_export_v1_*`, UNNEST(credits) credits
# WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
# GROUP BY 1
# ORDER BY 2 DESC
# LIMIT 10

# Daily spend trend
# SELECT
#   DATE(usage_start_time) as day,
#   SUM(cost) as daily_cost
# FROM `billing.dataset.gcp_billing_export_v1_*`
# GROUP BY 1 ORDER BY 1 DESC

# Cost anomaly detection (days where spend > 2x 7-day average)
# WITH daily AS (
#   SELECT DATE(usage_start_time) as day, SUM(cost) as cost
#   FROM `billing.dataset.gcp_billing_export_v1_*`
#   GROUP BY 1
# )
# SELECT day, cost,
#   AVG(cost) OVER (ORDER BY day ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) as avg7d
# FROM daily
# WHERE cost > 2 * AVG(cost) OVER (ORDER BY day ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING)
```

---

## Cost-Saving Strategies

```bash
# 1. Use Spot (preemptible) VMs for batch workloads
gcloud compute instances create batch-job \
    --provisioning-model=SPOT \
    --instance-termination-action=DELETE \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --machine-type=n2-standard-8

# 2. Set up auto-start/stop for dev VMs
# Schedule with Cloud Scheduler + Cloud Functions or Instance Schedules
gcloud compute resource-policies create instance-schedule \
    --name=dev-vm-schedule \
    --region=us-central1 \
    --vm-start-schedule="0 8 * * MON-FRI" \
    --vm-stop-schedule="0 19 * * MON-FRI" \
    --timezone="America/New_York"

gcloud compute instances add-resource-policies my-dev-vm \
    --zone=us-central1-a \
    --resource-policies=dev-vm-schedule

# 3. Right-size VMs using recommender
gcloud recommender recommendations list \
    --recommender=google.compute.instance.MachineTypeRecommender \
    --location=us-central1-a \
    --project=PROJECT_ID \
    --format="table(name,recommenderSubtype,stateInfo.state,primaryImpact.costProjection.cost.units)"

# 4. Delete unused resources
gcloud compute snapshots list --filter="creationTimestamp<2024-01-01" --format="value(name)" | \
    xargs -I {} gcloud compute snapshots delete {} --quiet
```

---

## References

- [Cloud Billing documentation](https://cloud.google.com/billing/docs)
- [Budget alerts](https://cloud.google.com/billing/docs/how-to/budgets)
- [Billing export to BigQuery](https://cloud.google.com/billing/docs/how-to/export-data-bigquery)
- [Committed use discounts](https://cloud.google.com/compute/docs/instances/signing-up-committed-use-discounts)

---

← [Previous: Projects](./projects.md) | [Home](../../README.md) | [Next: GCP IAM →](../02-iam/README.md)
