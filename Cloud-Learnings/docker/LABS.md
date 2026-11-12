# Labs Reference

All labs are in the `labs/` directory. Each lab has 7 files:

| File | Purpose |
|---|---|
| `README.md` | Introduction, overview, learning objectives |
| `tasks.md` | Step-by-step tasks to complete |
| `commands.md` | Command reference for this lab |
| `expected-output.md` | What success looks like |
| `validate.md` | How to verify your work |
| `troubleshooting.md` | Common issues and fixes |
| `solution.md` | Full solution (try yourself first!) |

## Available Labs

### AWS / LocalStack (`labs/aws-localstack/`)

**Profile required**: `aws`
**Start**: `./run.sh start aws`

Tasks:
- Create S3 bucket locally with AWS CLI
- Upload and download objects to/from S3
- Create SQS queue, send and receive messages
- Create SNS topic and subscribe SQS queue
- Create DynamoDB table, write and query items
- Create Lambda function (Node.js), invoke it
- Use Terraform with LocalStack S3 backend
- Use `aws --endpoint-url` pattern throughout

---

### Azure / Azurite (`labs/azure-azurite/`)

**Profile required**: `azure`
**Start**: `./run.sh start azure`

Tasks:
- Start Azurite and connect Azure CLI
- Create blob container and upload blob
- Download blob and verify
- List blobs with metadata
- Send and receive queue messages
- Use Azure Storage Explorer connection string
- Table storage CRUD operations

---

### GCP Emulators (`labs/gcp-emulators/`)

**Profile required**: `gcp`
**Start**: `./run.sh start gcp`

Tasks:
- Configure environment for GCP emulators
- Create Pub/Sub topic and subscription
- Publish messages to Pub/Sub topic
- Pull and acknowledge messages
- Firestore document CRUD via emulator
- Use MinIO as GCS substitute for object storage
- Understand what requires real GCP vs what is emulated

---

### MinIO Object Storage (`labs/minio-object-storage/`)

**Profile required**: `aws`
**Start**: `./run.sh start aws`

Tasks:
- Create MinIO buckets via Console UI
- Upload objects via mc CLI
- Configure bucket policies
- Generate presigned URLs
- Set lifecycle rules
- Use MinIO as S3-compatible backend for Terraform
- Enable versioning

---

### Docker Networking (`labs/docker-networking/`)

**Profile required**: `core`
**Start**: `./run.sh start core`

Tasks:
- Inspect Docker networks created by the platform
- Test connectivity between containers on same/different networks
- DNS resolution between containers
- Port exposure and binding concepts
- Traefik routing rules
- Self-signed TLS certificate generation
- Reverse proxy configuration

---

### Linux Debugging (`labs/linux-debugging/`)

**Profile required**: `core`
**Start**: `./run.sh start core`

Tasks:
- Enter running containers via `docker exec`
- Use `ps`, `top`, `netstat`, `ss`, `lsof` inside containers
- Check logs with `journalctl` and Docker logs
- Disk space and filesystem checks
- Process debugging
- Network connectivity troubleshooting
- Grep and awk log analysis

---

### Kubernetes Local (`labs/kubernetes-local/`)

**Requires**: `kind` or `k3d` installed on host
**Start**: `./run.sh kubernetes create kind`

Tasks:
- Create local cluster
- Deploy pods, deployments, services
- Configure Ingress with nginx-ingress
- Create ConfigMaps and Secrets
- Persistent volumes with hostPath
- Helm chart install and upgrade
- Kustomize base + overlay
- Debug CrashLoopBackOff
- Fix service selector mismatch
- Simulate image pull failure

---

### Terraform / OpenTofu (`labs/terraform-opentofu/`)

**Profile required**: `aws` + `iac`
**Start**: `./run.sh start aws && ./run.sh start iac`

Tasks:
- Write basic Terraform with local backend
- Variables, outputs, data sources
- Use LocalStack AWS provider
- Create S3 bucket, SQS queue with Terraform
- Terraform state management
- State drift detection and remediation
- Import existing resource into state
- Use OpenTofu as drop-in replacement
- Remote backend using MinIO S3-compatible storage

---

### Ansible (`labs/ansible/`)

**Profile required**: `iac`
**Start**: `./run.sh start iac`

Tasks:
- Write inventory file targeting Docker containers
- Write basic playbook (install, configure, start service)
- Use variables and `vars_files`
- Jinja2 templates for config files
- Idempotency testing (run playbook twice, no changes)
- Handlers for service restarts
- Ansible vault for secrets (local)

---

### Observability (`labs/observability/`)

**Profile required**: `observability` + `apps`
**Start**: `./run.sh start observability && ./run.sh start apps`

