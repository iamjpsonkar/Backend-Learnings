output "s3_bucket_data" {
  description = "S3 data bucket name"
  value       = aws_s3_bucket.app_data.bucket
}

output "s3_bucket_logs" {
  description = "S3 logs bucket name"
  value       = aws_s3_bucket.app_logs.bucket
}

output "sqs_queue_url" {
  description = "SQS main queue URL"
  value       = aws_sqs_queue.main.url
}

output "sqs_dlq_url" {
  description = "SQS dead-letter queue URL"
  value       = aws_sqs_queue.dlq.url
}

output "sns_topic_arn" {
  description = "SNS events topic ARN"
  value       = aws_sns_topic.events.arn
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.items.name
}
