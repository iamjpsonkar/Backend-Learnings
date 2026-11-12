← [Previous: Cloud Run](../07-containers/cloud-run.md) | [Home](../../README.md) | [Next: Cloud Functions →](./cloud-functions.md)

---

# GCP Serverless

---

## Service Overview

| Service | AWS Equivalent | Use Case |
|---------|----------------|---------|
| **Cloud Functions** | Lambda | Event-driven serverless compute |
| **Cloud Run** | ECS Fargate / Lambda (containers) | Containerized serverless HTTP services |
| **Cloud Pub/Sub** | SQS + SNS | Asynchronous messaging — queues and fan-out |
| **Eventarc** | EventBridge | Route events from GCP services to targets |
| **Cloud Tasks** | SQS (task queue) | Managed HTTP task queue with retries and rate limiting |
| **Cloud Scheduler** | EventBridge Scheduler | Cron-based job scheduling |
| **Workflows** | Step Functions | Serverless workflow orchestration |

---

## Cloud Functions (2nd Gen)

Cloud Functions 2nd gen runs on Cloud Run under the hood — longer timeouts, more memory, VPC support.

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"
SA_EMAIL="api-backend@${PROJECT_ID}.iam.gserviceaccount.com"

# Deploy an HTTP function
gcloud functions deploy my-app-api \
    --project=$PROJECT_ID \
    --region=$REGION \
    --gen2 \
    --runtime=python311 \
    --trigger-http \
    --entry-point=handle_request \
    --source=. \
    --service-account=$SA_EMAIL \
    --no-allow-unauthenticated \
    --memory=512MB \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=100 \
    --timeout=60 \
    --vpc-connector=vpc-connector-us-central1 \
    --vpc-egress=private-ranges-only \
    --set-env-vars=GCP_PROJECT_ID=$PROJECT_ID,APP_ENV=production \
    --set-secrets=DB_PASSWORD=api-database-password:latest

# Deploy a Pub/Sub-triggered function
gcloud functions deploy process-order \
    --project=$PROJECT_ID \
    --region=$REGION \
    --gen2 \
    --runtime=python311 \
    --trigger-topic=orders \
    --entry-point=process_order_message \
    --source=. \
    --service-account=$SA_EMAIL \
    --retry \
    --timeout=300

# Get function URL
gcloud functions describe my-app-api \
    --project=$PROJECT_ID \
    --region=$REGION \
    --gen2 \
    --format="value(serviceConfig.uri)"
```

### Python Function Code

```python
# main.py — Cloud Functions (2nd gen) HTTP + Pub/Sub handlers
import base64
import json
import logging
import os
import functions_framework
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

_secret_client = secretmanager.SecretManagerServiceClient()
_project_id = os.environ["GCP_PROJECT_ID"]


def _get_secret(secret_name: str) -> str:
    """Fetch a secret from Secret Manager."""
    name = f"projects/{_project_id}/secrets/{secret_name}/versions/latest"
    logger.info("Fetching secret: name=%s", secret_name)
    response = _secret_client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")


@functions_framework.http
def handle_request(request):
    """HTTP function — POST /orders."""
    request_id = request.headers.get("x-request-id", "unknown")
    logger.info("Handling HTTP request: method=%s path=%s request_id=%s",
                request.method, request.path, request_id)

    if request.method != "POST":
        logger.warning("Method not allowed: method=%s request_id=%s", request.method, request_id)
        return {"error": "Method not allowed"}, 405

    try:
        body = request.get_json(silent=True)
        if not body:
            return {"error": "Invalid JSON"}, 400
    except Exception as e:
        logger.error("Failed to parse request body: request_id=%s error=%s", request_id, str(e))
        return {"error": "Bad request"}, 400

    customer_id = body.get("customerId")
    if not customer_id:
        return {"error": "customerId is required"}, 400

    logger.info("Processing order creation: request_id=%s customer_id=%s", request_id, customer_id)
    order = {"orderId": "ord-123", "customerId": customer_id, "status": "created"}
    logger.info("Order created: request_id=%s order_id=%s", request_id, order["orderId"])
    return order, 201


