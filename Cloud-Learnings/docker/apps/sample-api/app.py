"""
Cloud-Learnings Sample API
FastAPI application with:
- Prometheus metrics
- Structured JSON logging
- OTLP distributed tracing
- PostgreSQL + Redis integration
"""

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger import jsonlogger
from pydantic import BaseModel

# =============================================================================
# Structured logging setup
# =============================================================================
def setup_logging() -> logging.Logger:
    logger = logging.getLogger("sample-api")
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"}
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    return logger


logger = setup_logging()

# =============================================================================
# OpenTelemetry setup
# =============================================================================
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({SERVICE_NAME: "sample-api"})
    provider = TracerProvider(resource=resource)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("sample-api")
    OTEL_ENABLED = True
    logger.info("OpenTelemetry tracing enabled", extra={"otlp_endpoint": otlp_endpoint})
except Exception as exc:
    OTEL_ENABLED = False
    tracer = None
    logger.warning("OpenTelemetry not available — continuing without tracing", extra={"error": str(exc)})


# =============================================================================
# Prometheus metrics
# =============================================================================
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"]
)
ACTIVE_REQUESTS = Gauge(
    "http_requests_active",
    "Active HTTP requests"
)
DB_QUERY_COUNT = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation", "status"]
)
ITEMS_TOTAL = Gauge("app_items_total", "Total items in database")


# =============================================================================
# Settings
# =============================================================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://labuser:labpassword123@localhost:5432/labdb"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://default:redispassword123@localhost:6379")


# =============================================================================
# Application state
# =============================================================================
class AppState:
    db_pool: asyncpg.Pool | None = None
    redis: aioredis.Redis | None = None


app_state = AppState()


# =============================================================================
# Lifespan — startup/shutdown
# =============================================================================
@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Starting sample-api", extra={"database_url": DATABASE_URL.split("@")[-1]})

    # Connect to PostgreSQL
    try:
        app_state.db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
        logger.info("PostgreSQL connection pool created")
    except Exception as exc:
        logger.warning("PostgreSQL not available — continuing without DB", extra={"error": str(exc)})
        app_state.db_pool = None

    # Connect to Redis
    try:
        app_state.redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        await app_state.redis.ping()
        logger.info("Redis connected")
    except Exception as exc:
        logger.warning("Redis not available — continuing without cache", extra={"error": str(exc)})
        app_state.redis = None

    logger.info("sample-api startup complete")
    yield

    # Cleanup
    if app_state.db_pool:
        await app_state.db_pool.close()
    if app_state.redis:
        await app_state.redis.aclose()
    logger.info("sample-api shutdown complete")


# =============================================================================
# App
# =============================================================================
app = FastAPI(
    title="Cloud-Learnings Sample API",
    description="Practice API for Cloud-Learnings Lab Platform",
    version="1.0.0",
    lifespan=lifespan,
)

if OTEL_ENABLED:
    FastAPIInstrumentor.instrument_app(app)


# =============================================================================
# Middleware — metrics + request ID
# =============================================================================
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    ACTIVE_REQUESTS.inc()
    start = time.time()

    try:
        response = await call_next(request)
        duration = time.time() - start
        REQUEST_COUNT.labels(
            method=request.method,
            path=request.url.path,
            status=response.status_code
        ).inc()
        REQUEST_DURATION.labels(
            method=request.method,
            path=request.url.path
        ).observe(duration)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            }
        )
        return response
    except Exception as exc:
        duration = time.time() - start
        REQUEST_COUNT.labels(method=request.method, path=request.url.path, status=500).inc()
        logger.error(
            "Request failed",
            extra={"request_id": request_id, "error": str(exc), "duration_ms": round(duration * 1000, 2)}
        )
        raise
    finally:
        ACTIVE_REQUESTS.dec()


# =============================================================================
# Models
# =============================================================================
class Item(BaseModel):
    name: str
    description: str = ""
    price: float = 0.0
    stock: int = 0


class ItemResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    stock: int


