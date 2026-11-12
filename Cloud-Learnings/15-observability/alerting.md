← [Previous: Tracing](./tracing.md) | [Home](../README.md) | [Next: Dashboards →](./dashboards.md)

---

# Alerting

Alerts tell you when something needs human attention. A good alert is actionable, rare, and linked to a runbook. Alert fatigue — too many low-signal alerts — is a leading cause of on-call burnout.

---

## Alert Design Principles

1. **Every alert must be actionable** — if you can't do anything about it, it shouldn't page
2. **Alert on symptoms, not causes** — alert on high error rate, not on CPU (which may be fine)
3. **Link to a runbook** — every alert should have a URL to a runbook in its description
4. **No alert without a test** — test alerts fire correctly in staging before production
5. **Tune thresholds** — a 1% error rate might be noise for one service, critical for another
6. **Dead Man's Switch** — alert if your alerting pipeline itself stops working

---

## Prometheus Alerting Rules

```yaml
# rules/alerts.yml
groups:
  - name: api_alerts
    rules:
      # ─── Error rate ───────────────────────────────────────────────────
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status_code=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))
          > 0.01
        for: 5m     # Must be true for 5 min before firing (reduces false positives)
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High error rate on {{ $labels.job }}"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 1%)"
          runbook: "https://wiki.my-app.com/runbooks/high-error-rate"
          dashboard: "https://grafana.my-app.com/d/api-overview"

      - alert: CriticalErrorRate
        expr: |
          sum(rate(http_requests_total{status_code=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))
          > 0.05
        for: 2m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "Critical error rate — service degraded"
          description: "Error rate {{ $value | humanizePercentage }} exceeds 5%"
          runbook: "https://wiki.my-app.com/runbooks/high-error-rate"

      # ─── Latency ──────────────────────────────────────────────────────
      - alert: HighP99Latency
        expr: |
          histogram_quantile(0.99,
            sum by (le, job) (rate(http_request_duration_seconds_bucket[5m]))
          ) > 2.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "p99 latency above 2s on {{ $labels.job }}"
          description: "p99={{ $value | humanizeDuration }}"
          runbook: "https://wiki.my-app.com/runbooks/high-latency"

      # ─── Availability ─────────────────────────────────────────────────
      - alert: ServiceDown
        expr: up{job=~"order-api|payment-api|inventory-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "Instance {{ $labels.instance }} has been unreachable for > 1 min"
          runbook: "https://wiki.my-app.com/runbooks/service-down"

  - name: resource_alerts
    rules:
      # ─── Memory ───────────────────────────────────────────────────────
      - alert: HighMemoryUsage
        expr: |
          container_memory_working_set_bytes{namespace="production"}
          /
          kube_pod_container_resource_limits{resource="memory", namespace="production"}
          > 0.85
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Pod {{ $labels.pod }} memory > 85%"
          runbook: "https://wiki.my-app.com/runbooks/oom-risk"

      # ─── Disk ─────────────────────────────────────────────────────────
      - alert: DiskSpaceLow
        expr: |
          (node_filesystem_avail_bytes{mountpoint="/"}
          / node_filesystem_size_bytes{mountpoint="/"}) < 0.15
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space on {{ $labels.instance }}"
          description: "{{ $value | humanizePercentage }} free on /"

      # ─── Dead Man's Switch ────────────────────────────────────────────
      - alert: WatchdogHeartbeat
        expr: vector(1)    # Always fires — used to test alerting pipeline
        labels:
          severity: none
        annotations:
          summary: "Alertmanager heartbeat — if this stops, alerting is broken"
```

---

## Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m
  slack_api_url: '${SLACK_WEBHOOK_URL}'
  pagerduty_url: 'https://events.pagerduty.com/v2/enqueue'

# Routing tree: match labels to receivers
route:
  group_by: ['alertname', 'job', 'team']
  group_wait: 30s         # Wait before sending first alert (deduplication window)
  group_interval: 5m      # Wait between sending updates for ongoing alerts
  repeat_interval: 4h     # Resend if still firing after this long
  receiver: default-slack

  routes:
    # P0: Critical alerts go directly to PagerDuty
    - match:
        severity: critical
      receiver: pagerduty-critical
      group_wait: 10s
      repeat_interval: 1h
      continue: true    # Also send to Slack

    # Team-specific routing
    - match:
        team: backend
      receiver: backend-slack

    # Silence the watchdog heartbeat
    - match:
        alertname: WatchdogHeartbeat
      receiver: "null"

