← [Previous: Azure Monitor](./azure-monitor.md) | [Home](../../README.md) | [Next: Azure IaC →](../11-iac/README.md)

---

# Azure Application Insights

Application Insights is the APM (Application Performance Monitoring) component of Azure Monitor. It provides distributed tracing, dependency tracking, live metrics, exceptions, custom events, and user analytics.

---

## Architecture

```
Your Application
  │
  ├── OpenTelemetry SDK (recommended) or classic SDK
  │     ├── Traces (distributed tracing)
  │     ├── Metrics (custom + runtime)
  │     └── Logs (structured)
  │
  ▼
Application Insights (OTLP endpoint / SDK connection string)
  │
  ▼
Log Analytics Workspace (backend storage)
  │
  ├── Application Map (service dependency graph)
  ├── Live Metrics Stream
  ├── Failures blade (exceptions + dependencies)
  ├── Performance blade (response times, call counts)
  └── KQL queries via Logs blade
```

---

## Creating Application Insights

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
LOCATION="eastus"

# Workspace-based Application Insights (recommended)
az monitor app-insights component create \
    --resource-group $RESOURCE_GROUP \
    --app appi-my-app-prod-eastus \
    --location $LOCATION \
    --kind web \
    --application-type web \
    --workspace-resource-id $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus --query id -o tsv) \
    --sampling-percentage 10 \
    --tags Environment=production Service=my-app

# Get connection string (use this, not instrumentation key)
CONN_STRING=$(az monitor app-insights component show \
    --resource-group $RESOURCE_GROUP \
    --app appi-my-app-prod-eastus \
    --query connectionString -o tsv)

echo "APPLICATIONINSIGHTS_CONNECTION_STRING=$CONN_STRING"
# Store in Key Vault or app settings
```

---

## Python — OpenTelemetry (Recommended)

```python
# requirements.txt:
# azure-monitor-opentelemetry
# opentelemetry-instrumentation-requests
# opentelemetry-instrumentation-psycopg2
# opentelemetry-instrumentation-redis

import os
import logging
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

# Configure once at application startup
configure_azure_monitor(
    connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"],
    logger_name="my_app",
    logging_level=logging.INFO,
)

# Auto-instrument common libraries
RequestsInstrumentor().instrument()
Psycopg2Instrumentor().instrument()

logger = logging.getLogger("my_app")
tracer = trace.get_tracer("my_app")
meter = metrics.get_meter("my_app")

# Custom metrics
order_counter = meter.create_counter(
    name="orders.created",
    unit="orders",
    description="Number of orders created",
)
order_value = meter.create_histogram(
    name="orders.value",
    unit="USD",
    description="Order total value distribution",
)


def process_order(order: dict) -> dict:
    """Process an order with full distributed tracing."""
    order_id = order.get("orderId", "unknown")

    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.type", order.get("type", "standard"))
        span.set_attribute("order.total", order.get("total", 0.0))

        logger.info("Processing order", extra={"order_id": order_id})

        try:
            # Validate
            with tracer.start_as_current_span("validate_order"):
                validated = validate(order)
                span.set_attribute("order.valid", validated)

            if not validated:
                span.set_attribute("order.status", "rejected")
                logger.warning("Order rejected", extra={"order_id": order_id})
                return {"status": "rejected"}

            # Charge
            with tracer.start_as_current_span("charge_payment"):
                charge_result = charge(order)

            # Record metrics
            order_counter.add(1, {"order.type": order.get("type", "standard"), "region": "eastus"})
            order_value.record(order.get("total", 0.0), {"order.type": order.get("type", "standard")})

            span.set_attribute("order.status", "fulfilled")
            logger.info("Order fulfilled", extra={"order_id": order_id, "charge_id": charge_result.get("id")})
            return {"status": "fulfilled", "chargeId": charge_result.get("id")}

        except Exception as exc:
            span.record_exception(exc)
            span.set_attribute("order.status", "failed")
            logger.error("Order processing failed", extra={"order_id": order_id, "error": str(exc)})
            raise


