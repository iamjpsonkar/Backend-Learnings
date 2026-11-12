← [Previous: Logging](./logging.md) | [Home](../README.md) | [Next: Alerting →](./alerting.md)

---

# Distributed Tracing

Distributed tracing tracks a request as it flows through multiple services. A trace is a collection of spans — each span represents one unit of work (an HTTP call, a DB query, a queue publish).

---

## Concepts

```
Trace ID: abc-123
│
├─ Span: api-gateway  (0ms → 250ms)
│   └─ Span: order-service  (5ms → 240ms)
│       ├─ Span: db-query "SELECT orders"  (10ms → 45ms)
│       ├─ Span: inventory-service  (50ms → 180ms)
│       │   └─ Span: db-query "UPDATE stock"  (60ms → 170ms)
│       └─ Span: notification-service  (185ms → 235ms)
│           └─ Span: ses:SendEmail  (190ms → 230ms)
```

| Term | Meaning |
|------|---------|
| **Trace** | End-to-end journey of one request |
| **Span** | Single unit of work within a trace |
| **Parent span** | Span that called another service |
| **Child span** | Span created by the called service |
| **Trace context** | `traceparent` header propagated across service calls |
| **Sampling** | Only record a fraction of traces (e.g., 10%) to control cost |

---

## OpenTelemetry Tracing (Python)

```python
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def configure_tracing() -> None:
    """Initialize OpenTelemetry tracing with OTLP export."""
    service_name = os.environ.get("SERVICE_NAME", "unknown-service")
    service_version = os.environ.get("SERVICE_VERSION", "0.0.0")
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    sample_rate = float(os.environ.get("OTEL_TRACE_SAMPLE_RATE", "0.1"))  # 10% default

    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.environ.get("ENVIRONMENT", "development"),
    })

    provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(sample_rate),
    )

    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    logger.info(
        "Tracing configured",
        extra={
            "service": service_name,
            "sample_rate": sample_rate,
            "otlp_endpoint": otlp_endpoint,
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    configure_tracing()
    FastAPIInstrumentor.instrument_app(app)          # Auto-instrument all routes
    HTTPXClientInstrumentor().instrument()            # Auto-instrument outbound HTTP
    SQLAlchemyInstrumentor().instrument(enable_commenter=True)  # Auto-instrument DB
    logger.info("Auto-instrumentation enabled")
    yield


app = FastAPI(lifespan=lifespan)
tracer = trace.get_tracer(__name__)


# Manual span for custom operations
async def process_order(order_id: str) -> dict:
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order_id)
        logger.info("Processing order", extra={"order_id": order_id,
                    "trace_id": format(span.get_span_context().trace_id, "032x")})

        # Nested span for DB operation
        with tracer.start_as_current_span("db.fetch_order") as db_span:
            db_span.set_attribute("db.system", "postgresql")
            db_span.set_attribute("db.statement", "SELECT * FROM orders WHERE id = ?")
            order = await fetch_order_from_db(order_id)
            db_span.set_attribute("db.rows_returned", 1)

        if not order:
            span.set_status(trace.StatusCode.ERROR, "Order not found")
            span.record_exception(ValueError(f"Order {order_id} not found"))
            raise ValueError(f"Order {order_id} not found")

        span.set_attribute("order.total_cents", order["total_cents"])
        span.set_attribute("order.status", order["status"])
        span.set_status(trace.StatusCode.OK)
        return order
```

---

## OTel Collector Configuration

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    send_batch_size: 1024
    timeout: 5s
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
  resource:
    attributes:
      - key: environment
        value: production
        action: upsert

exporters:
  # Export to Jaeger
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true

  # Export to Tempo (Grafana)
  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true

  # Export to AWS X-Ray
  awsxray:
    region: us-east-1

  # Export traces to OTLP-compatible backend (e.g., Honeycomb, Datadog)
  otlphttp/datadog:
    endpoint: https://trace.agent.datadoghq.com
    headers:
      DD-API-KEY: ${env:DD_API_KEY}

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch, resource]
      exporters: [jaeger, otlp/tempo]
```

---

## AWS X-Ray

```python
# AWS X-Ray with Flask/FastAPI
# Install: pip install aws-xray-sdk

from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.fastapi.middleware import XRayMiddleware
import logging

logger = logging.getLogger(__name__)

# Patch boto3, requests, httpx, sqlalchemy automatically
patch_all()

xray_recorder.configure(
    service="order-api",
    sampling=True,
    context_missing="LOG_ERROR",  # Don't crash if no segment
)

app.add_middleware(XRayMiddleware, recorder=xray_recorder)

# Manual subsegment
@xray_recorder.capture("process_payment")
def process_payment(payment_id: str, amount: int) -> dict:
    logger.info("Processing payment", extra={"payment_id": payment_id})
    xray_recorder.current_subsegment().put_annotation("payment_id", payment_id)
    xray_recorder.current_subsegment().put_metadata("amount_cents", amount)
    # ... payment logic
```

```bash
# View X-Ray traces
aws xray get-trace-summaries \
    --start-time $(($(date +%s) - 3600)) \
    --end-time $(date +%s) \
    --filter-expression "responsetime > 1 AND http.status = 500" \
    --query 'TraceSummaries[*].{Id:Id,Duration:Duration,Status:Http.HttpStatus}'
```

---

## Jaeger (Local Development)

```bash
# Run Jaeger all-in-one (development)
docker run -d \
    --name jaeger \
    -p 16686:16686 \   # UI
    -p 14250:14250 \   # gRPC receiver
    -p 4317:4317 \     # OTLP gRPC
    -p 4318:4318 \     # OTLP HTTP
    jaegertracing/all-in-one:1.51

# View UI
open http://localhost:16686
```

---

## Trace Sampling Strategies

```python
# OpenTelemetry sampling options

from opentelemetry.sdk.trace.sampling import (
    ALWAYS_ON,            # 100% — development only
    ALWAYS_OFF,           # 0% — disable tracing
    TraceIdRatioBased,    # Random N% of traces
    ParentBased,          # Respect parent's sampling decision (recommended for production)
)

# Production: 10% base rate, but respect upstream decisions
sampler = ParentBased(root=TraceIdRatioBased(0.10))

# Head-based sampling (decided at trace start)
# Tail-based sampling (decided after trace completes — requires collector)
# Tail-based: sample 100% of error traces, 5% of successful traces
```

```yaml
# OpenTelemetry Collector: tail-based sampling
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 50000
    expected_new_traces_per_sec: 100
    policies:
      # Always sample errors
      - name: errors-policy
        type: status_code
        status_code:
          status_codes: [ERROR]
      # Always sample slow traces (> 1s)
      - name: slow-traces-policy
        type: latency
        latency:
          threshold_ms: 1000
      # Sample 5% of everything else
      - name: probabilistic-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 5
```

---

## References

- [OpenTelemetry Python](https://opentelemetry-python.readthedocs.io/)
- [Jaeger](https://www.jaegertracing.io/docs/)
- [Grafana Tempo](https://grafana.com/docs/tempo/latest/)
- [AWS X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)

---

← [Previous: Logging](./logging.md) | [Home](../README.md) | [Next: Alerting →](./alerting.md)
