← [Previous: Cloud Logging](./cloud-logging.md) | [Home](../../README.md) | [Next: GCP IaC →](../11-iac/README.md)

---

# Cloud Trace

Cloud Trace is GCP's distributed tracing service. It collects latency data from applications and shows how requests propagate through microservices. OpenTelemetry is the recommended instrumentation.

---

## OpenTelemetry Setup

```python
import logging
import os
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

logger = logging.getLogger(__name__)

PROJECT = os.environ["GCP_PROJECT"]
SERVICE = os.environ.get("SERVICE_NAME", "my-app-api")


def setup_tracing() -> trace.Tracer:
    """Initialize OpenTelemetry tracing with Cloud Trace exporter."""
    resource = Resource.create({
        SERVICE_NAME: SERVICE,
        "service.version": os.environ.get("SERVICE_VERSION", "unknown"),
        "gcp.project_id": PROJECT,
    })

    exporter = CloudTraceSpanExporter(project_id=PROJECT)
    processor = BatchSpanProcessor(
        exporter,
        max_queue_size=512,
        max_export_batch_size=128,
        export_timeout_millis=30_000,
    )

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Auto-instrument common libraries
    FlaskInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()

    logger.info("Cloud Trace initialized", extra={"service": SERVICE, "project": PROJECT})
    return trace.get_tracer(SERVICE)


tracer = setup_tracing()
```

---

## Manual Spans

```python
import logging
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def process_order(order_id: str, customer_id: str) -> dict:
    """Process an order with full distributed trace coverage."""
    with tracer.start_as_current_span(
        "process_order",
        attributes={
            "order.id": order_id,
            "customer.id": customer_id,
        },
    ) as span:
        logger.info("Processing order", extra={"order_id": order_id, "customer_id": customer_id})

        try:
            # Validate
            with tracer.start_as_current_span("validate_order") as validate_span:
                validated = _validate_order(order_id)
                validate_span.set_attribute("order.valid", validated)
                logger.debug("Order validated", extra={"order_id": order_id, "valid": validated})

            # Charge payment
            with tracer.start_as_current_span("charge_payment") as payment_span:
                payment_span.set_attribute("payment.provider", "stripe")
                payment_id = _charge_payment(order_id)
                payment_span.set_attribute("payment.id", payment_id)
                logger.info("Payment charged", extra={"order_id": order_id, "payment_id": payment_id})

            # Fulfil
            with tracer.start_as_current_span("fulfil_order") as fulfil_span:
                tracking_number = _fulfil_order(order_id, payment_id)
                fulfil_span.set_attribute("fulfilment.tracking_number", tracking_number)
                logger.info(
                    "Order fulfilled",
                    extra={"order_id": order_id, "tracking_number": tracking_number},
                )

            span.set_status(Status(StatusCode.OK))
            return {"order_id": order_id, "tracking_number": tracking_number}

        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            logger.error(
                "Order processing failed",
                extra={"order_id": order_id, "error": str(exc)},
            )
            raise


def _validate_order(order_id: str) -> bool:
    """Stub — validation logic."""
    return True


def _charge_payment(order_id: str) -> str:
    """Stub — payment logic."""
    return "pay_abc123"


def _fulfil_order(order_id: str, payment_id: str) -> str:
    """Stub — fulfilment logic."""
    return "TRK123456"
```

---

## Trace Propagation (Service-to-Service)

```python
import logging
import os
import requests
from opentelemetry import trace
from opentelemetry.propagate import inject

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

DOWNSTREAM_URL = os.environ["DOWNSTREAM_SERVICE_URL"]


def call_downstream(payload: dict) -> dict:
    """Call a downstream service with trace context propagation."""
    with tracer.start_as_current_span("downstream_call") as span:
        span.set_attribute("http.url", f"{DOWNSTREAM_URL}/api/v1/process")
        span.set_attribute("http.method", "POST")

        # Inject trace context into outgoing headers
        headers = {"Content-Type": "application/json"}
        inject(headers)  # Adds traceparent / X-Cloud-Trace-Context header

        logger.info(
            "Calling downstream service",
            extra={"url": DOWNSTREAM_URL, "trace_id": format(span.get_span_context().trace_id, "032x")},
        )

        response = requests.post(
            f"{DOWNSTREAM_URL}/api/v1/process",
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()

        span.set_attribute("http.status_code", response.status_code)
        logger.info(
            "Downstream call complete",
            extra={"status_code": response.status_code},
        )
        return response.json()
```

---

## Viewing Traces

```bash
PROJECT="my-app-prod-123456"

# List recent traces
gcloud trace list \
    --project=$PROJECT \
    --start-time="2024-06-15T10:00:00Z" \
    --end-time="2024-06-15T11:00:00Z" \
    --filter="latency>1s" \
    --limit=20

# The Cloud Console Trace Explorer provides the full UI:
# https://console.cloud.google.com/traces/list?project=PROJECT_ID
```

---

## Error Reporting Integration

```python
from google.cloud import error_reporting

error_client = error_reporting.Client(project=PROJECT, service=SERVICE)


def report_exception(exc: Exception, request_url: str | None = None) -> None:
    """Report an exception to Cloud Error Reporting."""
    logger.error("Reporting exception to Error Reporting", extra={"error": str(exc)})

    if request_url:
        http_context = error_reporting.HTTPContext(url=request_url, method="POST")
        error_client.report_exception(http_context=http_context)
    else:
        error_client.report_exception()
```

---

## References

- [Cloud Trace documentation](https://cloud.google.com/trace/docs)
- [OpenTelemetry for Python](https://opentelemetry-python.readthedocs.io/)
- [Cloud Trace exporter](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python)
- [Error Reporting](https://cloud.google.com/error-reporting/docs)

---

← [Previous: Cloud Logging](./cloud-logging.md) | [Home](../../README.md) | [Next: GCP IaC →](../11-iac/README.md)
