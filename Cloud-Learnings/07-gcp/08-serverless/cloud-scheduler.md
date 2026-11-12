← [Previous: Pub/Sub](./pubsub.md) | [Home](../../README.md) | [Next: Cloud Tasks →](./cloud-tasks.md)

---

# Cloud Scheduler

Cloud Scheduler is a fully managed cron job service. It supports HTTP/S targets, Pub/Sub topics, and App Engine queues.

---

## Creating Jobs

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"
SERVICE_URL="https://my-app-worker-abc123-uc.a.run.app"

# HTTP job — invoke Cloud Run service
gcloud scheduler jobs create http daily-report \
    --project=$PROJECT \
    --location=$REGION \
    --schedule="0 8 * * 1-5" \
    --uri="$SERVICE_URL/jobs/daily-report" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"report_type": "daily", "recipients": ["ops@my-app.com"]}' \
    --oidc-service-account-email=sa-scheduler@$PROJECT.iam.gserviceaccount.com \
    --oidc-token-audience=$SERVICE_URL \
    --time-zone="America/New_York" \
    --attempt-deadline=10m \
    --description="Daily report — weekdays 8 AM ET"

# Pub/Sub job — publish to a topic
gcloud scheduler jobs create pubsub hourly-sync \
    --project=$PROJECT \
    --location=$REGION \
    --schedule="0 * * * *" \
    --topic=projects/$PROJECT/topics/my-app-events \
    --message-body='{"job": "hourly-sync"}' \
    --attributes="event_type=sync.triggered,source=scheduler" \
    --time-zone="UTC" \
    --description="Hourly data sync trigger"

# List jobs
gcloud scheduler jobs list \
    --project=$PROJECT \
    --location=$REGION \
    --format="table(name,schedule,state,lastAttemptTime,status.code)"

# Manually trigger a job (for testing)
gcloud scheduler jobs run daily-report \
    --project=$PROJECT \
    --location=$REGION

# Pause / resume a job
gcloud scheduler jobs pause daily-report \
    --project=$PROJECT \
    --location=$REGION

gcloud scheduler jobs resume daily-report \
    --project=$PROJECT \
    --location=$REGION

# Delete a job
gcloud scheduler jobs delete daily-report \
    --project=$PROJECT \
    --location=$REGION

# Grant Scheduler SA permission to invoke Cloud Run
gcloud run services add-iam-policy-binding my-app-worker \
    --project=$PROJECT \
    --region=$REGION \
    --member="serviceAccount:sa-scheduler@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
```

---

## Cron Syntax Reference

```
┌───────────── minute (0–59)
│ ┌───────────── hour (0–23)
│ │ ┌───────────── day of month (1–31)
│ │ │ ┌───────────── month (1–12)
│ │ │ │ ┌───────────── day of week (0–6, Sunday=0)
│ │ │ │ │
* * * * *

Common examples:
  0 * * * *         Every hour, on the hour
  */15 * * * *      Every 15 minutes
  0 9 * * 1-5       Weekdays at 9:00 AM
  0 0 1 * *         First day of every month at midnight
  30 6 * * *        Daily at 6:30 AM
  0 0 * * 0         Sundays at midnight

Special strings (also supported):
  @hourly           → 0 * * * *
  @daily            → 0 0 * * *
  @weekly           → 0 0 * * 0
  @monthly          → 0 0 1 * *
```

---

## Terraform Example

```hcl
resource "google_cloud_scheduler_job" "daily_report" {
  name        = "daily-report"
  project     = var.project_id
  region      = var.region
  description = "Daily report — weekdays 8 AM ET"
  schedule    = "0 8 * * 1-5"
  time_zone   = "America/New_York"

  attempt_deadline = "600s"

  retry_config {
    retry_count          = 3
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
    max_doublings        = 5
  }

  http_target {
    http_method = "POST"
    uri         = "${var.worker_url}/jobs/daily-report"

    body = base64encode(jsonencode({
      report_type = "daily"
      recipients  = ["ops@my-app.com"]
    }))

    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = var.scheduler_sa_email
      audience              = var.worker_url
    }
  }
}
```

---

## References

- [Cloud Scheduler documentation](https://cloud.google.com/scheduler/docs)
- [Cron format](https://cloud.google.com/scheduler/docs/configuring/cron-job-schedules)
- [Targeting Cloud Run](https://cloud.google.com/scheduler/docs/creating#targets)

---

← [Previous: Pub/Sub](./pubsub.md) | [Home](../../README.md) | [Next: Cloud Tasks →](./cloud-tasks.md)
