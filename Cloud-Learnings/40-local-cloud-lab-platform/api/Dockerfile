# api/Dockerfile — FastAPI Lab API
# Multi-stage build: dependencies → runtime

FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a venv
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────
# Runtime stage
# ─────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL com.cloudlabs.project="local-cloud-lab"
LABEL com.cloudlabs.service="api"

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd -r labapi && useradd -r -g labapi labapi

WORKDIR /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY app/ ./app/

# Data directory for SQLite
RUN mkdir -p /app/data && chown -R labapi:labapi /app

USER labapi

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 4567

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=10 \
    CMD curl -sf http://localhost:4567/health || exit 1

CMD ["uvicorn", "app.main:app", \
    "--host", "0.0.0.0", \
    "--port", "4567", \
    "--log-level", "info", \
    "--no-access-log"]
