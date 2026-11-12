← [Previous: Azure Security](../09-security/README.md) | [Home](../../README.md) | [Next: Azure Monitor →](./azure-monitor.md)

---

# Azure Observability

---

## Service Overview

| Service | AWS Equivalent | Purpose |
|---------|----------------|---------|
| **Azure Monitor** | CloudWatch | Platform-level metrics, logs, alerts, dashboards |
| **Log Analytics (Workspace)** | CloudWatch Logs Insights | Query and analyze logs with KQL |
| **Application Insights** | X-Ray + CloudWatch | APM — distributed tracing, request tracking, custom telemetry |
| **Azure Monitor Alerts** | CloudWatch Alarms | Metric, log, and activity log alerts with action groups |
| **Azure Dashboards** | CloudWatch Dashboards | Shared, pinnable dashboards |
| **Azure Workbooks** | — | Interactive, parameterized reports and analysis |

---

## Azure Monitor — Metrics

```bash
RESOURCE_GROUP="rg-my-app-production"
LOCATION="eastus"

# List available metrics for a resource
RESOURCE_ID=$(az vm show \
    --resource-group $RESOURCE_GROUP \
    --name vm-my-app-prod-eastus-001 \
    --query id --output tsv)

az monitor metrics list-definitions \
    --resource $RESOURCE_ID \
    --query '[*].{Metric:name.localizedValue,Unit:unit,Aggregations:supportedAggregationTypes}' \
    --output table

# Query a metric (CPU last 1 hour, 5-minute granularity)
az monitor metrics list \
    --resource $RESOURCE_ID \
    --metric "Percentage CPU" \
    --interval PT5M \
    --aggregation Average Maximum \
    --start-time $(date -u -v-1H +"%Y-%m-%dT%H:%MZ" 2>/dev/null || date -u -d '-1 hour' +"%Y-%m-%dT%H:%MZ") \
    --query 'value[0].timeseries[0].data[*].{Time:timeStamp,Avg:average,Max:maximum}' \
    --output table

# Publish a custom metric via REST (requires managed identity with Monitoring Metrics Publisher role)
# Use the Python SDK pattern below for application code
```

### Python — Custom Metrics (OpenTelemetry + Azure Exporter)

```python
# requirements: azure-monitor-opentelemetry-exporter opentelemetry-sdk opentelemetry-api
import logging
import os
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from azure.monitor.opentelemetry.exporter import AzureMonitorMetricExporter

logger = logging.getLogger(__name__)

_exporter = AzureMonitorMetricExporter(
    connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
)
_reader = PeriodicExportingMetricReader(_exporter, export_interval_millis=60_000)
_provider = MeterProvider(metric_readers=[_reader])
metrics.set_meter_provider(_provider)

meter = metrics.get_meter("my-app")

order_counter = meter.create_counter(
    name="orders.created",
    description="Number of orders created",
    unit="1",
)
order_value_histogram = meter.create_histogram(
    name="orders.value",
    description="Order value in USD",
    unit="USD",
)
active_connections_gauge = meter.create_observable_gauge(
    name="db.active_connections",
    description="Active database connections",
    unit="connections",
    callbacks=[lambda options: [metrics.observation.Observation(get_active_connections())]],
)


def create_order(customer_id: str, items: list, total_usd: float) -> dict:
    logger.info("Creating order: customer_id=%s items=%d total=%.2f", customer_id, len(items), total_usd)
    order = {"orderId": "ord-123", "customerId": customer_id, "status": "created"}

    order_counter.add(1, {"customer_type": "retail", "channel": "web"})
    order_value_histogram.record(total_usd, {"currency": "USD"})

    logger.info("Order created: order_id=%s", order["orderId"])
    return order


def get_active_connections() -> int:
    # ... query connection pool ...
    return 42
```

---

## Log Analytics Workspace

```bash
# Create a Log Analytics workspace
WORKSPACE_ID=$(az monitor log-analytics workspace create \
    --resource-group $RESOURCE_GROUP \
    --workspace-name law-my-app-prod-eastus \
    --location $LOCATION \
    --sku PerGB2018 \
    --retention-time 90 \
    --query customerId --output tsv)

# Connect a VM (Azure Monitor Agent replaces MMA/OMS agents)
az vm extension set \
    --resource-group $RESOURCE_GROUP \
    --vm-name vm-my-app-prod-eastus-001 \
    --name AzureMonitorLinuxAgent \
    --publisher Microsoft.Azure.Monitor \
    --settings "{\"workspaceId\": \"$WORKSPACE_ID\"}"

# Link a Function App's logs to the workspace
az monitor diagnostic-settings create \
    --resource $(az functionapp show \
        --resource-group $RESOURCE_GROUP \
        --name func-my-app-prod-eastus \
        --query id --output tsv) \
    --name diag-func-my-app \
    --workspace $(az monitor log-analytics workspace show \
        --resource-group $RESOURCE_GROUP \
        --workspace-name law-my-app-prod-eastus \
        --query id --output tsv) \
    --logs '[{"category":"FunctionAppLogs","enabled":true}]' \
    --metrics '[{"category":"AllMetrics","enabled":true}]'
```

