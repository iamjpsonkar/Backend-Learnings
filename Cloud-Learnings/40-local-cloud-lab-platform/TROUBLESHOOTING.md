# Troubleshooting Guide

---

## General Debugging Commands

```bash
make status                     # show all container states
make logs SERVICE=api           # tail API logs
make logs SERVICE=ui            # tail UI logs
make logs SERVICE=minio         # tail MinIO logs
make doctor                     # recheck all requirements
make health                     # check all service health endpoints
```

---

## Docker Issues

### "Cannot connect to the Docker daemon"

```bash
# Check Docker is running
docker info

# macOS: start Docker Desktop manually or:
open -a Docker

# Linux: start the daemon
sudo systemctl start docker
sudo systemctl enable docker

# Add yourself to docker group (requires re-login)
sudo usermod -aG docker $USER
newgrp docker
```

### "Error response from daemon: pull access denied"

Docker Hub rate limiting. Solutions:

```bash
# Log in to Docker Hub (free account)
docker login

# Or use a local mirror — add to /etc/docker/daemon.json:
# { "registry-mirrors": ["https://mirror.gcr.io"] }
```

### "No space left on device"

```bash
# See what's using space
docker system df

# Clean up unused images, containers, volumes
docker system prune -a --volumes

# Then retry
make start-core
```

### Container keeps restarting

```bash
# Find which container
make status

# View its logs
make logs SERVICE=<name>

# Or directly
docker compose logs --tail=50 <service-name>
```

### Port already in use

```bash
# Find what's using the port (example: 4567)
lsof -i :4567

# Kill it
kill -9 <PID>

# Or change the port in .env:
# LAB_API_PORT=4568
# Then restart: make stop && make start-core
```

---

## Docker Compose Issues

### "service ... failed to build"

```bash
# Force rebuild without cache
make rebuild SERVICE=api
make rebuild SERVICE=ui

# Or manually
docker compose build --no-cache api
```

### "Profile not found"

Make sure you're running from the `40-local-cloud-lab-platform/` directory:

```bash
cd /path/to/Cloud-Learnings/40-local-cloud-lab-platform
make start-core
```

### Volumes not mounting on macOS

Docker Desktop may need file sharing permissions:
1. Open Docker Desktop > Settings > Resources > File Sharing
2. Add the parent directory of this repo
3. Apply & Restart

---

## API Issues

### "Connection refused" on http://localhost:4567

```bash
# Check if the container is running
docker compose ps api

# View API startup logs
make logs SERVICE=api

# Common cause: Python dependency install failed during build
make rebuild SERVICE=api
```

### API returns 500 errors

```bash
# View detailed logs
make logs SERVICE=api

# Check the database
make db-shell
# Inside sqlite shell: .tables; select * from labs limit 5;

# Reset the database (wipes progress)
make reset-db
```

### Lab YAML validation fails on startup

```bash
# See which YAML files failed
make validate-labs

# View specific lab definition
cat labs/04-docker/docker-basics/lab.yaml
```

---

## UI Issues

### "http://localhost:3001" shows blank page or error

```bash
# Check UI container
docker compose ps ui
make logs SERVICE=ui

# Rebuild UI
make rebuild SERVICE=ui

# Check if API is reachable from UI
curl http://localhost:4567/health
```

### UI shows "API Unreachable"

The UI talks to the API on port 4567. Check:
1. API container is running: `docker compose ps api`
2. Port 4567 is not firewalled
3. `.env` has matching `LAB_API_PORT`

---

## Kubernetes (kind) Issues

### "kind: command not found"

```bash
# macOS
brew install kind

# Linux
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.23.0/kind-linux-amd64
chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind
```

### "cannot create cluster" / "failed to create cluster"

```bash
# Check Docker is running and has enough resources
docker info | grep -E "Memory|CPUs"

# Delete any existing lab cluster and recreate
kind delete cluster --name cloud-lab
make k8s-create-cluster
```

### kubectl can't reach the cluster

```bash
# Export the kubeconfig
kind export kubeconfig --name cloud-lab

# Verify
kubectl cluster-info --context kind-cloud-lab
```

---

## LocalStack Issues

### LocalStack container exits immediately

```bash
make logs SERVICE=localstack

# Common cause: not enough memory
# Increase Docker Desktop memory to at least 4 GB
```

### AWS CLI commands fail against LocalStack

```bash
# Always use --endpoint-url flag for LocalStack
aws --endpoint-url=http://localhost:4566 s3 ls

# Or use the awslocal wrapper installed by the lab
awslocal s3 ls

# Check LocalStack is ready
curl http://localhost:4566/health | jq .
```

---

## Vault Issues

### Vault sealed after restart

```bash
# Vault starts in dev mode — it auto-unseals
# If it's not starting, check logs
make logs SERVICE=vault

# Re-initialize for labs (dev mode)
make vault-init
```

### Cannot connect to Vault

```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=dev-root-token
vault status
```

---

## Performance Issues

### Everything is slow

```bash
# Check resource usage
docker stats --no-stream

# Stop profiles you're not using
make stop-observability
make stop-security
make stop-cicd
```

### High disk I/O (macOS)

On macOS, Docker Desktop volumes have overhead. Labs that need high I/O (databases, Kafka)
run slower than on Linux. This is expected — results are still correct.

Enable VirtioFS in Docker Desktop > Settings > General > "Use VirtioFS" for better performance.

---

## Lab Runner Issues

### "Lab not found"

```bash
# List available labs
make list-labs

# Use exact path (category/lab-name)
make run-lab LAB=04-docker/docker-basics   # correct
make run-lab LAB=docker-basics              # wrong
```

### Validation fails even when I completed the task

```bash
# View validation details
make run-lab LAB=04-docker/docker-basics VERBOSE=1

# View the validation script
cat labs/04-docker/docker-basics/validate.sh
```

### Grade script error

```bash
# Check the grade script directly
bash labs/04-docker/docker-basics/grade.sh

# View lab runner output in full
python3 lab-runner/runner.py run --lab=04-docker/docker-basics --verbose
```

---

## Reset and Cleanup

### Reset everything (wipes all progress and data)

```bash
make reset --confirm
```

### Remove only Docker resources from this lab platform

```bash
# Safe — only removes containers/volumes labelled com.cloudlabs.project=local-cloud-lab
make cleanup --confirm
```

### Keep lab data but restart services

```bash
make stop
make start-core    # or whichever profile
```

---

## Getting More Help

1. Check container logs: `make logs SERVICE=<name>`
2. Run diagnostics: `make doctor`
3. View all running containers: `make status`
4. Check the [GitHub Issues](https://github.com/iamjpsonkar/Cloud-Learnings/issues) for known problems
5. Open an issue with `make bug-report` output attached
