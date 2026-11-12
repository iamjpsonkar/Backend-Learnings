← [Previous: SQS & SNS](./sqs-sns.md) | [Home](../../README.md) | [Next: Step Functions →](./step-functions.md)

---

# Amazon EventBridge

EventBridge is a serverless event bus that routes events between AWS services, custom applications, and SaaS partners. It replaces CloudWatch Events and adds custom event buses, schema registry, Pipes, and Scheduler.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Event bus** | Channel that receives events. Default bus receives AWS service events. Custom buses receive your events. |
| **Rule** | Matches events on a bus and routes them to one or more targets |
| **Event pattern** | JSON filter applied to events — matched events trigger the rule |
| **Target** | Where matched events are sent (Lambda, SQS, SNS, Step Functions, API Gateway, etc.) |
| **EventBridge Pipes** | Point-to-point integration: source → filtering/enrichment → target (no fan-out) |
| **EventBridge Scheduler** | Create one-time or recurring schedules to invoke targets |
| **Schema registry** | Discover, create, and generate code bindings for event schemas |

---

## Default Event Bus (AWS Service Events)

```bash
# View rules on the default event bus
aws events list-rules \
    --event-bus-name default \
    --query 'Rules[*].{Name:Name,State:State,Pattern:EventPattern}' \
    --output table

# Example: alert when any EC2 instance enters a terminated state
aws events put-rule \
    --name ec2-instance-terminated \
    --event-bus-name default \
    --event-pattern '{
        "source": ["aws.ec2"],
        "detail-type": ["EC2 Instance State-change Notification"],
        "detail": {
            "state": ["terminated"]
        }
    }' \
    --state ENABLED \
    --description "Alert when EC2 instances are terminated"

# Add SNS target
aws events put-targets \
    --rule ec2-instance-terminated \
    --event-bus-name default \
    --targets Id=1,Arn=arn:aws:sns:us-east-1:123456789012:ops-alerts

# Grant EventBridge permission to invoke SNS
# (For SNS, EventBridge uses resource-based policy — grant via SNS policy)
```

---

## Custom Event Bus

```bash
# Create a custom event bus for your application
BUS_ARN=$(aws events create-event-bus \
    --name my-app-events \
    --tags Environment=production \
    --query 'EventBusArn' --output text)

echo "Event bus: $BUS_ARN"

# Grant another account permission to publish to this bus
aws events put-permission \
    --event-bus-name my-app-events \
    --action events:PutEvents \
    --principal 222222222222 \
    --statement-id allow-account-222

# Or grant entire org
aws events put-permission \
    --event-bus-name my-app-events \
    --action events:PutEvents \
    --principal "*" \
    --statement-id allow-org \
    --condition Type=StringEquals,Key=aws:PrincipalOrgID,Value=o-abc12345

# List permissions on a bus
aws events describe-event-bus --name my-app-events --query 'Policy'
```

---

## Publishing Events

```bash
# Publish one or more events to a custom bus
aws events put-events \
    --entries '[
        {
            "EventBusName": "my-app-events",
            "Source": "my-app.orders",
            "DetailType": "OrderPlaced",
            "Detail": "{\"orderId\": \"ORD-001\", \"userId\": \"USER#alice\", \"total\": 99.99}",
            "Resources": ["arn:aws:dynamodb:us-east-1:123456789012:table/MyAppTable"]
        },
        {
            "EventBusName": "my-app-events",
            "Source": "my-app.payments",
            "DetailType": "PaymentProcessed",
            "Detail": "{\"orderId\": \"ORD-001\", \"status\": \"SUCCESS\", \"amount\": 99.99}"
        }
    ]'
```

Python publisher pattern:

