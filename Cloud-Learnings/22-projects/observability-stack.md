← [Previous: CI/CD Pipeline](./cicd-pipeline.md) | [Home](../README.md) | [Next: Kubernetes App →](./kubernetes-app.md)

---

# Project: Observability Stack

Deploy a full observability stack: Prometheus for metrics, Grafana for dashboards, Loki for logs, and OpenTelemetry Collector for traces — all running on ECS Fargate or Kubernetes, plus integration with CloudWatch.

**Estimated cost:** ~$30–60/month (ECS Fargate tasks + EBS for Prometheus storage)
**Time to complete:** 3–4 hours

---

## Architecture

```
Applications (FastAPI / Node / Java)
  │  OpenTelemetry SDK (metrics + logs + traces)
  ▼
OTel Collector (gateway)
  ├── Metrics ──► Prometheus (scrape + OTLP receive)
  ├── Logs ─────► Loki (OTLP logs)
  └── Traces ───► Tempo / AWS X-Ray

Prometheus ──► Alertmanager ──► PagerDuty / Slack
    │
    ▼
Grafana (dashboards + alerting UI)
  └── Data sources: Prometheus, Loki, Tempo, CloudWatch
```

---

## Step 1: Docker Compose (Local Development)

```yaml
# docker-compose.yml — full local observability stack
version: "3.8"

services:
  # ── OTel Collector ────────────────────────────────────────────────
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.95.0
    volumes:
      - ./config/otel-collector.yaml:/etc/otelcol-contrib/config.yaml
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8888:8888"   # Collector self-metrics
    depends_on:
      - prometheus
      - loki

  # ── Prometheus ─────────────────────────────────────────────────────
  prometheus:
    image: prom/prometheus:v2.49.1
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./config/rules/:/etc/prometheus/rules/
      - prometheus-data:/prometheus
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=15d
      - --web.enable-lifecycle
    ports:
      - "9090:9090"

  # ── Alertmanager ───────────────────────────────────────────────────
  alertmanager:
    image: prom/alertmanager:v0.26.0
    volumes:
      - ./config/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - "9093:9093"

  # ── Loki ───────────────────────────────────────────────────────────
  loki:
    image: grafana/loki:2.9.4
    volumes:
      - ./config/loki.yml:/etc/loki/local-config.yaml
      - loki-data:/loki
    ports:
      - "3100:3100"

  # ── Grafana ────────────────────────────────────────────────────────
  grafana:
    image: grafana/grafana:10.3.1
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_INSTALL_PLUGINS: grafana-clock-panel
      GF_AUTH_ANONYMOUS_ENABLED: "false"
    volumes:
      - ./config/grafana/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml
      - ./config/grafana/dashboards.yml:/etc/grafana/provisioning/dashboards/dashboards.yml
      - ./config/grafana/dashboards/:/var/lib/grafana/dashboards/
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
      - loki

volumes:
  prometheus-data:
  loki-data:
  grafana-data:
```

---

## Step 2: OTel Collector Configuration

```yaml
# config/otel-collector.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  # Scrape Prometheus metrics from services
  prometheus:
    config:
      scrape_configs:
        - job_name: "order-api"
          scrape_interval: 15s
          static_configs:
            - targets: ["order-api:8080"]
          metrics_path: /metrics

processors:
  batch:
    timeout: 5s
    send_batch_size: 1000

  # Add resource attributes to all telemetry
  resource:
    attributes:
      - action: insert
        key: environment
        value: production
      - action: insert
        key: service.namespace
        value: myapp

  # Filter out health check spans (noisy)
  filter:
    spans:
      exclude:
        match_type: regexp
        attributes:
          - key: http.target
            value: ".*(health|metrics).*"

  memory_limiter:
    check_interval: 1s
    limit_mib: 512

exporters:
  # Metrics → Prometheus
  prometheusremotewrite:
    endpoint: "http://prometheus:9090/api/v1/write"

  # Logs → Loki
  loki:
    endpoint: "http://loki:3100/loki/api/v1/push"
    labels:
      resource:
        service.name: "service_name"
        service.version: "service_version"
        environment: "environment"

  # Traces → AWS X-Ray
  awsxray:
    region: us-east-1

  # Debug (dev only)
  debug:
    verbosity: detailed

service:
  pipelines:
    metrics:
      receivers: [otlp, prometheus]
      processors: [memory_limiter, resource, batch]
      exporters: [prometheusremotewrite]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [loki]
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, filter, batch]
      exporters: [awsxray]
```

---

## Step 3: Prometheus Configuration

