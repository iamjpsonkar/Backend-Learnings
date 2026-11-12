# Solution — AWS with LocalStack

**Try the tasks yourself before reading this!**

---

## Task 2 — S3 Solution

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# Create bucket
aws s3 mb s3://my-practice-bucket

# Upload
echo "Hello LocalStack!" > hello.txt
aws s3 cp hello.txt s3://my-practice-bucket/hello.txt

# List
aws s3 ls s3://my-practice-bucket/

# Download
aws s3 cp s3://my-practice-bucket/hello.txt ./downloaded.txt
cat downloaded.txt

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-practice-bucket \
  --versioning-configuration Status=Enabled

# Delete
aws s3 rb s3://my-practice-bucket --force
```

---

## Task 3 — SQS Solution

```bash
# Create
aws sqs create-queue --queue-name my-queue

# Get URL
QUEUE_URL=$(aws sqs get-queue-url --queue-name my-queue --query 'QueueUrl' --output text)

# Send 3 messages
for i in 1 2 3; do
  aws sqs send-message --queue-url "$QUEUE_URL" --message-body "Message $i"
done

# Receive
MESSAGES=$(aws sqs receive-message --queue-url "$QUEUE_URL" --max-number-of-messages 10)
echo "$MESSAGES"

# Delete each message
echo "$MESSAGES" | jq -r '.Messages[].ReceiptHandle' | while read handle; do
  aws sqs delete-message --queue-url "$QUEUE_URL" --receipt-handle "$handle"
done
```

---

## Task 6 — Lambda Solution

```bash
cat > lambda_handler.py << 'EOF'
import json
def handler(event, context):
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Hello!", "input": event})
    }
EOF

zip function.zip lambda_handler.py

aws lambda create-function \
  --function-name my-function \
  --runtime python3.12 \
  --handler lambda_handler.handler \
  --zip-file fileb://function.zip \
  --role arn:aws:iam::000000000000:role/lambda-role

aws lambda invoke \
  --function-name my-function \
  --payload '{"name": "LocalStack"}' \
  --cli-binary-format raw-in-base64-out \
  output.json

cat output.json
```

---

## Task 7 — Terraform Solution

```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3 = "http://localhost:4566"
  }
}

resource "aws_s3_bucket" "lab" {
  bucket = "terraform-lab-bucket"
}
```

```bash
terraform init
terraform plan
terraform apply -auto-approve
aws --endpoint-url=http://localhost:4566 s3 ls | grep terraform-lab
terraform destroy -auto-approve
```
