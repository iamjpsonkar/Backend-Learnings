← [Previous: EventBridge](./eventbridge.md) | [Home](../../README.md) | [Next: AWS Security →](../09-security/README.md)

---

# AWS Step Functions

Step Functions is a serverless orchestration service that lets you build multi-step workflows as state machines. Each state in the machine can invoke Lambda, call AWS SDK actions directly, wait for events, branch, retry on failure, and run parallel tasks.

---

## Standard vs Express Workflows

| | Standard | Express |
|--|----------|---------|
| Execution duration | Up to 1 year | Up to 5 minutes |
| Execution model | At-most-once | At-least-once |
| Pricing | $0.025 per 1,000 state transitions | $1/million workflow requests + duration |
| Audit history | Full execution history in console | CloudWatch Logs only |
| Use for | Long-running workflows, human approval, exactly-once steps | High-volume IoT, streaming, short ETL |

---

## Amazon States Language (ASL) Basics

A state machine is defined in JSON (or YAML). Key state types:

| State type | Purpose |
|-----------|---------|
| `Task` | Call a service (Lambda, SDK, HTTP endpoint) |
| `Choice` | Branch based on condition |
| `Wait` | Pause for a duration or until a timestamp |
| `Parallel` | Run branches simultaneously |
| `Map` | Iterate over an array |
| `Pass` | Pass input to output (useful for testing) |
| `Succeed` | End execution successfully |
| `Fail` | End execution with an error |

---

## Creating a State Machine

### Simple Order Processing Workflow

```bash
# Create the state machine
SM_ARN=$(aws stepfunctions create-state-machine \
    --name OrderProcessingWorkflow \
    --type STANDARD \
    --role-arn arn:aws:iam::123456789012:role/StepFunctionsRole \
    --definition '{
        "Comment": "Order processing workflow",
        "StartAt": "ValidateOrder",
        "States": {
            "ValidateOrder": {
                "Type": "Task",
                "Resource": "arn:aws:lambda:us-east-1:123456789012:function:validate-order",
                "Retry": [{
                    "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException"],
                    "IntervalSeconds": 2,
                    "MaxAttempts": 3,
                    "BackoffRate": 2
                }],
                "Catch": [{
                    "ErrorEquals": ["ValidationError"],
                    "ResultPath": "$.error",
                    "Next": "OrderRejected"
                }],
                "Next": "CheckInventory"
            },
            "CheckInventory": {
                "Type": "Task",
                "Resource": "arn:aws:states:::dynamodb:getItem",
                "Parameters": {
                    "TableName": "Inventory",
                    "Key": {
                        "productId": {"S.$": "$.productId"}
                    }
                },
                "ResultPath": "$.inventory",
                "Next": "IsInStock"
            },
            "IsInStock": {
                "Type": "Choice",
                "Choices": [{
                    "Variable": "$.inventory.Item.quantity.N",
                    "NumericGreaterThan": 0,
                    "Next": "ProcessPayment"
                }],
                "Default": "BackorderItem"
            },
            "ProcessPayment": {
                "Type": "Task",
                "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-payment",
                "TimeoutSeconds": 30,
                "Retry": [{
                    "ErrorEquals": ["States.Timeout"],
                    "IntervalSeconds": 5,
                    "MaxAttempts": 2
                }],
                "Catch": [{
                    "ErrorEquals": ["PaymentDeclined"],
                    "ResultPath": "$.error",
                    "Next": "OrderRejected"
                }],
                "Next": "FulfillOrder"
            },
            "FulfillOrder": {
                "Type": "Parallel",
                "Branches": [
                    {
                        "StartAt": "ShipOrder",
                        "States": {
                            "ShipOrder": {
                                "Type": "Task",
                                "Resource": "arn:aws:lambda:us-east-1:123456789012:function:ship-order",
                                "End": true
                            }
                        }
                    },
                    {
                        "StartAt": "SendConfirmation",
                        "States": {
                            "SendConfirmation": {
                                "Type": "Task",
                                "Resource": "arn:aws:lambda:us-east-1:123456789012:function:send-email",
                                "End": true
                            }
                        }
                    }
                ],
                "ResultPath": "$.fulfillment",
                "Next": "OrderComplete"
            },
            "BackorderItem": {
                "Type": "Task",
                "Resource": "arn:aws:lambda:us-east-1:123456789012:function:handle-backorder",
                "End": true
            },
            "OrderComplete": {
                "Type": "Succeed"
            },
            "OrderRejected": {
                "Type": "Fail",
                "Error": "OrderRejected",
                "Cause": "Order could not be processed"
            }
        }
    }' \
    --query 'stateMachineArn' --output text)

echo "State machine: $SM_ARN"
```

