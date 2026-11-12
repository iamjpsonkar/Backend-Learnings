← [Previous: ACI](../07-containers/aci.md) | [Home](../../README.md) | [Next: Azure Functions →](./functions.md)

---

# Azure Serverless

---

## Service Selection

| Service | AWS Equivalent | Use case |
|---------|----------------|---------|
| **Azure Functions** | Lambda | Event-driven serverless compute |
| **Azure API Management** | API Gateway | API gateway, throttling, auth, developer portal |
| **Azure Service Bus** | SQS + SNS | Enterprise messaging — queues and topics |
| **Azure Event Grid** | EventBridge | Event routing across services |
| **Azure Event Hubs** | Kinesis Data Streams | Big-data event streaming |
| **Azure Logic Apps** | Step Functions | Low-code workflow automation |
| **Azure Container Apps** | ECS Fargate + KEDA | Serverless containers with event-driven scaling |

---

## Azure Functions

### Key Concepts

| Concept | Meaning |
|---------|---------|
| **Function App** | Deployment and management unit — contains one or more functions |
| **Trigger** | What starts the function (HTTP, Timer, Queue, Blob, Event Hub, etc.) |
| **Binding** | Declarative way to connect inputs/outputs (read from Blob, write to Queue) |
| **Hosting plan** | Consumption (serverless), Premium (pre-warmed), Dedicated (App Service) |
| **Durable Functions** | Extension for stateful workflows — orchestrators, activities, entities |

### Creating a Function App

```bash
RESOURCE_GROUP="rg-my-app-production"
LOCATION="eastus"
STORAGE_ACCOUNT="stmyappprodeastus"

# Create Function App (Consumption plan — pay-per-execution)
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --name func-my-app-prod-eastus \
    --storage-account $STORAGE_ACCOUNT \
    --consumption-plan-location $LOCATION \
    --runtime python \
    --runtime-version "3.11" \
    --functions-version 4 \
    --os-type Linux \
    --assign-identity \
    --tags Environment=production

# Configure app settings
az functionapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name func-my-app-prod-eastus \
    --settings \
        APP_ENV=production \
        COSMOS_ENDPOINT=https://cosmos-my-app-prod-eastus.documents.azure.com \
        SERVICEBUS_CONNECTION_STRING="@Microsoft.KeyVault(SecretUri=https://kv-my-app-prod-eastus.vault.azure.net/secrets/servicebus-connection/)"

# Deploy from zip
func azure functionapp publish func-my-app-prod-eastus --python
```

### HTTP Trigger Function

```python
# function_app.py (Azure Functions v2 Python model)
import azure.functions as func
import json
import logging

logger = logging.getLogger(__name__)
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="orders", methods=["POST"])
def create_order(req: func.HttpRequest) -> func.HttpResponse:
    """Create a new order — HTTP POST /api/orders."""
    request_id = req.headers.get("x-request-id", "unknown")
    logger.info("Creating order: request_id=%s", request_id)

    try:
        body = req.get_json()
    except ValueError as e:
        logger.warning("Invalid JSON: request_id=%s error=%s", request_id, str(e))
        return func.HttpResponse("Invalid JSON", status_code=400)

    customer_id = body.get("customerId")
    if not customer_id:
        logger.warning("Missing customerId: request_id=%s", request_id)
        return func.HttpResponse("customerId is required", status_code=400)

    logger.info("Processing order: request_id=%s customer_id=%s", request_id, customer_id)

    # ... business logic ...
    order = {"orderId": "ord-123", "customerId": customer_id, "status": "created"}

    logger.info("Order created: request_id=%s order_id=%s", request_id, order["orderId"])
    return func.HttpResponse(
        json.dumps(order),
        mimetype="application/json",
        status_code=201,
    )
```

### Timer Trigger (Scheduled Function)

```python
@app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=False)
def cleanup_expired_sessions(timer: func.TimerRequest) -> None:
    """Delete expired sessions every 5 minutes."""
    logger.info("Starting session cleanup: is_past_due=%s", timer.past_due)
    # ... cleanup logic ...
    logger.info("Session cleanup complete")
```

### Queue Trigger (Service Bus)

```python
@app.service_bus_queue_trigger(
    arg_name="message",
    queue_name="orders",
    connection="SERVICEBUS_CONNECTION_STRING",
)
def process_order_message(message: func.ServiceBusMessage) -> None:
    """Process order from Service Bus queue."""
    body = message.get_body().decode("utf-8")
    logger.info(
        "Processing Service Bus message: message_id=%s sequence=%s body_preview=%.100s",
        message.message_id,
        message.sequence_number,
        body,
    )
    # ... process ...
    logger.info("Message processed: message_id=%s", message.message_id)
```

### Durable Functions (Orchestration)

```python
import azure.durable_functions as df

orchestration_app = df.Blueprint()


@orchestration_app.orchestration_trigger(context_name="context")
def order_orchestrator(context: df.DurableOrchestrationContext):
    """Orchestrate the order fulfillment workflow."""
    order = context.get_input()
    logger.info("Starting order orchestration: order_id=%s", order["orderId"])

    # Fan-out: run validation and inventory check in parallel
    results = yield context.task_all([
        context.call_activity("ValidateOrder", order),
        context.call_activity("CheckInventory", order["items"]),
    ])

    validation_result, inventory_result = results

    if not validation_result["valid"] or not inventory_result["available"]:
        logger.warning("Order rejected: order_id=%s", order["orderId"])
        return {"status": "rejected", "reason": "validation or inventory failed"}

    # Sequential steps
    payment_result = yield context.call_activity("ProcessPayment", order)
    shipment_result = yield context.call_activity("CreateShipment", {
        "order": order, "payment": payment_result
    })

    logger.info("Order fulfilled: order_id=%s shipment=%s", order["orderId"], shipment_result["trackingId"])
    return {"status": "fulfilled", "tracking": shipment_result["trackingId"]}


@orchestration_app.activity_trigger(input_name="order")
def ValidateOrder(order: dict) -> dict:
    logger.info("Validating order: order_id=%s", order["orderId"])
    # ... validation logic ...
    return {"valid": True}
```

