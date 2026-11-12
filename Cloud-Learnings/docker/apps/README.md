# Sample Applications

These sample apps are designed for practicing observability, CI/CD, event-driven architecture, and debugging.

## Applications

| App | Port | Purpose |
|---|---|---|
| `sample-api` | 8000 | Python FastAPI — metrics, traces, structured logs |
| `sample-worker` | — | Background worker — consumes from RabbitMQ |
| `sample-frontend` | 8100 | Nginx static site — UI for sample API |
| `event-producer` | 8001 | Publishes events to RabbitMQ + Redpanda |
| `event-consumer` | — | Consumes events from RabbitMQ + Redpanda |
| `serverless-simulator` | — | Simulates serverless function invocation |
| `broken-apps/` | — | Deliberately broken apps for debugging practice |

## Starting Apps

```bash
./run.sh start apps
```

This also starts `core`. Apps that need databases require `data` profile too:

```bash
./run.sh start data
./run.sh start apps
```

## Sample API Endpoints

```
GET  /health          Health check
GET  /metrics         Prometheus metrics
GET  /api/v1/items    List items (from PostgreSQL)
POST /api/v1/items    Create item
GET  /api/v1/items/{id}
PUT  /api/v1/items/{id}
DELETE /api/v1/items/{id}
GET  /api/v1/cache/{key}  Redis cache demo
POST /api/v1/events   Publish event to RabbitMQ
GET  /api/v1/trace    Demo distributed trace
```

## Observability Built-In

All apps export:
- **Prometheus metrics** — request count, duration, error rate
- **Structured JSON logs** — with trace_id, request_id
- **OTLP traces** — sent to OTel Collector → Tempo

To see traces, start observability profile first:
```bash
./run.sh start observability
./run.sh start apps
```

Then visit Grafana → Explore → Tempo → Search for "sample-api"

## Building Apps

Apps are built by Docker Compose when you first start the `apps` profile:
```bash
docker compose --project-name cloud-learnings-lab --profile apps build
```

Or rebuild specific app:
```bash
docker compose --project-name cloud-learnings-lab build sample-api
```