def validate(order: dict) -> bool:
    return bool(order.get("items") and order.get("customerId"))


def charge(order: dict) -> dict:
    return {"id": f"charge_{order.get('orderId')}", "status": "succeeded"}
```

---

## Python — Azure Functions Integration

```python
# Azure Functions with OpenTelemetry — auto-captured via configure_azure_monitor
import azure.functions as func
import logging
from opentelemetry import trace

# Call configure_azure_monitor() at module level (once per cold start)
# After that, all HTTP requests, dependencies, and logs are auto-captured

logger = logging.getLogger("my_app")
tracer = trace.get_tracer("my_app.functions")
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="orders/{order_id}")
def get_order(req: func.HttpRequest) -> func.HttpResponse:
    order_id = req.route_params.get("order_id")

    with tracer.start_as_current_span("get_order_handler") as span:
        span.set_attribute("order.id", order_id)
        logger.info("Get order", extra={"order_id": order_id, "invocation_id": req.params.get("invocationId")})

        # Business logic...
        return func.HttpResponse("{}", mimetype="application/json")
```

---

## KQL Queries for Application Insights

```kql
// Top 10 slowest requests in the last hour
requests
| where timestamp > ago(1h)
| where success == true
| project timestamp, name, url, duration, resultCode
| top 10 by duration desc

// Failed request rate by operation
requests
| where timestamp > ago(1h)
| summarize
    Total = count(),
    Failed = countif(success == false),
    AvgDuration = avg(duration)
    by operation_Name
| extend FailureRate = round(100.0 * Failed / Total, 2)
| where Total > 10
| order by FailureRate desc

// Dependency failures (outbound calls to DB, Redis, APIs)
dependencies
| where timestamp > ago(24h)
| where success == false
| summarize FailureCount = count() by target, name, type
| order by FailureCount desc

// Exception distribution
exceptions
| where timestamp > ago(24h)
| summarize Count = count() by type, outerMessage
| order by Count desc

// P95 response time per endpoint
requests
| where timestamp > ago(1h)
| summarize P50=percentile(duration, 50), P95=percentile(duration, 95), P99=percentile(duration, 99)
  by operation_Name
| order by P95 desc

// Custom events
customEvents
| where timestamp > ago(1h)
| where name == "orders.created"
| summarize Count = count(), AvgValue = avg(toreal(customDimensions["order.total"]))
  by bin(timestamp, 5m)
| render timechart
```

---

## Availability Tests

```bash
# Create a URL ping test (checks endpoint every 5 minutes from 5 locations)
az monitor app-insights web-test create \
    --resource-group $RESOURCE_GROUP \
    --app-insights-name appi-my-app-prod-eastus \
    --name "Homepage Availability" \
    --location "[{\"location\":\"us-va-ash-azr\"},{\"location\":\"us-ca-sjc-azr\"},{\"location\":\"us-tx-sn1-azr\"},{\"location\":\"emea-gb-db3-azr\"},{\"location\":\"apac-sg-sin-azr\"}]" \
    --url "https://my-app.example.com/health" \
    --expected-status-code 200 \
    --frequency 300 \
    --timeout 30
```

---

## References

- [Application Insights documentation](https://docs.microsoft.com/azure/azure-monitor/app/app-insights-overview)
- [OpenTelemetry Python distro for Azure](https://docs.microsoft.com/azure/azure-monitor/app/opentelemetry-enable?tabs=python)
- [KQL for Application Insights](https://docs.microsoft.com/azure/azure-monitor/logs/app-insights-azure-monitor-logs)
- [Availability tests](https://docs.microsoft.com/azure/azure-monitor/app/availability-overview)

---

← [Previous: Azure Monitor](./azure-monitor.md) | [Home](../../README.md) | [Next: Azure IaC →](../11-iac/README.md)
