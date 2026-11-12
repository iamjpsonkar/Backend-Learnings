# Monitoring Dashboard — Intermediate

**Difficulty**: Intermediate
**Profile**: `apps observability`
**Time estimate**: 60–90 minutes

---

## Scenario

The sample API is running but nobody can see what it is doing. Your job: build a Grafana dashboard that monitors it in real time.

---

## Setup

```bash
./run.sh start apps observability

# Wait for all services to be healthy
./run.sh status

# Generate some traffic
for i in $(seq 1 50); do
  curl -s http://localhost:8000/items > /dev/null
  curl -s http://localhost:8000/health > /dev/null
  sleep 0.5
done
```

---

## Tasks

### Task 1 — Find the metrics

Open Prometheus at http://localhost:9090

Find all metrics from `sample-api`:
```
{job="sample-api"}
```

List at least 5 unique metric names. What does each measure?

### Task 2 — Write PromQL queries

Write queries for:
- **Request rate** (requests per second, last 5 minutes)
- **Error rate** (5xx responses as % of total)
- **P95 latency** (95th percentile response time)
- **Active connections** (gauge)
- **Cache hit ratio** (if cache metrics exist)

Test each query in the Prometheus UI before using in Grafana.

### Task 3 — Create a Grafana dashboard

Open Grafana at http://localhost:3000 (admin / admin)

Create a new dashboard with:
- **Title**: "Sample API Overview"
- **5 panels**: one for each query above
- **Panel types**: use Time series for rates/latency, Stat for current values, Gauge for ratios

### Task 4 — Add annotations

Add an annotation that marks when you ran the traffic generator:
- Dashboard Settings → Annotations → Add
- Use a manual annotation (draw a vertical line at a specific time)

### Task 5 — Set up an alert

Create a Grafana alert that fires when error rate > 5%:
- Open the error rate panel
- Alert tab → Create alert rule
- Condition: error_rate > 0.05
- Set notification channel (even if there's no real destination)

### Task 6 — Explore logs with Loki

Open the Explore page, select Loki datasource.

Find all logs from sample-api:
```
{container="sample-api"}
```

Filter to only error logs:
```
{container="sample-api"} |= "ERROR"
```

Count errors per minute:
```
rate({container="sample-api"} |= "ERROR" [1m])
```

### Task 7 — Link metrics to traces (bonus)

In the P95 latency panel, configure an exemplar link to Tempo:
- Edit panel → Data source options → Enable exemplars
- This links slow requests to their traces

---

## Success criteria

- [ ] At least 5 metrics identified from Prometheus
- [ ] 5 PromQL queries written and working
- [ ] Grafana dashboard with 5 panels saved
- [ ] At least one annotation added
- [ ] Alert rule configured for error rate
- [ ] Log queries working in Loki explorer
