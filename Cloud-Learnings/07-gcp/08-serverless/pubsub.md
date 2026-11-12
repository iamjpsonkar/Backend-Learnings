← [Previous: Cloud Functions](./cloud-functions.md) | [Home](../../README.md) | [Next: Cloud Scheduler →](./cloud-scheduler.md)

---

# Cloud Pub/Sub

Pub/Sub is GCP's global messaging service for decoupled, durable, asynchronous communication. It guarantees at-least-once delivery and supports push, pull, and streaming pull.

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Topic** | Named channel where publishers send messages |
| **Subscription** | Named resource representing a subscriber's interest in a topic |
| **Pull subscription** | Subscriber calls `pull` to fetch messages |
| **Push subscription** | Pub/Sub delivers messages to an HTTPS endpoint |
| **Dead-letter topic** | Messages delivered after max delivery attempts go here |
| **Acknowledgement deadline** | Time subscriber has to ack before re-delivery (default 10s, max 600s) |

---

## Topics and Subscriptions

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"

# Create a topic
gcloud pubsub topics create my-app-events \
    --project=$PROJECT \
    --labels=environment=production

# Create a dead-letter topic
gcloud pubsub topics create my-app-events-dead-letter \
    --project=$PROJECT

# Create a pull subscription with dead-lettering
gcloud pubsub subscriptions create my-app-events-worker \
    --project=$PROJECT \
    --topic=my-app-events \
    --ack-deadline=60 \
    --min-retry-delay=10s \
    --max-retry-delay=600s \
    --dead-letter-topic=projects/$PROJECT/topics/my-app-events-dead-letter \
    --max-delivery-attempts=5 \
    --message-filter='attributes.event_type="order.created"' \
    --labels=environment=production

# Grant Pub/Sub permission to forward to dead-letter topic
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format="value(projectNumber)")
PUBSUB_SA="service-$PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com"

gcloud pubsub topics add-iam-policy-binding my-app-events-dead-letter \
    --project=$PROJECT \
    --member="serviceAccount:$PUBSUB_SA" \
    --role="roles/pubsub.publisher"

gcloud pubsub subscriptions add-iam-policy-binding my-app-events-worker \
    --project=$PROJECT \
    --member="serviceAccount:$PUBSUB_SA" \
    --role="roles/pubsub.subscriber"

# Create a push subscription (delivers to HTTP endpoint)
gcloud pubsub subscriptions create my-app-events-push \
    --project=$PROJECT \
    --topic=my-app-events \
    --push-endpoint="https://my-app-worker-abc123-uc.a.run.app/pubsub/push" \
    --push-auth-service-account=sa-pubsub-push@$PROJECT.iam.gserviceaccount.com \
    --ack-deadline=30

# List subscriptions for a topic
gcloud pubsub topics list-subscriptions my-app-events \
    --project=$PROJECT
```

---

## Publishing Messages

```python
import json
import logging
import os
from typing import Any
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)

PROJECT = os.environ["GCP_PROJECT"]

# Publisher is thread-safe; create one instance at module level
publisher = pubsub_v1.PublisherClient()


def publish_event(topic_id: str, event_type: str, payload: dict[str, Any]) -> str:
    """Publish a JSON message to a Pub/Sub topic. Returns message ID."""
    topic_path = publisher.topic_path(PROJECT, topic_id)
    data = json.dumps(payload).encode("utf-8")

    logger.info(
        "Publishing message",
        extra={"topic": topic_id, "event_type": event_type, "payload_keys": list(payload.keys())},
    )

    future = publisher.publish(
        topic_path,
        data=data,
        event_type=event_type,  # Message attribute — can be used in subscription filters
        source="my-app-api",
    )

    message_id = future.result(timeout=10)
    logger.info(
        "Message published",
        extra={"topic": topic_id, "message_id": message_id, "event_type": event_type},
    )
    return message_id


# Batch publishing for high throughput
def publish_batch(topic_id: str, events: list[dict]) -> list[str]:
    """Publish multiple events efficiently using batch settings."""
    topic_path = publisher.topic_path(PROJECT, topic_id)
    message_ids = []

    logger.info("Starting batch publish", extra={"topic": topic_id, "count": len(events)})

    futures = []
    for event in events:
        data = json.dumps(event["payload"]).encode("utf-8")
        future = publisher.publish(
            topic_path,
            data=data,
            event_type=event.get("event_type", "unknown"),
        )
        futures.append((future, event.get("event_type")))

    for future, event_type in futures:
        message_id = future.result(timeout=30)
        message_ids.append(message_id)

    logger.info(
        "Batch publish complete",
        extra={"topic": topic_id, "count": len(message_ids)},
    )
    return message_ids
```

---

## Pull Subscription (Synchronous)

```python
import base64
import json
import logging
import os
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)

PROJECT = os.environ["GCP_PROJECT"]
SUBSCRIPTION_ID = os.environ["PUBSUB_SUBSCRIPTION"]


