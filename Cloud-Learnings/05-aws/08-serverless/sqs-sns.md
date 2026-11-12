← [Previous: API Gateway](./api-gateway.md) | [Home](../../README.md) | [Next: EventBridge →](./eventbridge.md)

---

# Amazon SQS and SNS

SQS (Simple Queue Service) and SNS (Simple Notification Service) are the foundational messaging primitives for decoupling and fan-out in AWS architectures.

---

## SQS — Simple Queue Service

SQS is a fully managed message queue. Producers send messages; consumers poll and process them. Messages are durably stored until successfully deleted by the consumer.

### Standard vs FIFO Queues

| | Standard | FIFO |
|--|----------|------|
| Ordering | Best-effort (not guaranteed) | Strict FIFO per message group |
| Delivery | At-least-once (duplicates possible) | Exactly-once processing |
| Throughput | Unlimited | 3,000 msg/s per API call (with batching) |
| Deduplication | Manual (consumer handles) | 5-minute dedup window (ID-based) |
| Cost | $0.40/million | $0.50/million |
| Use for | Decoupling, high-throughput, order unimportant | Financial transactions, inventory, order processing |

---

### Creating SQS Queues

```bash
# Standard queue with a dead-letter queue (DLQ)
DLQ_URL=$(aws sqs create-queue \
    --queue-name my-app-queue-dlq \
    --attributes '{
        "MessageRetentionPeriod": "1209600"
    }' \
    --tags Environment=production \
    --query 'QueueUrl' --output text)

DLQ_ARN=$(aws sqs get-queue-attributes \
    --queue-url $DLQ_URL \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' --output text)

QUEUE_URL=$(aws sqs create-queue \
    --queue-name my-app-queue \
    --attributes '{
        "VisibilityTimeout": "60",
        "MessageRetentionPeriod": "86400",
        "ReceiveMessageWaitTimeSeconds": "20",
        "RedrivePolicy": "{\"deadLetterTargetArn\":\"'$DLQ_ARN'\",\"maxReceiveCount\":\"3\"}"
    }' \
    --tags Environment=production \
    --query 'QueueUrl' --output text)

echo "Queue: $QUEUE_URL"
echo "DLQ: $DLQ_URL"

# FIFO queue
FIFO_URL=$(aws sqs create-queue \
    --queue-name my-orders-queue.fifo \
    --attributes '{
        "FifoQueue": "true",
        "ContentBasedDeduplication": "true",
        "VisibilityTimeout": "60",
        "MessageRetentionPeriod": "86400",
        "RedrivePolicy": "{\"deadLetterTargetArn\":\"'$DLQ_ARN'.fifo\",\"maxReceiveCount\":\"3\"}"
    }' \
    --query 'QueueUrl' --output text)
```

### Sending and Receiving Messages

```bash
QUEUE_URL="https://sqs.us-east-1.amazonaws.com/123456789012/my-app-queue"

# Send a message
aws sqs send-message \
    --queue-url $QUEUE_URL \
    --message-body '{"order_id": "ORD-001", "action": "process"}' \
    --message-attributes '{
        "ContentType": {
            "DataType": "String",
            "StringValue": "application/json"
        }
    }'

# Send a batch (up to 10 messages, reduces cost by 10x)
aws sqs send-message-batch \
    --queue-url $QUEUE_URL \
    --entries '[
        {"Id": "1", "MessageBody": "{\"order_id\":\"ORD-002\"}"},
        {"Id": "2", "MessageBody": "{\"order_id\":\"ORD-003\"}"},
        {"Id": "3", "MessageBody": "{\"order_id\":\"ORD-004\"}"}
    ]'

# Receive and delete messages (long polling — waits up to 20s for messages)
RECEIPT=$(aws sqs receive-message \
    --queue-url $QUEUE_URL \
    --max-number-of-messages 10 \
    --wait-time-seconds 20 \
    --attribute-names All \
    --message-attribute-names All \
    --query 'Messages[0].ReceiptHandle' --output text)

# Delete after successful processing
aws sqs delete-message \
    --queue-url $QUEUE_URL \
    --receipt-handle $RECEIPT
```

### Python Consumer Pattern

