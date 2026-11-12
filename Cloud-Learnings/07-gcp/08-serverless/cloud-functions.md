← [Previous: GCP Serverless](./README.md) | [Home](../../README.md) | [Next: Pub/Sub →](./pubsub.md)

---

# Cloud Functions

Cloud Functions is Google Cloud's serverless compute platform for event-driven functions. **2nd generation** (based on Cloud Run) is the recommended offering — it supports longer timeouts, larger instances, and concurrency.

---

## Gen 1 vs Gen 2

| Feature | Gen 1 | Gen 2 |
|---------|-------|-------|
| Max timeout | 9 min | 60 min |
| Max instances | 3,000 | 3,000 |
| Concurrency | 1 per instance | Up to 1,000 |
| Max memory | 8 GiB | 32 GiB |
| Min instances | Yes | Yes |
| VPC connector | Yes | Yes |
| Based on | Cloud Functions runtime | Cloud Run |

---

## HTTP Function (2nd Gen)

```python
# main.py
import os
import json
import logging
import functions_framework
from flask import Request, Response, jsonify

logger = logging.getLogger(__name__)


@functions_framework.http
def handle_request(request: Request) -> Response:
    """HTTP-triggered Cloud Function."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.info("Function invoked", extra={"request_id": request_id, "method": request.method})

    if request.method == "OPTIONS":
        # CORS preflight
        response = Response("", status=204)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    if request.method != "POST":
        logger.warning("Method not allowed", extra={"method": request.method})
        return jsonify({"error": "method not allowed"}), 405

    data = request.get_json(silent=True)
    if not data:
        logger.warning("Missing request body", extra={"request_id": request_id})
        return jsonify({"error": "JSON body required"}), 400

    logger.info("Processing data", extra={"request_id": request_id, "keys": list(data.keys())})

    result = {"status": "ok", "processed": True, "request_id": request_id}
    logger.info("Request complete", extra={"request_id": request_id})
    return jsonify(result), 200
```

```bash
# requirements.txt
functions-framework==3.*
flask==3.*
```

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"

# Deploy HTTP function (2nd gen)
gcloud functions deploy handle-request \
    --project=$PROJECT \
    --region=$REGION \
    --gen2 \
    --runtime=python312 \
    --source=. \
    --entry-point=handle_request \
    --trigger-http \
    --service-account=sa-functions@$PROJECT.iam.gserviceaccount.com \
    --memory=512Mi \
    --cpu=1 \
    --timeout=60s \
    --min-instances=0 \
    --max-instances=100 \
    --concurrency=80 \
    --set-env-vars="GCP_PROJECT=$PROJECT,ENVIRONMENT=production" \
    --set-secrets="API_KEY=api-key:latest" \
    --vpc-connector=vpc-connector-prod \
    --vpc-egress=private-ranges-only \
    --no-allow-unauthenticated \
    --labels=environment=production,trigger=http

# Get function URL
gcloud functions describe handle-request \
    --project=$PROJECT \
    --region=$REGION \
    --gen2 \
    --format="value(serviceConfig.uri)"

# Allow unauthenticated invocation (public function)
gcloud functions add-invoker-iam-policy-binding handle-request \
    --project=$PROJECT \
    --region=$REGION \
    --gen2 \
    --member="allUsers"
```

---

## Pub/Sub Triggered Function (2nd Gen)

```python
# main.py
import base64
import json
import logging
import os
import functions_framework
from cloudevents.http import CloudEvent

logger = logging.getLogger(__name__)


