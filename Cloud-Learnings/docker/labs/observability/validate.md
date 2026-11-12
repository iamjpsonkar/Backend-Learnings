# Validation — Observability

## Check Prometheus targets

```bash
curl -s http://localhost:9090/api/v1/targets | \
  jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

Expected: entries with `health: "up"` for sample-api, prometheus.

## Check Loki receiving logs

```bash
curl -s -G http://localhost:3100/loki/api/v1/query \
  --data-urlencode 'query=count_over_time({container="cloud-learnings-sample-api"}[5m])' | \
  jq '.data.result'
```

Expected: a count > 0 if you've generated traffic.

## Check Tempo receiving traces

```bash
curl -s http://localhost:3200/api/search | jq '.traces | length'
```

Expected: number > 0 if you've hit the `/api/v1/trace` endpoint.

## Check Grafana data sources

```bash
curl -s -u admin:admin http://localhost:3001/api/datasources | \
  jq '.[].name'
```

Expected: "Prometheus", "Loki", "Tempo"

## Verify dashboard saved

```bash
curl -s -u admin:admin http://localhost:3001/api/search | \
  jq '.[] | select(.type=="dash-db") | .title'
```

Expected: "Lab Dashboard" (after Task 6)
