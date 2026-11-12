← [Previous: Security Checklist](../14-security/security-checklist.md) | [Home](../README.md) | [Next: Metrics →](./metrics.md)

---

# Observability

Observability is the ability to understand a system's internal state from its external outputs. The three pillars are metrics, logs, and traces — together they answer "is it broken, where is it broken, and why?"

---

## The Three Pillars

| Pillar | What it answers | Tools |
|--------|----------------|-------|
| **Metrics** | Is the system healthy? What are the numbers? | Prometheus, CloudWatch, Datadog |
| **Logs** | What happened? What was the error message? | Loki, ELK, CloudWatch Logs, GCP Logging |
| **Traces** | Where did this request spend its time? | Jaeger, Tempo, AWS X-Ray, GCP Trace |

**Combine all three**: an alert on a metric leads you to the relevant logs, and a trace ID in the log links to the distributed trace.

---

## Key Concepts

### RED Method (for services)
- **R**ate — requests per second
- **E**rrors — error rate (%)
- **D**uration — latency (p50, p95, p99)

### USE Method (for resources)
- **U**tilization — % time resource is busy
- **S**aturation — queue depth / waiting work
- **E**rrors — error events

### Four Golden Signals (Google SRE)
- Latency, Traffic, Errors, Saturation

---

## Topics

| File | Topics |
|------|--------|
| [Metrics](./metrics.md) | Prometheus data model, counters/gauges/histograms, PromQL, RED/USE |
| [Logging](./logging.md) | Structured logs, log levels, aggregation (Loki/ELK), CloudWatch |
| [Tracing](./tracing.md) | Distributed tracing concepts, OpenTelemetry, Jaeger, AWS X-Ray |
| [Alerting](./alerting.md) | Alert rules, routing, PagerDuty/OpsGenie, runbook links |
| [Dashboards](./dashboards.md) | Grafana, dashboard-as-code, useful panels |
| [OpenTelemetry](./opentelemetry.md) | OTel SDK, auto-instrumentation, Collector, exporters |
| [Prometheus & Grafana](./prometheus-grafana.md) | Prometheus Operator, recording rules, Grafana provisioning |

---

## References

- [Google SRE Book — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [OpenTelemetry](https://opentelemetry.io/docs/)
- [Prometheus](https://prometheus.io/docs/)
- [Grafana](https://grafana.com/docs/)

---

← [Previous: Security Checklist](../14-security/security-checklist.md) | [Home](../README.md) | [Next: Metrics →](./metrics.md)
