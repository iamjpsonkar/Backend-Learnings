← [Previous: Roadmaps Overview](./README.md) | [Home](../README.md) | [Next: DevOps Engineer Roadmap →](./devops-engineer.md)

---

# Cloud Engineer Roadmap

A cloud engineer provisions, manages, and optimizes cloud infrastructure. This roadmap builds skills in the order they depend on each other.

---

## Phase 1: Foundations (4–6 weeks)

```
Week 1–2: Linux + Networking
  ├── Linux: files, processes, services, shell scripting    → 02-linux/
  ├── Networking: TCP/IP, DNS, HTTP, subnets, firewalls     → 03-networking/
  └── Git basics: commits, branches, pull requests          → 04-git-devops-basics/

Week 3–4: Cloud Concepts
  ├── Service models (IaaS/PaaS/SaaS)                       → 00-foundations/
  ├── Shared responsibility model                           → 00-foundations/
  ├── Regions, AZs, edge locations                          → 00-foundations/
  └── Core concepts: compute, storage, networking, IAM      → 01-cloud-fundamentals/

Week 5–6: AWS Foundation
  ├── Account setup, billing alerts, MFA                    → 05-aws/01-account-setup/
  ├── IAM: users, roles, policies, least privilege          → 05-aws/02-iam/
  └── AWS CLI, SDKs, console navigation
```

**Milestone:** Deploy a static website on S3 + CloudFront with a custom domain.

---

## Phase 2: Core Services (6–8 weeks)

```
Week 7–8: Compute
  ├── EC2: instance types, AMIs, user data, key pairs        → 05-aws/04-compute/
  ├── Security groups, NACLs, VPC basics                    → 05-aws/03-networking/
  └── Systems Manager: SSM Sessions, Parameter Store

Week 9–10: Storage and Databases
  ├── S3: buckets, versioning, lifecycle, replication        → 05-aws/05-storage/
  ├── RDS: PostgreSQL, Multi-AZ, backups, parameter groups   → 05-aws/06-databases/
  └── DynamoDB: tables, indexes, capacity modes             → 05-aws/06-databases/

Week 11–12: Serverless and Containers
  ├── Lambda: functions, triggers, layers, concurrency       → 05-aws/08-serverless/
  ├── API Gateway: HTTP API, Lambda integration             → 05-aws/08-serverless/
  └── Docker basics: build, run, push to ECR               → 09-containers/
```

**Milestone:** Deploy the Serverless API project end-to-end.

---

## Phase 3: Operations (4–6 weeks)

```
Week 13–14: Security
  ├── KMS, Secrets Manager, encryption at rest              → 05-aws/09-security/
  ├── CloudTrail, Config, Security Hub                      → 05-aws/09-security/
  └── Vulnerability scanning basics (Trivy)                 → 14-security/

Week 15–16: Observability
  ├── CloudWatch: metrics, alarms, dashboards, log groups   → 05-aws/10-observability/
  ├── Structured logging (JSON)                             → 15-observability/
  └── Basic alerting and on-call processes

Week 17–18: Infrastructure as Code
  ├── Terraform: providers, resources, state, modules       → 11-terraform-opentofu/
  ├── GitHub Actions: workflows, jobs, secrets, OIDC        → 13-cicd-gitops/
  └── Deploying a full stack with Terraform
```

**Milestone:** The Containerized API project deployed via Terraform + GitHub Actions.

---

## Phase 4: Advanced (4–6 weeks)

```
Week 19–20: High Availability and DR
  ├── Auto Scaling Groups, ALB, target groups               → 05-aws/04-compute/
  ├── RDS Multi-AZ, read replicas, failover                 → 18-databases/
  └── Backup strategies and DR patterns                     → 19-disaster-recovery/

Week 21–22: Cost and Optimization
  ├── Cost Explorer, Budgets, tagging strategy              → 17-finops/
  ├── Savings Plans, Reserved Instances, Spot               → 17-finops/
  └── Rightsizing with Compute Optimizer

Week 23–24: Second Cloud
  ├── Azure or GCP foundation (pick one)                    → 06-azure/ or 07-gcp/
  └── Multi-cloud concepts and trade-offs                   → 21-multi-cloud/
```

**Milestone:** Multi-Tier App project with DR setup.

---

## Certifications (Optional but Valuable)

| Certification | When to take | Validates |
|--------------|-------------|----------|
| AWS Cloud Practitioner | After Phase 1 | Foundational cloud literacy |
| AWS Solutions Architect Associate | After Phase 2 | Core AWS architecture |
| AWS Solutions Architect Professional | After Phase 4 | Advanced architecture |
| HashiCorp Terraform Associate | After Phase 3 | Terraform skills |

---

← [Previous: Roadmaps Overview](./README.md) | [Home](../README.md) | [Next: DevOps Engineer Roadmap →](./devops-engineer.md)