Tasks:
- View Grafana dashboard
- Write a PromQL query in Prometheus
- Write a LogQL query in Loki (view app logs)
- View distributed trace in Tempo (from sample-api)
- Send custom metric from sample app
- Send custom log to Loki via Promtail
- Create an alert rule in Prometheus
- Build a Grafana dashboard panel
- Debug a broken metrics endpoint
- Debug missing logs scenario

---

### Security (`labs/security/`)

**Profile required**: `security`
**Start**: `./run.sh start security`

Tasks:
- Write and read a secret in Vault (KV v2)
- Enable Vault AppRole authentication
- Create Keycloak realm and client
- Configure OIDC token flow (concept)
- Scan Docker image with Trivy
- Scan Terraform code with Checkov
- Lint Dockerfile with Hadolint
- Identify and fix hardcoded secret
- Fix exposed port in Compose
- Fix insecure container (running as root)

---

### CI/CD (`labs/cicd/`)

**Profile required**: `cicd`
**Start**: `./run.sh start cicd`

Tasks:
- Create Gitea repository
- Push code to Gitea
- Create Jenkins pipeline job
- Write Jenkinsfile for: checkout, lint, build, test, push to registry
- Debug broken pipeline (missing env var)
- Debug broken pipeline (port conflict)
- Deploy sample app from Jenkins

---

### Databases (`labs/databases/`)

**Profile required**: `data`
**Start**: `./run.sh start data`

Tasks:
- PostgreSQL: CRUD, indexes, foreign keys, explain plan
- MySQL: CRUD, user grants, slow query log
- MongoDB: CRUD, aggregation pipeline, indexes
- Redis: strings, hashes, lists, expiry, pub/sub
- Cross-database backup and restore
- Connection troubleshooting (wrong password, wrong port)
- Database migration simulation

---

### Messaging (`labs/messaging/`)

**Profile required**: `messaging`
**Start**: `./run.sh start messaging`

Tasks:
- RabbitMQ: create exchange + queue, publish, consume
- RabbitMQ: dead-letter exchange setup
- Redpanda: create topic, produce, consume messages
- Redpanda: consumer group behavior
- Message durability (restart broker, check messages)
- Consumer failure and retry simulation
- Message schema using Schema Registry

---

### Serverless Events (`labs/serverless-events/`)

**Profile required**: `aws`
**Start**: `./run.sh start aws`

Tasks:
- LocalStack Lambda function (Node.js + Python)
- EventBridge-like event routing via LocalStack
- SQS trigger for Lambda
- SNS fan-out to multiple SQS queues
- Lambda with DynamoDB read/write

---

### FinOps Simulation (`labs/finops-simulation/`)

**Profile required**: `core` + `data`
**Start**: `./run.sh start data`

Tasks:
- Analyze fake cloud bill CSV dataset
- Identify top cost drivers
- Tag resources for cost allocation (simulation)
- Identify idle resources in sample data
- Rightsizing simulation
- Build cost dashboard in Grafana (fake metrics)
- Budget alert simulation

---

### SRE / Incident Response (`labs/sre-incident-response/`)

**Profile required**: `observability` + `apps`
**Start**: `./run.sh start observability && ./run.sh start apps`

Tasks:
- Use runbook to diagnose service down
- Identify high latency from metrics
- Fix bad environment variable config
- Debug database connection failure
- Identify queue backlog
- Simulate memory pressure and diagnose
- Simulate CPU pressure and diagnose
- Debug missing logs
- Debug bad deployment (wrong image tag)
- Write incident postmortem from template

---

### Broken Labs (`labs/broken-labs/`)

**Profile required**: varies
**Purpose**: Deliberately broken environments to fix

Scenarios:
- Broken DNS — container can't resolve hostname
- Broken container — app crashes on start, find root cause
- Broken DB — connection refused, wrong credentials
- Broken queue — messages not being consumed
- Broken Kubernetes — pod stuck in pending
- Broken Terraform — state locked, plan fails
- Broken pipeline — CI job never completes

---

### Real-World Projects (`labs/real-world-projects/`)

**Profile required**: varies (see individual README)

Projects:
- Static website with CDN simulation (MinIO + Nginx)
- Secure API platform (Vault secrets, Keycloak auth)
- 3-tier application (Frontend + API + PostgreSQL)
- Event-driven order system (RabbitMQ + worker)
- Kubernetes microservices (kind + Helm)
- Full observability platform (LGTM stack)
- Multi-cloud object storage (LocalStack + Azurite + MinIO)
- Disaster recovery simulation (backup + restore)
- CI/CD pipeline (Gitea + Jenkins + Registry)

---

## Running Labs

```bash
# List all labs
./run.sh lab list

# Start a lab (shows README and starts required services)
./run.sh lab start aws-localstack

# Validate lab completion
./run.sh lab validate aws-localstack

# Reset lab to clean state
./run.sh lab reset aws-localstack
```

## Adding Labs

See [docs/adding-new-labs.md](docs/adding-new-labs.md) for instructions on creating custom labs.
