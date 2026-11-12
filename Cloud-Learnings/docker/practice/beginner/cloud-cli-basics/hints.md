# Hints — Cloud CLI Basics

---

## Hint 1 — S3 commands

```bash
# Create bucket
aws s3 mb s3://my-practice-bucket

# Upload
echo "hello world" > test.txt
aws s3 cp test.txt s3://my-practice-bucket/test.txt

# List
aws s3 ls s3://my-practice-bucket

# Download
aws s3 cp s3://my-practice-bucket/test.txt downloaded.txt

# Delete object
aws s3 rm s3://my-practice-bucket/test.txt

# Delete bucket (must be empty)
aws s3 rb s3://my-practice-bucket
```

---

## Hint 2 — SQS commands

```bash
# Create queue
aws sqs create-queue --queue-name my-queue

# Get queue URL (needed for other commands)
URL=$(aws sqs get-queue-url --queue-name my-queue --query QueueUrl --output text)

# Send
aws sqs send-message --queue-url "$URL" --message-body "Hello from SQS"

# Receive (saves ReceiptHandle)
RECEIPT=$(aws sqs receive-message --queue-url "$URL" \
  --query "Messages[0].ReceiptHandle" --output text)

# Delete
aws sqs delete-message --queue-url "$URL" --receipt-handle "$RECEIPT"

# Delete queue
aws sqs delete-queue --queue-url "$URL"
```

---

## Hint 3 — DynamoDB commands

```bash
# Create table
aws dynamodb create-table \
  --table-name users \
  --attribute-definitions AttributeName=user_id,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Put item
aws dynamodb put-item \
  --table-name users \
  --item '{"user_id":{"S":"u001"},"name":{"S":"Alice"},"age":{"N":"30"}}'

# Get item
aws dynamodb get-item \
  --table-name users \
  --key '{"user_id":{"S":"u001"}}'

# Update
aws dynamodb update-item \
  --table-name users \
  --key '{"user_id":{"S":"u001"}}' \
  --update-expression "SET age = :a" \
  --expression-attribute-values '{":a":{"N":"31"}}'

# Delete item
aws dynamodb delete-item \
  --table-name users \
  --key '{"user_id":{"S":"u001"}}'

# Delete table
aws dynamodb delete-table --table-name users
```

---

## Hint 4 — Output formats compared

```
--output json   → full JSON, good for scripts with jq
--output table  → pretty ASCII table, good for reading
--output text   → tab-separated, good for shell variables
```

---

## Hint 5 — JMESPath --query cheatsheet

```bash
# Array of all values
--query "Items[].name.S"

# Filter where condition
--query "Items[?age.N=='31'].name.S"

# Count
--query "length(Items)"

# Nested access
--query "Table.ItemCount"
```
