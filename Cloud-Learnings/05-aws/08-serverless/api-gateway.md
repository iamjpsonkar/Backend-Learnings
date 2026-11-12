← [Previous: AWS Serverless](./README.md) | [Home](../../README.md) | [Next: SQS & SNS →](./sqs-sns.md)

---

# Amazon API Gateway

API Gateway is a fully managed service for creating, deploying, and managing APIs at any scale. It supports REST APIs (v1), HTTP APIs (v2), and WebSocket APIs.

---

## REST API vs HTTP API

| | REST API (v1) | HTTP API (v2) |
|--|--------------|--------------|
| Latency | ~6ms | ~1ms |
| Cost | $3.50/million requests | $1.00/million requests |
| Lambda integration | Proxy + custom | Proxy only (v2 format) |
| Authorizers | Lambda, Cognito, IAM | Lambda, JWT (built-in) |
| Usage plans + API keys | Yes | No |
| Request/response transforms | Yes (Velocity templates) | No |
| Private integrations | Yes | Yes |
| WebSocket | Separate API type | No |
| **Choose when** | Need transformations, API keys, fine-grained control | Default for new Lambda/HTTP APIs |

---

## HTTP API (v2) — Recommended

### Create an HTTP API with Lambda Integration

```bash
FUNC_ARN="arn:aws:lambda:us-east-1:123456789012:function:my-api-function"

# Create the HTTP API
API_ID=$(aws apigatewayv2 create-api \
    --name my-http-api \
    --protocol-type HTTP \
    --cors-configuration \
        AllowOrigins="https://example.com","https://app.example.com" \
        AllowMethods="GET","POST","PUT","DELETE","OPTIONS" \
        AllowHeaders="Content-Type","Authorization","X-Api-Key" \
        MaxAge=86400 \
    --tags Environment=production \
    --query 'ApiId' --output text)

echo "API ID: $API_ID"

# Create Lambda integration
INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id $API_ID \
    --integration-type AWS_PROXY \
    --integration-uri $FUNC_ARN \
    --integration-method POST \
    --payload-format-version 2.0 \
    --query 'IntegrationId' --output text)

# Create routes
for ROUTE in "GET /users" "POST /users" "GET /users/{userId}" "PUT /users/{userId}" "DELETE /users/{userId}"; do
    aws apigatewayv2 create-route \
        --api-id $API_ID \
        --route-key "$ROUTE" \
        --target integrations/$INTEGRATION_ID
done

# Deploy to a stage
aws apigatewayv2 create-stage \
    --api-id $API_ID \
    --stage-name prod \
    --auto-deploy \
    --access-log-settings '{
        "DestinationArn": "arn:aws:logs:us-east-1:123456789012:log-group:/api/my-http-api",
        "Format": "$context.requestId $context.httpMethod $context.routeKey $context.status $context.responseLength $context.integrationErrorMessage"
    }'

# Get the invoke URL
API_URL=$(aws apigatewayv2 get-api \
    --api-id $API_ID \
    --query 'ApiEndpoint' --output text)

echo "API URL: $API_URL/prod"

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
    --function-name my-api-function \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:us-east-1:123456789012:$API_ID/*/*"
```

### JWT Authorizer

HTTP APIs support native JWT authorizers without Lambda — validate tokens using an OIDC or Cognito issuer.

```bash
# Create a JWT authorizer (validate tokens against Cognito or any OIDC provider)
AUTHORIZER_ID=$(aws apigatewayv2 create-authorizer \
    --api-id $API_ID \
    --authorizer-type JWT \
    --name jwt-authorizer \
    --identity-source '$request.header.Authorization' \
    --jwt-configuration '{
        "Audience": ["my-app-client-id"],
        "Issuer": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXXX"
    }' \
    --query 'AuthorizerId' --output text)

# Protect routes with the authorizer
aws apigatewayv2 update-route \
    --api-id $API_ID \
    --route-id $(aws apigatewayv2 get-routes --api-id $API_ID \
        --query 'Items[?RouteKey==`GET /users`].RouteId' --output text) \
    --authorization-type JWT \
    --authorizer-id $AUTHORIZER_ID \
    --authorization-scopes openid email profile
```

