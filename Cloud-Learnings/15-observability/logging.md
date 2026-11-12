← [Previous: Metrics](./metrics.md) | [Home](../README.md) | [Next: Tracing →](./tracing.md)

---

# Logging

Logs are the narrative of what your system did. Structured logs are queryable; unstructured logs are archaeology.

---

## Structured Logging

Every log line should be machine-parseable JSON with consistent fields.

### Python — Structured JSON Logger

```python
import json
import logging
import os
import sys
import time
import traceback
from typing import Any


class StructuredLogHandler(logging.Handler):
    """
    Emit log records as JSON to stdout.
    Compatible with CloudWatch, Loki, GCP Logging, Datadog.
    """

    SERVICE = os.environ.get("SERVICE_NAME", "unknown-service")
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

    def emit(self, record: logging.LogRecord) -> None:
        log_entry: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
                         + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.SERVICE,
            "environment": self.ENVIRONMENT,
        }

        # Merge extra fields (e.g., request_id, user_id)
        if hasattr(record, "__dict__"):
            for key, val in record.__dict__.items():
                if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                    log_entry[key] = val

        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        print(json.dumps(log_entry, default=str), file=sys.stdout, flush=True)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with structured JSON handler."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(StructuredLogHandler())


# Usage
configure_logging(os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

logger.info("Order created", extra={
    "order_id": "ord_abc123",
    "user_id": "usr_xyz",
    "amount_cents": 4999,
    "currency": "usd",
})
# Output:
# {"timestamp":"2024-01-15T10:23:45.123Z","level":"INFO","logger":"orders.service",
#  "message":"Order created","service":"order-api","environment":"production",
#  "order_id":"ord_abc123","user_id":"usr_xyz","amount_cents":4999,"currency":"usd"}
```

### Request Context Propagation

```python
import contextvars
import uuid
import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

# Thread-local storage for request context
REQUEST_ID_VAR: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)

logger = logging.getLogger(__name__)


class RequestContextFilter(logging.Filter):
    """Inject request_id into every log record automatically."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID_VAR.get("")  # type: ignore[attr-defined]
        return True


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = REQUEST_ID_VAR.set(request_id)
        start = time.perf_counter()

        logger.info("Request started", extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        })

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info("Request completed", extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            })
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error("Request failed", extra={
                "request_id": request_id,
                "duration_ms": round(duration_ms, 2),
                "error": str(exc),
            }, exc_info=True)
            raise
        finally:
            REQUEST_ID_VAR.reset(token)


app = FastAPI()
app.add_middleware(RequestLoggingMiddleware)
```

---

## Log Levels

| Level | When to use |
|-------|------------|
| `DEBUG` | Detailed diagnostic info — disabled in production by default |
| `INFO` | Normal significant events: request received, job started, user logged in |
| `WARNING` | Recoverable issues: retried connection, deprecated API used, high memory |
| `ERROR` | Failure that needs investigation: exception, external API down |
| `CRITICAL` | System-level failure: cannot start, data corruption, security breach |

```python
# Level selection heuristic:
logger.debug("Cache key computed: %s", cache_key)          # Never in prod
logger.info("Payment processed", extra={"payment_id": pid}) # Normal flow
logger.warning("Rate limit approaching: %d/100", count)     # Degraded state
logger.error("DB connection failed", exc_info=True)         # Needs investigation
logger.critical("Secret rotation failed — service stopping") # Page immediately
```

---

## Grafana Loki

```yaml
# docker-compose: Loki + Promtail + Grafana
version: "3.8"
services:
  loki:
    image: grafana/loki:2.9.0
    ports: ["3100:3100"]
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./promtail-config.yaml:/etc/promtail/config.yaml
    command: -config.file=/etc/promtail/config.yaml

  grafana:
    image: grafana/grafana:10.2.0
    ports: ["3000:3000"]
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
```

```yaml
# promtail-config.yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: containers
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: [__meta_docker_container_name]
        target_label: container
      - source_labels: [__meta_docker_compose_service]
        target_label: service
    pipeline_stages:
      - json:
          expressions:
            level: level
            request_id: request_id
            message: message
      - labels:
          level:
          service:
```

### LogQL Queries

```logql
# All error logs in production
{environment="production"} |= `"level":"ERROR"`

# Parse JSON and filter by field
{service="order-api"} | json | level="ERROR"

# Count errors per service over 5 minutes
sum by (service) (
    count_over_time({environment="production"} | json | level="ERROR" [5m])
)

# Filter by request_id (trace a specific request)
{service="order-api"} | json | request_id="req-abc123"

# Latency of slow requests (> 1 second)
{service="api"} | json | duration_ms > 1000
| line_format "{{.method}} {{.path}} {{.duration_ms}}ms"

# Log rate by level
sum by (level) (
    rate({environment="production"} | json [1m])
)
```

---

## AWS CloudWatch Logs

```bash
# Create log group with retention
aws logs create-log-group \
    --log-group-name /apps/order-api/production

aws logs put-retention-policy \
    --log-group-name /apps/order-api/production \
    --retention-in-days 90

# Query logs with CloudWatch Insights
aws logs start-query \
    --log-group-name /apps/order-api/production \
    --start-time $(($(date +%s) - 3600)) \
    --end-time $(date +%s) \
    --query-string '
        fields @timestamp, level, message, request_id, order_id
        | filter level = "ERROR"
        | sort @timestamp desc
        | limit 50
    '

QUERY_ID=$(aws logs start-query ... --query 'queryId' --output text)
aws logs get-query-results --query-id $QUERY_ID

# Export to S3 for long-term storage
aws logs create-export-task \
    --log-group-name /apps/order-api/production \
    --from $(($(date +%s) - 86400))000 \
    --to $(date +%s)000 \
    --destination my-log-archive-bucket \
    --destination-prefix logs/order-api/
```

---

## What NOT to Log

```python
# ❌ Never log these:
logger.info("User logged in", extra={"password": password})
logger.debug("JWT token: %s", jwt_token)
logger.info("Card charged", extra={"card_number": "4111111111111111"})
logger.info("Secret fetched", extra={"secret_value": secret})

# ✅ Log safe identifiers instead:
logger.info("User logged in", extra={"user_id": user.id, "email_domain": email.split("@")[1]})
logger.debug("JWT issued", extra={"user_id": user.id, "expires_at": exp})
logger.info("Card charged", extra={"last4": "1111", "payment_id": payment.id})
logger.info("Secret fetched", extra={"secret_name": secret_name})  # name only, never value
```

---

## References

- [Grafana Loki](https://grafana.com/docs/loki/latest/)
- [LogQL](https://grafana.com/docs/loki/latest/query/)
- [CloudWatch Logs Insights syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [Twelve-Factor App: Logs](https://12factor.net/logs)

---

← [Previous: Metrics](./metrics.md) | [Home](../README.md) | [Next: Tracing →](./tracing.md)
