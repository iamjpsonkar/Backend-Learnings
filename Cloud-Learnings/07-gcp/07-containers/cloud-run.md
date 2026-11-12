← [Previous: GKE](./gke.md) | [Home](../../README.md) | [Next: GCP Serverless →](../08-serverless/README.md)

---

# Cloud Run

Cloud Run is a fully managed serverless container platform. It scales from zero to thousands of instances automatically and charges only for CPU and memory used during request processing.

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Service** | Long-running HTTP/gRPC endpoint — scales based on requests |
| **Job** | Batch/one-shot workload — runs to completion, not request-driven |
| **Revision** | Immutable snapshot of a service's container + config |
| **Traffic splitting** | Route traffic between revisions (canary, A/B, rollback) |
| **Concurrency** | Requests handled simultaneously per container instance |

---

## Deploying a Service

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"
SERVICE="my-app-api"
IMAGE="us-central1-docker.pkg.dev/$PROJECT/my-app/api:latest"

# Deploy a Cloud Run service
gcloud run deploy $SERVICE \
    --project=$PROJECT \
    --region=$REGION \
    --image=$IMAGE \
    --platform=managed \
    --service-account=sa-my-app@$PROJECT.iam.gserviceaccount.com \
    --set-env-vars="GCP_PROJECT=$PROJECT,ENVIRONMENT=production" \
    --set-secrets="DB_PASSWORD=db-password:latest,API_KEY=api-key:latest" \
    --cpu=1 \
    --memory=512Mi \
    --concurrency=80 \
    --min-instances=1 \
    --max-instances=100 \
    --timeout=30 \
    --port=8080 \
    --vpc-connector=vpc-connector-prod \
    --vpc-egress=private-ranges-only \
    --ingress=internal-and-cloud-load-balancing \
    --no-allow-unauthenticated \
    --labels=environment=production,team=backend

# Allow unauthenticated requests (public API)
gcloud run services add-iam-policy-binding $SERVICE \
    --project=$PROJECT \
    --region=$REGION \
    --member="allUsers" \
    --role="roles/run.invoker"

# Allow a specific service account to invoke (service-to-service)
gcloud run services add-iam-policy-binding $SERVICE \
    --project=$PROJECT \
    --region=$REGION \
    --member="serviceAccount:sa-frontend@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/run.invoker"

# Get service URL
gcloud run services describe $SERVICE \
    --project=$PROJECT \
    --region=$REGION \
    --format="value(status.url)"
```

---

## Traffic Splitting

```bash
# Deploy a new revision without serving traffic (tagged deploy)
gcloud run deploy $SERVICE \
    --project=$PROJECT \
    --region=$REGION \
    --image=us-central1-docker.pkg.dev/$PROJECT/my-app/api:v2.0 \
    --tag=v2 \
    --no-traffic

# Canary: send 10% to new revision
gcloud run services update-traffic $SERVICE \
    --project=$PROJECT \
    --region=$REGION \
    --to-revisions=LATEST=10,my-app-api-00005-abc=90

# Promote: send 100% to latest
gcloud run services update-traffic $SERVICE \
    --project=$PROJECT \
    --region=$REGION \
    --to-latest

# Rollback to a specific revision
gcloud run services update-traffic $SERVICE \
    --project=$PROJECT \
    --region=$REGION \
    --to-revisions=my-app-api-00004-xyz=100

# List revisions with traffic split
gcloud run revisions list \
    --project=$PROJECT \
    --region=$REGION \
    --service=$SERVICE \
    --format="table(name,status.conditions[0].status,spec.containerConcurrency,metadata.labels.run.googleapis.com/minScale)"
```

---

## Cloud Run Jobs

```bash
# Create a job (batch processing, migrations, etc.)
gcloud run jobs create db-migrate \
    --project=$PROJECT \
    --region=$REGION \
    --image=$IMAGE \
    --service-account=sa-my-app@$PROJECT.iam.gserviceaccount.com \
    --set-env-vars="GCP_PROJECT=$PROJECT" \
    --set-secrets="DB_PASSWORD=db-password:latest" \
    --cpu=2 \
    --memory=1Gi \
    --task-timeout=600 \
    --max-retries=2 \
    --parallelism=1 \
    --tasks=1 \
    --vpc-connector=vpc-connector-prod \
    --vpc-egress=all-traffic

# Execute a job
gcloud run jobs execute db-migrate \
    --project=$PROJECT \
    --region=$REGION \
    --wait

