← [Previous: Cloud Monitoring](./cloud-monitoring.md) | [Home](../../README.md) | [Next: Cloud Trace →](./cloud-trace.md)

---

# Cloud Logging

Cloud Logging collects and stores logs from GCP services, VMs, Kubernetes, and custom applications. It supports log-based metrics, sinks (export), and the Log Explorer for querying.

---

## Structured Logging (Python)

```python
import json
import logging
import os
import sys
from typing import Any


class StructuredLogHandler(logging.Handler):
    """Emit logs as JSON for Cloud Logging structured format."""

    # Mapping from Python log levels to Cloud Logging severities
    _SEVERITY_MAP = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
    }

    def emit(self, record: logging.LogRecord) -> None:
        log_entry: dict[str, Any] = {
            "severity": self._SEVERITY_MAP.get(record.levelno, "DEFAULT"),
            "message": record.getMessage(),
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        # Include extra fields set by the caller
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "message", "msg",
                "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName",
            ):
                log_entry[key] = value

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        print(json.dumps(log_entry), flush=True)


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for Cloud Logging."""
    root = logging.getLogger()
    root.handlers.clear()

    handler = StructuredLogHandler()
    handler.setLevel(level)
    root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# Usage
setup_logging(os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Log with structured fields — all extra kwargs become JSON fields
logger.info(
    "Order created",
    extra={
        "order_id": "ord_001",
        "customer_id": "cust_123",
        "amount": 99.99,
        "trace_id": "abc123",
    },
)

logger.warning(
    "Slow query detected",
    extra={"query_duration_ms": 1250, "table": "events", "threshold_ms": 1000},
)

logger.error(
    "Payment processing failed",
    extra={"order_id": "ord_002", "payment_provider": "stripe", "error_code": "card_declined"},
)
```

---

## Log Sinks (Export)

```bash
PROJECT="my-app-prod-123456"

# Export all logs to Cloud Storage (long-term retention / compliance)
gcloud logging sinks create all-logs-archive \
    --project=$PROJECT \
    storage.googleapis.com/my-app-prod-logs \
    --log-filter="" \
    --description="Archive all logs to GCS"

# Export error logs to BigQuery (for analysis)
gcloud logging sinks create error-logs-bq \
    --project=$PROJECT \
    bigquery.googleapis.com/projects/$PROJECT/datasets/log_analytics \
    --log-filter="severity >= ERROR" \
    --use-partitioned-tables \
    --description="Export ERROR+ logs to BigQuery"

# Export to Pub/Sub (stream to external SIEM)
gcloud logging sinks create security-logs-pubsub \
    --project=$PROJECT \
    pubsub.googleapis.com/projects/$PROJECT/topics/security-logs \
    --log-filter='resource.type="gce_instance" OR resource.type="k8s_container"' \
    --description="Stream compute logs to SIEM"

# Grant the sink's writer SA permission to write to destination
SINK_SA=$(gcloud logging sinks describe all-logs-archive \
    --project=$PROJECT \
    --format="value(writerIdentity)")

gcloud storage buckets add-iam-policy-binding gs://my-app-prod-logs \
    --member="$SINK_SA" \
    --role="roles/storage.objectCreator"

# List sinks
gcloud logging sinks list --project=$PROJECT
```

---

## Log Explorer Queries

```
# All errors in the last hour
severity >= ERROR
timestamp >= "now-1h"

# Errors from a specific Cloud Run service
resource.type="cloud_run_revision"
resource.labels.service_name="my-app-api"
severity >= ERROR

# Slow requests (custom field from structured log)
resource.type="cloud_run_revision"
jsonPayload.request_duration_ms > 1000

# Search by order ID (custom structured field)
jsonPayload.order_id="ord_001"

# Kubernetes pod logs for a deployment
resource.type="k8s_container"
resource.labels.namespace_name="production"
resource.labels.container_name="api"
severity >= WARNING

# IAM permission denied events (security audit)
protoPayload.status.code=7
log_name="projects/my-app-prod-123456/logs/cloudaudit.googleapis.com%2Factivity"

# Cloud SQL slow queries
resource.type="cloudsql_database"
textPayload =~ "Query_time:[^0-9]*[1-9][0-9]*\."

# Combine: errors from multiple services, last 15 minutes
(resource.type="cloud_run_revision" OR resource.type="k8s_container")
severity >= ERROR
timestamp >= "now-15m"
```

---

## Log-Based Metrics

```bash
# Count 5xx responses from Cloud Run
gcloud logging metrics create cloud-run-5xx \
    --project=$PROJECT \
    --description="Count of 5xx responses from Cloud Run" \
    --log-filter='resource.type="cloud_run_revision" AND httpRequest.status >= 500'

# Distribution metric — capture request latency as a distribution
gcloud logging metrics create cloud-run-latency \
    --project=$PROJECT \
    --description="Cloud Run request latency distribution" \
    --log-filter='resource.type="cloud_run_revision" AND httpRequest.latency:*' \
    --value-extractor="EXTRACT(httpRequest.latency)" \
    --metric-kind=DELTA \
    --value-type=DISTRIBUTION \
    --unit=s

# List metrics
gcloud logging metrics list --project=$PROJECT
```

---

## Retention and Access

```bash
# Set log retention (default 30 days for _Default, 400 days for _Required)
gcloud logging buckets update _Default \
    --project=$PROJECT \
    --location=global \
    --retention-days=90

# Create a custom log bucket for compliance
gcloud logging buckets create compliance-logs \
    --project=$PROJECT \
    --location=us-central1 \
    --retention-days=365 \
    --description="Compliance log bucket — 1 year retention"

# Lock retention (prevents reduction before expiry)
gcloud logging buckets update compliance-logs \
    --project=$PROJECT \
    --location=us-central1 \
    --locked

# Grant a service account log viewer access
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:sa-log-reader@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/logging.viewer"
```

---

## References

- [Cloud Logging documentation](https://cloud.google.com/logging/docs)
- [Structured logging](https://cloud.google.com/logging/docs/structured-logging)
- [Log-based metrics](https://cloud.google.com/logging/docs/logs-based-metrics)
- [Log sinks](https://cloud.google.com/logging/docs/export/configure_export_v2)

---

← [Previous: Cloud Monitoring](./cloud-monitoring.md) | [Home](../../README.md) | [Next: Cloud Trace →](./cloud-trace.md)
