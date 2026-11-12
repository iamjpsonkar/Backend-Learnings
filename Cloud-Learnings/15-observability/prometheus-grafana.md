← [Previous: OpenTelemetry](./opentelemetry.md) | [Home](../README.md) | [Next: SRE →](../16-sre/README.md)

---

# Prometheus & Grafana

Prometheus is the de facto metrics collection and alerting system for Kubernetes. Grafana is the visualization layer. Together they form the most widely deployed observability stack in cloud-native environments.

---

## Prometheus Operator (Kubernetes)

The Prometheus Operator manages Prometheus and Alertmanager instances declaratively via CRDs.

```bash
# Install via kube-prometheus-stack (includes Grafana + alerting rules)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    --create-namespace \
    --values prometheus-values.yaml \
    --wait
```

```yaml
# prometheus-values.yaml
prometheus:
  prometheusSpec:
    retention: 15d
    retentionSize: "40GB"
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          accessModes: [ReadWriteOnce]
          resources:
            requests:
              storage: 50Gi
    # Discover ServiceMonitors from all namespaces
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        memory: 4Gi
    additionalScrapeConfigs:
      - job_name: "external-services"
        static_configs:
          - targets: ["legacy-app:9090"]

alertmanager:
  alertmanagerSpec:
    storage:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          resources:
            requests:
              storage: 5Gi
  config:
    global:
      resolve_timeout: 5m
    route:
      group_by: [alertname, job]
      receiver: slack-default
    receivers:
      - name: slack-default
        slack_configs:
          - api_url: "${SLACK_WEBHOOK}"
            channel: "#alerts"

grafana:
  persistence:
    enabled: true
    size: 10Gi
  adminPassword: "${GRAFANA_ADMIN_PASSWORD}"
  grafana.ini:
    server:
      root_url: "https://grafana.my-app.com"
    auth.github:
      enabled: true
      client_id: "${GITHUB_OAUTH_CLIENT_ID}"
      client_secret: "${GITHUB_OAUTH_CLIENT_SECRET}"
      allowed_organizations: "my-org"
  sidecar:
    dashboards:
      enabled: true    # Auto-load dashboards from ConfigMaps with label grafana_dashboard=1
    datasources:
      enabled: true
```

---

## ServiceMonitor — Scrape Configuration

```yaml
# Tell Prometheus to scrape your service
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: order-api
  namespace: production
  labels:
    app: order-api
    release: kube-prometheus-stack    # Must match Prometheus operator selector
spec:
  selector:
    matchLabels:
      app: order-api
  namespaceSelector:
    matchNames: [production]
  endpoints:
    - port: metrics           # Port name in Service spec
      path: /metrics
      interval: 30s
      scrapeTimeout: 10s
      relabelings:
        - sourceLabels: [__meta_kubernetes_pod_name]
          targetLabel: pod
        - sourceLabels: [__meta_kubernetes_namespace]
          targetLabel: namespace
```

```yaml
# Service must expose a named port
apiVersion: v1
kind: Service
metadata:
  name: order-api
  namespace: production
  labels:
    app: order-api
spec:
  selector:
    app: order-api
  ports:
    - name: http
      port: 80
      targetPort: 8080
    - name: metrics
      port: 9090
      targetPort: 9090
```

---

## PrometheusRule — Alert Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: order-api-alerts
  namespace: production
  labels:
    release: kube-prometheus-stack
spec:
  groups:
    - name: order-api
      interval: 30s
      rules:
        - alert: OrderAPIHighErrorRate
          expr: |
            sum(rate(http_requests_total{job="order-api",status_code=~"5.."}[5m]))
            /
            sum(rate(http_requests_total{job="order-api"}[5m]))
            > 0.01
          for: 5m
          labels:
            severity: warning
            team: backend
          annotations:
            summary: "Order API error rate > 1%"
            description: "Error rate is {{ $value | humanizePercentage }}"
            runbook: "https://wiki.my-app.com/runbooks/order-api-errors"

        - record: job:http_request_duration_p99:5m
          expr: |
            histogram_quantile(0.99,
              sum by (job, le) (rate(http_request_duration_seconds_bucket[5m]))
            )
```

---

## Prometheus Scrape Config for Non-K8s Targets

```yaml
# prometheus.yml (standalone / VM-based)
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "node-exporter"
    static_configs:
      - targets:
          - "10.0.10.1:9100"
          - "10.0.10.2:9100"
          - "10.0.10.3:9100"

  - job_name: "api-services"
    file_sd_configs:          # File-based service discovery
      - files: ["/etc/prometheus/targets/*.json"]
        refresh_interval: 30s

  - job_name: "blackbox-http"   # Probe external URLs
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - https://api.my-app.com/health/ready
          - https://my-app.com
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
```

---

## Grafana — Key Queries for Operations

```promql
# ─── SLO: availability (successful requests / total) ─────────────────────────
sum(rate(http_requests_total{status_code!~"5.."}[30d]))
/ sum(rate(http_requests_total[30d]))

# ─── Pod restart rate (top crashlooping pods) ────────────────────────────────
topk(10,
    increase(kube_pod_container_status_restarts_total{namespace="production"}[1h])
)

# ─── Node disk pressure ───────────────────────────────────────────────────────
(node_filesystem_size_bytes{fstype!="tmpfs"} - node_filesystem_avail_bytes{fstype!="tmpfs"})
/ node_filesystem_size_bytes{fstype!="tmpfs"}

# ─── Container OOM events ────────────────────────────────────────────────────
increase(container_oom_events_total{namespace="production"}[1h])

# ─── Kubernetes deployment rollout health ────────────────────────────────────
kube_deployment_status_replicas_unavailable{namespace="production"} > 0

# ─── PVC usage ───────────────────────────────────────────────────────────────
(
  kubelet_volume_stats_used_bytes{namespace="production"}
  / kubelet_volume_stats_capacity_bytes{namespace="production"}
) > 0.80

# ─── Slowest endpoints (p99) ─────────────────────────────────────────────────
topk(10,
    histogram_quantile(0.99,
        sum by (handler, le) (rate(http_request_duration_seconds_bucket[5m]))
    )
)
```

---

## Exporters Reference

| Exporter | What it exports |
|----------|----------------|
| `node_exporter` | OS metrics: CPU, memory, disk, network |
| `kube-state-metrics` | Kubernetes object state (replicas, conditions) |
| `blackbox_exporter` | Probe endpoints: HTTP, TCP, ICMP |
| `postgres_exporter` | PostgreSQL queries, connections, replication lag |
| `redis_exporter` | Redis hits, misses, memory, connections |
| `mysqld_exporter` | MySQL queries, InnoDB stats |
| `elasticsearch_exporter` | Index size, search latency, cluster health |
| `kafka_exporter` | Consumer lag, partition counts |
| `aws_cloudwatch_exporter` | Bridge CloudWatch metrics into Prometheus |

---

## References

- [kube-prometheus-stack Helm chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [Prometheus Operator docs](https://prometheus-operator.dev/docs/)
- [Grafana provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- [PromQL cheat sheet](https://promlabs.com/promql-cheat-sheet/)

---

← [Previous: OpenTelemetry](./opentelemetry.md) | [Home](../README.md) | [Next: SRE →](../16-sre/README.md)
