← [Previous: Serverless](./serverless.md) | [Home](../README.md) | [Next: Linux →](../02-linux/README.md)

---

# Cross-Cloud Service Comparison

Service equivalents across AWS, Azure, and GCP. Use this as a lookup table when you know the concept but need to find the right service for a specific provider.

---

## Compute

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Virtual machines | EC2 | Virtual Machines | Compute Engine (GCE) |
| Managed Kubernetes | EKS | AKS | GKE |
| Container-as-a-Service | ECS (Fargate) | Container Apps | Cloud Run |
| Container registry | ECR | ACR | Artifact Registry |
| Serverless functions | Lambda | Azure Functions | Cloud Functions (gen 2) |
| GPU compute | EC2 P/G instances | NC/ND/NV-series VMs | A100/T4 Compute Engine |
| ARM / custom silicon | Graviton (t4g, m7g, c7g) | Ampere Altra (Dpsv5) | Tau T2A |
| Batch compute | AWS Batch | Azure Batch | Cloud Batch |
| HPC | ParallelCluster | CycleCloud | HPC Toolkit |
| Desktop-as-a-Service | WorkSpaces | Windows Virtual Desktop (AVD) | — |

---

## Storage

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Object storage | S3 | Blob Storage | Cloud Storage (GCS) |
| Block storage | EBS | Managed Disks | Persistent Disk / Hyperdisk |
| Shared file system (NFS) | EFS | Azure Files (NFS) | Filestore |
| Shared file system (SMB) | FSx for Windows | Azure Files (SMB) | — |
| High-performance FS (Lustre) | FSx for Lustre | — | Parallelstore |
| Archive storage | S3 Glacier Deep Archive | Archive tier (Blob) | Archive Storage Class |
| Hybrid storage gateway | Storage Gateway | StorSimple | Storage Transfer Service |
| Data transfer appliance | Snowball / Snowmobile | Data Box | Transfer Appliance |

---

## Networking

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Private network | VPC | Virtual Network (VNet) | VPC Network |
| Subnet | Subnet (AZ-scoped) | Subnet (region-scoped) | Subnet (region-scoped) |
| Internet gateway | Internet Gateway | Default route to internet | Cloud Router + NAT |
| NAT | NAT Gateway | NAT Gateway | Cloud NAT |
| Application load balancer | ALB | Application Gateway | HTTP(S) Load Balancing |
| Network load balancer | NLB | Azure Load Balancer (L4) | TCP/UDP Load Balancing |
| Global load balancer | CloudFront + ALB | Azure Front Door | Global Load Balancing |
| CDN | CloudFront | Azure CDN / Front Door | Cloud CDN |
| DNS | Route 53 | Azure DNS | Cloud DNS |
| VPN to on-prem | Site-to-Site VPN | VPN Gateway | Cloud VPN |
| Dedicated connection | Direct Connect | ExpressRoute | Cloud Interconnect |
| VPC peering | VPC Peering | VNet Peering | VPC Network Peering |
| Transit hub | Transit Gateway | Virtual WAN | Cloud Router |
| Private endpoint | PrivateLink / VPC Endpoint | Private Endpoint | Private Service Connect |
| DDoS protection | Shield / WAF | DDoS Protection / WAF | Cloud Armor |
| Firewall | Security Groups + NACLs | NSG + Azure Firewall | VPC Firewall Rules + Cloud Armor |

---

## Databases

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Managed PostgreSQL | RDS for PostgreSQL | Azure Database for PostgreSQL | Cloud SQL for PostgreSQL |
| Managed MySQL | RDS for MySQL | Azure Database for MySQL | Cloud SQL for MySQL |
| Managed SQL Server | RDS for SQL Server | Azure SQL Database | Cloud SQL for SQL Server |
| Proprietary SQL (high-perf) | Aurora | Azure SQL Hyperscale | Spanner (global) / AlloyDB |
| NoSQL key-value / document | DynamoDB | Cosmos DB | Firestore / Bigtable |
| In-memory cache | ElastiCache (Redis/Memcached) | Azure Cache for Redis | Memorystore |
| Data warehouse | Redshift | Synapse Analytics | BigQuery |
| Time-series | Timestream | — | Bigtable |
| Graph database | Neptune | Cosmos DB (Gremlin) | — |
| MongoDB-compatible | DocumentDB | Cosmos DB (MongoDB API) | — |
| Cassandra-compatible | Keyspaces | Cosmos DB (Cassandra API) | Bigtable |

---

## Identity and Access

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Identity service | IAM | Entra ID (Azure AD) | Cloud IAM |
| Machine identity | IAM role + instance profile | Managed Identity | Service Account |
| SSO / federated access | IAM Identity Center | Entra ID + SSPR | Cloud Identity |
| MFA enforcement | IAM + Cognito policy | Conditional Access (Entra) | 2-Step Verification |
| Secrets management | Secrets Manager | Key Vault | Secret Manager |
| Key management | KMS | Key Vault (HSM) | Cloud KMS |
| Certificate management | ACM | App Service Certificates / Key Vault | Certificate Manager |
| Directory service | AD Connector / Managed AD | Entra Domain Services | Managed Microsoft AD |

---

