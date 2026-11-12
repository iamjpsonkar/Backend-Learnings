# Lab: AWS with LocalStack

Practice AWS services locally using LocalStack — no real AWS account required.

## Objectives

1. Create and use S3 buckets locally
2. Send and receive messages via SQS
3. Publish events via SNS
4. Query DynamoDB tables
5. Invoke a Lambda function
6. Use Terraform with LocalStack backend

## Prerequisites

- Profile `aws` running: `./run.sh start aws`
- AWS CLI available (or use the aws-cli container)

## Access LocalStack

LocalStack endpoint: `http://localhost:4566`

### Option 1 — Use the aws-cli container (recommended)

```bash
docker exec -it cloud-learnings-aws-cli bash
# All commands inside use --endpoint-url=http://localstack:4566 automatically
```

### Option 2 — Use host AWS CLI

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
aws s3 ls
```

## Check LocalStack Health

```bash
curl http://localhost:4566/_localstack/health | jq .
```

## Continue

See [tasks.md](tasks.md) to start the lab.
