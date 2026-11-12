# Lab Index

Complete catalog of all available labs. Run any lab with:

```bash
make run-lab LAB=<category>/<lab-slug>
```

Difficulty: B=Beginner, I=Intermediate, A=Advanced

---

## 00 — Platform Foundations

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Platform Orientation | `00-foundations/platform-orientation` | B | 15 min | core |
| Docker Compose Profiles | `00-foundations/compose-profiles` | B | 20 min | core |
| Lab Runner Walkthrough | `00-foundations/lab-runner-walkthrough` | B | 15 min | core |

---

## 01 — Linux

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Basic Commands | `01-linux/basic-commands` | B | 30 min | core |
| File Permissions & Ownership | `01-linux/permissions` | B | 30 min | core |
| Users, Groups & sudo | `01-linux/users-groups` | B | 30 min | core |
| Process Management | `01-linux/processes` | B | 30 min | core |
| Shell Scripting | `01-linux/shell-scripting` | I | 45 min | core |
| Cron & Scheduling | `01-linux/cron-scheduling` | I | 30 min | core |
| SSH & SCP | `01-linux/ssh-scp` | I | 30 min | core |
| System Troubleshooting | `01-linux/troubleshooting` | A | 60 min | core |

---

## 02 — Networking

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| DNS Resolution | `02-networking/dns-resolution` | B | 30 min | core |
| HTTP & HTTPS Basics | `02-networking/http-https` | B | 30 min | core |
| Reverse Proxy with Traefik | `02-networking/reverse-proxy` | I | 45 min | core |
| TLS Certificates | `02-networking/tls-certificates` | I | 45 min | core |
| Network Troubleshooting | `02-networking/network-troubleshooting` | I | 45 min | core |
| Load Balancing | `02-networking/load-balancing` | A | 60 min | core |

---

## 03 — Git & DevOps Basics

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Git Basics | `03-git-devops/git-basics` | B | 30 min | none |
| Branching & Merging | `03-git-devops/branching-merging` | B | 30 min | none |
| Git Hooks | `03-git-devops/git-hooks` | I | 30 min | none |
| GitOps Workflow | `03-git-devops/gitops-workflow` | I | 45 min | cicd |

---

## 04 — Docker

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Docker Basics | `04-docker/docker-basics` | B | 45 min | core |
| Build Your First Image | `04-docker/build-image` | B | 45 min | core |
| Multi-Stage Builds | `04-docker/multi-stage-builds` | I | 45 min | core |
| Docker Networking | `04-docker/docker-networking` | I | 45 min | core |
| Docker Volumes | `04-docker/docker-volumes` | I | 30 min | core |
| Docker Compose | `04-docker/docker-compose` | I | 45 min | core |
| Container Security | `04-docker/container-security` | A | 60 min | core |
| Image Scanning with Trivy | `04-docker/image-scanning` | I | 30 min | core |

---

## 05 — Kubernetes

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Deploy First App | `05-kubernetes/deploy-first-app` | B | 45 min | kubernetes |
| Services & Ingress | `05-kubernetes/services-ingress` | I | 45 min | kubernetes |
| ConfigMaps & Secrets | `05-kubernetes/configmaps-secrets` | I | 30 min | kubernetes |
| Persistent Volumes | `05-kubernetes/persistent-volumes` | I | 45 min | kubernetes |
| Deployments & Rolling Updates | `05-kubernetes/rolling-updates` | I | 45 min | kubernetes |
| HPA — Horizontal Pod Autoscaling | `05-kubernetes/hpa` | I | 45 min | kubernetes |
| Helm Chart Basics | `05-kubernetes/helm-basics` | I | 60 min | kubernetes |
| RBAC | `05-kubernetes/rbac` | A | 60 min | kubernetes |
| Network Policies | `05-kubernetes/network-policies` | A | 45 min | kubernetes |
| Debug: CrashLoopBackOff | `05-kubernetes/k8s-crashloopbackoff` | A | 60 min | kubernetes |
| Debug: Pending Pods | `05-kubernetes/k8s-pending-pods` | A | 45 min | kubernetes |
| Multi-Container Patterns | `05-kubernetes/multi-container-patterns` | A | 60 min | kubernetes |

---

