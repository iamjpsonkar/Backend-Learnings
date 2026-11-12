← [Previous: Azure Serverless](./README.md) | [Home](../../README.md) | [Next: Service Bus →](./service-bus.md)

---

# Azure Functions

Azure Functions is a serverless compute service for event-driven code. It supports multiple triggers (HTTP, timer, queue, Blob, Service Bus, Event Grid) and integrates with Azure services via bindings.

---

## Hosting Plans

| Plan | Scale | Cold Start | Max Timeout | Best For |
|------|-------|-----------|-------------|----------|
| **Consumption** | Auto (0→N) | Yes | 10 min | Infrequent, cost-sensitive |
| **Flex Consumption** | Auto + pre-warmed | Reduced | 60 min | Variable with low latency needs |
| **Premium** | Pre-warmed instances | No | Unlimited | Production, VNet, long-running |
| **Dedicated (App Service)** | Manual or auto | No | Unlimited | Predictable load, existing ASP |
| **Container Apps** | Auto (K8s-based) | No | Unlimited | Microservices + functions together |

---

## Python v2 Programming Model

Azure Functions Python v2 uses decorators instead of `function.json` files.

```python
# function_app.py
import azure.functions as func
import logging
import json
import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


# HTTP trigger
@app.route(route="orders/{order_id}", methods=["GET"])
def get_order(req: func.HttpRequest) -> func.HttpResponse:
    order_id = req.route_params.get("order_id")
    logger.info("Get order request", extra={"order_id": order_id})

    if not order_id:
        return func.HttpResponse("order_id required", status_code=400)

    # Fetch from database...
    order = {"id": order_id, "status": "pending", "total": 99.99}

    logger.info("Order retrieved", extra={"order_id": order_id, "status": order["status"]})
    return func.HttpResponse(
        json.dumps(order),
        status_code=200,
        mimetype="application/json",
    )


# Timer trigger — runs every 5 minutes
@app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=False)
def cleanup_job(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logger.warning("Timer is past due — missed execution")
    logger.info("Cleanup job started")
    # Perform cleanup...
    logger.info("Cleanup job completed")


# Blob trigger — process files uploaded to storage
@app.blob_trigger(
    arg_name="blob",
    path="uploads/{name}",
    connection="AzureWebJobsStorage",
)
def process_upload(blob: func.InputStream) -> None:
    logger.info(
        "Blob trigger fired",
        extra={"name": blob.name, "size": blob.length},
    )
    content = blob.read()
    logger.info("Blob content read", extra={"bytes": len(content)})
    # Process the file...


# Service Bus trigger
@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="order-processing",
    connection="ServiceBusConnection",
)
def process_order_message(msg: func.ServiceBusMessage) -> None:
    body = msg.get_body().decode("utf-8")
    logger.info("Service Bus message received", extra={"message_id": msg.message_id})

    try:
        payload = json.loads(body)
        order_id = payload.get("orderId")
        logger.info("Processing order", extra={"order_id": order_id})
        # Process order...
        logger.info("Order processed", extra={"order_id": order_id})
    except json.JSONDecodeError as exc:
        logger.error("Invalid message format", extra={"error": str(exc), "body": body[:200]})
        raise  # Re-raise so Service Bus moves message to dead-letter after max retries
```

---

## Durable Functions

Durable Functions provides stateful orchestrations (long-running workflows with fan-out, waiting for events).

```python
import azure.durable_functions as df
import azure.functions as func
import logging

logger = logging.getLogger(__name__)
app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# Orchestrator — coordinates activities
@app.orchestration_trigger(context_name="context")
def order_orchestrator(context: df.DurableOrchestrationContext):
    order = context.get_input()
    order_id = order.get("orderId")

    logger.info(f"Orchestration started for order {order_id}")

    # Fan-out: run activities in parallel
    validate_task = context.call_activity("validate_order", order)
    check_inventory_task = context.call_activity("check_inventory", order)
    results = yield context.task_all([validate_task, check_inventory_task])

    if not all(results):
        logger.warning(f"Order {order_id} failed validation or inventory check")
        yield context.call_activity("cancel_order", order_id)
        return {"status": "cancelled", "orderId": order_id}

    yield context.call_activity("charge_payment", order)
    yield context.call_activity("fulfill_order", order)

    logger.info(f"Order {order_id} fulfilled")
    return {"status": "fulfilled", "orderId": order_id}


# Activity functions
@app.activity_trigger(input_name="order")
def validate_order(order: dict) -> bool:
    logger.info("Validating order", extra={"order_id": order.get("orderId")})
    return bool(order.get("items") and order.get("customerId"))


@app.activity_trigger(input_name="order")
def check_inventory(order: dict) -> bool:
    logger.info("Checking inventory", extra={"order_id": order.get("orderId")})
    # Check inventory...
    return True


# HTTP starter — kicks off an orchestration
@app.route(route="orders/start")
@app.durable_client_input(client_name="client")
async def start_order(req: func.HttpRequest, client: df.DurableOrchestrationClient) -> func.HttpResponse:
    order = req.get_json()
    instance_id = await client.start_new("order_orchestrator", client_input=order)
    logger.info("Orchestration started", extra={"instance_id": instance_id})
    return client.create_check_status_response(req, instance_id)
```

---

## Deployment

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
APP_NAME="func-my-app-prod-eastus"
STORAGE_ACCOUNT="stfuncprodeastus"
PLAN_NAME="plan-func-my-app-prod-eastus"

# Create Premium plan (VNet + no cold start)
az functionapp plan create \
    --resource-group $RESOURCE_GROUP \
    --name $PLAN_NAME \
    --location eastus \
    --sku EP1 \
    --is-linux true

# Create function app
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --plan $PLAN_NAME \
    --runtime python \
    --runtime-version 3.11 \
    --functions-version 4 \
    --storage-account $STORAGE_ACCOUNT \
    --assign-identity [system] \
    --tags Environment=production Service=my-app

# Enable VNet integration
az functionapp vnet-integration add \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --vnet vnet-my-app-prod-eastus-001 \
    --subnet snet-app

# Deploy using Core Tools
func azure functionapp publish $APP_NAME --python

# Deploy using Azure CLI zip deploy
zip -r function-app.zip . --exclude "*.pyc" --exclude "__pycache__/*"
az functionapp deployment source config-zip \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --src function-app.zip
```

---

## App Settings (Environment Variables)

```bash
# Set app settings
az functionapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings \
        ENV=production \
        "ServiceBusConnection=@Microsoft.KeyVault(SecretUri=https://kv-my-app-prod-eastus.vault.azure.net/secrets/servicebus-connection-string/)" \
        "COSMOS_ACCOUNT_URL=https://cosmos-my-app-prod-eastus.documents.azure.com:443/"

# Reference Key Vault secrets directly in settings (requires managed identity with Key Vault access)
az functionapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings "DB_PASSWORD=@Microsoft.KeyVault(VaultName=kv-my-app-prod-eastus;SecretName=db-password)"
```

---

## References

- [Azure Functions documentation](https://docs.microsoft.com/azure/azure-functions/)
- [Python v2 programming model](https://docs.microsoft.com/azure/azure-functions/functions-reference-python?pivots=python-mode-decorators)
- [Durable Functions](https://docs.microsoft.com/azure/azure-functions/durable/durable-functions-overview)
- [Hosting plans](https://docs.microsoft.com/azure/azure-functions/functions-scale)

---

← [Previous: Azure Serverless](./README.md) | [Home](../../README.md) | [Next: Service Bus →](./service-bus.md)
