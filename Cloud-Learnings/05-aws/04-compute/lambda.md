← [Previous: Load Balancers](./load-balancers.md) | [Home](../../README.md) | [Next: AWS Storage →](../05-storage/README.md)

---

# AWS Lambda

Lambda is a serverless compute service that runs your code in response to events without provisioning or managing servers. You pay only for the compute time consumed (in 1ms increments).

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Function** | Your code + runtime + configuration |
| **Handler** | Entry point function called by Lambda |
| **Runtime** | Language environment (Python 3.12, Node.js 20, Java 21, etc.) |
| **Execution role** | IAM role granting the function permissions to call AWS services |
| **Event source** | The trigger that invokes the function (API Gateway, SQS, EventBridge, etc.) |
| **Invocation model** | Synchronous (request/response), asynchronous (fire-and-forget), stream-based |
| **Concurrency** | Number of function instances running simultaneously |
| **Cold start** | Delay when Lambda initializes a new execution environment |
| **Layer** | Shared code/dependencies published separately and attached to functions |

---

## Pricing

- **Requests**: $0.20 per 1 million requests
- **Duration**: $0.0000166667 per GB-second
- **Free tier**: 1M requests + 400,000 GB-seconds per month (permanent)

Example: 128MB function running 100ms, 10M times/month:
- Requests: 10M × $0.20/1M = $2.00
- Duration: 10M × 0.1s × 0.125GB × $0.0000166667 = $2.08
- **Total: ~$4.08/month**

---

## Creating a Lambda Function

### From a Zip File

```bash
ROLE_ARN="arn:aws:iam::123456789012:role/my-lambda-role"

# Create function.py
cat > /tmp/function.py << 'EOF'
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Lambda handler — entry point for all invocations.
    """
    logger.info("Invocation started: request_id=%s", context.aws_request_id)
    logger.debug("Event: %s", json.dumps(event))

    try:
        name = event.get("name", "World")
        response = {"message": f"Hello, {name}!"}
        logger.info("Processed successfully: response=%s", response)
        return {
            "statusCode": 200,
            "body": json.dumps(response)
        }
    except Exception as e:
        logger.error("Handler failed: error=%s", str(e), exc_info=True)
        raise
EOF

# Package and deploy
cd /tmp && zip function.zip function.py

FUNC_ARN=$(aws lambda create-function \
    --function-name my-hello-function \
    --runtime python3.12 \
    --role $ROLE_ARN \
    --handler function.handler \
    --zip-file fileb:///tmp/function.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment Variables='{LOG_LEVEL=INFO,ENVIRONMENT=production}' \
    --tags Environment=production,Team=platform \
    --description "Hello world Lambda function" \
    --query 'FunctionArn' --output text)

echo "Function ARN: $FUNC_ARN"

# Test it immediately
aws lambda invoke \
    --function-name my-hello-function \
    --payload '{"name": "Alice"}' \
    --cli-binary-format raw-in-base64-out \
    /tmp/response.json && cat /tmp/response.json
```

### From an ECR Container Image

```bash
# Build and push container image
docker build -t my-lambda-function .
docker tag my-lambda-function 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda:latest
aws ecr get-login-password | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda:latest

# Create function from container image
aws lambda create-function \
    --function-name my-container-function \
    --package-type Image \
    --role $ROLE_ARN \
    --code ImageUri=123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda:latest \
    --timeout 60 \
    --memory-size 512 \
    --architectures arm64   # Graviton2 — same performance, 20% cheaper
```

---

## IAM Execution Role

```bash
# Create the execution role
ROLE_ARN=$(aws iam create-role \
    --role-name my-lambda-role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' \
    --query 'Role.Arn' --output text)

# Attach basic execution policy (CloudWatch Logs)
aws iam attach-role-policy \
    --role-name my-lambda-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Attach VPC execution policy (if function runs in VPC)
aws iam attach-role-policy \
    --role-name my-lambda-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole

# Add permissions for specific AWS services
aws iam put-role-policy \
    --role-name my-lambda-role \
    --policy-name app-permissions \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
                "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/my-table"
            },
            {
                "Effect": "Allow",
                "Action": "secretsmanager:GetSecretValue",
                "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-app/*"
            },
            {
                "Effect": "Allow",
                "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
                "Resource": "arn:aws:sqs:us-east-1:123456789012:my-queue"
            }
        ]
    }'
```

---

## Triggers (Event Sources)

### API Gateway (Synchronous)