## 06 — Terraform / OpenTofu

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Terraform Basics | `06-terraform-opentofu/terraform-basics` | B | 45 min | core |
| Variables & Outputs | `06-terraform-opentofu/variables-outputs` | B | 30 min | core |
| State Management | `06-terraform-opentofu/state-management` | I | 45 min | core |
| Modules | `06-terraform-opentofu/modules` | I | 60 min | core |
| Remote State (MinIO backend) | `06-terraform-opentofu/remote-state` | I | 45 min | core |
| Terraform with LocalStack | `06-terraform-opentofu/terraform-localstack` | I | 60 min | aws-local |
| OpenTofu Migration | `06-terraform-opentofu/opentofu-migration` | I | 30 min | core |
| IaC Testing with Checkov | `06-terraform-opentofu/iac-scanning` | I | 30 min | core |
| Workspaces | `06-terraform-opentofu/workspaces` | A | 45 min | core |
| Drift Detection | `06-terraform-opentofu/drift-detection` | A | 45 min | core |

---

## 07 — Ansible

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Ansible Basics | `07-ansible/ansible-basics` | B | 45 min | core |
| Playbooks | `07-ansible/playbooks` | I | 45 min | core |
| Roles & Galaxy | `07-ansible/roles` | I | 60 min | core |
| Ansible Vault (Secrets) | `07-ansible/ansible-vault` | I | 30 min | core |
| Idempotency Testing | `07-ansible/idempotency` | I | 45 min | core |
| Dynamic Inventory | `07-ansible/dynamic-inventory` | A | 60 min | core |

---

## 08 — AWS Local (LocalStack)

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| S3 Operations | `08-aws-local/s3-operations` | B | 45 min | aws-local |
| SQS Queues | `08-aws-local/sqs-queues` | I | 45 min | aws-local |
| Lambda Functions | `08-aws-local/lambda-functions` | I | 60 min | aws-local |
| DynamoDB | `08-aws-local/dynamodb` | I | 45 min | aws-local |
| IAM Policies | `08-aws-local/iam-policies` | I | 45 min | aws-local |
| SNS + SQS Fan-Out | `08-aws-local/sns-sqs-fanout` | A | 60 min | aws-local |
| Serverless API (API GW + Lambda) | `08-aws-local/serverless-api` | A | 90 min | aws-local |
| CloudFormation Basics | `08-aws-local/cloudformation` | I | 45 min | aws-local |
| S3 Event Triggers | `08-aws-local/s3-events` | A | 60 min | aws-local |
| VPC + Security Groups | `08-aws-local/vpc-security-groups` | A | 60 min | aws-local |

---

## 09 — Azure Local (Azurite)

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Blob Storage | `09-azure-local/blob-storage` | B | 45 min | azure-local |
| Queue Storage | `09-azure-local/queue-storage` | I | 30 min | azure-local |
| Table Storage | `09-azure-local/table-storage` | I | 30 min | azure-local |
| Blob Lifecycle Policies | `09-azure-local/blob-lifecycle` | I | 30 min | azure-local |
| SAS Tokens | `09-azure-local/sas-tokens` | I | 45 min | azure-local |
| ARM / Bicep Basics | `09-azure-local/bicep-basics` | I | 45 min | core |

---

## 10 — GCP Local

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| GCS Emulator | `10-gcp-local/gcs-emulator` | B | 30 min | core |
| Pub/Sub Emulator | `10-gcp-local/pubsub-emulator` | I | 45 min | data |
| Firestore Emulator | `10-gcp-local/firestore-emulator` | I | 45 min | core |
| BigQuery Local | `10-gcp-local/bigquery-local` | I | 60 min | data |

---

## 11 — Security

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Vault Basics | `11-security/vault-basics` | B | 45 min | security |
| Vault Secrets Injection | `11-security/vault-secrets-injection` | I | 60 min | security |
| Vault PKI (TLS Certs) | `11-security/vault-pki` | A | 60 min | security |
| Keycloak OIDC | `11-security/keycloak-oidc` | I | 60 min | security |
| Container Image Scanning | `11-security/image-scanning` | B | 30 min | core |
| IaC Security Scanning | `11-security/iac-scanning` | I | 30 min | core |
| Kubernetes RBAC | `11-security/k8s-rbac` | A | 60 min | kubernetes,security |
| Network Policies | `11-security/network-policies` | A | 45 min | kubernetes |
| Secrets Rotation | `11-security/secrets-rotation` | A | 60 min | security |
| Zero-Trust Patterns | `11-security/zero-trust` | A | 90 min | security |

