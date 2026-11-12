← [Previous: Alerting](./alerting.md) | [Home](../README.md) | [Next: OpenTelemetry →](./opentelemetry.md)

---

# Dashboards

Dashboards translate raw metrics into operational insight. A good dashboard answers "is my service healthy right now?" in under 5 seconds.

---

## Dashboard Design Principles

1. **Top row: current health** — RED metrics prominently displayed with color indicators
2. **Second row: trends** — time-series graphs showing rate, error rate, latency
3. **Third row: resources** — CPU, memory, connection pool, queue depth
4. **Annotations** — mark deployments and incidents on all graphs
5. **Variables** — allow filtering by environment, cluster, or service without editing
6. **Links** — connect to runbooks, related dashboards, and log search

---

## Grafana — Dashboard as Code

```json
// dashboard.json — minimal service overview dashboard
{
  "title": "Service Overview — {{ service }}",
  "uid": "service-overview",
  "refresh": "30s",
  "time": { "from": "now-1h", "to": "now" },
  "templating": {
    "list": [
      {
        "name": "namespace",
        "type": "query",
        "query": "label_values(kube_deployment_info, namespace)",
        "current": { "value": "production" }
      },
      {
        "name": "service",
        "type": "query",
        "query": "label_values(http_requests_total{namespace=\"$namespace\"}, job)"
      }
    ]
  },
  "annotations": {
    "list": [
      {
        "name": "Deployments",
        "datasource": "Loki",
        "expr": "{job=\"argocd\"} |= \"deployed\" |= \"$service\"",
        "titleFormat": "Deployed {{ version }}",
        "iconColor": "blue"
      }
    ]
  },
  "panels": [
    {
      "title": "Request Rate",
      "type": "timeseries",
      "gridPos": { "x": 0, "y": 0, "w": 8, "h": 8 },
      "targets": [{
        "expr": "sum(rate(http_requests_total{job=\"$service\", namespace=\"$namespace\"}[5m]))",
        "legendFormat": "req/s"
      }]
    },
    {
      "title": "Error Rate",
      "type": "timeseries",
      "gridPos": { "x": 8, "y": 0, "w": 8, "h": 8 },
      "fieldConfig": {
        "defaults": {
          "thresholds": {
            "steps": [
              { "color": "green", "value": 0 },
              { "color": "yellow", "value": 0.01 },
              { "color": "red", "value": 0.05 }
            ]
          },
          "unit": "percentunit"
        }
      },
      "targets": [{
        "expr": "sum(rate(http_requests_total{job=\"$service\",status_code=~\"5..\"}[5m])) / sum(rate(http_requests_total{job=\"$service\"}[5m]))",
        "legendFormat": "error rate"
      }]
    },
    {
      "title": "p99 Latency",
      "type": "timeseries",
      "gridPos": { "x": 16, "y": 0, "w": 8, "h": 8 },
      "fieldConfig": { "defaults": { "unit": "s" } },
      "targets": [{
        "expr": "histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket{job=\"$service\"}[5m])))",
        "legendFormat": "p99"
      },{
        "expr": "histogram_quantile(0.50, sum by (le) (rate(http_request_duration_seconds_bucket{job=\"$service\"}[5m])))",
        "legendFormat": "p50"
      }]
    }
  ]
}
```

### Provisioning Dashboards via ConfigMap (Kubernetes)

```yaml
# Grafana dashboard provisioning
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards-config
  namespace: monitoring
  labels:
    grafana_dashboard: "1"    # Grafana sidecar picks this up automatically
data:
  service-overview.json: |
    { "title": "Service Overview", ... }
---
# Grafana datasource provisioning
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        url: http://prometheus-operated:9090
        isDefault: true
        jsonData:
          timeInterval: "15s"
      - name: Loki
        type: loki
        url: http://loki:3100
        jsonData:
          derivedFields:
            - name: TraceID
              matcherRegex: '"trace_id":"(\w+)"'
              url: http://tempo:3200/trace/$${__value.raw}
              datasourceUid: tempo
      - name: Tempo
        type: tempo
        url: http://tempo:3200
```

---

## Grafana Provisioning via Terraform

```hcl
# terraform/grafana-dashboards.tf
terraform {
  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = "~> 2.0"
    }
  }
}

provider "grafana" {
  url  = var.grafana_url
  auth = var.grafana_api_key
}

resource "grafana_folder" "services" {
  title = "Services"
}

resource "grafana_dashboard" "service_overview" {
  folder      = grafana_folder.services.id
  config_json = file("${path.module}/dashboards/service-overview.json")
  overwrite   = true
}

resource "grafana_alert_rule" "high_error_rate" {
  name            = "High Error Rate"
  folder_uid      = grafana_folder.services.uid
  rule_group      = "api-alerts"
  for             = "5m"
  no_data_state   = "NoData"
  exec_err_state  = "Error"

  data {
    ref_id = "A"
    query_type = ""
    relative_time_range {
      from = 300
      to   = 0
    }
    datasource_uid = "prometheus"
    model = jsonencode({
      expr       = "sum(rate(http_requests_total{status_code=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m]))"
      instant    = true
      legendFormat = "error rate"
    })
  }

  condition = "B"

  data {
    ref_id = "B"
    query_type = "__expr__"
    relative_time_range { from = 0 to = 0 }
    datasource_uid = "__expr__"
    model = jsonencode({
      type       = "threshold"
      refId      = "B"
      conditions = [{ evaluator = { type = "gt", params = [0.01] }, query = { params = ["A"] } }]
    })
  }
}
```

---

## Useful Panel Types

| Panel | Best for |
|-------|---------|
| **Time series** | Any metric over time — the most useful panel |
| **Stat** | Single current value with threshold color (error rate %, uptime) |
| **Gauge** | Utilization percentage (CPU, memory, disk) |
| **Table** | Tabular data: top endpoints by latency, top error sources |
| **Bar chart** | Comparisons: error count by service |
| **Heatmap** | Latency distribution (histogram data) |
| **Logs** | Live log stream from Loki inline with metrics |
| **Node graph** | Service dependency map |
| **Alert list** | Current firing alerts |

---

## USE Dashboard: Infrastructure

```promql
# CPU Utilization (% of requests, not idle)
1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))

# Memory Saturation (swap usage — indicates memory pressure)
node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes

# Disk I/O Utilization (% time disk is busy)
rate(node_disk_io_time_seconds_total{device="sda"}[5m])

# Network Saturation (receive errors)
rate(node_network_receive_errs_total[5m])

# File descriptor exhaustion
node_filefd_allocated / node_filefd_maximum
```

---

## References

- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Grafana Terraform Provider](https://registry.terraform.io/providers/grafana/grafana/latest/docs)
- [USE Method](https://www.brendangregg.com/usemethod.html)
- [RED Method](https://www.weave.works/blog/the-red-method-key-metrics-for-microservices-architecture/)

---

← [Previous: Alerting](./alerting.md) | [Home](../README.md) | [Next: OpenTelemetry →](./opentelemetry.md)
