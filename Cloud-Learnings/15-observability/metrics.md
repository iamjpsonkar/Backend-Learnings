← [Previous: Observability Overview](./README.md) | [Home](../README.md) | [Next: Logging →](./logging.md)

---

# Metrics

Metrics are numeric measurements collected over time. They are cheap to store, easy to alert on, and essential for understanding system behavior at scale.

---

## Metric Types

| Type | Description | Example |
|------|-------------|---------|
| **Counter** | Monotonically increasing value; reset on restart | `http_requests_total` |
| **Gauge** | Value that goes up and down | `memory_usage_bytes`, `active_connections` |
| **Histogram** | Distribution of values in configurable buckets | Request latency in p50/p95/p99 |
| **Summary** | Pre-calculated quantiles (less flexible than histogram) | Legacy — prefer histogram |

---

## Prometheus Data Model

Every metric is identified by a name + a set of key-value labels:

```
http_requests_total{method="POST", status="200", handler="/api/orders"} 1234
http_requests_total{method="GET",  status="404", handler="/api/users"}    42
```

Labels enable slicing: sum by status code, average by endpoint, compare regions.

**Label cardinality warning**: never use high-cardinality values as labels (user IDs, request IDs, UUIDs) — they create millions of time series and crash Prometheus.

---

## Instrumenting Applications

### Python (prometheus-client)

```python
import logging
import time
from functools import wraps
from typing import Callable

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

# ─── Define metrics at module level ──────────────────────────────────────────
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ACTIVE_REQUESTS = Gauge(
    "http_requests_in_flight",
    "Currently processing HTTP requests",
    ["method", "endpoint"],
)

DB_QUERY_LATENCY = Histogram(
    "db_query_duration_seconds",
    "Database query latency",
    ["query_type", "table"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

ERROR_COUNT = Counter(
    "application_errors_total",
    "Application error count",
    ["error_type", "component"],
)


def track_request(method: str, endpoint: str) -> Callable:
    """Decorator to track HTTP request metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).inc()
            start = time.perf_counter()
            status_code = "200"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as exc:
                status_code = "500"
                ERROR_COUNT.labels(
                    error_type=type(exc).__name__,
                    component="request_handler",
                ).inc()
                logger.error(
                    "Request failed",
                    extra={"method": method, "endpoint": endpoint, "error": str(exc)},
                    exc_info=True,
                )
                raise
            finally:
                duration = time.perf_counter() - start
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                ).inc()
                REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
                ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).dec()
                logger.debug(
                    "Request completed",
                    extra={"method": method, "endpoint": endpoint,
                           "status": status_code, "duration_s": round(duration, 4)},
                )
        return wrapper
    return decorator


# Expose /metrics endpoint (for scraping)
if __name__ == "__main__":
    start_http_server(9090)
    logger.info("Prometheus metrics server started on :9090")
```

### FastAPI + prometheus-fastapi-instrumentator

```python
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

# Auto-instrument all routes
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    env_var_name="ENABLE_METRICS",
    latency_lowr_buckets=[0.001, 0.01, 0.1],
    latency_higher_buckets=[0.5, 1, 5],
)
instrumentator.instrument(app).expose(app, endpoint="/metrics")
logger.info("Prometheus instrumentation initialized")
```

---

## PromQL — Key Queries

```promql
# ─── Request rate ─────────────────────────────────────────────────────────
# Requests per second (5-min window)
rate(http_requests_total[5m])

# By endpoint
sum by (endpoint) (rate(http_requests_total[5m]))

# ─── Error rate ────────────────────────────────────────────────────────────
# 5xx error rate as a fraction of all requests
sum(rate(http_requests_total{status_code=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))

# ─── Latency ───────────────────────────────────────────────────────────────
# p99 latency (histogram_quantile requires histogram type)
histogram_quantile(0.99, sum by (le, endpoint) (
    rate(http_request_duration_seconds_bucket[5m])
))

# p50 / p95 / p99
histogram_quantile(0.50, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

# ─── Resource utilization ──────────────────────────────────────────────────
# CPU usage per pod
sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="production"}[5m]))

# Memory usage per pod
sum by (pod) (container_memory_working_set_bytes{namespace="production"})

# ─── Business metrics ──────────────────────────────────────────────────────
# Orders per minute
rate(orders_created_total[1m]) * 60

# Payment failure rate
sum(rate(payment_attempts_total{result="failed"}[5m]))
/ sum(rate(payment_attempts_total[5m]))
```

---

## CloudWatch Custom Metrics (AWS)

```python
import boto3
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

cw = boto3.client("cloudwatch", region_name=os.environ.get("AWS_REGION", "us-east-1"))
NAMESPACE = os.environ.get("METRICS_NAMESPACE", "MyApp/Production")


def put_metric(
    metric_name: str,
    value: float,
    unit: str = "None",
    dimensions: dict | None = None,
) -> None:
    """Publish a single CloudWatch custom metric."""
    dims = [{"Name": k, "Value": v} for k, v in (dimensions or {}).items()]
    logger.debug(
        "Publishing CloudWatch metric",
        extra={"metric": metric_name, "value": value, "dimensions": dimensions},
    )
    cw.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[{
            "MetricName": metric_name,
            "Timestamp": datetime.now(timezone.utc),
            "Value": value,
            "Unit": unit,
            "Dimensions": dims,
        }],
    )


# Usage
put_metric("OrdersProcessed", 1, unit="Count", dimensions={"Service": "order-api", "Region": "us-east-1"})
put_metric("OrderValueUSD", 49.99, unit="None", dimensions={"Service": "order-api"})
put_metric("CheckoutLatencyMs", 234.5, unit="Milliseconds", dimensions={"Service": "checkout"})
```

---

## Recording Rules (Prometheus)

Pre-compute expensive queries to speed up dashboards and reduce query load:

```yaml
# rules/recording-rules.yml
groups:
  - name: http_request_rates
    interval: 30s
    rules:
      # Pre-compute per-endpoint error rate
      - record: job:http_requests_errors:rate5m
        expr: |
          sum by (job, endpoint) (
            rate(http_requests_total{status_code=~"5.."}[5m])
          )
          /
          sum by (job, endpoint) (
            rate(http_requests_total[5m])
          )

      # Pre-compute p99 latency
      - record: job:http_request_duration_p99:rate5m
        expr: |
          histogram_quantile(0.99,
            sum by (job, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )

  - name: resource_utilization
    interval: 60s
    rules:
      - record: namespace:container_cpu_usage:rate5m
        expr: |
          sum by (namespace) (
            rate(container_cpu_usage_seconds_total[5m])
          )
```

---

## References

- [Prometheus data model](https://prometheus.io/docs/concepts/data_model/)
- [PromQL basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Histograms and summaries](https://prometheus.io/docs/practices/histograms/)
- [prometheus-client Python](https://github.com/prometheus/client_python)

---

← [Previous: Observability Overview](./README.md) | [Home](../README.md) | [Next: Logging →](./logging.md)