---

## 12 — Observability

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Prometheus Basics | `12-observability/prometheus-basics` | B | 45 min | observability |
| Grafana Dashboards | `12-observability/grafana-dashboards` | B | 45 min | observability |
| Alerting Rules | `12-observability/alerting-rules` | I | 45 min | observability |
| Loki Log Aggregation | `12-observability/loki-logs` | I | 45 min | observability |
| Distributed Tracing (Jaeger) | `12-observability/distributed-tracing` | I | 60 min | observability |
| OpenTelemetry Instrumentation | `12-observability/opentelemetry` | A | 90 min | observability |
| SLOs & Error Budgets | `12-observability/slo-error-budget` | A | 60 min | observability |
| Custom Metrics | `12-observability/custom-metrics` | I | 45 min | observability |
| Log-Based Alerts | `12-observability/log-based-alerts` | I | 45 min | observability |
| Runbook Automation | `12-observability/runbook-automation` | A | 60 min | observability |

---

## 13 — CI/CD

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Gitea Setup & First Repo | `13-cicd/gitea-setup` | B | 30 min | cicd |
| Woodpecker CI Pipeline | `13-cicd/woodpecker-pipeline` | B | 45 min | cicd |
| Build & Push Docker Image | `13-cicd/build-push-image` | I | 45 min | cicd |
| Test Automation in CI | `13-cicd/ci-test-automation` | I | 45 min | cicd |
| Deploy to Kubernetes | `13-cicd/deploy-to-k8s` | A | 60 min | cicd,kubernetes |
| GitOps with ArgoCD | `13-cicd/argocd-gitops` | A | 90 min | cicd,kubernetes |
| Pipeline Security Scanning | `13-cicd/pipeline-security` | I | 45 min | cicd |
| Rollback Strategy | `13-cicd/rollback-strategy` | A | 60 min | cicd,kubernetes |

---

## 14 — Databases

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| PostgreSQL Basics | `14-databases/postgres-basics` | B | 45 min | data |
| PostgreSQL Replication | `14-databases/postgres-replication` | A | 60 min | data |
| MongoDB CRUD | `14-databases/mongodb-crud` | B | 45 min | data |
| MongoDB Aggregation | `14-databases/mongodb-aggregation` | I | 45 min | data |
| Redis Caching Patterns | `14-databases/redis-caching` | I | 45 min | data |
| Redis Pub/Sub | `14-databases/redis-pubsub` | I | 30 min | data |
| Database Backup & Restore | `14-databases/backup-restore` | I | 45 min | data |
| Connection Pooling | `14-databases/connection-pooling` | I | 45 min | data |
| Schema Migrations | `14-databases/schema-migrations` | I | 45 min | data |
| Performance Tuning | `14-databases/performance-tuning` | A | 60 min | data |

---

## 15 — Storage

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| MinIO Object Storage | `15-storage/minio-basics` | B | 45 min | core |
| S3-Compatible API | `15-storage/s3-compatible-api` | I | 45 min | core |
| Object Lifecycle Policies | `15-storage/object-lifecycle` | I | 30 min | core |
| Bucket Versioning | `15-storage/bucket-versioning` | I | 30 min | core |
| Presigned URLs | `15-storage/presigned-urls` | I | 30 min | core |
| Multi-Tenant Storage | `15-storage/multi-tenant` | A | 60 min | core |

---

## 16 — Serverless & Events

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| RabbitMQ Queues | `16-serverless-events/rabbitmq-basics` | B | 45 min | data |
| Redpanda Kafka API | `16-serverless-events/redpanda-kafka` | I | 60 min | data |
| Event-Driven Architecture | `16-serverless-events/event-driven` | I | 60 min | data |
| Dead Letter Queues | `16-serverless-events/dead-letter-queues` | I | 45 min | data |
| Stream Processing | `16-serverless-events/stream-processing` | A | 90 min | data |
| Serverless Functions (OpenFaaS) | `16-serverless-events/openfaas` | I | 60 min | kubernetes |
| Fan-Out Patterns | `16-serverless-events/fan-out` | A | 60 min | data |
| CQRS Pattern | `16-serverless-events/cqrs` | A | 90 min | data |

---

