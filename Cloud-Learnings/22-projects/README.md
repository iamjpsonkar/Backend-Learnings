← [Previous: Multi-Cloud IaC](../21-multi-cloud/iac-abstractions.md) | [Home](../README.md) | [Next: Static Website →](./static-website.md)

---

# Projects

Hands-on projects tie together everything from the previous sections. Each project is self-contained: it starts from scratch, builds something real, and ends with a working deployment. Work through them in order or pick the ones most relevant to your role.

---

## Project Difficulty

```
Beginner  ──────────────────────────────────────────────────── Advanced
   │                                                               │
Static      Serverless    Containerized   CI/CD       Kubernetes   Multi-cloud
Website     API           API             Pipeline    App          Deployment
```

---

## Projects

| File | What you build | Key services |
|------|---------------|-------------|
| [Static Website CDN](./static-website.md) | Global static site with HTTPS | S3, CloudFront, ACM, Route 53 |
| [Serverless API](./serverless-api.md) | REST API with auth, DB, and monitoring | Lambda, API Gateway, DynamoDB, Cognito |
| [Containerized API](./containerized-api.md) | Production-grade ECS Fargate service | ECS, ECR, RDS, ALB, Secrets Manager |
| [CI/CD Pipeline](./cicd-pipeline.md) | Full deploy pipeline with tests and approvals | GitHub Actions, ECR, ECS, Terraform |
| [Observability Stack](./observability-stack.md) | Metrics, logs, traces, and alerting | Prometheus, Grafana, Loki, OpenTelemetry |
| [Kubernetes App](./kubernetes-app.md) | Multi-service app on EKS | EKS, Helm, Kustomize, HPA, Ingress |
| [Data Pipeline](./data-pipeline.md) | Streaming ETL from ingestion to warehouse | Kinesis, Lambda, Glue, Athena, S3 |
| [Multi-Tier Web App](./multi-tier-app.md) | 3-tier app: web + app + DB with HA | EC2, RDS Multi-AZ, ALB, Auto Scaling |
| [Disaster Recovery Setup](./dr-setup.md) | Warm standby DR with automated failover | RDS replica, Route 53, AWS Backup |
| [Multi-Cloud Deployment](./multi-cloud-deployment.md) | App on AWS + analytics on GCP | ECS, BigQuery, Terraform multi-provider |

---

## How to Use These Projects

1. **Read the architecture diagram** — understand what you're building before writing any code
2. **Follow the numbered steps** — each step builds on the previous
3. **Use the cost estimate** — all projects include an estimated monthly cost
4. **Clean up when done** — each project ends with a teardown section

---

## Prerequisites

- AWS account with administrative access (or scoped IAM permissions per project)
- AWS CLI v2 configured (`aws configure`)
- Terraform >= 1.6
- Docker Desktop (for container projects)
- `kubectl` (for Kubernetes project)
- Basic familiarity with the relevant sections in this repo

---

## References

- [AWS getting started guides](https://aws.amazon.com/getting-started/)
- [AWS samples (GitHub)](https://github.com/aws-samples)
- [Terraform AWS modules](https://registry.terraform.io/namespaces/terraform-aws-modules)

---

← [Previous: Multi-Cloud IaC](../21-multi-cloud/iac-abstractions.md) | [Home](../README.md) | [Next: Static Website →](./static-website.md)