## Security and Compliance

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Threat detection | GuardDuty | Microsoft Defender for Cloud | Security Command Center |
| Security posture | Security Hub | Microsoft Defender for Cloud | Security Command Center |
| Vulnerability scanning | Inspector | Microsoft Defender for Containers | Artifact Analysis |
| Web application firewall | WAF | WAF (App Gateway / Front Door) | Cloud Armor |
| DDoS protection | Shield Standard / Advanced | DDoS Network Protection | Cloud Armor |
| Config compliance | AWS Config | Azure Policy | Organization Policy |
| Audit logging | CloudTrail | Azure Monitor Activity Log | Cloud Audit Logs |
| Data classification | Macie (S3) | Microsoft Purview | Sensitive Data Protection (DLP) |
| SIEM | — (send to Splunk/Datadog) | Microsoft Sentinel | Chronicle |

---

## Observability and Monitoring

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Metrics | CloudWatch Metrics | Azure Monitor Metrics | Cloud Monitoring |
| Log aggregation | CloudWatch Logs | Log Analytics Workspace | Cloud Logging |
| Distributed tracing | X-Ray | Application Insights | Cloud Trace |
| Dashboards | CloudWatch Dashboards | Azure Dashboards / Workbooks | Cloud Monitoring Dashboards |
| Alerting | CloudWatch Alarms + SNS | Azure Monitor Alerts | Cloud Monitoring Alerting |
| Synthetic monitoring | CloudWatch Synthetics | Application Insights Availability | Cloud Monitoring Uptime Checks |
| APM | — (use Datadog / New Relic) | Application Insights | Cloud Profiler |

---

## Developer Tools and CI/CD

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Source control | CodeCommit (deprecated) | Azure Repos | Cloud Source Repositories |
| CI/CD pipeline | CodePipeline + CodeBuild | Azure Pipelines | Cloud Build |
| Artifact registry | ECR / CodeArtifact | Azure Artifacts | Artifact Registry |
| IDE / Cloud Shell | CloudShell | Azure Cloud Shell | Cloud Shell |
| Infrastructure as Code | CloudFormation / CDK | ARM / Bicep | Deployment Manager / Config Connector |
| Secrets in CI/CD | Secrets Manager / Parameter Store | Key Vault | Secret Manager |

---

## Serverless and Integration

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Functions | Lambda | Azure Functions | Cloud Functions |
| API gateway | API Gateway | API Management | Cloud Endpoints / API Gateway |
| Message queue | SQS | Service Bus (Queue) | Cloud Tasks / Pub/Sub |
| Pub/Sub messaging | SNS | Service Bus (Topic) | Pub/Sub |
| Event bus | EventBridge | Event Grid | Eventarc |
| Streaming | Kinesis | Event Hubs | Pub/Sub |
| Workflow orchestration | Step Functions | Logic Apps / Durable Functions | Workflows |
| Scheduled tasks | EventBridge Scheduler | Logic Apps (recurrence) | Cloud Scheduler |

---

## Machine Learning and AI

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| ML platform | SageMaker | Azure Machine Learning | Vertex AI |
| Foundation models / GenAI | Bedrock | Azure OpenAI Service | Vertex AI Gemini |
| Vision API | Rekognition | Computer Vision | Vision API |
| Speech API | Transcribe / Polly | Speech Services | Speech-to-Text / Text-to-Speech |
| NLP / Translation | Comprehend / Translate | Language / Translator | Natural Language / Translation |
| Data labeling | SageMaker Ground Truth | Azure ML Data Labeling | Vertex AI Data Labeling |

---

## Management and Operations

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Remote shell / no SSH | SSM Session Manager | Azure Bastion | OS Login + IAP Tunnel |
| Run command on fleet | SSM Run Command | Azure Run Command | OS Config |
| Patch management | SSM Patch Manager | Update Manager | OS Config |
| Config store | Parameter Store | App Configuration | Runtime Configurator |
| Resource tagging | Resource Groups + Tags | Tags | Labels |
| Cost analysis | Cost Explorer | Cost Management | Cloud Billing Reports |
| Billing alerts | AWS Budgets | Cost Management Budgets | Cloud Billing Budgets |
| Automation | Systems Manager Automation | Azure Automation | Cloud Scheduler + Cloud Functions |

---

## Notes on Equivalence

These mappings are approximate. Services with the same name often have different capabilities, pricing models, and integration patterns.

- **DynamoDB ≠ Cosmos DB**: Cosmos DB offers multiple consistency models and APIs; DynamoDB has a simpler model with stronger operational guarantees.
- **Lambda ≠ Azure Functions**: Lambda is more mature with a larger ecosystem of triggers; Azure Functions has tighter Azure service integration.
- **EKS ≠ AKS ≠ GKE**: GKE is generally considered the most feature-complete managed Kubernetes. EKS has the largest AWS ecosystem. AKS has tighter Azure AD integration.
- **GCP subnets are regional**: Unlike AWS subnets (AZ-scoped), GCP subnets span all zones in a region.
- **Azure VNets are regional**: Azure subnets are within a VNet and can span availability zones (zones are a subset of a region in Azure, different from AWS AZs).

---

## References

- [AWS to Azure service comparison](https://learn.microsoft.com/en-us/azure/architecture/aws-professional/services)
- [AWS to GCP service comparison](https://cloud.google.com/free/docs/aws-azure-gcp-service-comparison)
- [GCP to Azure service comparison](https://learn.microsoft.com/en-us/azure/architecture/gcp-professional/services)
---

← [Previous: Serverless](./serverless.md) | [Home](../README.md) | [Next: Linux →](../02-linux/README.md)
