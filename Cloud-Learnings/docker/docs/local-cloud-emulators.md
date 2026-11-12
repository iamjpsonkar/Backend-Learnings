# Local Cloud Emulators

What works locally, what doesn't, and which emulator to use for each service.

## AWS — LocalStack

LocalStack emulates 50+ AWS services. Free tier supports the most common ones.

### Works well in LocalStack free tier

| AWS Service | LocalStack Support | Notes |
|---|---|---|
| S3 | Excellent | CRUD, versioning, events, presigned URLs |
| SQS | Excellent | FIFO, standard, DLQ, visibility timeout |
| SNS | Excellent | Topics, subscriptions, fan-out |
| DynamoDB | Good | Tables, GSI, queries, streams |
| IAM | Partial | Policies work but not fully enforced |
| KMS | Good | Key creation, encrypt/decrypt |
| Secrets Manager | Good | Create/get/rotate secrets |
| Parameter Store (SSM) | Good | Get/put parameters |
| CloudFormation | Partial | Basic stacks |
| CloudWatch Logs | Good | Log groups, log streams |
| Lambda | Basic | Simple functions; cold start behavior differs |
| STS | Good | AssumeRole, GetCallerIdentity |
| Route 53 | Limited | Basic zones |

### Limited or not supported (free tier)

| Service | Reason |
|---|---|
| EC2 | Mocked only — no real compute |
| RDS | Not available — use real PostgreSQL container instead |
| ECS/EKS | Not available — use kind/k3d |
| CloudFront | Not available — use Nginx/Traefik locally |
| Cognito | Limited |
| Step Functions | Limited |
| Kinesis | Limited |

**For RDS**: Use the PostgreSQL/MySQL containers in the `data` profile. Connect your app to `postgres:5432`.
**For ECS**: Use Docker Compose services directly.
**For EKS**: Use kind or k3d.

### LocalStack CLI Usage

```bash
# Always use --endpoint-url
aws --endpoint-url=http://localhost:4566 s3 ls

# Or set environment variable
export AWS_ENDPOINT_URL=http://localhost:4566
aws s3 ls

# Use the aws-cli container (pre-configured)
docker exec -it cloud-learnings-aws-cli aws s3 ls
```

---

## Azure — Azurite

Azurite emulates Azure Storage services only.

### Works in Azurite

| Azure Service | Support | Notes |
|---|---|---|
| Blob Storage | Excellent | CRUD, tiers, metadata, SAS |
| Queue Storage | Good | Create, send, receive, delete |
| Table Storage | Good | CRUD operations |

### Not available locally

| Service | Alternative |
|---|---|
| Azure Functions | Use Python container with HTTP trigger simulation |
| Azure SQL | Use MySQL container |
| Cosmos DB | Use MongoDB container |
| Azure Active Directory | Use Keycloak |
| Event Hubs | Use Redpanda (Kafka-compatible) |
| Service Bus | Use RabbitMQ |
| Azure Monitor | Use Prometheus + Grafana |
| Application Insights | Use OTel Collector |

### Azurite Connection String

```
DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;
```

This is the standard Azurite development key (publicly known, local only).

---

## MinIO — S3-compatible Object Storage

MinIO is fully S3-compatible and often more stable than LocalStack S3 for high-volume testing.

### When to use MinIO instead of LocalStack S3

- Terraform remote state backend (more stable for state locking)
- Large file uploads
- When you need a realistic S3 console UI
- When LocalStack S3 has issues

### MinIO vs LocalStack S3

| Feature | LocalStack S3 | MinIO |
|---|---|---|
| S3 API compatibility | High | Very High |
| Console UI | None (free tier) | Yes (port 9002) |
| Multi-bucket | Yes | Yes |
| Versioning | Yes | Yes |
| Lifecycle rules | Partial | Full |
| Presigned URLs | Yes | Yes |
| Performance | Dev quality | Production quality |

---

## GCP — Emulators

GCP provides official emulators for a subset of services.

### Works with GCP emulators

| GCP Service | Emulator | Port | Notes |
|---|---|---|---|
| Pub/Sub | Official emulator | 8085 | Topics, subscriptions, publish, pull |
| Firestore | Official emulator | 8086 | CRUD, queries, collections |
| Datastore | Official emulator | 8081 | (deprecated, use Firestore) |

### GCP Pub/Sub Emulator Usage

```bash
export PUBSUB_EMULATOR_HOST=localhost:8085
gcloud pubsub topics list --project=local-dev-project
```

In code (Python):
```python
import os
os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
from google.cloud import pubsub_v1
# Client automatically uses the emulator
```

### Not available locally

| GCP Service | Alternative |
|---|---|
| Cloud Storage (GCS) | Use MinIO (S3-compatible) |
| BigQuery | Use PostgreSQL with analytics queries |
| Cloud SQL | Use PostgreSQL container |
| Cloud Run | Use Docker Compose with Traefik |
| GKE | Use kind/k3d |
| Cloud Monitoring | Use Prometheus + Grafana |
| Cloud Logging | Use Loki |
| Cloud Trace | Use Tempo |

---

## Summary: Emulator Selection Guide

| What you want to practice | Use |
|---|---|
| AWS S3, SQS, SNS, DynamoDB | LocalStack |
| AWS Lambda | LocalStack (basic only) |
| AWS infrastructure as code | Terraform + LocalStack |
| Azure Blob/Queue/Table storage | Azurite |
| GCP Pub/Sub | GCP Pub/Sub emulator |
| GCP Firestore | GCP Firestore emulator |
| Object storage (generic) | MinIO |
| Relational database (any cloud) | PostgreSQL or MySQL container |
| Redis/ElastiCache | Redis container |
| Kafka/Kinesis/Event Hubs | Redpanda |
| Message queue (SQS/Service Bus) | RabbitMQ or LocalStack SQS |
| Kubernetes (EKS/GKE/AKS) | kind or k3d |