def pull_messages(max_messages: int = 10, timeout: float = 5.0) -> int:
    """Pull and process messages synchronously. Returns count processed."""
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT, SUBSCRIPTION_ID)

    logger.info(
        "Pulling messages",
        extra={"subscription": SUBSCRIPTION_ID, "max_messages": max_messages},
    )

    response = subscriber.pull(
        request={"subscription": subscription_path, "max_messages": max_messages},
        timeout=timeout,
    )

    ack_ids = []
    processed = 0
    for received_message in response.received_messages:
        message = received_message.message
        message_id = message.message_id
        attributes = dict(message.attributes)

        try:
            payload = json.loads(message.data.decode("utf-8"))
            logger.info(
                "Processing message",
                extra={"message_id": message_id, "attributes": attributes},
            )
            _process(payload, attributes, message_id)
            ack_ids.append(received_message.ack_id)
            processed += 1
        except Exception as exc:
            logger.error(
                "Message processing failed — nacking",
                extra={"message_id": message_id, "error": str(exc)},
            )
            # Don't add to ack_ids — message will be redelivered

    if ack_ids:
        subscriber.acknowledge(
            request={"subscription": subscription_path, "ack_ids": ack_ids}
        )
        logger.info("Messages acknowledged", extra={"count": len(ack_ids)})

    return processed


def _process(payload: dict, attributes: dict, message_id: str) -> None:
    """Business logic for message processing."""
    event_type = attributes.get("event_type", "unknown")
    logger.info("Handling event", extra={"message_id": message_id, "event_type": event_type})
    # ... your logic here
```

---

## Streaming Pull (Long-Running Consumer)

```python
import json
import logging
import os
import signal
import time
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)

PROJECT = os.environ["GCP_PROJECT"]
SUBSCRIPTION_ID = os.environ["PUBSUB_SUBSCRIPTION"]

_running = True


def _signal_handler(signum, frame):
    global _running
    logger.info("Shutdown signal received", extra={"signum": signum})
    _running = False


def message_callback(message: pubsub_v1.types.PubsubMessage) -> None:
    """Called for each received message in a separate thread."""
    message_id = message.message_id
    attributes = dict(message.attributes)

    logger.info("Message received", extra={"message_id": message_id, "attributes": attributes})

    try:
        payload = json.loads(message.data.decode("utf-8"))
        _process(payload, attributes, message_id)
        message.ack()
        logger.info("Message acked", extra={"message_id": message_id})
    except Exception as exc:
        logger.error(
            "Processing failed, nacking message",
            extra={"message_id": message_id, "error": str(exc)},
        )
        message.nack()


def run_subscriber() -> None:
    """Long-running streaming pull subscriber."""
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT, SUBSCRIPTION_ID)

    flow_control = pubsub_v1.types.FlowControl(max_messages=100)

    logger.info("Starting streaming pull", extra={"subscription": SUBSCRIPTION_ID})

    streaming_pull_future = subscriber.subscribe(
        subscription_path,
        callback=message_callback,
        flow_control=flow_control,
    )

    try:
        while _running:
            time.sleep(1)
        logger.info("Stopping subscriber gracefully")
        streaming_pull_future.cancel()
        streaming_pull_future.result(timeout=10)
    except TimeoutError:
        logger.warning("Subscriber did not shut down cleanly")
    finally:
        subscriber.close()
        logger.info("Subscriber stopped")


if __name__ == "__main__":
    run_subscriber()
```

---

## Operations

```bash
# Publish a test message
gcloud pubsub topics publish my-app-events \
    --project=$PROJECT \
    --message='{"order_id": "ord_001", "amount": 99.99}' \
    --attribute=event_type=order.created

# Pull messages manually
gcloud pubsub subscriptions pull my-app-events-worker \
    --project=$PROJECT \
    --limit=5 \
    --auto-ack

# Seek to a timestamp (replay messages)
gcloud pubsub subscriptions seek my-app-events-worker \
    --project=$PROJECT \
    --time=2024-06-01T00:00:00Z

# Check subscription backlog
gcloud pubsub subscriptions describe my-app-events-worker \
    --project=$PROJECT \
    --format="table(name,pushConfig,ackDeadlineSeconds,messageRetentionDuration)"

# Grant a service account publish permission
gcloud pubsub topics add-iam-policy-binding my-app-events \
    --project=$PROJECT \
    --member="serviceAccount:sa-my-app@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"
```

---

## References

- [Pub/Sub documentation](https://cloud.google.com/pubsub/docs)
- [Python client library](https://cloud.google.com/python/docs/reference/pubsub/latest)
- [Message filtering](https://cloud.google.com/pubsub/docs/filtering)
- [Dead-letter topics](https://cloud.google.com/pubsub/docs/dead-letter-topics)

---

← [Previous: Cloud Functions](./cloud-functions.md) | [Home](../../README.md) | [Next: Cloud Scheduler →](./cloud-scheduler.md)
