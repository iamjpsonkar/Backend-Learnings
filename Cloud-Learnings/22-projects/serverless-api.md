← [Previous: Static Website](./static-website.md) | [Home](../README.md) | [Next: Containerized API →](./containerized-api.md)

---

# Project: Serverless REST API

Build a production-grade REST API with user authentication, a DynamoDB backend, structured logging, and monitoring — all without managing any servers.

**Estimated cost:** ~$1–5/month at low traffic (Lambda + API Gateway + DynamoDB + Cognito)
**Time to complete:** 2–3 hours

---

## Architecture

```
Client
  │  HTTPS
  ▼
API Gateway (HTTP API)
  │  JWT authorizer
  ▼
Amazon Cognito (user pool)
  │  validates token → Lambda
  ▼
Lambda Functions
  ├── POST /orders   → create-order
  ├── GET  /orders   → list-orders
  ├── GET  /orders/{id} → get-order
  └── PATCH /orders/{id} → update-order
        │
        ▼
DynamoDB (single-table design)
  │
  └── CloudWatch Logs → Log Insights
```

---

## Step 1: Cognito User Pool

```bash
export APP="serverless-api"
export REGION="us-east-1"

# Create user pool
USER_POOL_ID=$(aws cognito-idp create-user-pool \
    --pool-name "${APP}-users" \
    --policies '{
        "PasswordPolicy": {
            "MinimumLength": 12,
            "RequireUppercase": true,
            "RequireLowercase": true,
            "RequireNumbers": true,
            "RequireSymbols": false
        }
    }' \
    --auto-verified-attributes email \
    --username-attributes email \
    --mfa-configuration OFF \
    --region $REGION \
    --query 'UserPool.Id' --output text)

# Create app client (no secret — SPA/mobile)
CLIENT_ID=$(aws cognito-idp create-user-pool-client \
    --user-pool-id $USER_POOL_ID \
    --client-name "${APP}-client" \
    --no-generate-secret \
    --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --token-validity-units '{"AccessToken":"hours","IdToken":"hours","RefreshToken":"days"}' \
    --access-token-validity 1 \
    --id-token-validity 1 \
    --refresh-token-validity 30 \
    --query 'UserPoolClient.ClientId' --output text)

echo "User Pool: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
```

---

## Step 2: DynamoDB Table (Single-Table Design)

```bash
# Single table: partition key = PK, sort key = SK
# Pattern: USER#{userId} / ORDER#{orderId}
aws dynamodb create-table \
    --table-name "${APP}-table" \
    --attribute-definitions \
        AttributeName=PK,AttributeType=S \
        AttributeName=SK,AttributeType=S \
        AttributeName=GSI1PK,AttributeType=S \
        AttributeName=GSI1SK,AttributeType=S \
    --key-schema \
        AttributeName=PK,KeyType=HASH \
        AttributeName=SK,KeyType=RANGE \
    --global-secondary-indexes '[{
        "IndexName": "GSI1",
        "KeySchema": [
            {"AttributeName": "GSI1PK", "KeyType": "HASH"},
            {"AttributeName": "GSI1SK", "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
    }]' \
    --billing-mode PAY_PER_REQUEST \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
    --sse-specification Enabled=true \
    --tags Key=project,Value=$APP \
    --region $REGION

aws dynamodb wait table-exists --table-name "${APP}-table" --region $REGION
echo "DynamoDB table ready"
```

---

## Step 3: Lambda Functions

