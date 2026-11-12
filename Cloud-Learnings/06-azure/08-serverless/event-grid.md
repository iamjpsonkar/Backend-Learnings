← [Previous: Service Bus](./service-bus.md) | [Home](../../README.md) | [Next: API Management →](./apim.md)

---

# Azure Event Grid

Event Grid is a fully managed event routing service. It connects event sources (Azure services, custom apps) to event handlers (webhooks, Functions, Service Bus, Event Hubs) using a publish/subscribe model.

---

## Concepts

| Concept | Description |
|---------|-------------|
| **Event Source** | Where events originate (Storage, Resource Groups, custom topics) |
| **Topic** | Endpoint that receives events — system topic (Azure services) or custom topic |
| **Event Subscription** | Rules for filtering and routing events to a handler |
| **Event Handler** | Destination — Azure Function, Logic App, Service Bus, Webhook, Event Hubs |
| **Dead Letter** | Undeliverable events stored in a Blob container |

---

## Event Schema

```json
[{
  "id": "f12b7e83-5e4d-4a3b-8f6d-1b0c3d5e7f9a",
  "topic": "/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/stmyapp",
  "subject": "/blobServices/default/containers/uploads/blobs/invoice.pdf",
  "eventType": "Microsoft.Storage.BlobCreated",
  "eventTime": "2024-06-15T10:00:00.000Z",
  "data": {
    "api": "PutBlob",
    "contentType": "application/pdf",
    "contentLength": 204800,
    "blobType": "BlockBlob",
    "url": "https://stmyapp.blob.core.windows.net/uploads/invoice.pdf"
  },
  "dataVersion": "",
  "metadataVersion": "1"
}]
```

---

## System Topics (Built-in Azure Services)

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"

# Create a system topic for a storage account
az eventgrid system-topic create \
    --resource-group $RESOURCE_GROUP \
    --name st-events-my-app \
    --location eastus \
    --topic-type Microsoft.Storage.StorageAccounts \
    --source $(az storage account show \
        --resource-group $RESOURCE_GROUP \
        --name stmyappprodeastus --query id -o tsv)

# Subscribe — route blob events to a Function
az eventgrid system-topic event-subscription create \
    --resource-group $RESOURCE_GROUP \
    --system-topic-name st-events-my-app \
    --name process-blob-upload \
    --endpoint $(az functionapp function show \
        --resource-group $RESOURCE_GROUP \
        --name func-my-app-prod-eastus \
        --function-name process_upload \
        --query invokeUrlTemplate -o tsv) \
    --endpoint-type azurefunction \
    --included-event-types Microsoft.Storage.BlobCreated \
    --subject-begins-with /blobServices/default/containers/uploads/ \
    --event-delivery-schema eventgridschema \
    --max-delivery-attempts 30 \
    --event-ttl 1440 \
    --deadletter-endpoint $(az storage account show \
        --resource-group $RESOURCE_GROUP \
        --name stmyappprodeastus --query id -o tsv)/blobServices/default/containers/dead-letter

# Subscribe — route all resource group events to Service Bus
az eventgrid event-subscription create \
    --name rg-audit-events \
    --source-resource-id /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \
    --endpoint $(az servicebus topic show \
        --resource-group $RESOURCE_GROUP \
        --namespace-name sb-my-app-prod-eastus \
        --name order-events --query id -o tsv) \
    --endpoint-type servicebustopic
```

---

## Custom Topics

```bash
# Create a custom topic (for application-generated events)
az eventgrid topic create \
    --resource-group $RESOURCE_GROUP \
    --name topic-order-events \
    --location eastus \
    --input-schema cloudeventschemav1_0 \  # Use CloudEvents v1.0 (preferred)
    --public-network-access disabled \
    --tags Environment=production

# Get topic endpoint and key
TOPIC_ENDPOINT=$(az eventgrid topic show \
    --resource-group $RESOURCE_GROUP \
    --name topic-order-events \
    --query endpoint -o tsv)

TOPIC_KEY=$(az eventgrid topic key list \
    --resource-group $RESOURCE_GROUP \
    --name topic-order-events \
    --query key1 -o tsv)

# Subscribe to the custom topic with a webhook
az eventgrid event-subscription create \
    --name order-webhook-sub \
    --source-resource-id $(az eventgrid topic show \
        --resource-group $RESOURCE_GROUP \
        --name topic-order-events --query id -o tsv) \
    --endpoint https://my-app.example.com/webhooks/orders \
    --endpoint-type webhook \
    --included-event-types "order.created" "order.updated" \
    --advanced-filter data.orderTotal NumberGreaterThan 100