@functions_framework.cloud_event
def process_order_message(cloud_event):
    """Pub/Sub push function — triggered by messages on the 'orders' topic."""
    message_id = cloud_event.data.get("message", {}).get("messageId", "unknown")
    logger.info("Processing Pub/Sub message: message_id=%s", message_id)

    try:
        data_b64 = cloud_event.data["message"]["data"]
        data = json.loads(base64.b64decode(data_b64).decode("utf-8"))
        logger.debug("Message decoded: message_id=%s data_preview=%.100s", message_id, str(data))
    except (KeyError, json.JSONDecodeError, Exception) as e:
        logger.error("Failed to decode message: message_id=%s error=%s", message_id, str(e))
        raise  # Raise to trigger retry

    order_id = data.get("orderId")
    if not order_id:
        logger.error("Missing orderId in message: message_id=%s", message_id)
        return  # Return without raising — don't retry malformed messages

    logger.info("Fulfilling order: message_id=%s order_id=%s", message_id, order_id)
    # ... fulfillment logic ...
    logger.info("Order fulfilled: message_id=%s order_id=%s", message_id, order_id)
```

---

## Cloud Pub/Sub

```bash
# Create a topic
gcloud pubsub topics create orders \
    --project=$PROJECT_ID \
    --labels=environment=production

# Create a subscription (pull — consumers poll for messages)
gcloud pubsub subscriptions create orders-fulfillment \
    --project=$PROJECT_ID \
    --topic=orders \
    --ack-deadline=60 \
    --message-retention-duration=7d \
    --min-retry-delay=10s \
    --max-retry-delay=600s \
    --dead-letter-topic=projects/$PROJECT_ID/topics/orders-dead-letter \
    --max-delivery-attempts=5 \
    --labels=environment=production

# Create a push subscription (Pub/Sub pushes to an HTTPS endpoint)
gcloud pubsub subscriptions create orders-push-to-run \
    --project=$PROJECT_ID \
    --topic=orders \
    --push-endpoint=$(gcloud run services describe my-app-processor \
        --project=$PROJECT_ID --region=$REGION \
        --format="value(status.url)")/pubsub \
    --push-auth-service-account=pubsub-invoker@${PROJECT_ID}.iam.gserviceaccount.com \
    --ack-deadline=60

# Publish a message
gcloud pubsub topics publish orders \
    --project=$PROJECT_ID \
    --message='{"orderId":"ord-123","customerId":"cust-456"}' \
    --attribute=source=api,version=v1

# Pull messages (testing)
gcloud pubsub subscriptions pull orders-fulfillment \
    --project=$PROJECT_ID \
    --limit=5 \
    --auto-ack

# Create a dead-letter topic
gcloud pubsub topics create orders-dead-letter \
    --project=$PROJECT_ID

gcloud pubsub subscriptions create orders-dead-letter-viewer \
    --project=$PROJECT_ID \
    --topic=orders-dead-letter \
    --ack-deadline=600
```

---

## Eventarc

Eventarc routes events from GCP services and custom sources to Cloud Run, GKE, or Cloud Functions.

```bash
# Route Cloud Storage object creation events to a Cloud Run service
gcloud eventarc triggers create trigger-gcs-upload \
    --project=$PROJECT_ID \
    --location=$REGION \
    --destination-run-service=my-app-file-processor \
    --destination-run-region=$REGION \
    --event-filters="type=google.cloud.storage.object.v1.finalized" \
    --event-filters="bucket=${PROJECT_ID}-uploads" \
    --service-account=eventarc-invoker@${PROJECT_ID}.iam.gserviceaccount.com

# Route Pub/Sub messages to a Cloud Run service via Eventarc
gcloud eventarc triggers create trigger-orders-topic \
    --project=$PROJECT_ID \
    --location=$REGION \
    --destination-run-service=my-app-order-processor \
    --destination-run-region=$REGION \
    --event-filters="type=google.cloud.pubsub.topic.v1.messagePublished" \
    --transport-topic=orders \
    --service-account=eventarc-invoker@${PROJECT_ID}.iam.gserviceaccount.com

# List triggers
gcloud eventarc triggers list \
    --project=$PROJECT_ID \
    --location=$REGION
