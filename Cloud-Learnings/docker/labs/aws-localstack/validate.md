# Validation — AWS with LocalStack

Run these commands to verify your work.

## Check S3

```bash
# Should list at least one bucket you created
aws --endpoint-url=http://localhost:4566 s3 ls

# Should return your uploaded file
aws --endpoint-url=http://localhost:4566 s3 ls s3://my-practice-bucket/
```

## Check SQS

```bash
# Should list your queue
aws --endpoint-url=http://localhost:4566 sqs list-queues
```

## Check DynamoDB

```bash
# Should list your table
aws --endpoint-url=http://localhost:4566 dynamodb list-tables

# Should return your items
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name my-table
```

## Check Lambda

```bash
# Should list your function
aws --endpoint-url=http://localhost:4566 lambda list-functions \
  --query 'Functions[*].[FunctionName,Runtime]'
```

## Validation Script

```bash
#!/bin/bash
set -e
ENDPOINT="http://localhost:4566"
AWS="aws --endpoint-url=$ENDPOINT"

echo "=== Checking S3 ==="
$AWS s3 ls | grep -c "." && echo "PASS: S3 buckets found"

echo "=== Checking SQS ==="
$AWS sqs list-queues --query 'QueueUrls' --output text | grep -q "." && echo "PASS: SQS queues found"

echo "=== Checking DynamoDB ==="
$AWS dynamodb list-tables --query 'TableNames' --output text | grep -q "." && echo "PASS: DynamoDB tables found"

echo "=== Validation complete ==="
```
