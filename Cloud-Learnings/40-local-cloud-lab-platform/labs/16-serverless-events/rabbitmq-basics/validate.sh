#!/usr/bin/env bash
# Validate lab: rabbitmq-basics
set -euo pipefail

RABBITMQ_API="http://localhost:15672/api"
RABBITMQ_CREDS="labadmin:labpassword123"

echo "=== RabbitMQ Basics Lab Validation ==="

# Check RabbitMQ management API
if curl -sf -u "$RABBITMQ_CREDS" "$RABBITMQ_API/overview" 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
version = d.get('rabbitmq_version', '?')
print(f'RabbitMQ version: {version}')
exit(0 if version else 1)
" 2>/dev/null; then
    echo "PASS: RabbitMQ Management API accessible on port 15672"
else
    echo "FAIL: RabbitMQ not accessible — run: make start-data"
    exit 1
fi

# Check AMQP port
if bash -c "echo > /dev/tcp/localhost/5672" 2>/dev/null; then
    echo "PASS: AMQP port 5672 is open"
else
    echo "FAIL: AMQP port 5672 not reachable"
fi

# Check pika is installed
if python3 -c "import pika; print(pika.__version__)" 2>/dev/null; then
    PIKA_VER=$(python3 -c "import pika; print(pika.__version__)")
    echo "PASS: pika $PIKA_VER is installed"
else
    echo "WARN: pika not installed — pip3 install pika"
fi

# Test publish/receive cycle
if python3 -c "
import pika, sys
try:
    conn = pika.BlockingConnection(pika.ConnectionParameters(
        'localhost', 5672, '/',
        pika.PlainCredentials('labadmin', 'labpassword123'),
        connection_attempts=2, retry_delay=1
    ))
    ch = conn.channel()
    ch.queue_declare(queue='validate-test', durable=False, auto_delete=True)
    ch.basic_publish(exchange='', routing_key='validate-test', body=b'validation message')
    method, _, body = next(ch.consume('validate-test', auto_ack=True, inactivity_timeout=2))
    conn.close()
    if body == b'validation message':
        print('PASS: Publish/consume cycle works')
        sys.exit(0)
    else:
        print('FAIL: Wrong message received')
        sys.exit(1)
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
" 2>/dev/null; then
    echo "  Message round-trip successful"
else
    echo "WARN: Publish/consume test failed (pika may not be installed or RabbitMQ not running)"
fi

# Check queues via management API
QUEUE_LIST=$(curl -sf -u "$RABBITMQ_CREDS" "$RABBITMQ_API/queues" 2>/dev/null || echo "[]")
QUEUE_COUNT=$(echo "$QUEUE_LIST" | python3 -c "import sys,json; qs=json.load(sys.stdin); print(len(qs))" 2>/dev/null || echo "0")

if [ "$QUEUE_COUNT" -gt 0 ]; then
    echo "PASS: $QUEUE_COUNT queue(s) found in RabbitMQ"
    echo "$QUEUE_LIST" | python3 -c "
import sys, json
qs = json.load(sys.stdin)
for q in qs[:5]:
    msgs = q.get('messages', 0)
    print(f'  Queue: {q[\"name\"]} ({msgs} messages)')
" 2>/dev/null || true
else
    echo "INFO: No queues found yet — complete the lab tasks to create queues"
fi

# Check for hello queue specifically
if echo "$QUEUE_LIST" | python3 -c "
import sys, json
qs = json.load(sys.stdin)
names = [q['name'] for q in qs]
exit(0 if 'hello' in names else 1)
" 2>/dev/null; then
    echo "PASS: 'hello' queue exists (task 3 completed)"
fi

echo ""
echo "=== Validation complete ==="
