← [Previous: EKS](../07-containers/eks.md) | [Home](../../README.md) | [Next: API Gateway →](./api-gateway.md)

---

# AWS Serverless

Serverless on AWS means you provision no servers, pay only for what you use, and scale automatically from zero to millions of events. Lambda is the compute engine; API Gateway, SQS, SNS, EventBridge, and Step Functions handle ingestion, routing, and orchestration.

---

## Contents

| File | Description |
|------|-------------|
| [api-gateway.md](./api-gateway.md) | REST and HTTP APIs, WebSocket APIs, authorizers, stages |
| [sqs-sns.md](./sqs-sns.md) | SQS queues (standard + FIFO), SNS topics, fan-out patterns |
| [eventbridge.md](./eventbridge.md) | Event buses, rules, event patterns, pipes, scheduler |
| [step-functions.md](./step-functions.md) | State machines, Express vs Standard, error handling, SDK integrations |

> Lambda documentation is in [../04-compute/lambda.md](../04-compute/lambda.md).

---

## Serverless Architecture Patterns

```
Synchronous (request/response):
  Client → API Gateway → Lambda → Response

Asynchronous (fire-and-forget):
  Producer → SQS → Lambda (batch processor)

Event fan-out:
  Event → SNS → SQS (queue A)
              → SQS (queue B)
              → Lambda (direct)
              → Email

Event-driven microservices:
  Service A publishes event → EventBridge → Rule → Service B Lambda
                                                  → Service C SQS

Long-running workflows:
  API Gateway → Step Functions → Lambda step 1 → Lambda step 2 → DynamoDB
```

---

## Minimum Competency Checklist

- [ ] Create an HTTP API in API Gateway and connect it to Lambda
- [ ] Add a JWT authorizer to protect an API route
- [ ] Create an SQS queue with a dead-letter queue (DLQ)
- [ ] Implement a fan-out pattern with SNS → multiple SQS queues
- [ ] Write an EventBridge rule that matches a specific event pattern
- [ ] Create a Step Functions state machine with error handling and retries
- [ ] Explain the difference between Standard and FIFO SQS queues
- [ ] Estimate EventBridge vs SNS vs SQS cost for a given pattern

---

## Choosing the Right Messaging Service

| Scenario | Service |
|----------|---------|
| Decouple producer from consumer, buffering | SQS |
| Exactly-once delivery, ordered processing | SQS FIFO |
| Broadcast same event to many consumers | SNS |
| Fan-out: one event → multiple SQS + Lambda + email | SNS → SQS |
| Route events between services by pattern | EventBridge |
| Schedule tasks (cron/rate) | EventBridge Scheduler |
| Multi-step workflow with retries, branching | Step Functions |
| Real-time bidirectional communication | API Gateway WebSocket |
---

← [Previous: EKS](../07-containers/eks.md) | [Home](../../README.md) | [Next: API Gateway →](./api-gateway.md)