```python
import boto3
import json
import time
import logging

logger = logging.getLogger(__name__)
events_client = boto3.client("events", region_name="us-east-1")

EVENT_BUS = "my-app-events"


def publish_event(source: str, detail_type: str, detail: dict) -> str:
    """
    Publish a single event to EventBridge.
    Returns the EventId on success.
    """
    logger.info("Publishing event: source=%s detail_type=%s", source, detail_type)
    try:
        response = events_client.put_events(
            Entries=[{
                "EventBusName": EVENT_BUS,
                "Source": source,
                "DetailType": detail_type,
                "Detail": json.dumps(detail),
                "Time": time.time(),
            }]
        )
        failed = response.get("FailedEntryCount", 0)
        if failed > 0:
            logger.error("Event publish failed: detail_type=%s failures=%d entries=%s",
                         detail_type, failed, response["Entries"])
            raise RuntimeError(f"EventBridge publish failed for {detail_type}")

        event_id = response["Entries"][0]["EventId"]
        logger.info("Event published: detail_type=%s event_id=%s", detail_type, event_id)
        return event_id
    except Exception as e:
        logger.error("Failed to publish event: source=%s detail_type=%s error=%s", source, detail_type, str(e))
        raise
```

---

## Rules and Event Patterns

### Pattern Examples

```json
// Match specific source and detail-type
{
    "source": ["my-app.orders"],
    "detail-type": ["OrderPlaced"]
}

// Match orders over $100 from premium users
{
    "source": ["my-app.orders"],
    "detail-type": ["OrderPlaced"],
    "detail": {
        "total": [{"numeric": [">", 100]}],
        "userTier": ["premium"]
    }
}

// Match any order event (multiple detail-types)
{
    "source": ["my-app.orders"],
    "detail-type": ["OrderPlaced", "OrderUpdated", "OrderCancelled"]
}

// Match any AWS API call that failed (CloudTrail events)
{
    "source": ["aws.cloudtrail"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
        "errorCode": [{"exists": true}]
    }
}

// Match events where a specific field does NOT exist
{
    "detail": {
        "debugFlag": [{"exists": false}]
    }
}
```

### Creating Rules with Multiple Targets

```bash
BUS="my-app-events"

# Rule: OrderPlaced → Lambda processor + SQS analytics queue
aws events put-rule \
    --name order-placed \
    --event-bus-name $BUS \
    --event-pattern '{"source":["my-app.orders"],"detail-type":["OrderPlaced"]}' \
    --state ENABLED

LAMBDA_ARN="arn:aws:lambda:us-east-1:123456789012:function:process-order"
SQS_ARN="arn:aws:sqs:us-east-1:123456789012:analytics-queue"

aws events put-targets \
    --rule order-placed \
    --event-bus-name $BUS \
    --targets \
        "Id=lambda-processor,Arn=$LAMBDA_ARN" \
        "Id=analytics-queue,Arn=$SQS_ARN"

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
    --function-name process-order \
    --statement-id eventbridge-invoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:us-east-1:123456789012:rule/my-app-events/order-placed"

# Transform the event before sending to SQS (input transformer)
aws events put-targets \
    --rule order-placed \
    --event-bus-name $BUS \
    --targets '[{
        "Id": "analytics-queue-transformed",
        "Arn": "'$SQS_ARN'",
        "InputTransformer": {
            "InputPathsMap": {
                "orderId": "$.detail.orderId",
                "total": "$.detail.total",
                "ts": "$.time"
            },
            "InputTemplate": "{\"event\": \"order_placed\", \"order_id\": \"<orderId>\", \"revenue\": <total>, \"timestamp\": \"<ts>\"}"
        }
    }]'
```

---

## EventBridge Pipes (Point-to-Point)

Pipes connect a source to a target with optional filtering and enrichment — no fan-out.

```
SQS Queue → [Filter] → [Enrichment Lambda] → Step Functions / Lambda / API GW
```

