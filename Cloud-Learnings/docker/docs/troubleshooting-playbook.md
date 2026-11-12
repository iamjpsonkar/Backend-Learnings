# Troubleshooting Playbook

A structured approach to diagnosing issues with the platform.

## Playbook: Service Not Starting

**Symptom**: `./run.sh status` shows container in restart loop or exited.

**Step 1 — Check logs**
```bash
docker logs cloud-learnings-<service> --tail=50
```
Look for the last line before the crash. This usually contains the error.

**Step 2 — Check common causes**

| Error in logs | Likely cause | Fix |
|---|---|---|
| `port is already allocated` | Port conflict | Change port in .env |
| `FATAL: database "X" does not exist` | Wrong DB name | Check POSTGRES_DB in .env |
| `Connection refused` | Dependency not ready | Check depends_on health |
| `OOMKilled` | Out of memory | Increase Docker Desktop memory |
| `no such file or directory` | Missing config file | Check configs/ directory |
| `permission denied` | File permissions | `chmod -R 755 configs/` |

**Step 3 — Check dependencies**
```bash
# Check what the service depends on
docker inspect cloud-learnings-<service> | jq '.[0].HostConfig.Links'
```

**Step 4 — Try manual start**
```bash
docker compose --project-name cloud-learnings-lab --file docker-compose.yml \
  up -d <service>
```

---

## Playbook: Cannot Connect to Service

**Symptom**: `curl http://localhost:PORT` returns connection refused.

**Step 1 — Check if container is running**
```bash
docker ps | grep cloud-learnings
```

**Step 2 — Check if port is exposed**
```bash
docker port cloud-learnings-<service>
```

**Step 3 — Check if port is free on host**
```bash
lsof -i :<PORT>
```

**Step 4 — Test from inside container**
```bash
# If the service is inside Docker, test from inside
docker exec cloud-learnings-<service> curl localhost:<INTERNAL_PORT>
```

**Step 5 — Check firewall**
```bash
# macOS: System Preferences → Security → Firewall
# Linux: sudo iptables -L | grep REJECT
```

---

## Playbook: Database Won't Accept Connections

**Step 1 — Check health status**
```bash
docker inspect --format='{{.State.Health.Status}}' cloud-learnings-postgres
```

**Step 2 — Test connection directly**
```bash
docker exec cloud-learnings-postgres \
  psql -U labuser -d labdb -c "SELECT 1"
```

**Step 3 — Check credentials match .env**
```bash
grep POSTGRES_ .env
```

**Step 4 — Check init scripts ran**
```bash
docker logs cloud-learnings-postgres 2>&1 | grep -i "init\|error"
```

---

## Playbook: Observability Not Collecting Data

**Step 1 — Verify Prometheus targets**
```bash
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

**Step 2 — Check scrape interval**
Wait at least 15 seconds after starting services for first scrape.

**Step 3 — Check Loki**
```bash
curl http://localhost:3100/ready
curl http://localhost:3100/loki/api/v1/labels
```

**Step 4 — Check Promtail**
```bash
docker logs cloud-learnings-promtail --tail=20
```

**Step 5 — Generate some traffic**
```bash
for i in $(seq 1 10); do curl -s http://localhost:8000/health; sleep 1; done
```

---

## Playbook: Out of Memory

**Symptom**: Containers crash with `OOMKilled` or Docker Desktop is slow.

**Step 1 — Check current usage**
```bash
docker stats --no-stream
```

**Step 2 — Identify high-memory services**
Typical memory usage:
- Keycloak: 512MB - 1GB
- Jenkins: 512MB - 1GB
- Grafana: 200MB
- Prometheus: 200MB
- LocalStack: 500MB

**Step 3 — Stop unnecessary profiles**
```bash
docker compose --project-name cloud-learnings-lab stop keycloak jenkins
```

**Step 4 — Increase Docker Desktop limits**
Docker Desktop → Settings → Resources → Memory: 8GB

---

## Playbook: LocalStack Not Ready

**Step 1 — Wait**
LocalStack takes 30-60 seconds on first start. Be patient.

**Step 2 — Check health**
```bash
curl http://localhost:4566/_localstack/health | jq .
```

**Step 3 — Check logs**
```bash
docker logs cloud-learnings-localstack 2>&1 | tail -30
```

**Step 4 — Common fixes**
```bash
# Restart LocalStack
docker restart cloud-learnings-localstack
# Wait 60 seconds
curl http://localhost:4566/_localstack/health
```

---

## Playbook: CI/CD Pipeline Failing

**Step 1 — Check Jenkins is running**
```bash
curl http://localhost:8090/login
```

**Step 2 — Get unlock key (first time setup)**
```bash
docker exec cloud-learnings-jenkins \
  cat /var/jenkins_home/secrets/initialAdminPassword
```

**Step 3 — Check Gitea is accessible**
```bash
curl http://localhost:3002
```

**Step 4 — Check registry is up**
```bash
curl http://localhost:5000/v2/_catalog
```