```python
import boto3
import json
import logging
import time
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
sqs = boto3.client("sqs", region_name="us-east-1")

QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/my-app-queue"
VISIBILITY_TIMEOUT = 60   # must be >= max processing time


def process_messages():
    """
    Long-poll consumer loop. Receives batches, processes each message,
    and deletes successfully processed ones.
    """
    logger.info("SQS consumer starting: queue=%s", QUEUE_URL)

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
                AttributeNames=["All"],
                MessageAttributeNames=["All"],
            )
        except ClientError as e:
            logger.error("Failed to receive messages: error=%s", e.response["Error"]["Code"])
            time.sleep(5)
            continue

        messages = response.get("Messages", [])
        if not messages:
            logger.debug("No messages available, polling again")
            continue

        logger.info("Received batch: count=%d", len(messages))

        for message in messages:
            message_id = message["MessageId"]
            receipt_handle = message["ReceiptHandle"]

            try:
                body = json.loads(message["Body"])
                logger.info("Processing message: message_id=%s body_keys=%s", message_id, list(body.keys()))

                handle_message(body)

                # Delete only after successful processing
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
                logger.info("Message processed and deleted: message_id=%s", message_id)

            except Exception as e:
                logger.error("Message processing failed: message_id=%s error=%s", message_id, str(e), exc_info=True)
                # Do NOT delete — message will reappear after VisibilityTimeout
                # After maxReceiveCount retries, it moves to DLQ automatically


def handle_message(body: dict) -> None:
    """Process a single message body."""
    order_id = body.get("order_id")
    logger.info("Handling order: order_id=%s", order_id)
    # Your business logic here
```

### Queue Attributes and Monitoring

```bash
QUEUE_URL="https://sqs.us-east-1.amazonaws.com/123456789012/my-app-queue"

# View queue attributes
aws sqs get-queue-attributes \
    --queue-url $QUEUE_URL \
    --attribute-names All \
    --query 'Attributes.{
        Visible:ApproximateNumberOfMessages,
        InFlight:ApproximateNumberOfMessagesNotVisible,
        Delayed:ApproximateNumberOfMessagesDelayed,
        Visibility:VisibilityTimeout,
        Retention:MessageRetentionPeriod,
        MaxReceive:RedrivePolicy
    }'

# Alarm: DLQ has messages (indicates processing failures)
DLQ_URL="https://sqs.us-east-1.amazonaws.com/123456789012/my-app-queue-dlq"
DLQ_ARN="arn:aws:sqs:us-east-1:123456789012:my-app-queue-dlq"

aws cloudwatch put-metric-alarm \
    --alarm-name sqs-dlq-not-empty \
    --namespace AWS/SQS \
    --metric-name ApproximateNumberOfMessagesVisible \
    --dimensions Name=QueueName,Value=my-app-queue-dlq \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts
```

---

## SNS — Simple Notification Service

SNS is a fully managed pub/sub service. Publishers send messages to topics; SNS delivers to all subscriptions (SQS, Lambda, HTTP, email, SMS, mobile push).

### Creating a Topic and Subscriptions

```bash
# Create a standard SNS topic
TOPIC_ARN=$(aws sns create-topic \
    --name my-app-notifications \
    --attributes DisplayName="App Notifications" \
    --tags Key=Environment,Value=production \
    --query 'TopicArn' --output text)

echo "Topic: $TOPIC_ARN"

# Subscribe SQS queues (fan-out pattern)
QUEUE_A_ARN="arn:aws:sqs:us-east-1:123456789012:queue-service-a"
QUEUE_B_ARN="arn:aws:sqs:us-east-1:123456789012:queue-service-b"

aws sns subscribe \
    --topic-arn $TOPIC_ARN \
    --protocol sqs \
    --notification-endpoint $QUEUE_A_ARN

aws sns subscribe \
    --topic-arn $TOPIC_ARN \
    --protocol sqs \
    --notification-endpoint $QUEUE_B_ARN

# Subscribe Lambda
aws sns subscribe \
    --topic-arn $TOPIC_ARN \
    --protocol lambda \
    --notification-endpoint arn:aws:lambda:us-east-1:123456789012:function:my-processor

# Grant Lambda permission for SNS to invoke it
aws lambda add-permission \
    --function-name my-processor \
    --statement-id sns-invoke \
    --action lambda:InvokeFunction \
    --principal sns.amazonaws.com \
    --source-arn $TOPIC_ARN

# Subscribe email (requires confirmation)
aws sns subscribe \
    --topic-arn $TOPIC_ARN \
    --protocol email \
    --notification-endpoint ops@example.com

# SQS queue must have a policy allowing SNS to send to it
aws sqs set-queue-attributes \
    --queue-url $QUEUE_A_URL \
    --attributes '{
        "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"sns.amazonaws.com\"},\"Action\":\"sqs:SendMessage\",\"Resource\":\"'$QUEUE_A_ARN'\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"'$TOPIC_ARN'\"}}}]}"
    }'
```

### Publishing Messages