```python
# src/orders/handler.py
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)


def _response(status_code: int, body: Any, request_id: str) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Request-Id": request_id,
        },
        "body": json.dumps(body),
    }


def _get_user_id(event: dict) -> str:
    """Extract user ID from Cognito JWT claims."""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    return claims.get("sub", "anonymous")


def create_order(event: dict, context) -> dict:
    request_id = context.aws_request_id
    user_id = _get_user_id(event)

    logger.info("Creating order", extra={"request_id": request_id, "user_id": user_id})

    try:
        body = json.loads(event.get("body") or "{}")
        items = body.get("items", [])

        if not items:
            return _response(400, {"error": "items is required"}, request_id)

        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        total = sum(i.get("price", 0) * i.get("quantity", 1) for i in items)

        order = {
            "PK": f"USER#{user_id}",
            "SK": f"ORDER#{order_id}",
            "GSI1PK": f"ORDER#{order_id}",
            "GSI1SK": f"ORDER#{order_id}",
            "order_id": order_id,
            "user_id": user_id,
            "items": items,
            "total": str(total),
            "status": "PENDING",
            "created_at": now,
            "updated_at": now,
        }

        table.put_item(Item=order)

        logger.info("Order created", extra={
            "request_id": request_id,
            "order_id": order_id,
            "user_id": user_id,
            "item_count": len(items),
            "total": str(total),
        })
        return _response(201, {"order_id": order_id, "status": "PENDING", "total": str(total)}, request_id)

    except Exception as exc:
        logger.error("Failed to create order", extra={
            "request_id": request_id, "error": str(exc),
        }, exc_info=True)
        return _response(500, {"error": "Internal server error"}, request_id)


def list_orders(event: dict, context) -> dict:
    request_id = context.aws_request_id
    user_id = _get_user_id(event)

    logger.info("Listing orders", extra={"request_id": request_id, "user_id": user_id})

    try:
        result = table.query(
            KeyConditionExpression=Key("PK").eq(f"USER#{user_id}") & Key("SK").begins_with("ORDER#"),
            ScanIndexForward=False,
            Limit=50,
        )
        orders = result.get("Items", [])

        logger.info("Orders listed", extra={
            "request_id": request_id, "user_id": user_id, "count": len(orders),
        })
        return _response(200, {"orders": orders, "count": len(orders)}, request_id)

    except Exception as exc:
        logger.error("Failed to list orders", extra={
            "request_id": request_id, "error": str(exc),
        }, exc_info=True)
        return _response(500, {"error": "Internal server error"}, request_id)


def get_order(event: dict, context) -> dict:
    request_id = context.aws_request_id
    user_id = _get_user_id(event)
    order_id = event.get("pathParameters", {}).get("id", "")

    logger.info("Getting order", extra={
        "request_id": request_id, "user_id": user_id, "order_id": order_id,
    })

    try:
        result = table.get_item(
            Key={"PK": f"USER#{user_id}", "SK": f"ORDER#{order_id}"}
        )
        item = result.get("Item")

        if not item:
            return _response(404, {"error": "Order not found"}, request_id)

        return _response(200, item, request_id)

    except Exception as exc:
        logger.error("Failed to get order", extra={
            "request_id": request_id, "order_id": order_id, "error": str(exc),
        }, exc_info=True)
        return _response(500, {"error": "Internal server error"}, request_id)
```

---

## Step 4: Deploy with Terraform

```hcl
# main.tf

module "lambda_create_order" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 6.0"

  function_name = "${var.app}-create-order"
  handler       = "orders.handler.create_order"
  runtime       = "python3.12"
  source_path   = "${path.module}/src"

  environment_variables = {
    TABLE_NAME   = aws_dynamodb_table.main.name
    LOG_LEVEL    = "INFO"
  }

  attach_policies    = true
  policies           = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
  attach_policy_json = true
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:UpdateItem"]
      Resource = [aws_dynamodb_table.main.arn, "${aws_dynamodb_table.main.arn}/index/*"]
    }]
  })

  cloudwatch_logs_retention_in_days = 14
  tracing_mode                      = "Active"  # X-Ray

  tags = { project = var.app }
}

resource "aws_apigatewayv2_api" "main" {
  name          = "${var.app}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["https://${var.frontend_domain}"]
    allow_methods = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
    allow_headers = ["Authorization", "Content-Type"]
    max_age       = 86400
  }
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-authorizer"

  jwt_configuration {
    audience = [var.cognito_client_id]
    issuer   = "https://cognito-idp.${var.region}.amazonaws.com/${var.cognito_user_pool_id}"
  }
}

resource "aws_apigatewayv2_route" "create_order" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /orders"
  target             = "integrations/${aws_apigatewayv2_integration.create_order.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "prod"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access_logs.arn
    format = jsonencode({
      requestId       = "$context.requestId"
      requestTime     = "$context.requestTime"
      httpMethod      = "$context.httpMethod"
      routeKey        = "$context.routeKey"
      status          = "$context.status"
      responseLatency = "$context.responseLatency"
      userId          = "$context.authorizer.claims.sub"
    })
  }
}
```

---

## Step 5: Test the API

```bash
# Register a user
aws cognito-idp sign-up \
    --client-id $CLIENT_ID \
    --username testuser@example.com \
    --password "TestPass123!" \
    --region $REGION

# Confirm sign-up (admin confirmation for testing)
aws cognito-idp admin-confirm-sign-up \
    --user-pool-id $USER_POOL_ID \
    --username testuser@example.com \
    --region $REGION

# Get tokens
TOKEN=$(aws cognito-idp initiate-auth \
    --client-id $CLIENT_ID \
    --auth-flow USER_PASSWORD_AUTH \
    --auth-parameters USERNAME=testuser@example.com,PASSWORD="TestPass123!" \
    --region $REGION \
    --query 'AuthenticationResult.IdToken' --output text)

API_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod"

# Create order
curl -sf -X POST "$API_URL/orders" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"items": [{"id": "item-1", "name": "Widget", "price": 9.99, "quantity": 2}]}'

# List orders
curl -sf "$API_URL/orders" \
    -H "Authorization: Bearer $TOKEN" | jq .
```

---

## Teardown

```bash
# Terraform destroy
terraform destroy -var-file=prod.tfvars

# If not using Terraform:
aws dynamodb delete-table --table-name "${APP}-table"
aws cognito-idp delete-user-pool --user-pool-id $USER_POOL_ID
# Delete Lambda functions and API Gateway via console or CLI
```

---

← [Previous: Static Website](./static-website.md) | [Home](../README.md) | [Next: Containerized API →](./containerized-api.md)