```yaml
# config/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: prod
    region: us-east-1

rule_files:
  - "/etc/prometheus/rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: otel-collector
    static_configs:
      - targets: ["otel-collector:8888"]

  - job_name: order-api
    scrape_interval: 15s
    static_configs:
      - targets: ["order-api:8080"]
    metrics_path: /metrics
```

```yaml
# config/rules/order-api.yml
groups:
  - name: order-api
    interval: 30s
    rules:
      # Recording rule: 5-minute error rate
      - record: job:http_errors:rate5m
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) by (job)

      # Alert: sustained error rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5..", job="order-api"}[5m]))
            /
            sum(rate(http_requests_total{job="order-api"}[5m]))
          ) > 0.05
        for: 2m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High error rate on order-api"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"
          runbook_url: "https://wiki.myapp.com/runbooks/high-error-rate"

      - alert: APIDown
        expr: up{job="order-api"} == 0
        for: 1m
        labels:
          severity: critical
          page: "true"
        annotations:
          summary: "order-api is down"
          description: "order-api target {{ $labels.instance }} has been down for 1 minute"
```

---

## Step 4: Grafana Provisioning

```yaml
# config/grafana/datasources.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    jsonData:
      httpMethod: POST
      exemplarTraceIdDestinations:
        - name: traceID
          datasourceUid: tempo

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    jsonData:
      derivedFields:
        - datasourceUid: tempo
          matcherRegex: '"trace_id":"(\w+)"'
          name: TraceID
          url: '$${__value.raw}'

  - name: CloudWatch
    type: cloudwatch
    jsonData:
      authType: default
      defaultRegion: us-east-1
```

```json
{
  "title": "Order API — RED Dashboard",
  "uid": "order-api-red",
  "panels": [
    {
      "title": "Request Rate (RPS)",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0},
      "targets": [{
        "expr": "sum(rate(http_requests_total{job='order-api'}[1m]))",
        "legendFormat": "req/s"
      }]
    },
    {
      "title": "Error Rate (%)",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 8, "x": 8, "y": 0},
      "targets": [{
        "expr": "100 * sum(rate(http_requests_total{job='order-api',status=~'5..'}[5m])) / sum(rate(http_requests_total{job='order-api'}[5m]))",
        "legendFormat": "% errors"
      }],
      "fieldConfig": {"defaults": {"unit": "percent", "thresholds": {"steps": [
        {"color": "green", "value": 0},
        {"color": "yellow", "value": 1},
        {"color": "red", "value": 5}
      ]}}}
    },
    {
      "title": "P99 Latency (ms)",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 8, "x": 16, "y": 0},
      "targets": [{
        "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job='order-api'}[5m])) by (le)) * 1000",
        "legendFormat": "p99 ms"
      }]
    }
  ]
}
```

---

## Step 5: Deploy to ECS

```bash
# Build and push observability stack images
for SERVICE in prometheus alertmanager loki grafana otel-collector; do
    echo "Deploying $SERVICE..."
    aws ecs update-service \
        --cluster observability-cluster \
        --service $SERVICE \
        --force-new-deployment \
        --region $REGION
done

# Verify all services are stable
aws ecs wait services-stable \
    --cluster observability-cluster \
    --services prometheus alertmanager loki grafana otel-collector \
    --region $REGION

echo "Observability stack deployed"
```

---

## Instrument Your Application

```python
# Add to your FastAPI application
from app.telemetry import init_telemetry

# In main.py lifespan:
init_telemetry(
    service_name="order-api",
    service_version=os.environ.get("APP_VERSION", "unknown"),
    otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"),
)
```

See `15-observability/opentelemetry.md` for the full `init_telemetry()` implementation.

---

## Verification

```bash
# Prometheus — check targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job:.labels.job, health:.health}'

# Grafana — check datasources
curl -s -u admin:admin http://localhost:3000/api/datasources | jq '.[].name'

# Test alert firing
curl -X POST http://localhost:9090/-/reload   # reload rules
curl -s "http://localhost:9090/api/v1/alerts" | jq '.data.alerts[].labels.alertname'

# Loki — query recent logs
curl -sG http://localhost:3100/loki/api/v1/query_range \
    --data-urlencode 'query={service_name="order-api"}' \
    --data-urlencode "start=$(date -v-5M +%s)000000000" \
    --data-urlencode "end=$(date +%s)000000000" \
    | jq '.data.result[0].values[-3:]'
```

---

← [Previous: CI/CD Pipeline](./cicd-pipeline.md) | [Home](../README.md) | [Next: Kubernetes App →](./kubernetes-app.md)