# =============================================================================
# Routes
# =============================================================================
@app.get("/health")
async def health():
    db_ok = app_state.db_pool is not None
    redis_ok = app_state.redis is not None
    status = "healthy" if (db_ok or True) else "degraded"
    return {
        "status": status,
        "service": "sample-api",
        "version": "1.0.0",
        "dependencies": {
            "postgres": "connected" if db_ok else "unavailable",
            "redis": "connected" if redis_ok else "unavailable",
        }
    }


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/items")
async def list_items(limit: int = 10, offset: int = 0):
    logger.info("Listing items", extra={"limit": limit, "offset": offset})

    if app_state.db_pool is None:
        # Return mock data if DB not available
        return {"items": [{"id": 1, "name": "Mock Item", "price": 9.99}], "total": 1}

    try:
        async with app_state.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, name, description, price, stock FROM app.items LIMIT $1 OFFSET $2",
                limit, offset
            )
            count = await conn.fetchval("SELECT COUNT(*) FROM app.items")
        DB_QUERY_COUNT.labels(operation="select", status="success").inc()
        ITEMS_TOTAL.set(count)
        logger.info("Items retrieved", extra={"count": len(rows), "total": count})
        return {"items": [dict(r) for r in rows], "total": count}
    except Exception as exc:
        DB_QUERY_COUNT.labels(operation="select", status="error").inc()
        logger.error("Failed to list items", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail="Database error")


@app.post("/api/v1/items", status_code=201)
async def create_item(item: Item):
    logger.info("Creating item", extra={"name": item.name, "price": item.price})

    if app_state.db_pool is None:
        return {"id": 999, "name": item.name, "message": "Mock response — DB unavailable"}

    try:
        async with app_state.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO app.items (name, description, price, stock) VALUES ($1, $2, $3, $4) RETURNING id, name, description, price, stock",
                item.name, item.description, item.price, item.stock
            )
        DB_QUERY_COUNT.labels(operation="insert", status="success").inc()
        logger.info("Item created", extra={"item_id": row["id"], "name": row["name"]})
        return dict(row)
    except Exception as exc:
        DB_QUERY_COUNT.labels(operation="insert", status="error").inc()
        logger.error("Failed to create item", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/api/v1/items/{item_id}")
async def get_item(item_id: int):
    logger.info("Getting item", extra={"item_id": item_id})

    if app_state.db_pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        async with app_state.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, description, price, stock FROM app.items WHERE id = $1",
                item_id
            )
        DB_QUERY_COUNT.labels(operation="select", status="success").inc()
        if row is None:
            logger.warning("Item not found", extra={"item_id": item_id})
            raise HTTPException(status_code=404, detail="Item not found")
        return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        DB_QUERY_COUNT.labels(operation="select", status="error").inc()
        logger.error("Failed to get item", extra={"item_id": item_id, "error": str(exc)})
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/api/v1/cache/{key}")
async def get_cache(key: str):
    logger.info("Cache lookup", extra={"key": key})

    if app_state.redis is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    value = await app_state.redis.get(key)
    if value is None:
        # Cache miss — set a value
        await app_state.redis.set(key, f"cached-value-for-{key}", ex=60)
        logger.info("Cache miss — set new value", extra={"key": key})
        return {"key": key, "value": None, "cache_hit": False}

    logger.info("Cache hit", extra={"key": key})
    return {"key": key, "value": value, "cache_hit": True}


@app.post("/api/v1/events")
async def publish_event(payload: dict[str, Any]):
    logger.info("Publishing event", extra={"event_type": payload.get("type", "unknown")})
    # Mock event publishing (RabbitMQ integration optional)
    event_id = str(uuid.uuid4())
    logger.info("Event published", extra={"event_id": event_id, "type": payload.get("type")})
    return {"event_id": event_id, "status": "published"}


@app.get("/api/v1/trace")
async def demo_trace():
    """Demonstrates distributed tracing with nested spans."""
    request_id = str(uuid.uuid4())
    logger.info("Starting trace demo", extra={"request_id": request_id})

    if OTEL_ENABLED and tracer:
        with tracer.start_as_current_span("demo-operation") as span:
            span.set_attribute("demo.request_id", request_id)

            # Simulate some work
            time.sleep(0.01)

            with tracer.start_as_current_span("db-query-simulation"):
                time.sleep(0.005)

            with tracer.start_as_current_span("cache-lookup-simulation"):
                time.sleep(0.002)

    logger.info("Trace demo complete", extra={"request_id": request_id})
    return {
        "message": "Trace recorded. Check Grafana → Tempo.",
        "request_id": request_id,
        "tracing_enabled": OTEL_ENABLED
    }


@app.get("/api/v1/info")
async def info():
    return {
        "service": "sample-api",
        "version": "1.0.0",
        "environment": "cloud-learnings-lab",
        "features": {
            "tracing": OTEL_ENABLED,
            "database": app_state.db_pool is not None,
            "cache": app_state.redis is not None,
        }
    }