### Lambda Authorizer (Custom Auth)

```bash
# Create a Lambda authorizer for custom token validation
AUTH_FUNC_ARN="arn:aws:lambda:us-east-1:123456789012:function:my-authorizer"

AUTHORIZER_ID=$(aws apigatewayv2 create-authorizer \
    --api-id $API_ID \
    --authorizer-type REQUEST \
    --name lambda-authorizer \
    --identity-source '$request.header.Authorization' \
    --authorizer-uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/$AUTH_FUNC_ARN/invocations" \
    --authorizer-payload-format-version 2.0 \
    --enable-simple-responses \
    --authorizer-result-ttl-in-seconds 300 \
    --query 'AuthorizerId' --output text)
```

Lambda authorizer function returning simple response:

```python
import logging

logger = logging.getLogger(__name__)

def handler(event, context):
    """
    HTTP API Lambda authorizer — simple response format.
    Returns isAuthorized boolean + context dict passed to Lambda.
    """
    token = event.get("headers", {}).get("authorization", "")
    route_arn = event.get("routeArn", "")
    request_id = context.aws_request_id

    logger.info("Authorizer invoked: route=%s request_id=%s", route_arn, request_id)

    if not token.startswith("Bearer "):
        logger.warning("Missing or malformed token: request_id=%s", request_id)
        return {"isAuthorized": False}

    raw_token = token[7:]

    try:
        claims = validate_jwt(raw_token)    # your JWT validation logic
        user_id = claims["sub"]
        logger.info("Authorization granted: user_id=%s route=%s", user_id, route_arn)
        return {
            "isAuthorized": True,
            "context": {
                "userId": user_id,
                "email": claims.get("email", ""),
                "scopes": claims.get("scope", ""),
            }
        }
    except Exception as e:
        logger.warning("Authorization denied: error=%s request_id=%s", str(e), request_id)
        return {"isAuthorized": False}


def validate_jwt(token: str) -> dict:
    # Implement: decode + verify signature against JWKS, check expiry, audience, issuer
    raise NotImplementedError
```

---

## REST API (v1) — Key Features

### Create a REST API with Usage Plan

```bash
# Create REST API
REST_API_ID=$(aws apigateway create-rest-api \
    --name my-rest-api \
    --description "My REST API with usage plans" \
    --endpoint-configuration types=REGIONAL \
    --query 'id' --output text)

# Get root resource ID
ROOT_ID=$(aws apigateway get-resources \
    --rest-api-id $REST_API_ID \
    --query 'items[?path==`/`].id' --output text)

# Create /items resource
RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $REST_API_ID \
    --parent-id $ROOT_ID \
    --path-part items \
    --query 'id' --output text)

# Create GET method on /items
aws apigateway put-method \
    --rest-api-id $REST_API_ID \
    --resource-id $RESOURCE_ID \
    --http-method GET \
    --authorization-type NONE \
    --api-key-required

# Lambda integration
aws apigateway put-integration \
    --rest-api-id $REST_API_ID \
    --resource-id $RESOURCE_ID \
    --http-method GET \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/$FUNC_ARN/invocations"

# Deploy to prod stage
aws apigateway create-deployment \
    --rest-api-id $REST_API_ID \
    --stage-name prod \
    --description "Initial production deployment"

# Create API key
API_KEY_ID=$(aws apigateway create-api-key \
    --name my-client-key \
    --enabled \
    --query 'id' --output text)

API_KEY_VALUE=$(aws apigateway get-api-key \
    --api-key $API_KEY_ID \
    --include-value \
    --query 'value' --output text)

echo "API Key: $API_KEY_VALUE"

# Create usage plan (rate limiting)
PLAN_ID=$(aws apigateway create-usage-plan \
    --name standard-plan \
    --description "Standard rate limits" \
    --api-stages apiId=$REST_API_ID,stage=prod \
    --throttle burstLimit=200,rateLimit=100 \
    --quota limit=10000,period=DAY \
    --query 'id' --output text)

# Associate API key with usage plan
aws apigateway create-usage-plan-key \
    --usage-plan-id $PLAN_ID \
    --key-id $API_KEY_ID \
    --key-type API_KEY
```

