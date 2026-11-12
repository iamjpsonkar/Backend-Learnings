# Solution — Observability

## Task 2 — Traffic Generator

```bash
#!/bin/bash
echo "Generating traffic..."
for i in $(seq 1 50); do
  curl -s http://localhost:8000/health > /dev/null
  curl -s http://localhost:8000/api/v1/items > /dev/null
  curl -s http://localhost:8000/api/v1/trace > /dev/null
  sleep 0.2
done
echo "Done."
```

## Task 4 — Useful LogQL Queries

```logql
# All logs from all platform containers
{com_cloudlearnings_project="cloud-learnings-lab"}

# Only sample-api logs, error level
{container="cloud-learnings-sample-api"} | json | level="ERROR"

# Count log lines per minute
sum(rate({container="cloud-learnings-sample-api"}[1m]))

# Lines containing a specific request_id
{container="cloud-learnings-sample-api"} |= "abc-123"
```

## Task 5 — Trace Query API

```bash
# Search all traces for sample-api
curl -s 'http://localhost:3200/api/search?tags=service.name%3Dsample-api&limit=10' | jq '.traces[]'

# Get specific trace by ID
curl -s 'http://localhost:3200/api/traces/<TRACE_ID>' | jq '.'
```

## Task 6 — Dashboard JSON (Simplified)

Import this JSON in Grafana → Dashboards → Import:

```json
{
  "title": "Lab Dashboard",
  "panels": [
    {
      "type": "timeseries",
      "title": "Request Rate",
      "targets": [{"expr": "rate(http_requests_total[1m])", "datasource": {"type": "prometheus"}}]
    },
    {
      "type": "stat",
      "title": "Active Requests",
      "targets": [{"expr": "http_requests_active", "datasource": {"type": "prometheus"}}]
    }
  ]
}
```