```

---

## Python SDK — Publishing Events

```python
import os
import json
import logging
import uuid
from datetime import datetime, UTC
from azure.eventgrid import EventGridPublisherClient
from azure.core.messaging import CloudEvent
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

TOPIC_ENDPOINT = os.environ["EVENT_GRID_TOPIC_ENDPOINT"]


def publish_order_event(order_id: str, order: dict, event_type: str = "order.created") -> None:
    """Publish a CloudEvent to Event Grid custom topic."""
    credential = DefaultAzureCredential()
    client = EventGridPublisherClient(TOPIC_ENDPOINT, credential)

    event = CloudEvent(
        type=event_type,
        source=f"/orders/{order_id}",
        data=order,
        subject=f"orders/{order_id}",
        id=str(uuid.uuid4()),
        time=datetime.now(UTC),
        datacontenttype="application/json",
    )

    logger.info(
        "Publishing event",
        extra={"event_type": event_type, "order_id": order_id, "event_id": event.id},
    )

    try:
        client.send([event])
        logger.info("Event published", extra={"event_id": event.id, "event_type": event_type})
    except Exception as exc:
        logger.error(
            "Event publish failed",
            extra={"event_id": event.id, "event_type": event_type, "error": str(exc)},
        )
        raise


def publish_batch(events: list[dict]) -> None:
    """Publish multiple events in a single call (max 1 MB per batch)."""
    credential = DefaultAzureCredential()
    client = EventGridPublisherClient(TOPIC_ENDPOINT, credential)

    cloud_events = [
        CloudEvent(
            type=ev["type"],
            source=ev["source"],
            data=ev["data"],
            id=str(uuid.uuid4()),
        )
        for ev in events
    ]

    logger.info("Publishing event batch", extra={"count": len(cloud_events)})
    client.send(cloud_events)
    logger.info("Batch published", extra={"count": len(cloud_events)})
```

---

## Python SDK — Receiving Events (Webhook)

```python
# Azure Functions HTTP trigger — receives Event Grid events
import azure.functions as func
import json
import logging
from azure.eventgrid import EventGridEvent
from azure.messaging.eventgrid import SystemEventNames

logger = logging.getLogger(__name__)
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="webhooks/orders", methods=["POST"])
def order_event_handler(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json()

    # Event Grid validation handshake (first-time subscription confirmation)
    if req.headers.get("aeg-event-type") == "SubscriptionValidation":
        validation_code = body[0]["data"]["validationCode"]
        logger.info("Event Grid validation handshake", extra={"validation_code": validation_code})
        return func.HttpResponse(
            json.dumps({"validationResponse": validation_code}),
            mimetype="application/json",
        )

    # Process actual events
    for event_data in body:
        event_type = event_data.get("type") or event_data.get("eventType")
        subject = event_data.get("subject", "")
        data = event_data.get("data", {})

        logger.info("Event received", extra={"event_type": event_type, "subject": subject})

        if event_type == "order.created":
            handle_order_created(data)
        elif event_type == "order.updated":
            handle_order_updated(data)
        else:
            logger.warning("Unknown event type", extra={"event_type": event_type})

    return func.HttpResponse(status_code=200)


def handle_order_created(data: dict) -> None:
    order_id = data.get("orderId", "unknown")
    logger.info("Handling order created", extra={"order_id": order_id})
    # Business logic...


def handle_order_updated(data: dict) -> None:
    order_id = data.get("orderId", "unknown")
    logger.info("Handling order updated", extra={"order_id": order_id})
```

---

## Useful Commands

```bash
# List event subscriptions for a resource
az eventgrid event-subscription list \
    --source-resource-id $(az storage account show \
        --resource-group $RESOURCE_GROUP \
        --name stmyappprodeastus --query id -o tsv) \
    --output table

# Check delivery metrics
az monitor metrics list \
    --resource $(az eventgrid system-topic show \
        --resource-group $RESOURCE_GROUP \
        --name st-events-my-app --query id -o tsv) \
    --metric "DeliverySuccessCount,DeadLetteredCount" \
    --interval PT5M \
    --aggregation Total \
    --output table
```

---

## References

- [Azure Event Grid documentation](https://docs.microsoft.com/azure/event-grid/)
- [CloudEvents schema](https://docs.microsoft.com/azure/event-grid/cloud-event-schema)
- [Event Grid Python SDK](https://docs.microsoft.com/azure/event-grid/publish-receive-events-using-namespace-topics-python)
- [Event filtering](https://docs.microsoft.com/azure/event-grid/event-filtering)

---

← [Previous: Service Bus](./service-bus.md) | [Home](../../README.md) | [Next: API Management →](./apim.md)