---

## SDK Integrations (Direct AWS API Calls)

Step Functions can call 220+ AWS services directly without Lambda — reducing cost and latency.

```json
{
    "StartAt": "SendSQSMessage",
    "States": {
        "SendSQSMessage": {
            "Type": "Task",
            "Resource": "arn:aws:states:::sqs:sendMessage",
            "Parameters": {
                "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue",
                "MessageBody.$": "States.JsonToString($.payload)"
            },
            "Next": "PutDynamoDBItem"
        },
        "PutDynamoDBItem": {
            "Type": "Task",
            "Resource": "arn:aws:states:::dynamodb:putItem",
            "Parameters": {
                "TableName": "MyTable",
                "Item": {
                    "PK": {"S.$": "$.orderId"},
                    "SK": {"S": "STATUS"},
                    "status": {"S": "QUEUED"},
                    "timestamp": {"S.$": "$$.Execution.StartTime"}
                }
            },
            "Next": "PublishSNS"
        },
        "PublishSNS": {
            "Type": "Task",
            "Resource": "arn:aws:states:::sns:publish",
            "Parameters": {
                "TopicArn": "arn:aws:sns:us-east-1:123456789012:my-topic",
                "Message.$": "States.Format('Order {} processed', $.orderId)"
            },
            "End": true
        }
    }
}
```

---

## Map State (Parallel Iteration)

```json
{
    "ProcessOrderItems": {
        "Type": "Map",
        "ItemsPath": "$.items",
        "ItemSelector": {
            "item.$": "$$.Map.Item.Value",
            "orderId.$": "$.orderId",
            "index.$": "$$.Map.Item.Index"
        },
        "MaxConcurrency": 10,
        "Iterator": {
            "StartAt": "ProcessItem",
            "States": {
                "ProcessItem": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-item",
                    "Retry": [{
                        "ErrorEquals": ["States.TaskFailed"],
                        "IntervalSeconds": 1,
                        "MaxAttempts": 2
                    }],
                    "End": true
                }
            }
        },
        "ResultPath": "$.processedItems",
        "Next": "OrderComplete"
    }
}
```

---

## Wait for Callback (Human Approval / Async)

The `.waitForTaskToken` integration pauses execution until your code calls `SendTaskSuccess` or `SendTaskFailure` with the task token. Use this for human approval steps or long-running async operations.

```json
{
    "WaitForApproval": {
        "Type": "Task",
        "Resource": "arn:aws:states:::lambda:invoke.waitForTaskToken",
        "Parameters": {
            "FunctionName": "send-approval-email",
            "Payload": {
                "taskToken.$": "$$.Task.Token",
                "orderId.$": "$.orderId",
                "approvalUrl.$": "States.Format('https://api.example.com/approve?token={}', $$.Task.Token)"
            }
        },
        "HeartbeatSeconds": 3600,
        "TimeoutSeconds": 86400,
        "Next": "ProcessApproval"
    }
}
```

```python
# In your approval endpoint Lambda, call back to Step Functions:
import boto3
import logging

logger = logging.getLogger(__name__)
sfn = boto3.client("stepfunctions")


def handle_approval(task_token: str, approved: bool, reviewer: str) -> None:
    """Complete the Step Functions wait-for-callback state."""
    logger.info("Processing approval: approved=%s reviewer=%s", approved, reviewer)
    try:
        if approved:
            sfn.send_task_success(
                taskToken=task_token,
                output=f'{{"approved": true, "reviewer": "{reviewer}"}}',
            )
            logger.info("Task approved: reviewer=%s", reviewer)
        else:
            sfn.send_task_failure(
                taskToken=task_token,
                error="ApprovalDenied",
                cause=f"Rejected by {reviewer}",
            )
            logger.info("Task rejected: reviewer=%s", reviewer)
    except Exception as e:
        logger.error("Failed to send task result: error=%s", str(e))
        raise
```

---

## Error Handling

Every `Task` state should have `Retry` and `Catch` configured.

