← [Previous: IAM](./iam.md) | [Home](../README.md) | [Next: Cross-Cloud Comparison →](./cross-cloud-comparison.md)

---

# Serverless Computing Fundamentals

## What "Serverless" Actually Means

Serverless doesn't mean there are no servers. Servers still exist — you just don't see, provision, or manage them. The cloud provider handles all server infrastructure automatically.

**What changes with serverless:**

| Traditional | Serverless |
|------------|-----------|
| Provision a server | Write a function |
| Configure runtime | Choose a runtime from a list |
| Set up auto-scaling | Auto-scales automatically (including to zero) |
| Pay for server uptime | Pay per invocation |
| Manage OS and patches | Provider handles runtime maintenance |
| Idle server = idle cost | No requests = no cost |

**The key insight:** With serverless, the unit of deployment is a function or a container — not a server.

---

## Functions as a Service (FaaS)

FaaS is the most well-known form of serverless. You upload code as individual functions; the provider runs them in response to events.

### Lifecycle of a Function Invocation

```
Event arrives (HTTP request, S3 upload, SQS message)
       ↓
Provider: Is a warm container available?
  ├── Yes (warm) → Execute function (fast, ~1ms overhead)
  └── No (cold)  → Initialize container → Load runtime → Execute function
                   (slow: 100ms–3s depending on runtime and package size)
       ↓
Function executes
       ↓
Response returned / result written
       ↓
Container kept warm for ~5–15 minutes (then destroyed if idle)
```

### Cold Starts

A **cold start** is the latency added when a provider must initialize a new execution environment for a function.

**Cold start factors:**

| Factor | Impact on cold start |
|--------|---------------------|
| Runtime | Java/C# cold = 1–3s. Node/Python cold = 100–500ms. Go cold = 50–100ms |
| Package size | Larger = slower initialization |
| VPC attachment | +500ms–1s to attach the function to a VPC |
| Memory allocation | More memory = slightly faster startup |
| Initialization code | Code outside the handler runs on every cold start |

**Mitigation strategies:**
- Use provisioned concurrency (AWS Lambda) to pre-warm containers
- Choose lightweight runtimes (Node.js, Python) for latency-sensitive paths
- Minimize package size (exclude dev dependencies, use tree-shaking)
- Move expensive initialization (DB connections, SDK clients) outside the handler but inside the module — it runs once per container, not per invocation

```python
# BAD: Creates a new DB connection on every invocation
def handler(event, context):
    conn = connect_to_db()  # cold path: every call creates a new connection
    result = conn.query(...)
    return result

# GOOD: Connection reused across warm invocations
conn = connect_to_db()  # runs once per container initialization

def handler(event, context):
    result = conn.query(...)  # reuses existing connection
    return result
```

---

## Provider FaaS Services

### AWS Lambda

| Property | Value |
|---------|-------|
| Max execution time | 15 minutes |
| Memory | 128MB – 10,240MB (10GB) |
| CPU | Proportional to memory (1 vCPU at 1,769MB) |
| Package size | 50MB zipped (250MB unzipped) direct upload; 10GB container image |
| Pricing | $0.20/million requests + $0.0000166667/GB-second |
| Free tier | 1M requests + 400,000 GB-seconds/month (always free) |

**Supported runtimes:** Python, Node.js, Java, Go, Ruby, .NET, custom (container)

### Azure Functions

| Property | Value |
|---------|-------|
| Max execution time | 10 min (consumption), unlimited (premium/dedicated) |
| Pricing | Consumption plan: pay per execution |
| Runtimes | C#, JavaScript, Python, Java, PowerShell, TypeScript |

**Key Azure Functions concepts:**
- **Bindings**: Declarative connections to triggers and outputs — no SDK code needed
- **Durable Functions**: Stateful workflows built on top of Azure Functions

### GCP Cloud Functions / Cloud Run

**Cloud Functions (gen 2):** Built on Cloud Run, supports longer timeout (60 min).

**Cloud Run:** Runs containers (not just functions), supporting any language or runtime. More flexible than Lambda but requires containerization.

| | Cloud Functions | Cloud Run |
|---|----------------|-----------|
| Deployment unit | Function (code) | Container image |
| Max timeout | 60 minutes | 60 minutes |
| Concurrency | 1 request per instance (default) | Up to 1000 per instance |
| Language | Node, Python, Go, Java, Ruby, PHP | Any (containerized) |

---

