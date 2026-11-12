# Hints — Queue Worker

---

## Hint 1 — Minimal pika consumer

```python
import pika
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_message(ch, method, properties, body):
    try:
        data = json.loads(body)
        logger.info("Processing order %s, amount: $%.2f",
                    data.get("order_id"), data.get("amount", 0))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse message: %s — sending to DLQ", e)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

connection = pika.BlockingConnection(
    pika.ConnectionParameters("localhost", 5672)
)
channel = connection.channel()
channel.basic_qos(prefetch_count=1)
channel.basic_consume("lab.orders", process_message)
channel.start_consuming()
```

---

## Hint 2 — Reconnect loop

```python
import time

def connect_with_retry(host, max_retries=10, delay=5):
    for attempt in range(max_retries):
        try:
            logger.info("Connecting to RabbitMQ (attempt %d)", attempt + 1)
            conn = pika.BlockingConnection(pika.ConnectionParameters(host))
            logger.info("Connected to RabbitMQ")
            return conn
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning("Connection failed: %s — retrying in %ds", e, delay)
            time.sleep(delay)
    raise RuntimeError("Could not connect to RabbitMQ after %d attempts" % max_retries)
```

---

## Hint 3 — Persistent producer

```python
channel.basic_publish(
    exchange="lab.events",
    routing_key="order.created",
    body=json.dumps({"order_id": "ORD-042", "amount": 49.99}),
    properties=pika.BasicProperties(
        delivery_mode=pika.DeliveryMode.Persistent,  # survive broker restart
        content_type="application/json",
    ),
)
```

---

## Hint 4 — Check DLQ in Management UI

Navigate to: Queues → `lab.dead-letters` → Get Messages

Or via API:
```bash
curl -u guest:guest \
  "http://localhost:15672/api/queues/%2F/lab.dead-letters/get" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"count":5,"ackmode":"ack_requeue_false","encoding":"auto"}'
```

---

## Hint 5 — x-death header

When a message enters the DLQ, RabbitMQ adds an `x-death` header showing:
- Which queue it came from
- Why it was rejected (`rejected`, `expired`, or `maxlen`)
- How many times it died

```python
x_death = properties.headers.get("x-death", [])
if x_death:
    logger.warning("Message died from queue: %s, reason: %s",
                   x_death[0].get("queue"), x_death[0].get("reason"))
```
