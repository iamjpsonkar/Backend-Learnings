← [Previous: Azure Projects](../06-azure/12-projects/README.md) | [Home](../README.md) | [Next: GCP Account Setup →](./01-account-setup/README.md)

---

# Google Cloud Platform (GCP)

GCP is Google's public cloud platform, differentiated by its global private fiber network, BigQuery analytics, Kubernetes origin (GKE), and AI/ML tooling (Vertex AI).

---

## AWS / Azure / GCP Service Equivalents

| Category | AWS | Azure | GCP |
|----------|-----|-------|-----|
| **Compute — VMs** | EC2 | Azure VMs | Compute Engine |
| **Compute — Managed** | Elastic Beanstalk | App Service | App Engine |
| **Serverless Functions** | Lambda | Azure Functions | Cloud Functions |
| **Containers — Orchestrated** | EKS | AKS | Google Kubernetes Engine (GKE) |
| **Containers — Serverless** | ECS Fargate | Azure Container Apps | Cloud Run |
| **Container Registry** | ECR | ACR | Artifact Registry |
| **Object Storage** | S3 | Blob Storage | Cloud Storage |
| **Block Storage** | EBS | Managed Disks | Persistent Disk |
| **File Storage** | EFS | Azure Files | Filestore |
| **Relational DB** | RDS | Azure Database | Cloud SQL |
| **Managed PostgreSQL** | Aurora PostgreSQL | PostgreSQL Flexible Server | Cloud SQL for PostgreSQL / AlloyDB |
| **NoSQL** | DynamoDB | Cosmos DB | Firestore / Bigtable |
| **In-Memory Cache** | ElastiCache | Azure Cache for Redis | Memorystore |
| **Data Warehouse** | Redshift | Synapse Analytics | BigQuery |
| **Networking** | VPC | VNet | VPC |
| **DNS** | Route 53 | Azure DNS | Cloud DNS |
| **CDN** | CloudFront | Azure CDN / Front Door | Cloud CDN |
| **Load Balancing** | ALB / NLB | Application Gateway | Cloud Load Balancing |
| **IAM** | IAM | Entra ID | Cloud IAM |
| **Secret Management** | Secrets Manager | Key Vault | Secret Manager |
| **Key Management** | KMS | Key Vault (keys) | Cloud KMS |
| **Monitoring** | CloudWatch | Azure Monitor | Cloud Monitoring |
| **Logging** | CloudWatch Logs | Log Analytics | Cloud Logging |
| **Tracing** | X-Ray | Application Insights | Cloud Trace |
| **IaC** | CloudFormation | Bicep / ARM | Deployment Manager / Config Connector |
| **Multi-cloud IaC** | Terraform | Terraform | Terraform |
| **Message Queue** | SQS | Service Bus (queues) | Cloud Pub/Sub |
| **Event Streaming** | Kinesis | Event Hubs | Pub/Sub |
| **CI/CD** | CodePipeline | Azure DevOps | Cloud Build |
| **Artifact Storage** | CodeArtifact | Azure Artifacts | Artifact Registry |
| **ML Platform** | SageMaker | Azure ML | Vertex AI |

---

## GCP Resource Hierarchy

```
Organization (example.com)
└── Folders (optional — team / environment grouping)
    └── Projects (unit of billing, IAM, quotas)
        └── Resources (VMs, buckets, clusters, etc.)
```

- **Organization**: root node — tied to a Google Workspace or Cloud Identity domain.
- **Folder**: optional grouping for departments or environments.
- **Project**: primary isolation boundary — every resource belongs to exactly one project. Billing and quotas are per-project.

IAM policies are **inherited downward** — a policy set at the Organization is inherited by all folders, projects, and resources within it.

---

## Global vs Regional vs Zonal Resources

| Scope | Examples |
|-------|---------|
| **Global** | Cloud Load Balancing, Cloud CDN, IAM, Cloud KMS |
| **Regional** | Cloud Storage (default), Cloud Run, Cloud SQL, Artifact Registry |
| **Zonal** | Compute Engine VMs, Persistent Disks, GKE node pools |

GCP's global load balancer is a single anycast IP that routes traffic to the nearest healthy backend — no per-region ALB setup needed.

---

## Pricing Models

| Model | Description |
|-------|-------------|
| **On-demand** | Pay per second (minimum 1 minute for Compute Engine) |
| **Sustained Use Discounts (SUD)** | Automatic discounts (up to 30%) for VMs running >25% of the month — no commitment needed |
| **Committed Use Discounts (CUD)** | 1- or 3-year commitment — up to 57% discount (general-purpose) or 70% (memory-optimized) |
| **Spot VMs** | Interruptible VMs — up to 91% discount; preempted with 30s notice |
| **Free Tier** | Always-free products (e.g., 1 f1-micro VM/month, 5 GB Cloud Storage) |

---

## Section Index

| Section | Content |
|---------|---------|
| [01 Account Setup](01-account-setup/README.md) | gcloud CLI, projects, billing, quotas |
| [02 IAM](02-iam/README.md) | Roles, service accounts, Workload Identity Federation |
| [03 Networking](03-networking/README.md) | VPC, subnets, firewall rules, Cloud NAT, load balancing |
| [04 Compute](04-compute/README.md) | Compute Engine, instance templates, managed instance groups |
| [05 Storage](05-storage/README.md) | Cloud Storage, Persistent Disk, Filestore |
| [06 Databases](06-databases/README.md) | Cloud SQL, Firestore, Bigtable, Memorystore, BigQuery |
| [07 Containers](07-containers/README.md) | Artifact Registry, GKE, Cloud Run |
| [08 Serverless](08-serverless/README.md) | Cloud Functions, Pub/Sub, Eventarc, Cloud Tasks, Workflows |
| [09 Security](09-security/README.md) | Secret Manager, Cloud KMS, Security Command Center, Cloud Armor |
| [10 Observability](10-observability/README.md) | Cloud Monitoring, Cloud Logging, Cloud Trace, Error Reporting |
| [11 IaC](11-iac/README.md) | Terraform on GCP, Config Connector |
| [12 Projects](12-projects/README.md) | Static website, secure VPC, GKE microservice, serverless API |
---

← [Previous: Azure Projects](../06-azure/12-projects/README.md) | [Home](../README.md) | [Next: GCP Account Setup →](./01-account-setup/README.md)