## Triggers and Events

Serverless functions are **event-driven** — they execute in response to an event from a source.

### Common Trigger Types

**HTTP / API triggers:**
- External HTTP requests (via API Gateway, Function URLs, Azure API Management)
- Webhooks from external services

**Cloud storage events:**
- S3 object created/deleted → Lambda
- Azure Blob Storage events → Azure Functions
- GCS object change → Cloud Function

**Message queue / stream triggers:**
- SQS message → Lambda (batch processing)
- SNS notification → Lambda (fan-out)
- Kinesis data stream → Lambda (real-time streaming)
- Azure Service Bus → Azure Functions
- Pub/Sub → Cloud Function

**Database events:**
- DynamoDB Streams → Lambda (process inserts/updates/deletes)
- Firestore triggers → Cloud Functions

**Scheduled (cron) triggers:**
- EventBridge Scheduler → Lambda (AWS)
- Azure Timer trigger → Azure Functions
- Cloud Scheduler → Cloud Function

**IoT and device events:**
- AWS IoT Core rules → Lambda

---

## Event-Driven Architecture Patterns

### Fan-Out

One event triggers multiple downstream functions.

```
Upload image → S3
                └── SNS topic
                      ├── Lambda A: create thumbnail
                      ├── Lambda B: extract metadata
                      └── Lambda C: send notification email
```

### Queue-Based Processing

Decouple producers from consumers. Lambda processes messages from SQS in batches.

```
API → writes to SQS → Lambda (processes 10 messages at a time)
                       └── Writes to DynamoDB
```

**Benefits:** Lambda scales automatically with queue depth. If processing slows, messages accumulate in SQS (not dropped). Automatic retry on failure.

### Event Streaming

Process events as they arrive from a data stream in order.

```
App → Kinesis Data Stream (ordered, replay-able)
              └── Lambda (processes in order per shard)
                    └── Writes to Elasticsearch / S3
```

---

## Serverless Application Architecture

A typical serverless API:

```
Client
   ↓
API Gateway (rate limiting, auth, routing)
   ↓
Lambda function (business logic)
   ↓
DynamoDB (data store) or RDS Proxy → RDS
```

**Why RDS Proxy for Lambda + RDS:** Lambda can scale to thousands of concurrent executions. Each would open a DB connection, overwhelming the DB connection limit. RDS Proxy pools connections between Lambda and RDS.

---

## Serverless vs Containers vs VMs

| Dimension | VM (EC2) | Container (ECS/EKS) | Serverless (Lambda) |
|-----------|----------|--------------------|--------------------|
| Startup time | Minutes | Seconds | Milliseconds (warm) |
| Max runtime | Unlimited | Unlimited | 15 minutes |
| Idle cost | Hourly charge | Hourly charge | Zero |
| Management overhead | High (OS, patches) | Medium (container, orchestration) | Low |
| State | Stateful | Stateful/stateless | Stateless |
| Scaling | Manual / Auto Scaling Group | HPA / cluster autoscaler | Automatic |
| Best for | Long-running, stateful, complex | Microservices, portability | Events, short tasks |

---

## Serverless Gotchas

- **Cold starts on infrequent traffic**: Low-traffic APIs will feel slow to first users. Use provisioned concurrency for critical paths.
- **Concurrency limits**: Lambda has a default account-level limit of 1,000 concurrent executions per region. Reserve concurrency for critical functions.
- **15-minute limit**: If your task takes longer, use Step Functions, Fargate, or a long-running EC2/ECS task.
- **No persistent connections**: Lambda can't maintain a WebSocket connection or long-lived TCP connection across invocations (use API Gateway WebSocket API or AppSync for real-time).
- **Vendor lock-in**: Lambda + API Gateway + DynamoDB creates strong AWS coupling. Containerizing with Docker reduces this.
- **Debugging complexity**: Distributed tracing (AWS X-Ray, OpenTelemetry) is essential — traditional debuggers don't work.

---

## References

- [AWS Lambda documentation](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [AWS Lambda best practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Azure Functions documentation](https://learn.microsoft.com/en-us/azure/azure-functions/)
- [GCP Cloud Run documentation](https://cloud.google.com/run/docs)
- [Serverless Land (AWS patterns)](https://serverlessland.com/)
---

← [Previous: IAM](./iam.md) | [Home](../README.md) | [Next: Cross-Cloud Comparison →](./cross-cloud-comparison.md)
