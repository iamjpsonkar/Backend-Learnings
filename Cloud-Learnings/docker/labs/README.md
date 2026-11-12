# Labs

Guided labs with tasks, commands, expected output, validation, troubleshooting, and solutions.

## How Labs Work

Each lab directory contains 7 files:

| File | Purpose |
|---|---|
| `README.md` | Lab introduction, objectives, prerequisites |
| `tasks.md` | Step-by-step tasks to complete |
| `commands.md` | Command reference for this lab |
| `expected-output.md` | Screenshots/text of what success looks like |
| `validate.md` | How to verify your work |
| `troubleshooting.md` | Common issues in this lab |
| `solution.md` | Full solution (try yourself first!) |

## Running Labs

```bash
# List all labs
./run.sh lab list

# Start a lab
./run.sh lab start aws-localstack

# Validate your work
./run.sh lab validate aws-localstack

# Reset to clean state
./run.sh lab reset aws-localstack
```

## Labs Index

See [lab-index.yaml](lab-index.yaml) for machine-readable lab metadata.

| Lab ID | Topic | Profile | Difficulty |
|---|---|---|---|
| aws-localstack | AWS services via LocalStack | aws | Beginner |
| azure-azurite | Azure storage via Azurite | azure | Beginner |
| gcp-emulators | GCP Pub/Sub + Firestore emulators | gcp | Beginner |
| minio-object-storage | S3-compatible storage with MinIO | aws | Beginner |
| docker-networking | Docker networks and DNS | core | Beginner |
| linux-debugging | Container debugging skills | core | Beginner |
| kubernetes-local | Local Kubernetes with kind/k3d | — (host) | Intermediate |
| terraform-opentofu | Terraform and OpenTofu with LocalStack | aws,iac | Intermediate |
| ansible | Ansible playbooks and configuration | iac | Intermediate |
| observability | Prometheus, Grafana, Loki, Tempo | observability | Intermediate |
| security | Vault, Keycloak, Trivy, Checkov | security | Intermediate |
| cicd | Gitea + Jenkins + Docker Registry | cicd | Intermediate |
| databases | PostgreSQL, MySQL, MongoDB, Redis | data | Beginner |
| messaging | RabbitMQ + Redpanda | messaging | Intermediate |
| serverless-events | Lambda + EventBridge via LocalStack | aws | Intermediate |
| finops-simulation | Cloud cost simulation | data | Intermediate |
| sre-incident-response | Incident response practice | observability,apps | Advanced |
| broken-labs | Broken environments to fix | varies | Advanced |
| real-world-projects | End-to-end project practice | varies | Advanced |