```bash
# Create HTTP API (API Gateway v2 — lower cost, simpler)
API_ID=$(aws apigatewayv2 create-api \
    --name my-lambda-api \
    --protocol-type HTTP \
    --query 'ApiId' --output text)

# Create Lambda integration
INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id $API_ID \
    --integration-type AWS_PROXY \
    --integration-uri $FUNC_ARN \
    --payload-format-version 2.0 \
    --query 'IntegrationId' --output text)

# Create route
aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key "GET /hello" \
    --target integrations/$INTEGRATION_ID

# Deploy to a stage
aws apigatewayv2 create-stage \
    --api-id $API_ID \
    --stage-name prod \
    --auto-deploy

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
    --function-name my-hello-function \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:us-east-1:123456789012:$API_ID/*"
```

### SQS (Asynchronous — Batch Processing)

```bash
QUEUE_URL="https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
QUEUE_ARN="arn:aws:sqs:us-east-1:123456789012:my-queue"

# Create event source mapping
aws lambda create-event-source-mapping \
    --function-name my-processor-function \
    --event-source-arn $QUEUE_ARN \
    --batch-size 10 \
    --maximum-batching-window-in-seconds 5 \
    --function-response-types ReportBatchItemFailures \
    --scaling-config MaximumConcurrency=50
```

The function receives a batch and should report partial failures:

```python
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    SQS batch processor with partial failure support.
    Returns failed message IDs so they are retried without re-processing successes.
    """
    logger.info("Processing SQS batch: message_count=%d", len(event["Records"]))
    batch_item_failures = []

    for record in event["Records"]:
        message_id = record["messageId"]
        try:
            body = json.loads(record["body"])
            logger.info("Processing message: message_id=%s body_keys=%s", message_id, list(body.keys()))
            process_message(body)
            logger.info("Message processed successfully: message_id=%s", message_id)
        except Exception as e:
            logger.error("Failed to process message: message_id=%s error=%s", message_id, str(e), exc_info=True)
            batch_item_failures.append({"itemIdentifier": message_id})

    logger.info("Batch complete: total=%d failures=%d", len(event["Records"]), len(batch_item_failures))
    return {"batchItemFailures": batch_item_failures}

def process_message(body):
    # Your processing logic here
    pass
```

### EventBridge (Scheduled / Event-Driven)

```bash
# Create a scheduled rule (run every 5 minutes)
RULE_ARN=$(aws events put-rule \
    --name my-function-schedule \
    --schedule-expression "rate(5 minutes)" \
    --state ENABLED \
    --query 'RuleArn' --output text)

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
    --function-name my-hello-function \
    --statement-id eventbridge-invoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn $RULE_ARN

# Set Lambda as the target
aws events put-targets \
    --rule my-function-schedule \
    --targets Id=1,Arn=$FUNC_ARN
```

---

## Concurrency

Lambda concurrency = the number of function instances running simultaneously.

| Type | Description | Use |
|------|-------------|-----|
| **Unreserved** | Shared from account-level pool (default 1,000) | General use |
| **Reserved** | Dedicated to this function; reduces pool for others | Protect downstream services |
| **Provisioned** | Pre-initialized instances; eliminates cold starts | Latency-sensitive APIs |

```bash
FUNC_NAME="my-hello-function"

# View current account-level concurrency limits
aws lambda get-account-settings \
    --query '{TotalConcurrency:AccountLimit.ConcurrentExecutions,UnreservedConcurrency:AccountLimit.UnreservedConcurrentExecutions}'

# Reserve concurrency for a function (cap it at 50)
aws lambda put-function-concurrency \
    --function-name $FUNC_NAME \
    --reserved-concurrent-executions 50

# Remove reservation (return to shared pool)
aws lambda delete-function-concurrency --function-name $FUNC_NAME

# Provision concurrency (eliminates cold starts — charged per hour)
aws lambda put-provisioned-concurrency-config \
    --function-name $FUNC_NAME \
    --qualifier prod \
    --provisioned-concurrent-executions 5

# View concurrency configuration
aws lambda get-function-concurrency --function-name $FUNC_NAME
```

---

## Layers (Shared Dependencies)

Layers allow you to share libraries and code across multiple functions without packaging them in each deployment.

```bash
# Package the layer
mkdir -p /tmp/layer/python
pip install requests boto3-stubs -t /tmp/layer/python/
cd /tmp/layer && zip -r layer.zip python/

# Publish the layer
LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name common-dependencies \
    --description "Shared Python dependencies" \
    --zip-file fileb:///tmp/layer/layer.zip \
    --compatible-runtimes python3.12 python3.11 \
    --query 'LayerVersionArn' --output text)

echo "Layer ARN: $LAYER_ARN"

# Attach the layer to a function
aws lambda update-function-configuration \
    --function-name $FUNC_NAME \
    --layers $LAYER_ARN
```