### KQL Queries (Log Analytics)

```kql
// --- Request failure rate over time ---
AppRequests
| where TimeGenerated > ago(1h)
| summarize
    Total = count(),
    Failed = countif(Success == false)
    by bin(TimeGenerated, 5m)
| extend FailureRate = round(100.0 * Failed / Total, 2)
| project TimeGenerated, Total, Failed, FailureRate
| order by TimeGenerated asc

// --- P50 / P95 / P99 response time by operation ---
AppRequests
| where TimeGenerated > ago(1h)
| summarize
    P50 = percentile(DurationMs, 50),
    P95 = percentile(DurationMs, 95),
    P99 = percentile(DurationMs, 99),
    RequestCount = count()
    by OperationName
| order by P99 desc

// --- Top errors with stack traces ---
AppExceptions
| where TimeGenerated > ago(24h)
| summarize
    Count = count(),
    Sample = any(OuterMessage)
    by ExceptionType, OperationName
| order by Count desc
| take 20

// --- Cold start rate for Azure Functions ---
AppTraces
| where TimeGenerated > ago(1h)
| where Message contains "Host initialized"
| summarize ColdStarts = count() by bin(TimeGenerated, 5m)

// --- Failed login attempts from Entra ID ---
SigninLogs
| where TimeGenerated > ago(24h)
| where ResultType != 0
| summarize
    FailedAttempts = count()
    by UserPrincipalName, IPAddress, ResultDescription
| order by FailedAttempts desc

// --- Dependency failures (external calls) ---
AppDependencies
| where TimeGenerated > ago(1h)
| where Success == false
| project TimeGenerated, Name, Target, DurationMs, ResultCode, OperationName
| order by TimeGenerated desc
```

---

## Application Insights

Application Insights provides end-to-end distributed tracing, request tracking, dependency mapping, and custom telemetry.

```bash
# Create Application Insights (workspace-based — recommended)
az monitor app-insights component create \
    --resource-group $RESOURCE_GROUP \
    --app appi-my-app-prod-eastus \
    --location $LOCATION \
    --kind web \
    --workspace $(az monitor log-analytics workspace show \
        --resource-group $RESOURCE_GROUP \
        --workspace-name law-my-app-prod-eastus \
        --query id --output tsv) \
    --tags Environment=production

# Get the connection string (preferred over instrumentation key)
az monitor app-insights component show \
    --resource-group $RESOURCE_GROUP \
    --app appi-my-app-prod-eastus \
    --query connectionString --output tsv

# Query via AI Analytics (uses same KQL)
az monitor app-insights query \
    --app appi-my-app-prod-eastus \
    --analytics-query "requests | summarize count() by success | order by count_ desc"
```

### Python SDK — Application Insights Tracing

```python
# requirements: azure-monitor-opentelemetry
import logging
import os
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

logger = logging.getLogger(__name__)

# Auto-instruments HTTP, DB, logging — call once at startup
configure_azure_monitor(
    connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"],
    logger_name="my-app",          # capture this logger's records as traces
    sampling_ratio=1.0,            # 1.0 = 100%, reduce in high-volume production
)

# Optionally enable automatic instrumentation for specific libraries
RequestsInstrumentor().instrument()
Psycopg2Instrumentor().instrument()

tracer = trace.get_tracer("my-app")


def process_order(order_id: str, customer_id: str) -> dict:
    logger.info("Processing order: order_id=%s customer_id=%s", order_id, customer_id)

    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("customer.id", customer_id)

        try:
            result = _validate_and_fulfill(order_id)
            span.set_attribute("order.status", result["status"])
            logger.info("Order processed: order_id=%s status=%s", order_id, result["status"])
            return result
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            logger.error("Order processing failed: order_id=%s error=%s", order_id, str(e))
            raise


def _validate_and_fulfill(order_id: str) -> dict:
    # Nested span — appears as a child in the distributed trace map
    with tracer.start_as_current_span("fulfill_order"):
        logger.debug("Fulfilling order: order_id=%s", order_id)
        # ... fulfillment logic ...
        return {"status": "fulfilled"}
```

---

## Azure Monitor Alerts

### Action Groups

