← [Previous: Dashboards](./dashboards.md) | [Home](../README.md) | [Next: Prometheus & Grafana →](./prometheus-grafana.md)

---

# OpenTelemetry

OpenTelemetry (OTel) is the CNCF standard for generating, collecting, and exporting telemetry (traces, metrics, logs). It replaces vendor-specific agents and SDKs with a single, portable instrumentation layer.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Application                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐               │
│  │  OTel SDK: TracerProvider + MeterProvider + LoggerProvider   │               │
│  │  Auto-instrumentation: FastAPI, HTTPX, SQLAlchemy, Redis...  │               │
│  └──────────────────────────────┬───────────────────────────────┘               │
└─────────────────────────────────┼───────────────────────────────────────────────┘
                                  │ OTLP (gRPC or HTTP)
                    ┌─────────────▼──────────────┐
                    │  OTel Collector            │
                    │  Receivers → Processors    │
                    │          → Exporters       │
                    └─────┬────────┬─────────┬──┘
                          │        │         │
                     Jaeger/   Prometheus  Datadog /
                     Tempo      Remote     Honeycomb /
                               Write       AWS X-Ray
```

---

## SDK Setup (Python)

### Installation

```bash
pip install \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-exporter-otlp-proto-grpc \
    opentelemetry-instrumentation-fastapi \
    opentelemetry-instrumentation-httpx \
    opentelemetry-instrumentation-sqlalchemy \
    opentelemetry-instrumentation-redis \
    opentelemetry-instrumentation-logging
```

### Complete Initialization

```python
import logging
import os

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

logger = logging.getLogger(__name__)

OTEL_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
SERVICE = os.environ.get("SERVICE_NAME", "unknown")
VERSION = os.environ.get("SERVICE_VERSION", "0.0.0")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
SAMPLE_RATE = float(os.environ.get("OTEL_SAMPLE_RATE", "0.1"))


def init_telemetry() -> None:
    """Initialize all three OTel pillars: traces, metrics, logs."""
    resource = Resource.create({
        SERVICE_NAME: SERVICE,
        SERVICE_VERSION: VERSION,
        "deployment.environment": ENVIRONMENT,
        "telemetry.sdk.language": "python",
    })

    _init_tracing(resource)
    _init_metrics(resource)
    _init_logging(resource)
    _instrument_libraries()

    logger.info(
        "OpenTelemetry initialized",
        extra={"service": SERVICE, "version": VERSION, "endpoint": OTEL_ENDPOINT},
    )


def _init_tracing(resource: Resource) -> None:
    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(root=TraceIdRatioBased(SAMPLE_RATE)),
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True))
    )
    trace.set_tracer_provider(provider)


def _init_metrics(resource: Resource) -> None:
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True),
        export_interval_millis=30_000,
    )
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)


def _init_logging(resource: Resource) -> None:
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=OTEL_ENDPOINT, insecure=True))
    )
    set_logger_provider(provider)
    # Bridge Python logging → OTel logs
    LoggingInstrumentor().instrument(set_logging_format=True)


def _instrument_libraries() -> None:
    FastAPIInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(enable_commenter=True)
    RedisInstrumentor().instrument()
```

---

## Custom Metrics via OTel

```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__, version="1.0.0")

# Counter — monotonically increasing
orders_counter = meter.create_counter(
    "orders.created",
    unit="1",
    description="Number of orders created",
)

# Histogram — distribution of values
order_value = meter.create_histogram(
    "orders.value",
    unit="USD",
    description="Order value in USD",
)

# UpDownCounter — bidirectional
active_sessions = meter.create_up_down_counter(
    "sessions.active",
    unit="1",
    description="Currently active user sessions",
)

# Observable gauge — current value via callback
import psutil

def cpu_callback(options) -> list:
    return [metrics.Observation(psutil.cpu_percent() / 100.0)]

meter.create_observable_gauge(
    "system.cpu.utilization",
    callbacks=[cpu_callback],
    unit="1",
    description="CPU utilization ratio",
)


# Using the metrics
def create_order(order: dict) -> str:
    orders_counter.add(1, {
        "payment_method": order["payment_method"],
        "region": order["region"],
    })
    order_value.record(order["total_usd"], {"region": order["region"]})
    return order["id"]
```

---

## OTel Collector Full Config

```yaml
# otel-collector-config.yaml
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  pprof:
    endpoint: 0.0.0.0:1777

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        max_recv_msg_size_mib: 32
      http:
        endpoint: 0.0.0.0:4318
  # Scrape Prometheus metrics from services
  prometheus:
    config:
      scrape_configs:
        - job_name: "otel-collector"
          static_configs:
            - targets: ["localhost:8888"]

processors:
  batch:
    send_batch_size: 8192
    timeout: 10s
    send_batch_max_size: 16384
  memory_limiter:
    check_interval: 1s
    limit_percentage: 75
    spike_limit_percentage: 20
  resource:
    attributes:
      - key: "collector.version"
        value: "0.90.0"
        action: insert
  # Filter out health check noise
  filter/health:
    traces:
      span:
        - 'attributes["http.target"] == "/health/ready"'
        - 'attributes["http.target"] == "/health/live"'
        - 'attributes["http.target"] == "/metrics"'
  # Sample traces based on error status
  probabilistic_sampler:
    hash_seed: 22
    sampling_percentage: 10

exporters:
  # Grafana Tempo (traces)
  otlp/tempo:
    endpoint: http://tempo:4317
    tls:
      insecure: true
  # Prometheus (metrics)
  prometheus:
    endpoint: 0.0.0.0:8889
    namespace: otelcol
    send_timestamps: true
    metric_expiration: 180m
  # Grafana Loki (logs)
  loki:
    endpoint: http://loki:3100/loki/api/v1/push
    labels:
      resource:
        service.name: "service_name"
        deployment.environment: "environment"

service:
  extensions: [health_check, pprof]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, filter/health, batch, resource]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp, prometheus]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch, resource]
      exporters: [loki]
```

---

## Auto-Instrumentation via Kubernetes Operator

```yaml
# Instrument a deployment without code changes
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: python-instrumentation
  namespace: production
spec:
  exporter:
    endpoint: http://otel-collector:4317
  propagators:
    - tracecontext
    - baggage
  sampler:
    type: parentbased_traceidratio
    argument: "0.1"
  python:
    env:
      - name: OTEL_LOGS_EXPORTER
        value: otlp
      - name: OTEL_PYTHON_LOG_CORRELATION
        value: "true"
---
# Annotate pods to auto-instrument
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-api
  namespace: production
spec:
  template:
    metadata:
      annotations:
        instrumentation.opentelemetry.io/inject-python: "true"
```

---

## References

- [OpenTelemetry Python](https://opentelemetry-python.readthedocs.io/)
- [OTel Collector](https://opentelemetry.io/docs/collector/)
- [OTel Operator for Kubernetes](https://github.com/open-telemetry/opentelemetry-operator)
- [OTLP Specification](https://opentelemetry.io/docs/reference/specification/protocol/otlp/)

---

← [Previous: Dashboards](./dashboards.md) | [Home](../README.md) | [Next: Prometheus & Grafana →](./prometheus-grafana.md)
