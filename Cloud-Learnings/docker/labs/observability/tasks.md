# Tasks — Observability

## Task 1 — Explore Prometheus

- [ ] Open Prometheus at http://localhost:9090
- [ ] Go to Status → Targets — verify sample-api and traefik are UP
- [ ] Write a PromQL query for total HTTP requests:
  ```
  http_requests_total
  ```
- [ ] Filter by path:
  ```
  http_requests_total{path="/health"}
  ```
- [ ] Get request rate over 5 minutes:
  ```
  rate(http_requests_total[5m])
  ```
- [ ] Find active requests gauge:
  ```
  http_requests_active
  ```

## Task 2 — Generate sample traffic

```bash
# Generate traffic to sample-api
for i in $(seq 1 20); do
  curl -s http://localhost:8000/health > /dev/null
  curl -s http://localhost:8000/api/v1/items > /dev/null
  curl -s http://localhost:8000/api/v1/trace > /dev/null
  sleep 0.5
done
```

- [ ] After generating traffic, re-run your PromQL queries
- [ ] Observe the rate graph in Prometheus

## Task 3 — Explore Grafana

- [ ] Open Grafana at http://localhost:3001
- [ ] Log in: admin/admin
- [ ] Go to Explore → select Prometheus data source
- [ ] Run the same queries from Task 1

## Task 4 — View Logs in Loki

- [ ] In Grafana, go to Explore → select Loki data source
- [ ] Query all logs from sample-api:
  ```
  {container="cloud-learnings-sample-api"}
  ```
- [ ] Filter for errors:
  ```
  {container="cloud-learnings-sample-api"} |= "ERROR"
  ```
- [ ] Parse JSON and filter by field:
  ```
  {container="cloud-learnings-sample-api"} | json | level = "INFO"
  ```

## Task 5 — View Traces in Tempo

- [ ] Generate a trace: `curl http://localhost:8000/api/v1/trace`
- [ ] In Grafana, go to Explore → select Tempo data source
- [ ] Search by service name: `sample-api`
- [ ] Click on a trace to see span details

## Task 6 — Build a Grafana Dashboard

- [ ] Create a new dashboard
- [ ] Add a Time series panel with query:
  ```
  rate(http_requests_total[1m])
  ```
- [ ] Add a Stat panel for:
  ```
  http_requests_active
  ```
- [ ] Add a Logs panel querying Loki:
  ```
  {container="cloud-learnings-sample-api"}
  ```
- [ ] Save the dashboard as "Lab Dashboard"

## Task 7 — Simulate an alert

- [ ] Open Prometheus at http://localhost:9090/rules
- [ ] View the alert rules from `configs/prometheus/rules/alerts.yml`
- [ ] Trigger a ServiceDown condition (stop a service):
  ```bash
  docker stop cloud-learnings-sample-api
  # Wait 2 minutes
  # Check http://localhost:9090/alerts
  docker start cloud-learnings-sample-api
  ```
