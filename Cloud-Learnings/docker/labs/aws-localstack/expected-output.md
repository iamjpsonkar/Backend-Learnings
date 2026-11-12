# Expected Output — AWS with LocalStack

## LocalStack Health

```json
{
  "services": {
    "s3": "running",
    "sqs": "running",
    "sns": "running",
    "dynamodb": "running",
    "lambda": "running"
  }
}
```

## S3 Bucket List

```
2024-01-01 12:00:00 lab-bucket
2024-01-01 12:00:00 lab-assets
2024-01-01 12:00:00 my-practice-bucket
```

## SQS Receive Message

```json
{
  "Messages": [
    {
      "MessageId": "abc-123",
      "ReceiptHandle": "...",
      "MD5OfBody": "...",
      "Body": "Hello from SQS"
    }
  ]
}
```

## DynamoDB Scan

```json
{
  "Items": [
    {
      "id": {"S": "item-001"},
      "name": {"S": "Widget"},
      "price": {"N": "9.99"}
    }
  ],
  "Count": 1
}
```

## Lambda Invoke

```json
{
  "statusCode": 200,
  "body": "{\"message\": \"Hello from Lambda!\", \"event\": {\"key\": \"value\"}}"
}
```
