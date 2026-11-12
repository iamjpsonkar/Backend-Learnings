← [Previous: GKE Microservice](./gke-microservice.md) | [Home](../../README.md) | [Next: Other Clouds →](../../08-other-clouds/README.md)

---

# Project: Cloud Run Microservice API

Deploy a production-ready REST API on Cloud Run with Cloud SQL (PostgreSQL via Cloud SQL Python Connector), Secret Manager, Cloud Monitoring/Tracing, and a full CI/CD pipeline.

---

## Architecture

```
GitHub Actions
    │
    └── Cloud Build (test → build → push → deploy)
                                        │
                                        ▼
                               Cloud Run (managed)
                                        │
                             Workload Identity (SA)
                                        │
                              ┌─────────┼─────────┐
                              ▼         ▼         ▼
                         Cloud SQL  Secret    Cloud Monitoring
                        (PostgreSQL) Manager  (traces, metrics)
```

---

## Application Code

```python
# app/main.py
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.db import init_db, close_db
from app.routers import orders, health
from app.telemetry import setup_tracing, setup_metrics

logger = logging.getLogger(__name__)

PORT = int(os.environ.get("PORT", "8080"))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    logger.info("Starting up", extra={"environment": ENVIRONMENT})
    await init_db()
    yield
    logger.info("Shutting down")
    await close_db()


def create_app() -> FastAPI:
    setup_tracing()
    setup_metrics()

    app = FastAPI(
        title="My App API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if ENVIRONMENT == "production" else "/docs",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("ALLOWED_ORIGINS", "").split(","),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    app.include_router(health.router, tags=["health"])
    app.include_router(orders.router, prefix="/api/v1", tags=["orders"])

    FastAPIInstrumentor.instrument_app(app)
    logger.info("Application created", extra={"environment": ENVIRONMENT})
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        workers=1,
        log_config=None,  # Use our structured logging
    )
```

```python
# app/db.py
import logging
import os
from google.cloud.sql.connector import AsyncConnector, IPTypes
import asyncpg
from app.secrets import get_secret

logger = logging.getLogger(__name__)

PROJECT = os.environ["GCP_PROJECT"]
REGION = os.environ.get("DB_REGION", "us-central1")
DB_INSTANCE = os.environ["DB_INSTANCE"]  # e.g. my-app-prod-123456:us-central1:postgres-main
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]

_connector: AsyncConnector | None = None
_pool: asyncpg.Pool | None = None


async def init_db() -> None:
    """Initialize Cloud SQL Connector and asyncpg connection pool."""
    global _connector, _pool

    logger.info("Initializing database connection pool", extra={"instance": DB_INSTANCE})

    _connector = AsyncConnector()
    db_password = get_secret("db-password")

    async def getconn():
        return await _connector.connect_async(
            DB_INSTANCE,
            "asyncpg",
            user=DB_USER,
            password=db_password,
            db=DB_NAME,
            ip_type=IPTypes.PRIVATE,
        )

    _pool = await asyncpg.create_pool(
        min_size=2,
        max_size=10,
        connect=getconn,
    )
    logger.info("Database pool ready", extra={"min_size": 2, "max_size": 10})


async def close_db() -> None:
    global _connector, _pool
    if _pool:
        await _pool.close()
        logger.info("Database pool closed")
    if _connector:
        await _connector.close_async()


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool
```

---

## Dockerfile

```dockerfile
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/packages -r requirements.txt

# --- Final stage ---
FROM python:3.12-slim

RUN addgroup --gid 1000 app && adduser --uid 1000 --gid 1000 --no-create-home app

WORKDIR /app
COPY --from=builder /packages /usr/local/lib/python3.12/site-packages
COPY app/ ./app/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER app
EXPOSE 8080

CMD ["python", "-m", "app.main"]
```

---

## Cloud Build Pipeline