```json
{
    "ProcessOrder": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-order",
        "Retry": [
            {
                "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
                "IntervalSeconds": 2,
                "MaxAttempts": 3,
                "BackoffRate": 2,
                "JitterStrategy": "FULL"
            },
            {
                "ErrorEquals": ["States.Timeout"],
                "IntervalSeconds": 5,
                "MaxAttempts": 2,
                "BackoffRate": 1
            }
        ],
        "Catch": [
            {
                "ErrorEquals": ["PaymentDeclined"],
                "ResultPath": "$.error",
                "Next": "HandleDecline"
            },
            {
                "ErrorEquals": ["States.ALL"],
                "ResultPath": "$.error",
                "Next": "WorkflowFailed"
            }
        ],
        "TimeoutSeconds": 60,
        "Next": "OrderComplete"
    }
}
```

Common `ErrorEquals` values:

| Error | Meaning |
|-------|---------|
| `States.ALL` | Catch all errors |
| `States.Timeout` | Task exceeded TimeoutSeconds |
| `States.TaskFailed` | Task returned a failure |
| `States.HeartbeatTimeout` | No heartbeat received |
| `Lambda.ServiceException` | Lambda service error |
| `Lambda.AWSLambdaException` | Lambda function error |
| Your custom error | Your Lambda raised an exception with this name |

---

## Starting and Monitoring Executions

```bash
SM_ARN="arn:aws:states:us-east-1:123456789012:stateMachine:OrderProcessingWorkflow"

# Start an execution
EXEC_ARN=$(aws stepfunctions start-execution \
    --state-machine-arn $SM_ARN \
    --name "order-ORD-001-$(date +%s)" \
    --input '{"orderId": "ORD-001", "productId": "PROD-42", "quantity": 2}' \
    --query 'executionArn' --output text)

echo "Execution: $EXEC_ARN"

# Check execution status
aws stepfunctions describe-execution \
    --execution-arn $EXEC_ARN \
    --query '{Status:status,StartTime:startDate,StopTime:stopDate,Output:output}'

# View execution history (step-by-step)
aws stepfunctions get-execution-history \
    --execution-arn $EXEC_ARN \
    --query 'events[*].{Time:timestamp,Type:type,Details:stateEnteredEventDetails}' \
    --output table

# List recent executions for a state machine
aws stepfunctions list-executions \
    --state-machine-arn $SM_ARN \
    --status-filter FAILED \
    --max-results 20 \
    --query 'executions[*].{Name:name,Status:status,Start:startDate}' \
    --output table

# For Express workflows: list executions from CloudWatch Logs
aws logs filter-log-events \
    --log-group-name /aws/states/OrderProcessingWorkflow \
    --filter-pattern '"status": "FAILED"' \
    --start-time $(($(date +%s) - 3600))000   # last 1 hour
```

---

## IAM Role for Step Functions

```bash
# Create the execution role
SF_ROLE_ARN=$(aws iam create-role \
    --role-name StepFunctionsRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "states.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' \
    --query 'Role.Arn' --output text)

aws iam put-role-policy \
    --role-name StepFunctionsRole \
    --policy-name step-functions-permissions \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": "arn:aws:lambda:us-east-1:123456789012:function:*"
            },
            {
                "Effect": "Allow",
                "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"],
                "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/*"
            },
            {
                "Effect": "Allow",
                "Action": "sqs:SendMessage",
                "Resource": "arn:aws:sqs:us-east-1:123456789012:*"
            },
            {
                "Effect": "Allow",
                "Action": "sns:Publish",
                "Resource": "arn:aws:sns:us-east-1:123456789012:*"
            },
            {
                "Effect": "Allow",
                "Action": ["logs:CreateLogGroup", "logs:CreateLogDelivery", "logs:PutLogEvents"],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": "xray:PutTraceSegments",
                "Resource": "*"
            }
        ]
    }'
```

---

## References

- [Step Functions documentation](https://docs.aws.amazon.com/step-functions/latest/dg/)
- [Amazon States Language reference](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-amazon-states-language.html)
- [SDK integrations](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-service-integrations.html)
- [Step Functions pricing](https://aws.amazon.com/step-functions/pricing/)
- [Workflow Studio](https://docs.aws.amazon.com/step-functions/latest/dg/workflow-studio.html) — visual state machine designer in the console
---

← [Previous: EventBridge](./eventbridge.md) | [Home](../../README.md) | [Next: AWS Security →](../09-security/README.md)