## 17 — SRE

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| SLO Design | `17-sre/slo-design` | I | 45 min | observability |
| Error Budget Tracking | `17-sre/error-budget` | I | 45 min | observability |
| Chaos Engineering | `17-sre/chaos-engineering` | A | 60 min | kubernetes |
| On-Call Simulation | `17-sre/on-call-simulation` | A | 90 min | observability |
| Incident Response | `17-sre/incident-response` | A | 60 min | observability |
| Runbook Writing | `17-sre/runbook-writing` | I | 45 min | none |
| Capacity Planning | `17-sre/capacity-planning` | A | 60 min | observability |
| Toil Reduction | `17-sre/toil-reduction` | A | 60 min | none |

---

## 18 — FinOps

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Cost Tagging Strategy | `18-finops/cost-tagging` | B | 30 min | none |
| Infracost Basics | `18-finops/infracost` | I | 45 min | none |
| Resource Right-Sizing | `18-finops/right-sizing` | I | 45 min | none |
| FinOps Dashboard | `18-finops/finops-dashboard` | A | 60 min | observability |

---

## 19 — Multi-Cloud

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Cloud Abstraction Layer | `19-multi-cloud/abstraction-layer` | A | 90 min | aws-local,azure-local |
| Cross-Cloud Storage | `19-multi-cloud/cross-cloud-storage` | A | 60 min | aws-local,azure-local |
| Multi-Cloud IaC | `19-multi-cloud/multi-cloud-iac` | A | 90 min | aws-local |
| Data Replication | `19-multi-cloud/data-replication` | A | 60 min | data |
| Cost Comparison | `19-multi-cloud/cost-comparison` | I | 45 min | none |
| Vendor Lock-In Avoidance | `19-multi-cloud/vendor-lockout` | A | 60 min | none |

---

## 20 — Hybrid Cloud

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| On-Prem to Cloud Bridge | `20-hybrid-cloud/onprem-bridge` | A | 90 min | aws-local |
| VPN Simulation | `20-hybrid-cloud/vpn-simulation` | A | 60 min | core |
| Identity Federation | `20-hybrid-cloud/identity-federation` | A | 60 min | security |

---

## 21 — Disaster Recovery

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| Backup & Restore | `21-disaster-recovery/backup-restore` | I | 60 min | data |
| RTO/RPO Testing | `21-disaster-recovery/rto-rpo-testing` | A | 90 min | data |
| Database Failover | `21-disaster-recovery/db-failover` | A | 60 min | data |
| Application Recovery | `21-disaster-recovery/app-recovery` | A | 60 min | kubernetes |
| Chaos + Recovery | `21-disaster-recovery/chaos-recovery` | A | 90 min | kubernetes |
| DR Runbook | `21-disaster-recovery/dr-runbook` | I | 45 min | none |

---

## 22 — Production Troubleshooting

| Lab | Slug | Difficulty | Time | Profiles |
|-----|------|-----------|------|---------|
| High CPU Scenario | `22-production-troubleshooting/high-cpu` | A | 60 min | core |
| Memory Leak | `22-production-troubleshooting/memory-leak` | A | 60 min | core |
| Disk Full | `22-production-troubleshooting/disk-full` | A | 45 min | core |
| Database Connection Exhaustion | `22-production-troubleshooting/db-connections` | A | 60 min | data |
| Slow API Response | `22-production-troubleshooting/slow-api` | A | 60 min | observability |
| Certificate Expiry | `22-production-troubleshooting/cert-expiry` | A | 45 min | security |
| DNS Misconfiguration | `22-production-troubleshooting/dns-misconfig` | A | 45 min | core |
| Network Partition | `22-production-troubleshooting/network-partition` | A | 60 min | kubernetes |

---

## Total Lab Count

| Category | Labs |
|----------|------|
| Foundations | 3 |
| Linux | 8 |
| Networking | 6 |
| Git & DevOps | 4 |
| Docker | 8 |
| Kubernetes | 12 |
| Terraform/OpenTofu | 10 |
| Ansible | 6 |
| AWS Local | 10 |
| Azure Local | 6 |
| GCP Local | 4 |
| Security | 10 |
| Observability | 10 |
| CI/CD | 8 |
| Databases | 10 |
| Storage | 6 |
| Serverless & Events | 8 |
| SRE | 8 |
| FinOps | 4 |
| Multi-Cloud | 6 |
| Hybrid Cloud | 3 |
| Disaster Recovery | 6 |
| Production Troubleshooting | 8 |
| **Total** | **164** |
