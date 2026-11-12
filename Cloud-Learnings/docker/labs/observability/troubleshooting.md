# Troubleshooting — Observability

## Grafana shows "No data"

1. Check if Prometheus is running:
   ```bash
   curl http://localhost:9090/-/healthy
   ```
2. Check Grafana data source configuration:
   - Grafana → Connections → Data Sources → Prometheus
   - URL must be: `http://prometheus:9090` (not localhost — uses Docker DNS)
3. Check time range in Grafana (top right) — set to "Last 15 minutes"

## Prometheus target shows DOWN

```bash
# Check if service is running
docker ps | grep sample-api

# Check service logs
docker logs cloud-learnings-sample-api --tail=20

# Manually check the metrics endpoint
curl http://localhost:8000/metrics
```

## Loki shows no logs

1. Check Promtail is running:
   ```bash
   docker logs cloud-learnings-promtail --tail=20
   ```
2. Promtail needs Docker socket access — verify `/var/run/docker.sock` is mounted
3. Verify Loki is healthy: `curl http://localhost:3100/ready`

## Tempo shows no traces

1. Check OTel Collector is running:
   ```bash
   docker logs cloud-learnings-otel-collector --tail=20
   ```
2. Make sure sample-api is started (`./run.sh start apps`)
3. Hit the trace endpoint:
   ```bash
   curl http://localhost:8000/api/v1/trace
   ```
4. Wait 10 seconds, then search in Tempo

## Grafana "Connection refused" to data source

The data source URLs use Docker internal DNS (`prometheus:9090`), not `localhost`.
This is correct — Grafana is inside Docker. Don't change the URLs.

## Alert not firing

Alerts need the condition to be true for `for: 1m` (or whatever duration is set).
Wait the required duration after triggering the condition.

Check Prometheus rules page: http://localhost:9090/rules