```

---

## Cloud Scheduler

```bash
# Create a cron job that publishes to Pub/Sub (triggers a Cloud Function)
gcloud scheduler jobs create pubsub daily-report \
    --project=$PROJECT_ID \
    --location=$REGION \
    --schedule="0 8 * * *" \
    --time-zone="America/New_York" \
    --topic=daily-report-trigger \
    --message-body='{"report":"daily-summary","date":"today"}' \
    --description="Trigger daily report generation at 8 AM ET"

# Create a cron job that calls an HTTP endpoint
gcloud scheduler jobs create http cleanup-expired-sessions \
    --project=$PROJECT_ID \
    --location=$REGION \
    --schedule="*/5 * * * *" \
    --uri="$(gcloud run services describe my-app-api \
        --project=$PROJECT_ID --region=$REGION --format='value(status.url)')/admin/cleanup" \
    --http-method=POST \
    --oidc-service-account-email=scheduler-invoker@${PROJECT_ID}.iam.gserviceaccount.com \
    --oidc-token-audience="$(gcloud run services describe my-app-api \
        --project=$PROJECT_ID --region=$REGION --format='value(status.url)')" \
    --message-body='{}' \
    --headers=Content-Type=application/json

# Run a job immediately (testing)
gcloud scheduler jobs run cleanup-expired-sessions \
    --project=$PROJECT_ID \
    --location=$REGION

# Pause a job
gcloud scheduler jobs pause cleanup-expired-sessions \
    --project=$PROJECT_ID \
    --location=$REGION
```

---

## Cloud Tasks

Cloud Tasks is a managed HTTP task queue with rate limiting, deduplication, and retry control.

```bash
# Create a queue
gcloud tasks queues create order-processing \
    --project=$PROJECT_ID \
    --location=$REGION \
    --max-dispatches-per-second=100 \
    --max-concurrent-dispatches=50 \
    --max-attempts=5 \
    --min-backoff=10s \
    --max-backoff=600s \
    --max-doublings=4
```

```python
# Enqueue an HTTP task from application code
import logging
import json
import os
from datetime import timedelta
from google.cloud import tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2
from google.api_core.exceptions import AlreadyExists

logger = logging.getLogger(__name__)

_tasks_client = tasks_v2.CloudTasksClient()
_project_id = os.environ["GCP_PROJECT_ID"]
_region = os.environ.get("GCP_REGION", "us-central1")
_queue = "order-processing"


def enqueue_order(order_id: str, payload: dict, delay_seconds: int = 0) -> str:
    """Enqueue an order processing task with optional delay."""
    queue_path = _tasks_client.queue_path(_project_id, _region, _queue)
    task_id = f"order-{order_id}"
    task_name = f"{queue_path}/tasks/{task_id}"

    logger.info("Enqueueing task: queue=%s task_id=%s delay=%ds", _queue, task_id, delay_seconds)

    task = {
        "name": task_name,
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{os.environ['WORKER_BASE_URL']}/tasks/process-order",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode(),
            "oidc_token": {
                "service_account_email": os.environ["TASKS_SA_EMAIL"],
            },
        },
    }

    if delay_seconds > 0:
        from google.protobuf import timestamp_pb2
        from datetime import datetime, timezone
        scheduled = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        task["schedule_time"] = {
            "seconds": int(scheduled.timestamp()),
        }

    try:
        response = _tasks_client.create_task(request={"parent": queue_path, "task": task})
        logger.info("Task enqueued: task_name=%s", response.name)
        return response.name
    except AlreadyExists:
        logger.info("Task already exists (deduplication): task_id=%s", task_id)
        return task_name
```

---

## References

- [Cloud Functions documentation](https://cloud.google.com/functions/docs)
- [Cloud Pub/Sub documentation](https://cloud.google.com/pubsub/docs)
- [Eventarc documentation](https://cloud.google.com/eventarc/docs)
- [Cloud Scheduler documentation](https://cloud.google.com/scheduler/docs)
- [Cloud Tasks documentation](https://cloud.google.com/tasks/docs)
---

← [Previous: Cloud Run](../07-containers/cloud-run.md) | [Home](../../README.md) | [Next: Cloud Functions →](./cloud-functions.md)