```yaml
# cloudbuild.yaml
steps:
  - id: "test"
    name: "python:3.12"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        pip install -r requirements-dev.txt
        pytest tests/ -v --tb=short --cov=app --cov-report=term-missing
    env:
      - "GCP_PROJECT=$PROJECT_ID"
      - "ENVIRONMENT=test"

  - id: "build"
    name: "gcr.io/cloud-builders/docker"
    args:
      - "build"
      - "-t"
      - "$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE:$COMMIT_SHA"
      - "-t"
      - "$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE:latest"
      - "--cache-from"
      - "$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE:latest"
      - "--build-arg"
      - "BUILDKIT_INLINE_CACHE=1"
      - "."
    waitFor: ["test"]

  - id: "push"
    name: "gcr.io/cloud-builders/docker"
    args:
      - "push"
      - "--all-tags"
      - "$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE"
    waitFor: ["build"]

  - id: "deploy"
    name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    entrypoint: "gcloud"
    args:
      - "run"
      - "deploy"
      - "$_SERVICE_NAME"
      - "--image=$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE:$COMMIT_SHA"
      - "--region=$_REGION"
      - "--project=$PROJECT_ID"
      - "--tag=commit-$SHORT_SHA"
      - "--no-traffic"
    waitFor: ["push"]

  - id: "smoke-test"
    name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        SERVICE_URL=$(gcloud run services describe $_SERVICE_NAME \
            --region=$_REGION --project=$PROJECT_ID \
            --format='value(status.traffic[0].url)')
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
            "$SERVICE_URL/health/ready")
        [ "$STATUS" = "200" ] || (echo "Smoke test failed: HTTP $STATUS" && exit 1)
        echo "Smoke test passed: HTTP $STATUS"
    waitFor: ["deploy"]

  - id: "promote"
    name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    entrypoint: "gcloud"
    args:
      - "run"
      - "services"
      - "update-traffic"
      - "$_SERVICE_NAME"
      - "--region=$_REGION"
      - "--project=$PROJECT_ID"
      - "--to-latest"
    waitFor: ["smoke-test"]

substitutions:
  _REGION: us-central1
  _REPO: my-app
  _IMAGE: api
  _SERVICE_NAME: my-app-api

timeout: "900s"

options:
  machineType: "E2_HIGHCPU_8"
  logging: CLOUD_LOGGING_ONLY
```

---

## Cloud Run Service Configuration

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"
SERVICE="my-app-api"
IMAGE="$REGION-docker.pkg.dev/$PROJECT/my-app/api"

# Deploy initial service
gcloud run deploy $SERVICE \
    --project=$PROJECT \
    --region=$REGION \
    --image=$IMAGE:latest \
    --service-account=sa-my-app@$PROJECT.iam.gserviceaccount.com \
    --set-env-vars="\
GCP_PROJECT=$PROJECT,\
ENVIRONMENT=production,\
DB_INSTANCE=$PROJECT:$REGION:postgres-main,\
DB_NAME=my_app,\
DB_USER=my_app,\
DB_REGION=$REGION" \
    --set-secrets="DB_PASSWORD_UNUSED=db-password:latest" \
    --cpu=1 \
    --memory=512Mi \
    --concurrency=80 \
    --min-instances=1 \
    --max-instances=50 \
    --timeout=30 \
    --port=8080 \
    --vpc-connector=vpc-connector-prod \
    --vpc-egress=private-ranges-only \
    --ingress=internal-and-cloud-load-balancing \
    --no-allow-unauthenticated

# Enable CPU boost on startup
gcloud run services update $SERVICE \
    --project=$PROJECT \
    --region=$REGION \
    --cpu-boost
```

---

## Monitoring Alert

```bash
# Create an alert for high error rate (>5% of requests)
cat > alert-error-rate.json <<EOF
{
  "displayName": "Cloud Run Error Rate > 5%",
  "conditions": [{
    "displayName": "5xx error rate exceeded",
    "conditionThreshold": {
      "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\" AND resource.labels.service_name=\"$SERVICE\"",
      "aggregations": [{
        "alignmentPeriod": "60s",
        "perSeriesAligner": "ALIGN_RATE",
        "crossSeriesReducer": "REDUCE_SUM",
        "groupByFields": ["resource.labels.service_name"]
      }],
      "comparison": "COMPARISON_GT",
      "thresholdValue": 0.05,
      "duration": "120s"
    }
  }],
  "combiner": "OR",
  "notificationChannels": ["projects/$PROJECT/notificationChannels/CHANNEL_ID"],
  "severity": "ERROR"
}
EOF

gcloud alpha monitoring policies create \
    --project=$PROJECT \
    --policy-from-file=alert-error-rate.json
```

---

## References

- [Cloud Run documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Python Connector](https://github.com/GoogleCloudPlatform/cloud-sql-python-connector)
- [FastAPI on Cloud Run](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service)
- [Cloud Build CI/CD](https://cloud.google.com/build/docs/deploying-builds/deploy-cloud-run)

---

← [Previous: GKE Microservice](./gke-microservice.md) | [Home](../../README.md) | [Next: Other Clouds →](../../08-other-clouds/README.md)