---

## Azure Service Bus

Service Bus provides enterprise-grade message queuing with ordering, dead-lettering, and transactions.

```bash
# Create a Service Bus namespace (Standard — queues + topics)
az servicebus namespace create \
    --resource-group $RESOURCE_GROUP \
    --name sb-my-app-prod-eastus \
    --location $LOCATION \
    --sku Standard \
    --tags Environment=production

# Create a queue
az servicebus queue create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name sb-my-app-prod-eastus \
    --name orders \
    --max-size 1024 \
    --default-message-time-to-live P7D \
    --dead-lettering-on-message-expiration true \
    --max-delivery-count 5

# Create a topic with subscriptions (pub-sub)
az servicebus topic create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name sb-my-app-prod-eastus \
    --name order-events \
    --max-size 1024

az servicebus topic subscription create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name sb-my-app-prod-eastus \
    --topic-name order-events \
    --name fulfillment-service \
    --dead-letter-on-filter-evaluation-exceptions true \
    --max-delivery-count 5

az servicebus topic subscription create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name sb-my-app-prod-eastus \
    --topic-name order-events \
    --name analytics-service

# Get connection string
az servicebus namespace authorization-rule keys list \
    --resource-group $RESOURCE_GROUP \
    --namespace-name sb-my-app-prod-eastus \
    --name RootManageSharedAccessKey \
    --query primaryConnectionString --output tsv
```

---

## Azure Event Grid

Event Grid routes events between Azure services and custom endpoints.

```bash
# Create a custom Event Grid topic
az eventgrid topic create \
    --resource-group $RESOURCE_GROUP \
    --name egt-my-app-prod-eastus \
    --location $LOCATION \
    --input-schema CloudEventSchemaV1_0

# Subscribe to Blob Storage events (route to Azure Function)
az eventgrid event-subscription create \
    --source-resource-id $(az storage account show \
        --resource-group $RESOURCE_GROUP \
        --name stmyappprodeastus --query id --output tsv) \
    --name blob-created-sub \
    --endpoint $(az functionapp function show \
        --resource-group $RESOURCE_GROUP \
        --name func-my-app-prod-eastus \
        --function-name process-blob \
        --query invokeUrlTemplate --output tsv) \
    --endpoint-type azurefunction \
    --included-event-types Microsoft.Storage.BlobCreated \
    --subject-begins-with "/blobServices/default/containers/uploads/"

# Subscribe to custom events
az eventgrid event-subscription create \
    --source-resource-id $(az eventgrid topic show \
        --resource-group $RESOURCE_GROUP \
        --name egt-my-app-prod-eastus --query id --output tsv) \
    --name order-created-sub \
    --endpoint https://my-app.example.com/events/order-created \
    --endpoint-type webhook \
    --included-event-types OrderCreated \
    --deadletter-endpoint $(az storage account show \
        --resource-group $RESOURCE_GROUP \
        --name stmyappprodeastus --query id --output tsv)/blobServices/default/containers/deadletters
```

---

## Azure API Management

```bash
# Create API Management instance (takes 20–40 minutes to provision)
az apim create \
    --resource-group $RESOURCE_GROUP \
    --name apim-my-app-prod-eastus \
    --location $LOCATION \
    --publisher-name "My Company" \
    --publisher-email "api@example.com" \
    --sku-name Developer  # Use Premium for production with VNet integration

# Import an API from OpenAPI spec
az apim api import \
    --resource-group $RESOURCE_GROUP \
    --service-name apim-my-app-prod-eastus \
    --display-name "My App API" \
    --path "api/v1" \
    --specification-url https://my-app.example.com/openapi.json \
    --specification-format OpenAPI

# Create a product (groups APIs and subscriptions)
az apim product create \
    --resource-group $RESOURCE_GROUP \
    --service-name apim-my-app-prod-eastus \
    --product-id "unlimited" \
    --product-name "Unlimited" \
    --state published \
    --subscription-required true

# Apply rate limit policy (100 calls per 60 seconds per subscription)
az apim api policy create \
    --resource-group $RESOURCE_GROUP \
    --service-name apim-my-app-prod-eastus \
    --api-id my-app-api \
    --xml-policy '<policies>
  <inbound>
    <rate-limit calls="100" renewal-period="60" />
    <validate-jwt header-name="Authorization" failed-validation-httpcode="401">
      <openid-config url="https://login.microsoftonline.com/{tenant}/.well-known/openid-configuration" />
    </validate-jwt>
  </inbound>
  <backend><forward-request /></backend>
  <outbound><set-header name="X-Powered-By" exists-action="delete" /></outbound>
</policies>'
```

---

## References

- [Azure Functions documentation](https://docs.microsoft.com/azure/azure-functions/)
- [Durable Functions](https://docs.microsoft.com/azure/azure-functions/durable/)
- [Azure Service Bus](https://docs.microsoft.com/azure/service-bus-messaging/)
- [Azure Event Grid](https://docs.microsoft.com/azure/event-grid/)
- [Azure API Management](https://docs.microsoft.com/azure/api-management/)
---

← [Previous: ACI](../07-containers/aci.md) | [Home](../../README.md) | [Next: Azure Functions →](./functions.md)
