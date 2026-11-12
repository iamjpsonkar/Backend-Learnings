# Security Guide

## Credential Safety

### All credentials in this platform are fake and local-only

The `.env.example` file contains:

- **Fake AWS credentials** (`AWS_ACCESS_KEY_ID=test`) — work only with LocalStack, not real AWS
- **Fake Azure storage keys** — the default Azurite key is public knowledge, designed for local dev
- **Fake GCP project ID** — `local-dev-project` is not a real GCP project
- **Fake database passwords** — `labpassword123` etc. are for local containers only
- **Vault dev token** — `dev-root-token` is the LocalStack/dev-mode default, not production
- **Keycloak admin password** — `adminpassword123` is local-only

**Never use any of these values in real cloud environments.**

### What to do with real credentials

If you ever need to test against real cloud services (optional extension):

1. Create a **separate** `.env.real` file — never commit it
2. Add it to `.gitignore` (already included)
3. Use IAM roles or short-lived tokens where possible
4. Use least-privilege principles — never use root/owner accounts
5. Set budget alerts before testing anything with billing

---

## Docker Socket Access

Several containers mount the Docker socket (`/var/run/docker.sock`):

| Container | Reason | Risk Level |
|---|---|---|
| Traefik | Reads container labels for routing | Low (read-only) |
| Homepage | Reads container status for dashboard | Low (read-only) |
| Portainer | Full Docker management UI | **High** (opt-in only) |
| LocalStack | Lambda execution | Medium |
| Jenkins | Building Docker images | Medium |
| Trivy | Scanning local images | Low (read-only) |

All mounts use `:ro` (read-only) except Jenkins and LocalStack.

**Portainer** has full Docker socket access and should only be used in trusted local environments. It is behind the `dashboard` profile and requires opt-in. Enable only if you understand the risk.

### Mitigations

- All socket mounts are on `127.0.0.1` only — not exposed to network
- Portainer is opt-in (`ENABLE_PORTAINER=false` by default in `.env`)
- Jenkins uses a pre-built image with Docker installed — never run untrusted Jenkinsfiles

---

## Privileged Containers

No containers run with `--privileged` by default.

Vault requires `CAP_IPC_LOCK` to prevent secrets from being swapped to disk. This is minimal and specific.

If you add privileged containers for Kubernetes labs (DinD), mark them clearly and only run them locally.

---

## Port Exposure

All ports bind to `127.0.0.1` (localhost) by default. Services are NOT accessible from the network.

If you change port bindings to `0.0.0.0`, services become accessible from the network. Do this only if:
- You're on a trusted isolated network
- You explicitly need remote access for testing

**Never expose Vault, Keycloak, Traefik dashboard, or Jenkins to the internet without authentication.**

### Port security summary

| Service | Port | Authentication | Notes |
|---|---|---|---|
| Traefik dashboard | 8080 | None (insecure mode) | Local only |
| Homepage | 3000 | None | Local only |
| Vault | 8200 | Token required | Dev token in .env |
| Keycloak | 8180 | Admin password | Local only |
| Grafana | 3001 | admin/admin | Local only, change for real use |
| Portainer | 9000 | Setup on first use | Opt-in only |
| Jenkins | 8090 | Password on first use | Local only |
| LocalStack | 4566 | None (dev mode) | Local only |
| PostgreSQL | 5432 | Password | Local only |
| Redis | 6379 | Password | Local only |

---

## Secrets in Logs

This platform does **not** log secrets. However:

- Database passwords appear in connection strings in app logs — these are fake local passwords
- Vault tokens appear in CLI commands in lab documentation — these are dev-mode tokens
- Never paste real credentials into any log, issue, or document

---

## Network Isolation

Internal networks (`private_net`, `data_net`, `security_net`) have `internal: true` set. This means:

- Containers on these networks cannot reach the internet
- Containers can only communicate with other containers on the same network
- Databases, security tools, and internal services are isolated from public access

This simulates a real cloud network segmentation:
- Databases are not publicly accessible
- Internal APIs don't have public routes
- Security tools are isolated from the public zone

---

## Image Security

### Scanning images

Use Trivy to scan any image:

```bash
# Scan an image from Docker Hub
docker exec -it cloud-learnings-trivy trivy image nginx:alpine

# Scan a locally built image
docker exec -it cloud-learnings-trivy trivy image cloud-learnings-sample-api:local

# Output to file
docker exec -it cloud-learnings-trivy trivy image --output /reports/nginx-scan.json --format json nginx:alpine
```

### Scanning Terraform/IaC

```bash
docker exec -it cloud-learnings-checkov checkov -d /workspace
```

### Scanning Dockerfiles

```bash
docker exec -it cloud-learnings-hadolint hadolint /workspace/sample-api/Dockerfile
```

---

## Real Cloud Credential Warnings

If you ever extend this platform to use real cloud credentials:

1. **Never commit `.env` with real credentials**
   - `.gitignore` already excludes `.env`
   - Use `git secrets` or `gitleaks` to prevent accidental commits

2. **Use short-lived credentials**
   - AWS: IAM roles or `aws sts assume-role` with expiry
   - Azure: Service Principal with OIDC (workload identity)
   - GCP: Workload Identity Federation

3. **Use least privilege**
   - Never use root account
   - Never use `AdministratorAccess` policy
   - Create a dedicated IAM user with only needed permissions

4. **Set budget alerts**
   - Before any real cloud test, set a $5-10 budget alert
   - Enable cost anomaly detection

5. **Clean up real resources**
   - Run `terraform destroy` after real cloud labs
   - Check cloud console for orphaned resources
   - Unused resources continue to bill

---

## Cleanup

Always clean up when done:

```bash
./run.sh stop           # Stop containers (data preserved)
./run.sh clean          # Remove containers + volumes (data lost)
./run.sh nuke           # Full reset
```

Cleaning removes:
- All containers with label `com.cloudlearnings.project=cloud-learnings-lab`
- All volumes with the same label
- All networks with the same label

It does NOT remove:
- Files in `docker/` directory
- `.env` file
- Any host system files

---

## Security Best Practices for This Platform

1. Run only as your own user — never `sudo docker`
2. Don't expose ports to `0.0.0.0` on untrusted networks
3. Keep Docker Desktop updated
4. Use `./run.sh clean` when done — don't leave services running indefinitely
5. Don't install unknown plugins in Keycloak or Jenkins in local labs
6. Never mount `/` or sensitive host directories into containers
7. Review Dockerfiles in `apps/` before building — they are safe but always verify
