← [Previous: VPC Service Controls](../09-security/vpc-service-controls.md) | [Home](../../README.md) | [Next: Cloud Monitoring →](./cloud-monitoring.md)

---

# GCP Observability

---

## Service Overview

| Service | AWS Equivalent | Purpose |
|---------|----------------|---------|
| **Cloud Monitoring** | CloudWatch Metrics + Alarms | Metrics, dashboards, uptime checks, alerting |
| **Cloud Logging** | CloudWatch Logs | Log ingestion, storage, routing, and querying |
| **Cloud Trace** | X-Ray | Distributed request tracing |
| **Cloud Profiler** | CodeGuru Profiler | Continuous production profiling (CPU, heap) |
| **Error Reporting** | — | Automatic error grouping and alerting |
| **Log-based Metrics** | CloudWatch Metric Filters | Convert log entries into metrics |

---

## Cloud Monitoring

### Metrics and Uptime Checks

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"

# Create an uptime check (synthetic monitoring)
gcloud monitoring uptime create \
    --project=$PROJECT_ID \
    --display-name="My App API Health" \
    --resource-type=uptime_url \
    --hostname=my-app.example.com \
    --path=/health \
    --port=443 \
    --use-ssl \
    --check-interval=60 \
    --timeout=10

# List uptime checks
gcloud monitoring uptime list \
    --project=$PROJECT_ID \
    --format="table(displayName,httpCheck.host,httpCheck.path,period)"
```

### Custom Metrics (Python — OpenTelemetry)

```python
# requirements: opentelemetry-sdk opentelemetry-exporter-gcp-monitoring opentelemetry-api
import logging
import os
import time
from functools import wraps
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter

logger = logging.getLogger(__name__)

_exporter = CloudMonitoringMetricsExporter(project_id=os.environ["GCP_PROJECT_ID"])
_reader = PeriodicExportingMetricReader(_exporter, export_interval_millis=60_000)
_provider = MeterProvider(metric_readers=[_reader])
metrics.set_meter_provider(_provider)

meter = metrics.get_meter("my-app", version="1.0.0")

request_counter = meter.create_counter(
    name="my_app/request_count",
    description="Total HTTP requests handled",
    unit="1",
)
request_latency = meter.create_histogram(
    name="my_app/request_latency",
    description="HTTP request latency",
    unit="ms",
)
active_orders_gauge = meter.create_observable_gauge(
    name="my_app/active_orders",
    description="Currently active orders",
    unit="1",
    callbacks=[lambda opts: [metrics.observation.Observation(_get_active_orders_count())]],
)


