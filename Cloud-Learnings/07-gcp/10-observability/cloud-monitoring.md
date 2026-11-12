← [Previous: GCP Observability](./README.md) | [Home](../../README.md) | [Next: Cloud Logging →](./cloud-logging.md)

---

# Cloud Monitoring

Cloud Monitoring (formerly Stackdriver) collects metrics, creates dashboards, sets alerting policies, and runs uptime checks for GCP and hybrid cloud resources.

---

## Uptime Checks

```bash
PROJECT="my-app-prod-123456"

# Create an HTTPS uptime check
gcloud monitoring uptime create my-app-api \
    --project=$PROJECT \
    --display-name="My App API Uptime" \
    --http-check-path=/health/ready \
    --monitored-resource-type=uptime_url \
    --hostname=api.my-app.com \
    --port=443 \
    --use-ssl \
    --period=60 \
    --timeout=10 \
    --content-match-type=CONTAINS_STRING \
    --content-match='{"status":"ready"}'

# List uptime checks
gcloud monitoring uptime list --project=$PROJECT
```

---

## Alerting Policies

```bash
# Create an alerting notification channel (email)
gcloud monitoring channels create \
    --project=$PROJECT \
    --display-name="Ops Email" \
    --type=email \
    --channel-labels=email_address=ops@my-app.com

CHANNEL_ID=$(gcloud monitoring channels list \
    --project=$PROJECT \
    --filter="displayName='Ops Email'" \
    --format="value(name)")

# Create an alert: Cloud Run request latency p99 > 2s
cat > alert-latency.json <<EOF
{
  "displayName": "Cloud Run P99 Latency > 2s",
  "conditions": [{
    "displayName": "P99 latency exceeded",
    "conditionThreshold": {
      "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\" AND resource.labels.service_name=\"my-app-api\"",
      "aggregations": [{
        "alignmentPeriod": "60s",
        "perSeriesAligner": "ALIGN_PERCENTILE_99",
        "crossSeriesReducer": "REDUCE_MEAN",
        "groupByFields": ["resource.labels.service_name"]
      }],
      "comparison": "COMPARISON_GT",
      "thresholdValue": 2000,
      "duration": "120s"
    }
  }],
  "alertStrategy": {
    "autoClose": "86400s"
  },
  "combiner": "OR",
  "notificationChannels": ["$CHANNEL_ID"],
  "severity": "WARNING"
}
EOF

gcloud alpha monitoring policies create \
    --project=$PROJECT \
    --policy-from-file=alert-latency.json
```

---

## Custom Metrics with OpenTelemetry

```python
import logging
import os
import time
from functools import wraps
from typing import Callable, Any
from opentelemetry import metrics
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

logger = logging.getLogger(__name__)

PROJECT = os.environ["GCP_PROJECT"]
SERVICE = os.environ.get("SERVICE_NAME", "my-app-api")


def setup_metrics() -> metrics.Meter:
    """Initialize OpenTelemetry metrics with Cloud Monitoring exporter."""
    resource = Resource.create({SERVICE_NAME: SERVICE})

    exporter = CloudMonitoringMetricsExporter(project_id=PROJECT)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=60_000)

    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    logger.info("Cloud Monitoring metrics initialized", extra={"service": SERVICE, "project": PROJECT})
    return metrics.get_meter(SERVICE)


meter = setup_metrics()

# Define instruments
request_counter = meter.create_counter(
    "app.requests.total",
    description="Total HTTP requests processed",
    unit="1",
)

request_duration = meter.create_histogram(
    "app.request.duration",
    description="HTTP request duration",
    unit="ms",
)

active_connections = meter.create_up_down_counter(
    "app.connections.active",
    description="Currently active connections",
    unit="1",
)

error_counter = meter.create_counter(
    "app.errors.total",
    description="Total errors",
    unit="1",
)


def track_request(endpoint: str):
    """Decorator to record request metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start = time.time()
            labels = {"endpoint": endpoint, "service": SERVICE}
            active_connections.add(1, labels)
            logger.debug("Request started", extra={"endpoint": endpoint})

            try:
                result = func(*args, **kwargs)
                status = "success"
                return result
            except Exception as exc:
                status = "error"
                error_counter.add(1, {**labels, "error_type": type(exc).__name__})
                logger.error(
                    "Request failed",
                    extra={"endpoint": endpoint, "error": str(exc)},
                )
                raise
            finally:
                duration_ms = (time.time() - start) * 1000
                request_counter.add(1, {**labels, "status": status})
                request_duration.record(duration_ms, {**labels, "status": status})
                active_connections.add(-1, labels)
                logger.debug(
                    "Request finished",
                    extra={"endpoint": endpoint, "duration_ms": duration_ms, "status": status},
                )

        return wrapper
    return decorator


@track_request("/api/v1/orders")
def list_orders(customer_id: str) -> list:
    """Example function instrumented with metrics."""
    logger.info("Listing orders", extra={"customer_id": customer_id})
    # ... business logic
    return []
```

---

## Dashboards (Terraform)

```hcl
resource "google_monitoring_dashboard" "api_dashboard" {
  project        = var.project_id
  dashboard_json = jsonencode({
    displayName = "My App API Dashboard"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "Request Rate (req/s)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields    = ["resource.labels.service_name"]
                    }
                  }
                }
              }]
            }
          }
        },
        {
          xPos   = 6
          width  = 6
          height = 4
          widget = {
            title = "P99 Latency (ms)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_PERCENTILE_99"
                    }
                  }
                }
              }]
            }
          }
        }
      ]
    }
  })
}
```

---

## References

- [Cloud Monitoring documentation](https://cloud.google.com/monitoring/docs)
- [OpenTelemetry for GCP](https://cloud.google.com/opentelemetry/docs)
- [Alerting policies](https://cloud.google.com/monitoring/alerts/using-alerting-ui)
- [MQL (Monitoring Query Language)](https://cloud.google.com/monitoring/mql)

---

← [Previous: GCP Observability](./README.md) | [Home](../../README.md) | [Next: Cloud Logging →](./cloud-logging.md)
