# Troubleshooting

## Quick Diagnosis

```bash
./run.sh doctor     # Checks prerequisites, ports, memory, disk
./run.sh status     # Shows container status
./run.sh logs       # Shows all logs
./run.sh validate   # Runs health checks against running services
```

---

## Container Issues

### Container keeps restarting

```bash
# Check restart count and last exit code
docker ps -a --filter "name=cloud-learnings"

# Read the logs for the specific container
./run.sh logs <service-name>
# Example:
./run.sh logs postgres
./run.sh logs localstack
```

Common causes:
- Port already in use by another process
- Insufficient memory (Docker Desktop memory limit too low)
- Volume permission issue
- Missing config file

### Container exits immediately

```bash
# Check last 100 lines of logs
docker logs --tail=100 cloud-learnings-<service>
```

### All containers fail to start

```bash
# Check if Docker daemon is running
docker info

# Check available memory
free -h        # Linux
vm_stat        # macOS

# Restart Docker Desktop (macOS)
# Settings → Troubleshoot → Restart Docker
```

---

## Port Conflicts

### Error: Bind for 0.0.0.0:PORT failed: port is already allocated

```bash
# Find what's using the port (macOS/Linux)
lsof -i :5432      # Example: Postgres port
lsof -i :4566      # Example: LocalStack port
```

Fix:
1. Stop the conflicting process, OR
2. Change the port in `.env`:
   ```env
   POSTGRES_PORT=5433
   ```
3. Restart: `./run.sh stop && ./run.sh start <profile>`

---

## Memory Issues

### Services crashing with OOMKilled

Docker Desktop has a default memory limit. Increase it:

1. Docker Desktop → Settings → Resources
2. Set Memory: 8 GB (minimum for heavy profiles)
3. Apply and Restart

Check container memory usage:
```bash
./run.sh resources
# or
docker stats --no-stream
```

### Which profiles to avoid on low memory

| Available RAM | Recommended |
|---|---|
| 4 GB | core only |
| 6 GB | core + one profile (data or aws) |
| 8 GB | core + cloud + data |
| 12 GB | core + observability + security |
| 16 GB+ | all |

---

## LocalStack (AWS Emulator)

### LocalStack health check fails

```bash
curl http://localhost:4566/_localstack/health
```

Expected response includes `"running": true`.

If not ready yet, wait 60 seconds on first start (downloads AWS service binaries).

### AWS CLI returns error: Unable to connect to endpoint

Make sure you always use `--endpoint-url`:

```bash
aws --endpoint-url=http://localhost:4566 s3 ls
```

Or set in shell session:
```bash
export AWS_ENDPOINT_URL=http://localhost:4566
aws s3 ls
```

### Lambda not working in LocalStack free tier

Lambda execution requires LocalStack Pro for full support.
Free tier supports basic invocation with `local` executor.

Check `LAMBDA_EXECUTOR=local` is set in `.env`.

---

## PostgreSQL

### psql: FATAL: password authentication failed

Check credentials in `.env`:
```env
POSTGRES_USER=labuser
POSTGRES_PASSWORD=labpassword123
POSTGRES_DB=labdb
```

Connect:
```bash
docker exec -it cloud-learnings-postgres \
  psql -U labuser -d labdb
```

### pg_isready returns "no response"

PostgreSQL is still starting. Wait for health check to pass:
```bash
docker inspect --format '{{.State.Health.Status}}' cloud-learnings-postgres
```

---

## Azurite (Azure Storage)

### Connection string not working

Use the exact connection string from `.env.example`:
```
DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=...;BlobEndpoint=http://localhost:10000/devstoreaccount1;
```

### Azure CLI commands failing

Azurite doesn't implement every Azure API. Some operations require real Azure.

Set connection string:
```bash
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;..."
az storage container list
```

---

## Vault

### Vault sealed

Dev mode Vault starts unsealed. If it becomes sealed (container restart), check:

```bash
docker exec -it cloud-learnings-vault vault status
# If sealed:
docker exec -it cloud-learnings-vault vault operator unseal
```

