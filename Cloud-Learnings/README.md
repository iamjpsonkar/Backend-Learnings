# Cloud-Learnings

A comprehensive, vendor-neutral knowledge base for cloud engineering, DevOps, infrastructure, security, and platform reliability.

Covers AWS, Azure, GCP, Kubernetes, Terraform, Ansible, CI/CD, SRE, FinOps, and more — with hands-on examples, real-world patterns, cheatsheets, and interview prep.

---

## Quick Start

**Read documentation** → Start at [00-foundations](./00-foundations/README.md)

**Practice locally (simple)** → [docker/QUICKSTART.md](./docker/QUICKSTART.md)
- Single `docker-compose.yml` with profiles, interactive `./run.sh` menu, 19 labs, 14 profiles

**Practice locally (advanced)** → [40-local-cloud-lab-platform/QUICKSTART.md](./40-local-cloud-lab-platform/QUICKSTART.md)
- FastAPI backend, React dashboard, 30 structured lab exercises, lab runner with validation and grading

---

## Repository Structure

| Section | Topics |
|---------|--------|
| [00-foundations](./00-foundations/README.md) | Cloud concepts, IaaS/PaaS/SaaS, shared responsibility, regions |
| [01-cloud-fundamentals](./01-cloud-fundamentals/README.md) | Compute, storage, networking, databases, IAM, serverless |
| [02-linux](./02-linux/README.md) | Filesystem, users, processes, shell scripting, SSH |
| [03-networking](./03-networking/README.md) | OSI, TCP/IP, DNS, CIDR, NAT, firewalls, load balancing |
| [04-git-devops-basics](./04-git-devops-basics/README.md) | Git workflow, GitHub, SSH keys |
| [05-aws](./05-aws/README.md) | Full AWS service coverage — compute, storage, networking, security |
| [06-azure](./06-azure/README.md) | Azure services — compute, storage, Entra ID, AKS |
| [07-gcp](./07-gcp/README.md) | GCP services — GKE, Cloud Run, BigQuery, IAM |
| [08-other-clouds](./08-other-clouds/README.md) | OCI, IBM Cloud, Alibaba, DigitalOcean, Cloudflare |
| [09-containers](./09-containers/README.md) | Docker, Dockerfile, Docker Compose, registries |
| [10-kubernetes](./10-kubernetes/README.md) | Architecture, workloads, networking, RBAC, Helm |
| [11-terraform-opentofu](./11-terraform-opentofu/README.md) | Providers, modules, state backends, security |
| [12-ansible](./12-ansible/README.md) | Playbooks, roles, real-world examples |
| [13-cicd-gitops](./13-cicd-gitops/README.md) | GitHub Actions, GitLab CI, ArgoCD, FluxCD |
| [14-security](./14-security/README.md) | IAM, zero-trust, secrets, encryption, container security |
| [15-observability](./15-observability/README.md) | Metrics, logs, traces, dashboards, golden signals |
| [16-sre](./16-sre/README.md) | SLI/SLO/SLA, error budgets, incidents, postmortems |
| [17-finops](./17-finops/README.md) | Pricing models, budgets, rightsizing, cost optimization |
| [18-databases](./18-databases/README.md) | SQL vs NoSQL, caching, queues |
| [19-disaster-recovery](./19-disaster-recovery/README.md) | RTO/RPO, backup-restore, multi-region strategies |
| [20-migration](./20-migration/README.md) | Migration strategies, hybrid connectivity |
| [21-multi-cloud](./21-multi-cloud/README.md) | Multi-cloud strategy, vendor lock-in |
| [22-projects](./22-projects/README.md) | Real-world end-to-end projects |
| [23-troubleshooting](./23-troubleshooting/README.md) | Production readiness, networking, Kubernetes, Terraform |
| [24-cheatsheets](./24-cheatsheets/README.md) | Quick reference for AWS, Kubernetes, Terraform, Linux |
| [25-glossary](./25-glossary/README.md) | Terminology and definitions |
| [26-roadmaps](./26-roadmaps/README.md) | Beginner, intermediate, and advanced learning paths |
| [27-interview-prep](./27-interview-prep/README.md) | AWS, Kubernetes, networking, security questions |
| [28-references](./28-references/README.md) | Official docs, books, and curated links |
| [docker/](./docker/README.md) | Local Docker Lab Platform — single compose, 14 profiles, 19 labs, interactive run.sh |
| [40-local-cloud-lab-platform/](./40-local-cloud-lab-platform/README.md) | Advanced Lab Platform — FastAPI API, React UI, 30 structured labs, validation + grading |

---

## Learning Paths

| Goal | Path |
|------|------|
| **Beginner** | [00-foundations](./00-foundations/README.md) → [01-cloud-fundamentals](./01-cloud-fundamentals/README.md) → [02-linux](./02-linux/README.md) → [05-aws](./05-aws/README.md) → [docker/LABS.md](./docker/LABS.md) |
| **DevOps / SRE** | [09-containers](./09-containers/README.md) → [10-kubernetes](./10-kubernetes/README.md) → [11-terraform-opentofu](./11-terraform-opentofu/README.md) → [13-cicd-gitops](./13-cicd-gitops/README.md) → [16-sre](./16-sre/README.md) → [docker/](./docker/README.md) |
| **Cloud Certifications** | Provider section → [24-cheatsheets](./24-cheatsheets/README.md) → [27-interview-prep](./27-interview-prep/README.md) |
| **Hands-on Practice** | [docker/QUICKSTART.md](./docker/QUICKSTART.md) or [40-local-cloud-lab-platform/QUICKSTART.md](./40-local-cloud-lab-platform/QUICKSTART.md) → [22-projects](./22-projects/README.md) |

---

## Assets

- Images: [assets/images/](./assets/images/) — organized by provider
- Diagrams: [assets/diagrams/](./assets/diagrams/) — Mermaid, SVG, Draw.io sources
- Attributions: [assets/ATTRIBUTIONS.md](./assets/ATTRIBUTIONS.md)

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on adding or improving content.

## License

[MIT](./LICENSE)

---

[Next: Foundations →](./00-foundations/README.md)
