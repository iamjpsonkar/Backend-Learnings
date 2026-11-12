# Broken Scenario: Queue Consumer

**Difficulty**: Intermediate
**Profile**: `messaging apps`

---

## Scenario

The event-consumer is running but messages are piling up in the RabbitMQ queue. No messages are being processed. The consumer shows as "running" in `docker ps`.

---

## Setup

```bash
./run.sh start messaging apps
```

Send some test messages:
```bash
for i in $(seq 1 10); do
  curl -u guest:guest -X POST http://localhost:15672/api/exchanges/%2F/lab.events/publish \
    -H "Content-Type: application/json" \
    -d "{\"properties\":{},\"routing_key\":\"order.created\",\"payload\":\"{\\\"order_id\\\":\\\"ORD-$i\\\"}\",\"payload_encoding\":\"string\"}"
done
```

Check queue depth:
```bash
curl -s -u guest:guest http://localhost:15672/api/queues/%2F/lab.orders \
  | jq '.messages'
# Messages should be > 0 and not decreasing
```

---

## Constraints

- Do NOT modify the consumer Python code
- You may modify environment variables and compose config
- The fix should be non-destructive (no message loss)

---

## Clues

1. Check container logs carefully — what is the last log line?
2. Is the consumer connected to RabbitMQ at all?
3. Check the consumer's environment variables — RABBITMQ_HOST, RABBITMQ_PORT
4. Verify the queue name the consumer is subscribed to vs the queue that has messages

---

## Investigation commands

```bash
# Consumer logs
docker logs cloud-learnings-lab-event-consumer-1 --tail 30

# RabbitMQ connections
curl -s -u guest:guest http://localhost:15672/api/connections | jq '.[].name'

# RabbitMQ consumers per queue
curl -s -u guest:guest http://localhost:15672/api/queues/%2F/lab.orders \
  | jq '.consumer_details'

# Consumer environment
docker exec cloud-learnings-lab-event-consumer-1 env | grep RABBIT
```

---

## Solution validation

After fixing:
```bash
# Queue depth should decrease to 0
watch -n 1 'curl -s -u guest:guest http://localhost:15672/api/queues/%2F/lab.orders | jq .messages'
```