receivers:
  - name: "null"

  - name: default-slack
    slack_configs:
      - channel: '#alerts'
        title: '{{ template "slack.title" . }}'
        text: '{{ template "slack.text" . }}'
        send_resolved: true
        actions:
          - type: button
            text: 'Runbook'
            url: '{{ (index .Alerts 0).Annotations.runbook }}'
          - type: button
            text: 'Dashboard'
            url: '{{ (index .Alerts 0).Annotations.dashboard }}'

  - name: pagerduty-critical
    pagerduty_configs:
      - routing_key: '${PAGERDUTY_INTEGRATION_KEY}'
        description: '{{ template "pagerduty.description" . }}'
        details:
          severity: '{{ (index .Alerts 0).Labels.severity }}'
          runbook: '{{ (index .Alerts 0).Annotations.runbook }}'

  - name: backend-slack
    slack_configs:
      - channel: '#backend-alerts'
        send_resolved: true

inhibit_rules:
  # If a node is down, suppress all alerts from pods on that node
  - source_match:
      severity: critical
      alertname: NodeDown
    target_match_re:
      severity: warning|info
    equal: [node]
```

---

## AWS CloudWatch Alarms

```bash
# High error rate alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "OrderAPI-HighErrorRate" \
    --alarm-description "5xx error rate > 1% for 5 min" \
    --namespace "MyApp/Production" \
    --metric-name "5xxErrorRate" \
    --dimensions Name=ServiceName,Value=order-api \
    --statistic Average \
    --period 60 \
    --evaluation-periods 5 \
    --threshold 1.0 \
    --comparison-operator GreaterThanThreshold \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:prod-alerts \
    --ok-actions arn:aws:sns:us-east-1:123456789012:prod-alerts \
    --treat-missing-data notBreaching

# Composite alarm (AND conditions)
aws cloudwatch put-composite-alarm \
    --alarm-name "OrderAPI-Degraded" \
    --alarm-rule "ALARM(OrderAPI-HighErrorRate) AND ALARM(OrderAPI-HighLatency)" \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:prod-critical

# Anomaly detection alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "OrderAPI-AnomalousRequestRate" \
    --comparison-operator GreaterThanUpperThreshold \
    --evaluation-periods 2 \
    --metrics '[{
        "Id": "m1",
        "MetricStat": {
            "Metric": {"Namespace": "MyApp/Production", "MetricName": "RequestCount"},
            "Period": 300, "Stat": "Sum"
        }
    },{
        "Id": "ad1",
        "Expression": "ANOMALY_DETECTION_BAND(m1, 2)",
        "Label": "RequestCount (expected)"
    }]' \
    --threshold-metric-id ad1 \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:prod-alerts
```

---

## PagerDuty / OpsGenie Integration

```python
# Send alert via PagerDuty Events API v2
import httpx
import logging
import os

logger = logging.getLogger(__name__)

PAGERDUTY_ROUTING_KEY = os.environ["PAGERDUTY_ROUTING_KEY"]


async def send_pagerduty_alert(
    summary: str,
    severity: str,   # critical | error | warning | info
    component: str,
    details: dict,
    dedup_key: str | None = None,
) -> str:
    """Create or resolve a PagerDuty incident. Returns dedup_key."""
    payload = {
        "routing_key": PAGERDUTY_ROUTING_KEY,
        "event_action": "trigger",
        "dedup_key": dedup_key or summary,
        "payload": {
            "summary": summary,
            "severity": severity,
            "source": component,
            "component": component,
            "group": "production",
            "custom_details": details,
        },
        "links": [{"href": details.get("runbook", ""), "text": "Runbook"}],
    }

    logger.warning(
        "Triggering PagerDuty alert",
        extra={"summary": summary, "severity": severity, "component": component},
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://events.pagerduty.com/v2/enqueue",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        logger.info("PagerDuty alert sent", extra={"dedup_key": result.get("dedup_key")})
        return result.get("dedup_key", "")
```

---

## References

- [Prometheus Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [PagerDuty Events API v2](https://developer.pagerduty.com/docs/events-api-v2/overview/)
- [Google SRE — Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)

---

← [Previous: Tracing](./tracing.md) | [Home](../README.md) | [Next: Dashboards →](./dashboards.md)
