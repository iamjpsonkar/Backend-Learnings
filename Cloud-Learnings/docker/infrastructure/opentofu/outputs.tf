output "s3_app_data_bucket" {
  description = "App data S3 bucket name"
  value       = aws_s3_bucket.app_data.bucket
}

output "s3_backups_bucket" {
  description = "Backups S3 bucket name"
  value       = aws_s3_bucket.backups.bucket
}

output "sqs_orders_url" {
  description = "Orders SQS queue URL"
  value       = aws_sqs_queue.orders.url
}

output "sqs_dlq_url" {
  description = "Dead-letter queue URL"
  value       = aws_sqs_queue.dead_letter.url
}

output "sns_events_arn" {
  description = "Events SNS topic ARN"
  value       = aws_sns_topic.events.arn
}

output "dynamodb_sessions_table" {
  description = "Sessions DynamoDB table name"
  value       = aws_dynamodb_table.sessions.name
}

output "dynamodb_inventory_table" {
  description = "Inventory DynamoDB table name"
  value       = aws_dynamodb_table.inventory.name
}