# Parallel job (process N tasks concurrently)
gcloud run jobs create process-events \
    --project=$PROJECT \
    --region=$REGION \
    --image=$IMAGE \
    --tasks=50 \
    --parallelism=10 \
    --set-env-vars="TOTAL_TASKS=50"
    # CLOUD_RUN_TASK_INDEX and CLOUD_RUN_TASK_COUNT env vars auto-injected

# List job executions
gcloud run jobs executions list \
    --project=$PROJECT \
    --region=$REGION \
    --job=db-migrate
```

---

## Python Service Example

```python
import os
import logging
import json
from typing import Any
import functions_framework
from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cloud Run injects PORT; default to 8080
PORT = int(os.environ.get("PORT", 8080))


@app.route("/health/ready")
def readiness():
    """Readiness probe — check dependencies."""
    return jsonify({"status": "ready"}), 200


@app.route("/health/live")
def liveness():
    """Liveness probe."""
    return jsonify({"status": "alive"}), 200


@app.route("/api/v1/process", methods=["POST"])
def process_request():
    """Main endpoint."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.info("Processing request", extra={"request_id": request_id})

    data = request.get_json(force=True)
    if not data:
        logger.warning("Empty request body", extra={"request_id": request_id})
        return jsonify({"error": "request body required"}), 400

    logger.info("Request processed", extra={"request_id": request_id, "keys": list(data.keys())})
    return jsonify({"status": "ok", "request_id": request_id}), 200


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=json.dumps(
            {
                "severity": "%(levelname)s",
                "message": "%(message)s",
                "time": "%(asctime)s",
            }
        ),
    )
    app.run(host="0.0.0.0", port=PORT)
```

---

## Serverless NEG (Custom Domain via Load Balancer)

```bash
# Reserve a global static IP
gcloud compute addresses create my-app-ip \
    --project=$PROJECT \
    --global

# Create a Serverless NEG for Cloud Run
gcloud compute network-endpoint-groups create neg-my-app \
    --project=$PROJECT \
    --region=$REGION \
    --network-endpoint-type=serverless \
    --cloud-run-service=$SERVICE

# Create backend service
gcloud compute backend-services create bs-my-app \
    --project=$PROJECT \
    --global \
    --load-balancing-scheme=EXTERNAL_MANAGED

gcloud compute backend-services add-backend bs-my-app \
    --project=$PROJECT \
    --global \
    --network-endpoint-group=neg-my-app \
    --network-endpoint-group-region=$REGION

# Create URL map → HTTPS proxy → forwarding rule
gcloud compute url-maps create urlmap-my-app \
    --project=$PROJECT \
    --default-service=bs-my-app

gcloud compute ssl-certificates create cert-my-app \
    --project=$PROJECT \
    --domains=api.my-app.com \
    --global

gcloud compute target-https-proxies create https-proxy-my-app \
    --project=$PROJECT \
    --url-map=urlmap-my-app \
    --ssl-certificates=cert-my-app

gcloud compute forwarding-rules create fr-my-app \
    --project=$PROJECT \
    --global \
    --target-https-proxy=https-proxy-my-app \
    --address=my-app-ip \
    --ports=443
```

---

## Service-to-Service Authentication

```python
import os
import logging
import google.auth.transport.requests
import google.oauth2.id_token
import requests as http_requests

logger = logging.getLogger(__name__)

TARGET_URL = os.environ["DOWNSTREAM_SERVICE_URL"]  # Cloud Run URL


def call_downstream_service(payload: dict) -> dict:
    """Call another Cloud Run service using identity token auth."""
    logger.info("Fetching identity token", extra={"target_url": TARGET_URL})

    auth_req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(auth_req, TARGET_URL)

    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json",
    }

    logger.info("Calling downstream service", extra={"target_url": TARGET_URL})
    response = http_requests.post(
        f"{TARGET_URL}/api/v1/process",
        json=payload,
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()

    logger.info(
        "Downstream call complete",
        extra={"target_url": TARGET_URL, "status_code": response.status_code},
    )
    return response.json()
```

---

## References

- [Cloud Run documentation](https://cloud.google.com/run/docs)
- [Cloud Run Jobs](https://cloud.google.com/run/docs/create-jobs)
- [Traffic management](https://cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration)
- [Serverless NEG](https://cloud.google.com/load-balancing/docs/negs/serverless-neg-concepts)

---

← [Previous: GKE](./gke.md) | [Home](../../README.md) | [Next: GCP Serverless →](../08-serverless/README.md)