def track_request(route: str):
    """Decorator to track request count and latency."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                elapsed_ms = (time.monotonic() - start) * 1000
                labels = {"route": route, "status": status}
                request_counter.add(1, labels)
                request_latency.record(elapsed_ms, labels)
                logger.debug("Request tracked: route=%s status=%s latency_ms=%.1f",
                             route, status, elapsed_ms)
        return wrapper
    return decorator


def _get_active_orders_count() -> int:
    # ... query database ...
    return 0
```

---

## Cloud Logging

### Structured Logging

```python
# requirements: google-cloud-logging
import logging
import os
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler

# Set up Cloud Logging client
_client = google.cloud.logging.Client(project=os.environ["GCP_PROJECT_ID"])

# Option 1: Attach Cloud Logging handler to root logger
_client.setup_logging(log_level=logging.INFO)

# Option 2: Use structured logging via standard library (preferred in Cloud Run / GKE)
# Log structured JSON to stdout — Cloud Logging agent picks it up automatically.
import json
import sys


class StructuredLogHandler(logging.StreamHandler):
    """Emit structured JSON logs compatible with Cloud Logging."""

    SEVERITY_MAP = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
    }

    def emit(self, record: logging.LogRecord) -> None:
        log_entry = {
            "severity": self.SEVERITY_MAP.get(record.levelno, "DEFAULT"),
            "message": self.format(record),
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }
        # Attach trace context if available
        trace_id = getattr(record, "trace_id", None)
        if trace_id:
            project_id = os.environ.get("GCP_PROJECT_ID", "")
            log_entry["logging.googleapis.com/trace"] = f"projects/{project_id}/traces/{trace_id}"

        # Merge any extra fields from the log record
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                log_entry[key] = value

        print(json.dumps(log_entry), file=sys.stdout, flush=True)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(StructuredLogHandler())
```

### Log Explorer Queries

```
# --- All ERROR+ logs in the last hour ---
resource.type="cloud_run_revision"
resource.labels.service_name="my-app-api"
severity >= ERROR
timestamp >= "2024-06-01T00:00:00Z"

# --- Requests slower than 5 seconds ---
resource.type="cloud_run_revision"
httpRequest.latency > "5s"

# --- Find a specific request by trace ID ---
resource.type="cloud_run_revision"
logging.googleapis.com/trace="projects/my-app-production/traces/TRACE_ID"

# --- 5xx errors with request details ---
resource.type="cloud_run_revision"
httpRequest.status >= 500
labels."cloud.googleapis.com/location"="us-central1"

# --- Cloud SQL slow queries ---
resource.type="cloudsql_database"
resource.labels.database_id="my-app-production:pg-my-app-prod"
textPayload:"duration:"
textPayload:"LOG:"
```

### Log-Based Metrics

```bash
# Create a counter metric for 5xx errors
gcloud logging metrics create http-5xx-errors \
    --project=$PROJECT_ID \
    --description="Count of HTTP 5xx responses from Cloud Run" \
    --log-filter='resource.type="cloud_run_revision" AND httpRequest.status>=500'

# Create a distribution metric for request latency
gcloud logging metrics create request-latency-ms \
    --project=$PROJECT_ID \
    --description="HTTP request latency in milliseconds" \
    --log-filter='resource.type="cloud_run_revision" AND httpRequest.latency!=""' \
    --value-extractor='EXTRACT(httpRequest.latency)' \
    --units=ms
```

---

## Alerting Policies

```bash
# Create an alerting policy for high error rate
# (using the log-based metric created above)
gcloud alpha monitoring policies create \
    --project=$PROJECT_ID \
    --policy='{
        "displayName": "High 5xx Error Rate",
        "conditions": [{
            "displayName": "HTTP 5xx errors",
            "conditionThreshold": {
                "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/http-5xx-errors\"",
                "aggregations": [{"alignmentPeriod": "300s", "perSeriesAligner": "ALIGN_RATE"}],
                "comparison": "COMPARISON_GT",
                "thresholdValue": 0.1,
                "duration": "60s"
            }
        }],
        "alertStrategy": {"autoClose": "604800s"},
        "combiner": "OR",
        "notificationChannels": ["projects/my-app-production/notificationChannels/CHANNEL_ID"]
    }'

# Create a notification channel (email)
gcloud alpha monitoring channels create \
    --project=$PROJECT_ID \
    --display-name="On-Call Engineer" \
    --type=email \
    --channel-labels=email_address=oncall@example.com

# Create an uptime alert (fires when uptime check fails from 2+ regions)
gcloud alpha monitoring policies create \
    --project=$PROJECT_ID \
    --policy='{
        "displayName": "My App API Downtime",
        "conditions": [{
            "displayName": "Uptime check failed",
            "conditionThreshold": {
                "filter": "resource.type=\"uptime_url\" AND metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\"",
                "aggregations": [{"alignmentPeriod": "60s", "perSeriesAligner": "ALIGN_FRACTION_TRUE"}],
                "comparison": "COMPARISON_LT",
                "thresholdValue": 1,
                "duration": "0s"
            }
        }],
        "combiner": "OR",
        "notificationChannels": ["projects/my-app-production/notificationChannels/CHANNEL_ID"]
    }'
```

---

## Cloud Trace

```python
# requirements: opentelemetry-sdk opentelemetry-exporter-gcp-trace opentelemetry-instrumentation-requests
import logging
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import CloudTraceFormatPropagator

logger = logging.getLogger(__name__)

# Configure tracing
_exporter = CloudTraceSpanExporter(project_id=os.environ["GCP_PROJECT_ID"])
_provider = TracerProvider()
_provider.add_span_processor(BatchSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)
set_global_textmap(CloudTraceFormatPropagator())

# Auto-instrument HTTP client calls
RequestsInstrumentor().instrument()

tracer = trace.get_tracer("my-app")


def handle_order(order_id: str) -> dict:
    """Process an order with distributed tracing."""
    logger.info("Handling order: order_id=%s", order_id)

    with tracer.start_as_current_span("handle_order") as span:
        span.set_attribute("order.id", order_id)

        with tracer.start_as_current_span("validate_order"):
            logger.debug("Validating order: order_id=%s", order_id)
            # ... validation ...

        with tracer.start_as_current_span("charge_payment"):
            logger.debug("Charging payment: order_id=%s", order_id)
            # ... payment ...

        result = {"orderId": order_id, "status": "fulfilled"}
        span.set_attribute("order.status", result["status"])
        logger.info("Order handled: order_id=%s status=%s", order_id, result["status"])
        return result
```

---

## Error Reporting

Error Reporting automatically groups and surfaces exceptions from Cloud Run, GKE, App Engine, and Cloud Functions.

```python
from google.cloud import error_reporting
import os

_error_client = error_reporting.Client(project=os.environ["GCP_PROJECT_ID"])


def safe_process(order_id: str) -> None:
    """Example of reporting exceptions to Error Reporting."""
    try:
        # ... risky operation ...
        pass
    except Exception as e:
        # Report to Error Reporting (in addition to logging)
        _error_client.report_exception()
        raise
```

---

## Observability Best Practices Checklist

- [ ] Enable Cloud Logging data access audit logs for sensitive APIs (BigQuery, Secret Manager)
- [ ] Export logs to Cloud Storage or BigQuery for long-term retention and compliance
- [ ] Create log-based metrics for 5xx errors and request latency
- [ ] Set up alerting policies with notification channels (PagerDuty, email, Slack via webhook)
- [ ] Add uptime checks for all public-facing endpoints
- [ ] Instrument all services with OpenTelemetry for distributed tracing
- [ ] Enable Cloud Profiler in production to identify CPU/memory hotspots
- [ ] Use structured (JSON) logging so Cloud Logging can parse and filter on individual fields

---

## References

- [Cloud Monitoring documentation](https://cloud.google.com/monitoring/docs)
- [Cloud Logging documentation](https://cloud.google.com/logging/docs)
- [Cloud Trace documentation](https://cloud.google.com/trace/docs)
- [Error Reporting documentation](https://cloud.google.com/error-reporting/docs)
- [OpenTelemetry on GCP](https://opentelemetry.io/docs/instrumentation/python/)
---

← [Previous: VPC Service Controls](../09-security/vpc-service-controls.md) | [Home](../../README.md) | [Next: Cloud Monitoring →](./cloud-monitoring.md)