```bash
# Publish a message to all subscribers
aws sns publish \
    --topic-arn $TOPIC_ARN \
    --subject "Order Placed" \
    --message '{"order_id": "ORD-001", "user_id": "USER#alice", "total": 99.99}' \
    --message-attributes '{
        "eventType": {
            "DataType": "String",
            "StringValue": "ORDER_PLACED"
        },
        "priority": {
            "DataType": "Number",
            "StringValue": "1"
        }
    }'

# Publish different messages per protocol (message structure)
aws sns publish \
    --topic-arn $TOPIC_ARN \
    --message-structure json \
    --message '{
        "default": "Order ORD-001 placed",
        "email": "Your order ORD-001 has been placed. Total: $99.99",
        "sqs": "{\"order_id\": \"ORD-001\", \"action\": \"process\"}",
        "lambda": "{\"order_id\": \"ORD-001\", \"action\": \"notify\"}"
    }'

# Publish to a specific SQS queue directly (no fan-out)
aws sns publish \
    --topic-arn $TOPIC_ARN \
    --message '{"event": "test"}' \
    --target-arn $QUEUE_A_ARN

# Batch publish (up to 10 messages)
aws sns publish-batch \
    --topic-arn $TOPIC_ARN \
    --publish-batch-request-entries '[
        {"Id": "1", "Message": "{\"order_id\": \"ORD-002\"}"},
        {"Id": "2", "Message": "{\"order_id\": \"ORD-003\"}"}
    ]'
```

### Message Filtering

Subscriptions can filter messages by attribute, reducing unnecessary processing.

```bash
# Service A only receives ORDER_PLACED events
aws sns set-subscription-attributes \
    --subscription-arn arn:aws:sns:us-east-1:123456789012:my-app-notifications:abc123 \
    --attribute-name FilterPolicy \
    --attribute-value '{"eventType": ["ORDER_PLACED", "ORDER_UPDATED"]}'

# Service B only receives high-priority events
aws sns set-subscription-attributes \
    --subscription-arn arn:aws:sns:us-east-1:123456789012:my-app-notifications:def456 \
    --attribute-name FilterPolicy \
    --attribute-value '{"priority": [{"numeric": [">=", 5]}]}'

# Service C receives everything except internal events
aws sns set-subscription-attributes \
    --subscription-arn arn:aws:sns:us-east-1:123456789012:my-app-notifications:ghi789 \
    --attribute-name FilterPolicy \
    --attribute-value '{"eventType": [{"anything-but": ["INTERNAL_HEARTBEAT"]}]}'
```

---

## Fan-Out Pattern (SNS → Multiple SQS)

```
Publisher
   │
   ▼
SNS Topic (my-app-notifications)
   ├──→ SQS Queue A (order-processor) — processes orders
   ├──→ SQS Queue B (notification-service) — sends emails/SMS
   ├──→ SQS Queue C (analytics-service) — records events
   └──→ Lambda (realtime-dashboard) — pushes to WebSocket
```

```bash
# Create three downstream queues
for SERVICE in order-processor notification-service analytics-service; do
    QUEUE=$(aws sqs create-queue \
        --queue-name $SERVICE \
        --query 'QueueUrl' --output text)

    QUEUE_ARN=$(aws sqs get-queue-attributes \
        --queue-url $QUEUE \
        --attribute-names QueueArn \
        --query 'Attributes.QueueArn' --output text)

    # Subscribe each queue to the topic
    aws sns subscribe \
        --topic-arn $TOPIC_ARN \
        --protocol sqs \
        --notification-endpoint $QUEUE_ARN

    # Allow SNS to send to each queue
    aws sqs set-queue-attributes \
        --queue-url $QUEUE \
        --attributes "{\"Policy\":\"{\\\"Version\\\":\\\"2012-10-17\\\",\\\"Statement\\\":[{\\\"Effect\\\":\\\"Allow\\\",\\\"Principal\\\":{\\\"Service\\\":\\\"sns.amazonaws.com\\\"},\\\"Action\\\":\\\"sqs:SendMessage\\\",\\\"Resource\\\":\\\"$QUEUE_ARN\\\",\\\"Condition\\\":{\\\"ArnEquals\\\":{\\\"aws:SourceArn\\\":\\\"$TOPIC_ARN\\\"}}}]}]\\\"}"

    echo "Subscribed $SERVICE ($QUEUE_ARN) to topic"
done
```

---

## FIFO Topic (Ordered Fan-Out)

FIFO SNS topics preserve message order and guarantee exactly-once delivery to FIFO SQS subscribers.

```bash
# Create FIFO topic
FIFO_TOPIC=$(aws sns create-topic \
    --name my-orders-topic.fifo \
    --attributes '{
        "FifoTopic": "true",
        "ContentBasedDeduplication": "true"
    }' \
    --query 'TopicArn' --output text)

# Publish to FIFO topic (requires MessageGroupId)
aws sns publish \
    --topic-arn $FIFO_TOPIC \
    --message '{"order_id": "ORD-001"}' \
    --message-group-id "customer-alice" \
    --message-deduplication-id "ORD-001"
```

---

## References

- [SQS documentation](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/)
- [SNS documentation](https://docs.aws.amazon.com/sns/latest/dg/)
- [SNS message filtering](https://docs.aws.amazon.com/sns/latest/dg/sns-message-filtering.html)
- [SQS pricing](https://aws.amazon.com/sqs/pricing/)
---

← [Previous: API Gateway](./api-gateway.md) | [Home](../../README.md) | [Next: EventBridge →](./eventbridge.md)