---

## WebSocket API

WebSocket APIs enable persistent two-way communication between clients and backend, ideal for chat, real-time dashboards, and gaming.

```bash
# Create WebSocket API
WS_API_ID=$(aws apigatewayv2 create-api \
    --name my-websocket-api \
    --protocol-type WEBSOCKET \
    --route-selection-expression '$request.body.action' \
    --query 'ApiId' --output text)

# Create routes: $connect, $disconnect, sendMessage
for ROUTE in '$connect' '$disconnect' 'sendMessage'; do
    INTEGRATION_ID=$(aws apigatewayv2 create-integration \
        --api-id $WS_API_ID \
        --integration-type AWS_PROXY \
        --integration-uri $FUNC_ARN \
        --query 'IntegrationId' --output text)

    aws apigatewayv2 create-route \
        --api-id $WS_API_ID \
        --route-key "$ROUTE" \
        --target integrations/$INTEGRATION_ID
done

aws apigatewayv2 create-stage \
    --api-id $WS_API_ID \
    --stage-name prod \
    --auto-deploy
```

Lambda pushing messages to connected clients:

```python
import boto3
import logging

logger = logging.getLogger(__name__)

def send_to_client(connection_id: str, data: dict, api_id: str, stage: str) -> None:
    """Push a message to a specific WebSocket connection."""
    gateway_client = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=f"https://{api_id}.execute-api.us-east-1.amazonaws.com/{stage}",
    )
    logger.info("Sending WebSocket message: connection_id=%s", connection_id)
    try:
        gateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=__import__("json").dumps(data).encode(),
        )
        logger.debug("Message sent: connection_id=%s", connection_id)
    except gateway_client.exceptions.GoneException:
        logger.warning("Connection stale, removing: connection_id=%s", connection_id)
        # Remove stale connection from your connection store (DynamoDB, etc.)
```

---

## Custom Domain Names

```bash
# Create custom domain with ACM certificate
DOMAIN="api.example.com"
CERT_ARN="arn:aws:acm:us-east-1:123456789012:certificate/abc123"

aws apigatewayv2 create-domain-name \
    --domain-name $DOMAIN \
    --domain-name-configurations CertificateArn=$CERT_ARN,EndpointType=REGIONAL

# Map the domain to the API + stage
aws apigatewayv2 create-api-mapping \
    --domain-name $DOMAIN \
    --api-id $API_ID \
    --stage prod \
    --api-mapping-key ""    # empty = root mapping

# Get the Route 53 alias target
aws apigatewayv2 get-domain-name \
    --domain-name $DOMAIN \
    --query 'DomainNameConfigurations[0].{Target:ApiGatewayDomainName,HostedZoneId:HostedZoneId}'
```

---

## Access Logging and Monitoring

```bash
# Enable CloudWatch access logs for HTTP API stage
LOG_GROUP_ARN=$(aws logs create-log-group \
    --log-group-name /api/my-http-api \
    --query 'logGroupName' --output text)

aws apigatewayv2 update-stage \
    --api-id $API_ID \
    --stage-name prod \
    --access-log-settings \
        DestinationArn="arn:aws:logs:us-east-1:123456789012:log-group:/api/my-http-api" \
        Format='$context.requestId $context.httpMethod $context.routeKey $context.status $context.responseLength $context.integrationErrorMessage $context.authorizer.error'

# Key API Gateway CloudWatch metrics:
# Count          — total requests
# 4XXError       — client errors
# 5XXError       — server/integration errors
# Latency        — total request time
# IntegrationLatency — time for Lambda/backend to respond

aws cloudwatch put-metric-alarm \
    --alarm-name api-5xx-errors \
    --namespace AWS/ApiGateway \
    --metric-name 5XXError \
    --dimensions Name=ApiId,Value=$API_ID Name=Stage,Value=prod \
    --statistic Sum \
    --period 60 \
    --evaluation-periods 2 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts
```

---

## References

- [HTTP API documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [REST API documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-rest-api.html)
- [WebSocket API](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html)
- [API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/)
---

← [Previous: AWS Serverless](./README.md) | [Home](../../README.md) | [Next: SQS & SNS →](./sqs-sns.md)
