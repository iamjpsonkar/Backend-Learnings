← [Previous: Azure Functions](./functions.md) | [Home](../../README.md) | [Next: Event Grid →](./event-grid.md)

---

# Azure Service Bus

Azure Service Bus is an enterprise-grade message broker supporting queues (point-to-point) and topics/subscriptions (pub/sub). It guarantees at-least-once delivery, ordering, deduplication, and dead-lettering.

---

## Queues vs Topics vs Event Hubs vs Event Grid

| Feature | Service Bus Queue | Service Bus Topic | Event Hubs | Event Grid |
|---------|------------------|-------------------|------------|------------|
| Pattern | Point-to-point | Pub/sub | Stream | Event routing |
| Consumers | One | Many (subscriptions) | Many (consumer groups) | Many (webhooks) |
| Ordering | FIFO (sessions) | FIFO (sessions) | Per partition | No |
| Message size | 100 MB (Premium) | 100 MB (Premium) | 1 MB (batch) | 64 KB |
| Retention | Up to 14 days | Up to 14 days | Up to 90 days | N/A |
| Dead-letter | Yes | Yes | No | No |
| Deduplication | Yes | Yes | No | No |
| Use case | Task queues, workflows | Fan-out messaging | Log ingestion, telemetry | Azure event routing |

---

## Creating a Namespace and Queue

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
NAMESPACE_NAME="sb-my-app-prod-eastus"

# Create Premium namespace (required for VNet, large messages, geo-DR)
az servicebus namespace create \
    --resource-group $RESOURCE_GROUP \
    --name $NAMESPACE_NAME \
    --location eastus \
    --sku Premium \
    --capacity 1 \
    --zone-redundant true \
    --tags Environment=production Service=my-app

# Create a queue
az servicebus queue create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name $NAMESPACE_NAME \
    --name order-processing \
    --max-size 5120 \
    --default-message-time-to-live P14D \
    --lock-duration PT2M \
    --max-delivery-count 10 \
    --dead-lettering-on-message-expiration true \
    --enable-session false \
    --enable-duplicate-detection false

# Create a queue with sessions (for FIFO ordering per customer)
az servicebus queue create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name $NAMESPACE_NAME \
    --name order-processing-fifo \
    --enable-session true \
    --lock-duration PT5M \
    --max-delivery-count 5

# Create a dead-letter queue check interval alert
# (Dead-letter queue is auto-created at: order-processing/$DeadLetterQueue)
```

---

## Topics and Subscriptions

```bash
# Create a topic
az servicebus topic create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name $NAMESPACE_NAME \
    --name order-events \
    --max-size 5120 \
    --default-message-time-to-live P7D \
    --enable-duplicate-detection true \
    --duplicate-detection-history-time-window PT10M

# Create subscriptions (each gets its own copy of the message)
az servicebus topic subscription create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name $NAMESPACE_NAME \
    --topic-name order-events \
    --name inventory-service \
    --max-delivery-count 10 \
    --dead-lettering-on-message-expiration true

az servicebus topic subscription create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name $NAMESPACE_NAME \
    --topic-name order-events \
    --name notification-service \
    --max-delivery-count 5

# Add a filter — notify only for high-value orders
az servicebus topic subscription rule create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name $NAMESPACE_NAME \
    --topic-name order-events \
    --subscription-name notification-service \
    --name high-value-filter \
    --filter-sql-expression "orderTotal > 1000"

# List topics and subscriptions
az servicebus topic list \
    --resource-group $RESOURCE_GROUP \
    --namespace-name $NAMESPACE_NAME \
    --output table

az servicebus topic subscription list \
    --resource-group $RESOURCE_GROUP \
    --namespace-name $NAMESPACE_NAME \
    --topic-name order-events \
    --output table
```

---

## Private Endpoint

```bash
# Disable public network access and use private endpoint
az servicebus namespace update \
    --resource-group $RESOURCE_GROUP \
    --name $NAMESPACE_NAME \
    --public-network-access Disabled

az network private-endpoint create \
    --resource-group $RESOURCE_GROUP \
    --name pe-servicebus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-private-endpoints \
    --private-connection-resource-id $(az servicebus namespace show \
        --resource-group $RESOURCE_GROUP \
        --name $NAMESPACE_NAME --query id -o tsv) \
    --group-id namespace \
    --connection-name pe-conn-servicebus

# Private DNS zone for Service Bus
az network private-dns zone create \
    --resource-group $RESOURCE_GROUP \
    --name "privatelink.servicebus.windows.net"

az network private-dns link vnet create \
    --resource-group $RESOURCE_GROUP \
    --zone-name "privatelink.servicebus.windows.net" \
    --name dns-link-servicebus \
    --virtual-network vnet-my-app-prod-eastus-001 \
    --registration-enabled false

az network private-endpoint dns-zone-group create \
    --resource-group $RESOURCE_GROUP \
    --endpoint-name pe-servicebus \
    --name sb-zone-group \
    --private-dns-zone "privatelink.servicebus.windows.net" \
    --zone-name servicebus