---

## VPC Configuration

Lambda functions can run inside a VPC to access RDS, ElastiCache, or other private resources.

```bash
# Configure function to run in a VPC
aws lambda update-function-configuration \
    --function-name $FUNC_NAME \
    --vpc-config SubnetIds=subnet-priv-1a,subnet-priv-1b,SecurityGroupIds=sg-lambda

# The function's IAM role needs AWSLambdaVPCAccessExecutionRole
# Lambda creates ENIs in the specified subnets
# Ensure the subnet has enough free IP addresses (one ENI per concurrent execution in older model)
# Modern Lambda uses Hyperplane ENIs — shared across functions in the same VPC/SG/subnet combo
```

---

## Function URLs (Direct HTTPS Endpoint)

```bash
# Create a function URL (no API Gateway needed for simple cases)
FUNC_URL=$(aws lambda create-function-url-config \
    --function-name $FUNC_NAME \
    --auth-type NONE \
    --cors '{
        "AllowOrigins": ["https://example.com"],
        "AllowMethods": ["GET", "POST"],
        "AllowHeaders": ["Content-Type"]
    }' \
    --query 'FunctionUrl' --output text)

echo "Function URL: $FUNC_URL"

# For auth type AWS_IAM (requires SigV4 signing)
aws lambda create-function-url-config \
    --function-name $FUNC_NAME \
    --auth-type AWS_IAM
```

---

## Updating and Versioning

```bash
FUNC_NAME="my-hello-function"

# Update function code
zip -j /tmp/function.zip /tmp/function.py
aws lambda update-function-code \
    --function-name $FUNC_NAME \
    --zip-file fileb:///tmp/function.zip

# Wait for update to complete
aws lambda wait function-updated --function-name $FUNC_NAME

# Publish an immutable version
VERSION=$(aws lambda publish-version \
    --function-name $FUNC_NAME \
    --description "v1.2.3 — add retry logic" \
    --query 'Version' --output text)

echo "Published version: $VERSION"

# Create an alias pointing to the version (stable reference for event sources)
aws lambda create-alias \
    --function-name $FUNC_NAME \
    --name prod \
    --function-version $VERSION \
    --description "Production alias"

# Update alias to new version (zero-downtime promotion)
aws lambda update-alias \
    --function-name $FUNC_NAME \
    --name prod \
    --function-version $VERSION

# Canary deployment: 90% prod, 10% new version
NEW_VERSION="5"
aws lambda update-alias \
    --function-name $FUNC_NAME \
    --name prod \
    --function-version $NEW_VERSION \
    --routing-config AdditionalVersionWeights={\"4\"=0.9}
```

---

## Monitoring and Debugging

```bash
FUNC_NAME="my-hello-function"

# View CloudWatch log group
LOG_GROUP="/aws/lambda/$FUNC_NAME"

# Get recent log events
aws logs tail $LOG_GROUP --since 1h --follow

# View function metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Errors \
    --dimensions Name=FunctionName,Value=$FUNC_NAME \
    --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum \
    --output table

# Key Lambda metrics to monitor:
# Invocations       — total calls
# Errors            — invocations that returned an error
# Throttles         — requests rejected due to concurrency limit
# Duration          — execution time (P50/P99 most useful)
# ConcurrentExecutions — peak concurrency
# InitDuration      — cold start time (in X-Ray traces)

# Enable active tracing (X-Ray)
aws lambda update-function-configuration \
    --function-name $FUNC_NAME \
    --tracing-config Mode=Active
```

---

## Cold Start Mitigation

| Strategy | Trade-off |
|----------|-----------|
| Provisioned Concurrency | Eliminates cold starts; billed per hour |
| Smaller deployment package | Faster initialization |
| Lazy imports (load modules only when needed) | Reduces init time |
| Graviton2 (arm64) | Faster init for most runtimes |
| Use Python/Node over Java/JVM | Java has the highest cold start times |
| Keep functions warm with EventBridge ping | Unreliable; use Provisioned Concurrency instead |

---

## References

- [Lambda documentation](https://docs.aws.amazon.com/lambda/latest/dg/)
- [Lambda event source mappings](https://docs.aws.amazon.com/lambda/latest/dg/invocation-eventsourcemapping.html)
- [Lambda concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)
- [Lambda performance tuning](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
---

← [Previous: Load Balancers](./load-balancers.md) | [Home](../../README.md) | [Next: AWS Storage →](../05-storage/README.md)