```bash
PIPE_ARN=$(aws pipes create-pipe \
    --name order-processing-pipe \
    --source arn:aws:sqs:us-east-1:123456789012:raw-orders-queue \
    --target arn:aws:states:us-east-1:123456789012:stateMachine:OrderWorkflow \
    --target-parameters '{
        "StepFunctionStateMachineParameters": {
            "InvocationType": "FIRE_AND_FORGET"
        }
    }' \
    --filter-criteria '{
        "Filters": [{
            "Pattern": "{\"body\": {\"status\": [\"PENDING\"]}}"
        }]
    }' \
    --enrichment arn:aws:lambda:us-east-1:123456789012:function:enrich-order \
    --role-arn arn:aws:iam::123456789012:role/PipeRole \
    --query 'Arn' --output text)

echo "Pipe: $PIPE_ARN"
```

---

## EventBridge Scheduler

Scheduler replaces EventBridge rate/cron rules for scheduling tasks. It is more flexible (timezone support, flexible windows, one-time schedules) and more cost-effective at scale.

```bash
# One-time schedule — run at a specific UTC time
aws scheduler create-schedule \
    --name send-weekly-report \
    --schedule-expression "at(2026-06-01T09:00:00)" \
    --schedule-expression-timezone "America/New_York" \
    --target '{
        "Arn": "arn:aws:lambda:us-east-1:123456789012:function:generate-report",
        "RoleArn": "arn:aws:iam::123456789012:role/SchedulerRole",
        "Input": "{\"report_type\": \"weekly\", \"period\": \"2026-W22\"}"
    }' \
    --flexible-time-window Mode=OFF

# Recurring cron schedule — daily at 08:00 UTC, every weekday
aws scheduler create-schedule \
    --name daily-digest \
    --schedule-expression "cron(0 8 ? * MON-FRI *)" \
    --schedule-expression-timezone "UTC" \
    --target '{
        "Arn": "arn:aws:sqs:us-east-1:123456789012:digest-queue",
        "RoleArn": "arn:aws:iam::123456789012:role/SchedulerRole",
        "Input": "{\"type\": \"daily_digest\"}"
    }' \
    --flexible-time-window Mode=FLEXIBLE,MaximumWindowInMinutes=15

# List schedules
aws scheduler list-schedules \
    --query 'Schedules[*].{Name:Name,State:State,Expression:ScheduleExpression}' \
    --output table

# Delete a schedule
aws scheduler delete-schedule --name send-weekly-report
```

---

## Monitoring and Debugging

```bash
# Dead-letter queue for failed event deliveries
aws events put-rule \
    --name order-placed \
    --event-bus-name my-app-events \
    --event-pattern '{"source":["my-app.orders"]}'

DLQ_ARN="arn:aws:sqs:us-east-1:123456789012:eventbridge-dlq"

aws events put-targets \
    --rule order-placed \
    --event-bus-name my-app-events \
    --targets '[{
        "Id": "lambda-processor",
        "Arn": "'$LAMBDA_ARN'",
        "RetryPolicy": {
            "MaximumRetryAttempts": 3,
            "MaximumEventAgeInSeconds": 3600
        },
        "DeadLetterConfig": {
            "Arn": "'$DLQ_ARN'"
        }
    }]'

# Key CloudWatch metrics for EventBridge:
# MatchedEvents    — events that matched a rule
# TriggeredRules   — rules that fired
# FailedInvocations — delivery failures
# ThrottledRules   — rules throttled

aws cloudwatch put-metric-alarm \
    --alarm-name eventbridge-failed-invocations \
    --namespace AWS/Events \
    --metric-name FailedInvocations \
    --dimensions Name=RuleName,Value=order-placed Name=EventBusName,Value=my-app-events \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts
```

---

## References

- [EventBridge documentation](https://docs.aws.amazon.com/eventbridge/latest/userguide/)
- [EventBridge Pipes](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes.html)
- [EventBridge Scheduler](https://docs.aws.amazon.com/scheduler/latest/UserGuide/)
- [Event pattern reference](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)
---

← [Previous: SQS & SNS](./sqs-sns.md) | [Home](../../README.md) | [Next: Step Functions →](./step-functions.md)
