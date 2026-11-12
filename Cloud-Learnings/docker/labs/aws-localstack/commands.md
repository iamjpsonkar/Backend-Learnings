# Commands — AWS with LocalStack

All commands use `--endpoint-url=http://localhost:4566`.

Set these in your shell for convenience:

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export AWS_REQUEST_CHECKSUM_CALCULATION=when_required
export AWS_RESPONSE_CHECKSUM_VALIDATION=when_required
alias awsl="aws --endpoint-url=http://localhost:4566"
```

---

## S3

```bash
# Create bucket
aws s3 mb s3://my-practice-bucket

# List buckets
aws s3 ls

# Upload file
echo "Hello LocalStack!" > hello.txt
aws s3 cp hello.txt s3://my-practice-bucket/hello.txt

# List objects
aws s3 ls s3://my-practice-bucket/

# Download file
aws s3 cp s3://my-practice-bucket/hello.txt ./downloaded.txt

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-practice-bucket \
  --versioning-configuration Status=Enabled

# Delete object
aws s3 rm s3://my-practice-bucket/hello.txt

# Delete bucket (must be empty)
aws s3 rb s3://my-practice-bucket

# Delete bucket and all contents
aws s3 rb s3://my-practice-bucket --force
```

---

## SQS

```bash
# Create queue
aws sqs create-queue --queue-name my-queue

# Get queue URL
QUEUE_URL=$(aws sqs get-queue-url --queue-name my-queue --query 'QueueUrl' --output text)

# Send message
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body "Hello from SQS"

# Send message with attributes
aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"orderId": "ORD-001", "amount": 99.99}' \
  --message-attributes 'ContentType={"DataType":"String","StringValue":"application/json"}'

# Receive messages
aws sqs receive-message \
  --queue-url "$QUEUE_URL" \
  --max-number-of-messages 10 \
  --wait-time-seconds 5

# Delete message (use ReceiptHandle from receive output)
aws sqs delete-message \
  --queue-url "$QUEUE_URL" \
  --receipt-handle "RECEIPT_HANDLE_HERE"

# Get queue attributes
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names All
```

---

## SNS

```bash
# Create topic
aws sns create-topic --name my-topic

# List topics
aws sns list-topics

# Subscribe SQS queue to topic
TOPIC_ARN=$(aws sns list-topics --query 'Topics[0].TopicArn' --output text)
QUEUE_ARN=$(aws sqs get-queue-attributes --queue-url "$QUEUE_URL" \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

aws sns subscribe \
  --topic-arn "$TOPIC_ARN" \
  --protocol sqs \
  --notification-endpoint "$QUEUE_ARN"

# Publish message
aws sns publish \
  --topic-arn "$TOPIC_ARN" \
  --message "Hello from SNS"
```

---

## DynamoDB

```bash
# Create table
aws dynamodb create-table \
  --table-name my-table \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Put item
aws dynamodb put-item \
  --table-name my-table \
  --item '{"id": {"S": "item-001"}, "name": {"S": "Widget"}, "price": {"N": "9.99"}}'

# Get item
aws dynamodb get-item \
  --table-name my-table \
  --key '{"id": {"S": "item-001"}}'

# Scan all items
aws dynamodb scan --table-name my-table

# Query
aws dynamodb query \
  --table-name my-table \
  --key-condition-expression "id = :id" \
  --expression-attribute-values '{":id": {"S": "item-001"}}'

# Delete item
aws dynamodb delete-item \
  --table-name my-table \
  --key '{"id": {"S": "item-001"}}'
```

---

## Lambda

```bash
# Create function code
cat > lambda_handler.py << 'EOF'
import json
def handler(event, context):
    return {"statusCode": 200, "body": json.dumps({"message": "Hello from Lambda!", "event": event})}
EOF

zip function.zip lambda_handler.py

# Create Lambda function
aws lambda create-function \
  --function-name my-function \
  --runtime python3.12 \
  --handler lambda_handler.handler \
  --zip-file fileb://function.zip \
  --role arn:aws:iam::000000000000:role/lambda-role

# Invoke function
aws lambda invoke \
  --function-name my-function \
  --payload '{"key": "value"}' \
  --cli-binary-format raw-in-base64-out \
  output.json
cat output.json

# List functions
aws lambda list-functions
```