```bash
# Create an action group (email + webhook)
az monitor action-group create \
    --resource-group $RESOURCE_GROUP \
    --name ag-my-app-ops-prod \
    --short-name myappops \
    --email-receivers name=OnCallEngineer email=oncall@example.com useCommonAlertSchema=true \
    --webhook-receivers name=PagerDuty serviceUri=https://events.pagerduty.com/generic/2010-04-15/create_event.json useCommonAlertSchema=true
```

### Metric Alerts

```bash
# Alert: CPU > 80% for 5 minutes
az monitor metrics alert create \
    --resource-group $RESOURCE_GROUP \
    --name alert-vm-cpu-high \
    --scopes $(az vm show \
        --resource-group $RESOURCE_GROUP \
        --name vm-my-app-prod-eastus-001 \
        --query id --output tsv) \
    --condition "avg Percentage CPU > 80" \
    --window-size 5m \
    --evaluation-frequency 1m \
    --severity 2 \
    --action $(az monitor action-group show \
        --resource-group $RESOURCE_GROUP \
        --name ag-my-app-ops-prod \
        --query id --output tsv) \
    --description "VM CPU utilization exceeded 80%"

# Alert: Function App 5xx errors (count > 10 in 5 minutes)
az monitor metrics alert create \
    --resource-group $RESOURCE_GROUP \
    --name alert-func-5xx \
    --scopes $(az functionapp show \
        --resource-group $RESOURCE_GROUP \
        --name func-my-app-prod-eastus \
        --query id --output tsv) \
    --condition "count Http5xx > 10" \
    --window-size 5m \
    --evaluation-frequency 1m \
    --severity 1 \
    --action $(az monitor action-group show \
        --resource-group $RESOURCE_GROUP \
        --name ag-my-app-ops-prod \
        --query id --output tsv) \
    --description "Function App returned more than 10 HTTP 5xx errors in 5 minutes"

# Alert: PostgreSQL storage usage > 85%
az monitor metrics alert create \
    --resource-group $RESOURCE_GROUP \
    --name alert-pg-storage-high \
    --scopes $(az postgres flexible-server show \
        --resource-group $RESOURCE_GROUP \
        --name pg-my-app-prod-eastus \
        --query id --output tsv) \
    --condition "avg storage_percent > 85" \
    --window-size 15m \
    --evaluation-frequency 5m \
    --severity 2 \
    --action $(az monitor action-group show \
        --resource-group $RESOURCE_GROUP \
        --name ag-my-app-ops-prod \
        --query id --output tsv)
```

### Log (KQL) Alerts

```bash
# Alert: more than 50 exceptions in 15 minutes
az monitor scheduled-query create \
    --resource-group $RESOURCE_GROUP \
    --name alert-app-exceptions \
    --scopes $(az monitor app-insights component show \
        --resource-group $RESOURCE_GROUP \
        --app appi-my-app-prod-eastus \
        --query id --output tsv) \
    --condition-query "exceptions | summarize count() | where count_ > 50" \
    --condition "count > 0" \
    --evaluation-frequency 5m \
    --window-size 15m \
    --severity 2 \
    --action-groups $(az monitor action-group show \
        --resource-group $RESOURCE_GROUP \
        --name ag-my-app-ops-prod \
        --query id --output tsv) \
    --description "More than 50 exceptions logged in 15 minutes"
```

---

## Observability Best Practices Checklist

- [ ] Route all resource diagnostic logs to a central Log Analytics workspace
- [ ] Enable Application Insights for every web app and function app using workspace-based (not classic) resources
- [ ] Use the OpenTelemetry-based SDK (`azure-monitor-opentelemetry`) over the legacy `opencensus` SDK
- [ ] Create action groups with both email and webhook (PagerDuty/Opsgenie) receivers
- [ ] Alert on P99 latency, error rate, and saturation (CPU/memory/storage) for every tier
- [ ] Set up availability (ping) tests in Application Insights for public endpoints
- [ ] Retain logs for 90 days in hot storage; archive to Storage Account for long-term compliance
- [ ] Tag all alerts with Environment and Service to route correctly in multi-team setups

---

## References

- [Azure Monitor documentation](https://docs.microsoft.com/azure/azure-monitor/)
- [Log Analytics KQL reference](https://docs.microsoft.com/azure/data-explorer/kusto/query/)
- [Application Insights](https://docs.microsoft.com/azure/azure-monitor/app/app-insights-overview)
- [Azure Monitor alerts](https://docs.microsoft.com/azure/azure-monitor/alerts/alerts-overview)
---

← [Previous: Azure Security](../09-security/README.md) | [Home](../../README.md) | [Next: Azure Monitor →](./azure-monitor.md)
