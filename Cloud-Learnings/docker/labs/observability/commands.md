# Commands — Observability

## Prometheus

```bash
# Check health
curl http://localhost:9090/-/healthy

# Query via API
curl 'http://localhost:9090/api/v1/query?query=up'

# Query with time range
curl 'http://localhost:9090/api/v1/query_range?query=rate(http_requests_total[5m])&start=now-1h&end=now&step=60'

# Reload config
curl -X POST http://localhost:9090/-/reload
```

## Loki (via API)

```bash
# Query logs
curl -G http://localhost:3100/loki/api/v1/query \
  --data-urlencode 'query={container="cloud-learnings-sample-api"}' \
  --data-urlencode 'limit=10'

# Check Loki health
curl http://localhost:3100/ready
```

## Grafana (via API)

```bash
# Health check
curl http://localhost:3001/api/health

# List dashboards
curl -u admin:admin http://localhost:3001/api/search

# List data sources
curl -u admin:admin http://localhost:3001/api/datasources
```

## Tempo

```bash
# Health check
curl http://localhost:3200/ready

# Search traces
curl 'http://localhost:3200/api/search?service.name=sample-api&limit=5'
```

## Generating Traffic for Practice

```bash
# Continuous traffic
while true; do
  curl -s http://localhost:8000/health > /dev/null
  curl -s http://localhost:8000/api/v1/items > /dev/null
  curl -s http://localhost:8000/api/v1/trace > /dev/null
  sleep 1
done
```

## Key PromQL Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Active requests
http_requests_active

# DB query rate
rate(db_queries_total[5m])
```

## Key LogQL Queries

```logql
# All logs
{container="cloud-learnings-sample-api"}

# Errors only
{container="cloud-learnings-sample-api"} |= "ERROR"

# JSON parse + filter
{container="cloud-learnings-sample-api"} | json | level = "ERROR"

# Count errors per minute
count_over_time({container="cloud-learnings-sample-api"} |= "ERROR" [1m])

# Extract field and filter
{container="cloud-learnings-sample-api"} | json | status >= 500
```
