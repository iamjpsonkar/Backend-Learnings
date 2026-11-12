# Lab: Observability Stack

Practice with the full LGTM stack: Loki (logs), Grafana (dashboards), Tempo (traces), Prometheus (metrics).

## Objectives

1. Explore Prometheus metrics and write PromQL queries
2. View and query logs in Loki (LogQL)
3. See distributed traces in Tempo
4. Build a Grafana dashboard panel
5. Create and test alert rules
6. Debug a missing metrics scenario

## Prerequisites

- Profiles running:
  ```bash
  ./run.sh start observability
  ./run.sh start apps
  ```

## Service URLs

| Service | URL | Credentials |
|---|---|---|
| Grafana | http://localhost:3001 | admin/admin |
| Prometheus | http://localhost:9090 | — |
| Loki | http://localhost:3100 | — |
| Tempo | http://localhost:3200 | — |

## Architecture

```
Sample API → OTel Collector → Tempo (traces)
                           ↘ Loki (logs)
Prometheus → scrapes → Sample API /metrics
                    → scrapes → Traefik /metrics
Promtail → reads Docker logs → Loki
Grafana → queries → Prometheus + Loki + Tempo
```

## Continue

See [tasks.md](tasks.md).