```

---

## Python SDK

```python
import os
import json
import logging
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.servicebus.exceptions import ServiceBusError
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

NAMESPACE_URL = os.environ["SERVICE_BUS_NAMESPACE"]  # sb-my-app-prod-eastus.servicebus.windows.net
QUEUE_NAME = "order-processing"


def send_order(order: dict) -> None:
    """Send an order message to the queue."""
    credential = DefaultAzureCredential()
    order_id = order.get("orderId", "unknown")

    with ServiceBusClient(NAMESPACE_URL, credential) as client:
        with client.get_queue_sender(QUEUE_NAME) as sender:
            message = ServiceBusMessage(
                body=json.dumps(order).encode("utf-8"),
                subject="order.created",
                message_id=order_id,                  # Idempotency key
                content_type="application/json",
                application_properties={"orderType": order.get("type", "standard")},
            )
            logger.info("Sending order to queue", extra={"order_id": order_id, "queue": QUEUE_NAME})
            sender.send_messages(message)
            logger.info("Order sent", extra={"order_id": order_id})


def send_batch(orders: list[dict]) -> None:
    """Send multiple orders as a single batch."""
    credential = DefaultAzureCredential()
    logger.info("Sending batch to queue", extra={"count": len(orders), "queue": QUEUE_NAME})

    with ServiceBusClient(NAMESPACE_URL, credential) as client:
        with client.get_queue_sender(QUEUE_NAME) as sender:
            batch = sender.create_message_batch()
            for order in orders:
                try:
                    batch.add_message(ServiceBusMessage(json.dumps(order).encode("utf-8")))
                except ValueError:
                    # Batch full — send and start a new one
                    sender.send_messages(batch)
                    logger.info("Batch sent, starting new batch")
                    batch = sender.create_message_batch()
                    batch.add_message(ServiceBusMessage(json.dumps(order).encode("utf-8")))
            sender.send_messages(batch)
            logger.info("Final batch sent")


def receive_and_process(max_messages: int = 10, timeout_seconds: float = 10.0) -> None:
    """Receive and process messages with peek-lock (safe processing)."""
    credential = DefaultAzureCredential()

    with ServiceBusClient(NAMESPACE_URL, credential) as client:
        with client.get_queue_receiver(QUEUE_NAME, max_wait_time=timeout_seconds) as receiver:
            messages = receiver.receive_messages(max_message_count=max_messages)
            logger.info("Received messages", extra={"count": len(messages), "queue": QUEUE_NAME})

            for msg in messages:
                order_id = str(msg.message_id or "unknown")
                logger.info("Processing message", extra={"order_id": order_id, "delivery_count": msg.delivery_count})

                try:
                    order = json.loads(msg.body)
                    # Process order...
                    process_order(order)
                    receiver.complete_message(msg)  # Remove from queue
                    logger.info("Message completed", extra={"order_id": order_id})

                except Exception as exc:
                    logger.error("Processing failed", extra={"order_id": order_id, "error": str(exc)})
                    if msg.delivery_count >= 9:
                        # Max retries reached — send to dead-letter
                        receiver.dead_letter_message(msg, reason="MaxRetriesExceeded", error_description=str(exc))
                        logger.warning("Message dead-lettered", extra={"order_id": order_id})
                    else:
                        receiver.abandon_message(msg)  # Return to queue for retry


def process_order(order: dict) -> None:
    logger.info("Processing order", extra={"order_id": order.get("orderId")})
```

---

## Geo-Disaster Recovery (Premium)

```bash
# Create geo-DR pairing (passive secondary namespace)
az servicebus georecovery-alias create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name $NAMESPACE_NAME \
    --alias sb-my-app-geodr \
    --partner-namespace $(az servicebus namespace show \
        --resource-group rg-my-app-dr-westus \
        --name sb-my-app-dr-westus --query id -o tsv)

# Initiate failover (promotes secondary to primary)
az servicebus georecovery-alias fail-over \
    --resource-group rg-my-app-dr-westus \
    --namespace-name sb-my-app-dr-westus \
    --alias sb-my-app-geodr

# Applications connect using alias FQDN — transparent failover
# sb-my-app-geodr.servicebus.windows.net
```

---

## References

- [Azure Service Bus documentation](https://docs.microsoft.com/azure/service-bus-messaging/)
- [Service Bus queues, topics, and subscriptions](https://docs.microsoft.com/azure/service-bus-messaging/service-bus-queues-topics-subscriptions)
- [Python SDK](https://docs.microsoft.com/azure/service-bus-messaging/service-bus-python-how-to-use-queues)
- [Geo-disaster recovery](https://docs.microsoft.com/azure/service-bus-messaging/service-bus-geo-dr)

---

← [Previous: Azure Functions](./functions.md) | [Home](../../README.md) | [Next: Event Grid →](./event-grid.md)