Note: Dev mode Vault doesn't persist data across restarts by design.

### Error: missing client token

Set the root token:
```bash
export VAULT_TOKEN=dev-root-token
export VAULT_ADDR=http://localhost:8200
vault kv put secret/test value=hello
```

---

## Keycloak

### Keycloak takes too long to start

Keycloak is JVM-based and takes 60-120 seconds on first start. Check:
```bash
./run.sh logs keycloak
```

Wait for: `Keycloak 24.x.x on JVM (powered by Quarkus x.x.x) started`

### Keycloak admin console returns 404

Use the correct URL: `http://localhost:8180/admin` (not `/admin/`)

---

## Grafana / Observability

### Grafana shows no data

1. Check if Prometheus is running and collecting metrics:
   ```
   http://localhost:9090/targets
   ```
2. Check the data source is configured correctly in Grafana:
   - Connections → Data Sources → Prometheus → URL: `http://prometheus:9090`

### Loki not receiving logs

Check Promtail is running and pointing to the correct Loki URL:
```bash
./run.sh logs promtail
```

Verify Loki is healthy:
```bash
curl http://localhost:3100/ready
```

---

## CI/CD

### Jenkins initial setup

On first start, get the initial admin password:
```bash
docker exec cloud-learnings-jenkins \
  cat /var/jenkins_home/secrets/initialAdminPassword
```

Then navigate to `http://localhost:8090` and enter the password.

### Gitea first run

Gitea requires initial configuration on first visit:
1. Open `http://localhost:3002`
2. Accept default settings (SQLite, etc.)
3. Create admin account

---

## Build Issues

### Docker build fails for sample apps

```bash
# Check build logs
docker compose --project-name cloud-learnings-lab build --no-cache sample-api
docker compose --project-name cloud-learnings-lab build --no-cache jenkins
```

### Image pull fails (rate limit or network issue)

```bash
# Pull images manually one at a time
docker pull postgres:16-alpine
docker pull localstack/localstack:3.0
```

For Docker Hub rate limits, log in:
```bash
docker login
```

---

## Clean and Reset

### Start completely fresh

```bash
./run.sh stop
./run.sh nuke
./run.sh setup
./run.sh start core
```

### Remove only a specific service's data

```bash
# Example: reset PostgreSQL data
docker stop cloud-learnings-postgres
docker volume rm cloud-learnings-postgres-data
./run.sh start data
```

### Fix volume permission errors

```bash
# Remove all project volumes
docker compose --project-name cloud-learnings-lab down -v
```

---

## Docker Compose Errors

### Error: No such service

Make sure you're running from the `docker/` directory:
```bash
cd /path/to/Cloud-Learnings/docker
./run.sh start core
```

### Error: service profile not found

Check available profiles:
```bash
docker compose config --profiles
```

### Error: no configuration file provided

You must be in the `docker/` directory or use the full path:
```bash
cd docker && ./run.sh start core
```

---

## macOS Specific

### Docker socket permission denied

Docker Desktop manages socket access. If you see permission errors:
1. Ensure Docker Desktop is running
2. Settings → Advanced → Allow the default Docker socket to be used

### Slow performance on macOS

- Use Docker Desktop's VirtioFS file sharing (Settings → General → VirtioFS)
- Avoid mounting many large directories as volumes
- Use named volumes instead of bind mounts for databases

---

## Windows (WSL2) Specific

### Containers not starting in WSL2

1. Make sure Docker Desktop WSL2 integration is enabled
2. Run everything from WSL2 terminal (not PowerShell)
3. Clone repo inside WSL2 filesystem: `~/Cloud-Learnings/docker/`
   (NOT from `/mnt/c/...` — filesystem is slow)

### File permission issues on WSL2

Set correct permissions in WSL2:
```bash
chmod +x run.sh
chmod -R 755 configs/
```

---

## Still Stuck?

1. Read the service-specific docs in `docs/`
2. Check lab-specific `troubleshooting.md` files
3. Run `./run.sh doctor` and share the output
4. Check Docker logs: `docker logs --tail=200 cloud-learnings-<service>`