@functions_framework.cloud_event
def process_message(cloud_event: CloudEvent) -> None:
    """Pub/Sub-triggered Cloud Function (CloudEvents format for Gen 2)."""
    logger.info(
        "Cloud event received",
        extra={
            "event_id": cloud_event["id"],
            "event_type": cloud_event["type"],
            "source": cloud_event["source"],
        },
    )

    # Decode Pub/Sub message
    pubsub_message = cloud_event.data.get("message", {})
    message_id = pubsub_message.get("messageId", "unknown")
    raw_data = pubsub_message.get("data", "")
    attributes = pubsub_message.get("attributes", {})

    try:
        payload = json.loads(base64.b64decode(raw_data).decode("utf-8"))
    except (ValueError, KeyError) as exc:
        logger.error(
            "Failed to decode message",
            extra={"message_id": message_id, "error": str(exc)},
        )
        raise  # Re-raise to trigger retry (Pub/Sub nack)

    logger.info(
        "Processing Pub/Sub message",
        extra={"message_id": message_id, "attributes": attributes, "payload_keys": list(payload.keys())},
    )

    # Process payload
    _handle_event(payload, message_id)
    logger.info("Message processed successfully", extra={"message_id": message_id})


def _handle_event(payload: dict, message_id: str) -> None:
    """Business logic for the event."""
    event_type = payload.get("event_type")
    logger.info("Handling event", extra={"message_id": message_id, "event_type": event_type})
    # ... your logic here
```

```bash
# Deploy Pub/Sub triggered function
TOPIC="my-app-events"

gcloud functions deploy process-message \
    --project=$PROJECT \
    --region=$REGION \
    --gen2 \
    --runtime=python312 \
    --source=. \
    --entry-point=process_message \
    --trigger-topic=$TOPIC \
    --service-account=sa-functions@$PROJECT.iam.gserviceaccount.com \
    --memory=256Mi \
    --timeout=300s \
    --retry \
    --set-env-vars="GCP_PROJECT=$PROJECT"
```

---

## Storage-Triggered Function

```python
import functions_framework
import logging
from cloudevents.http import CloudEvent

logger = logging.getLogger(__name__)


@functions_framework.cloud_event
def on_gcs_finalize(cloud_event: CloudEvent) -> None:
    """Triggered when a GCS object is created/updated."""
    data = cloud_event.data
    bucket = data.get("bucket")
    name = data.get("name")
    size = data.get("size")
    content_type = data.get("contentType")

    logger.info(
        "GCS object finalized",
        extra={"bucket": bucket, "name": name, "size": size, "content_type": content_type},
    )

    if not name.endswith(".json"):
        logger.info("Skipping non-JSON file", extra={"name": name})
        return

    # Process the file
    logger.info("Processing JSON file", extra={"bucket": bucket, "name": name})
```

```bash
# Deploy GCS-triggered function
gcloud functions deploy on-gcs-finalize \
    --project=$PROJECT \
    --region=$REGION \
    --gen2 \
    --runtime=python312 \
    --source=. \
    --entry-point=on_gcs_finalize \
    --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
    --trigger-event-filters="bucket=my-app-prod-uploads" \
    --trigger-location=$REGION \
    --service-account=sa-functions@$PROJECT.iam.gserviceaccount.com \
    --memory=512Mi \
    --timeout=120s
```

---

## Managing Functions

```bash
# List functions
gcloud functions list \
    --project=$PROJECT \
    --gen2 \
    --regions=$REGION \
    --format="table(name,state,runtime,updateTime)"

# View logs
gcloud functions logs read handle-request \
    --project=$PROJECT \
    --region=$REGION \
    --gen2 \
    --limit=50

# Update environment variables only
gcloud functions deploy handle-request \
    --project=$PROJECT \
    --region=$REGION \
    --gen2 \
    --update-env-vars="LOG_LEVEL=DEBUG"

# Delete a function
gcloud functions delete handle-request \
    --project=$PROJECT \
    --region=$REGION \
    --gen2
```

---

## References

- [Cloud Functions documentation](https://cloud.google.com/functions/docs)
- [Functions Framework for Python](https://github.com/GoogleCloudPlatform/functions-framework-python)
- [Gen 2 overview](https://cloud.google.com/functions/docs/concepts/version-comparison)
- [CloudEvents spec](https://cloudevents.io/)

---

← [Previous: GCP Serverless](./README.md) | [Home](../../README.md) | [Next: Pub/Sub →](./pubsub.md)
