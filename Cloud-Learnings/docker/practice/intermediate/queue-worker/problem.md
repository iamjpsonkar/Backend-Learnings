# Queue Worker — Intermediate

**Difficulty**: Intermediate
**Profile**: `messaging apps`
**Time estimate**: 60–90 minutes

---

## Scenario

You need to build a reliable background job processor using RabbitMQ. Jobs must be processed at-least-once, failed jobs must go to a dead-letter queue, and the worker must handle reconnection gracefully.

---

## Setup

```bash
./run.sh start messaging

# RabbitMQ Management UI: http://localhost:15672 (guest/guest)
# Verify exchanges and queues are created from definitions.json
```

---

## Tasks

### Task 1 — Explore the RabbitMQ topology

Open the Management UI at http://localhost:15672

Find:
- What exchanges exist?
- What queues exist?
- What bindings connect them?
- What is the DLX (Dead Letter Exchange) for the `lab.orders` queue?

### Task 2 — Publish a message (CLI)

Use `rabbitmqadmin` or the RabbitMQ HTTP API to publish a test message:

```bash
# Via Management API
curl -u guest:guest \
  -H "Content-Type: application/json" \
  -X POST http://localhost:15672/api/exchanges/%2F/lab.events/publish \
  -d '{
    "properties": {"delivery_mode": 2},
    "routing_key": "order.created",
    "payload": "{\"order_id\": \"ORD-001\", \"amount\": 99.99}",
    "payload_encoding": "string"
  }'
```

Verify it appears in the `lab.orders` queue.

### Task 3 — Write a consumer in Python

Create `worker.py` that:
1. Connects to RabbitMQ (`amqp://guest:guest@localhost:5672/`)
2. Consumes from `lab.orders`
3. Parses JSON messages
4. Logs: `Processing order ORD-XXX, amount: $XX.XX`
5. Acknowledges after successful processing
6. NACKs (without requeue) on parse errors → goes to DLQ

```python
import pika
import json
import logging

# Your code here
```

### Task 4 — Test the dead-letter flow

1. Publish an invalid message (not valid JSON)
2. Your consumer should NACK it
3. Verify it appears in `lab.dead-letters` queue in the Management UI

### Task 5 — Simulate reconnection

1. Start your worker
2. Restart the RabbitMQ container: `docker restart cloud-learnings-lab-rabbitmq-1`
3. Your worker should reconnect automatically (retry loop)
4. Publish a new message — it should be processed

### Task 6 — Publish from Python

Extend the script or write a separate producer that:
1. Accepts an order from stdin (or hardcodes one)
2. Publishes to `lab.events` exchange with routing key `order.created`
3. Uses persistent delivery mode (survives broker restart)

---

## Success criteria

- [ ] RabbitMQ topology understood (exchanges, queues, bindings, DLX)
- [ ] Message published via HTTP API and visible in queue
- [ ] Consumer processes messages and logs them
- [ ] Invalid messages go to dead-letter queue
- [ ] Consumer reconnects after broker restart
- [ ] Python producer publishes persistent messages
