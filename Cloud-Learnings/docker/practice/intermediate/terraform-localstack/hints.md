# Hints — Terraform with LocalStack

## Hint 1 — File Structure

```
terraform-localstack/
├── main.tf
├── variables.tf
├── outputs.tf
├── terraform.tfvars
└── terraform.tfstate  (generated)
```

## Hint 2 — S3 Bucket with Versioning

```hcl
resource "aws_s3_bucket" "main" {
  bucket = "${var.project_name}-${var.environment}-data"
  tags   = { project = var.project_name }
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

## Hint 3 — Dead Letter Queue

```hcl
resource "aws_sqs_queue" "dlq" {
  name = "${var.project_name}-${var.environment}-dlq"
}

resource "aws_sqs_queue" "main" {
  name = "${var.project_name}-${var.environment}-queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}
```

## Hint 4 — SNS Subscription

```hcl
resource "aws_sns_topic" "main" {
  name = "${var.project_name}-${var.environment}-events"
}

resource "aws_sns_topic_subscription" "sqs" {
  topic_arn = aws_sns_topic.main.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.main.arn
}
```

## Hint 5 — Outputs

```hcl
output "bucket_name" {
  value = aws_s3_bucket.main.bucket
}
output "queue_url" {
  value = aws_sqs_queue.main.url
}
output "topic_arn" {
  value = aws_sns_topic.main.arn
}
```
