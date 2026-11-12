← [Previous: Cloud Engineer Roadmap](./cloud-engineer.md) | [Home](../README.md) | [Next: SRE Roadmap →](./sre.md)

---

# DevOps Engineer Roadmap

A DevOps engineer builds the systems that let developers ship faster and safer. The focus is on automation, pipelines, infrastructure as code, and container orchestration.

**Prerequisite:** Cloud Engineer Roadmap Phase 1–2, or equivalent experience.

---

## Phase 1: Containers (3–4 weeks)

```
Week 1–2: Docker
  ├── Dockerfile best practices (multi-stage, non-root, minimal)  → 09-containers/
  ├── Docker Compose for local development
  ├── Layer caching, image optimization
  └── Container security: scanning with Trivy, non-root users

Week 3–4: Container Orchestration
  ├── ECS Fargate: task definitions, services, auto scaling      → 05-aws/07-containers/
  ├── ECR: repositories, lifecycle policies, image scanning
  └── Service discovery and load balancing
```

**Milestone:** Containerize an existing application and deploy to ECS Fargate.

---

## Phase 2: CI/CD (4–5 weeks)

```
Week 5–6: GitHub Actions
  ├── Workflow syntax: jobs, steps, triggers, conditions         → 13-cicd-gitops/
  ├── OIDC authentication to AWS (no stored credentials)
  ├── Matrix builds, caching, artifacts
  └── Security scanning in CI (Trivy, Semgrep, pip-audit)

Week 7–8: Deployment Strategies
  ├── Rolling updates, blue/green, canary                       → 13-cicd-gitops/
  ├── ECS deployment circuit breaker and rollback
  ├── Database migrations in CD pipelines
  └── Feature flags and dark launches

Week 9: GitOps
  ├── ArgoCD or FluxCD: sync from Git                           → 13-cicd-gitops/
  ├── Application sets and multi-env management
  └── Drift detection and self-healing
```

**Milestone:** CI/CD Pipeline project: full pipeline with tests, scans, staging, and prod approval.

---

## Phase 3: Infrastructure as Code (4–5 weeks)

```
Week 10–11: Terraform
  ├── Providers, resources, data sources, outputs              → 11-terraform-opentofu/
  ├── State management (S3 backend + DynamoDB locking)
  ├── Modules: writing and consuming
  └── Workspaces and environment management

Week 12–13: Advanced Terraform
  ├── Terragrunt for DRY configurations
  ├── Testing: Terratest, checkov, tfsec
  ├── Terraform in CI (plan on PR, apply on merge)
  └── Importing existing resources

Week 14: Ansible
  ├── Playbooks, roles, inventory                              → 12-ansible/
  ├── Idempotent configuration management
  └── Secrets with Ansible Vault
```

**Milestone:** Provision a full multi-tier stack via Terraform with CI/CD pipeline.

---

## Phase 4: Kubernetes (4–6 weeks)

```
Week 15–16: Kubernetes Core
  ├── Pods, Deployments, Services, ConfigMaps, Secrets         → 10-kubernetes/
  ├── HPA, resource requests/limits
  ├── Health probes: liveness, readiness, startup
  └── Rolling updates, rollbacks

Week 17–18: EKS in Production
  ├── eksctl cluster creation, managed node groups
  ├── IRSA, AWS Load Balancer Controller, ExternalDNS
  ├── Kustomize overlays for multi-env
  └── Helm: charts, values, releases

Week 19–20: Advanced Kubernetes
  ├── Network policies, pod security standards
  ├── Persistent volumes, storage classes
  ├── Cluster autoscaler, Karpenter
  └── Kubernetes costs with Kubecost
```

**Milestone:** Kubernetes App project: EKS with full production stack.

---

## Phase 5: Observability and Reliability (3–4 weeks)

```
Week 21–22: Observability
  ├── Prometheus metrics + recording rules + alerting          → 15-observability/
  ├── Structured logging + Loki/CloudWatch
  ├── Distributed tracing (OpenTelemetry)
  └── Grafana dashboards as code

Week 23–24: Reliability
  ├── Error budgets and SLOs                                   → 16-sre/
  ├── Incident response and postmortems
  ├── Chaos engineering (LitmusChaos, AWS FIS)
  └── On-call tooling and runbooks
```

**Milestone:** Observability Stack project: full metrics/logs/traces stack.

---

## Certifications

| Certification | When to take | Validates |
|--------------|-------------|----------|
| AWS DevOps Engineer Professional | After Phase 3 | CI/CD + IaC on AWS |
| CKA (Certified Kubernetes Administrator) | After Phase 4 | Kubernetes administration |
| CKAD (Certified Kubernetes App Developer) | After Phase 4 | Kubernetes application deployment |
| HashiCorp Terraform Associate | After Phase 3 | Terraform skills |

---

← [Previous: Cloud Engineer Roadmap](./cloud-engineer.md) | [Home](../README.md) | [Next: SRE Roadmap →](./sre.md)
