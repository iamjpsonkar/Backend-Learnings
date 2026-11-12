# Projects

Multi-service projects that combine multiple platform skills into end-to-end scenarios.
Unlike labs (which focus on one skill), projects build a complete system.

## Available Projects

| Project | Skills | Profiles |
|---------|--------|---------|
| [E-Commerce Platform](01-ecommerce/) | Docker, PostgreSQL, Redis, MinIO, Traefik | core, data |
| [Microservices on Kubernetes](02-k8s-microservices/) | Kubernetes, Helm, GitOps | kubernetes, cicd |
| [Observability Stack from Scratch](03-observability-stack/) | Prometheus, Grafana, OTel, Loki | observability |
| [GitOps CI/CD Pipeline](04-gitops-pipeline/) | Gitea, Woodpecker CI, ArgoCD, Kubernetes | cicd, kubernetes |
| [Serverless Event Pipeline](05-event-pipeline/) | Redpanda, RabbitMQ, Lambda (LocalStack) | data, aws-local |
| [Multi-Cloud Disaster Recovery](06-multi-cloud-dr/) | LocalStack, Azurite, Terraform | aws-local, azure-local |

## Running a Project

```bash
make run-lab LAB=projects/01-ecommerce
```

Projects take 2–8 hours to complete and are ideal for portfolio building.

## Project Structure

```
projects/<name>/
├── README.md          # Project overview, architecture, goals
├── lab.yaml           # Lab definition (same schema as labs/)
├── architecture/      # Architecture diagrams
├── services/          # Docker Compose services for the project
├── config/            # Configuration files
└── solution/          # Reference implementation
```
