← [Previous: Databases Overview](./README.md) | [Home](../README.md) | [Next: NoSQL →](./nosql.md)

---

# Relational Databases

Relational databases (RDBMS) store data in tables with rows and columns, enforce schemas, and provide ACID guarantees. PostgreSQL is the default choice for new applications — it is versatile, feature-rich, and handles most workloads from startup to large scale.

---

## AWS RDS PostgreSQL

```bash
# Create a production-grade RDS PostgreSQL instance
aws rds create-db-instance \
    --db-instance-identifier prod-postgres \
    --db-instance-class db.t3.medium \
    --engine postgres \
    --engine-version 15.4 \
    --master-username app_admin \
    --master-user-password "$(openssl rand -base64 32)" \
    --allocated-storage 100 \
    --storage-type gp3 \
    --storage-encrypted \
    --kms-key-id alias/prod/rds-key \
    --vpc-security-group-ids sg-db-prod \
    --db-subnet-group-name prod-db-subnet-group \
    --no-publicly-accessible \
    --multi-az \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "Sun:04:00-Sun:05:00" \
    --deletion-protection \
    --enable-performance-insights \
    --performance-insights-retention-period 7 \
    --enable-cloudwatch-logs-exports postgresql upgrade \
    --auto-minor-version-upgrade \
    --copy-tags-to-snapshot \
    --tags Key=environment,Value=production Key=service,Value=order-api

# Enable enhanced monitoring (1-second granularity)
aws rds modify-db-instance \
    --db-instance-identifier prod-postgres \
    --monitoring-interval 1 \
    --monitoring-role-arn arn:aws:iam::123456789012:role/RDSEnhancedMonitoringRole

# Create a read replica
aws rds create-db-instance-read-replica \
    --db-instance-identifier prod-postgres-replica \
    --source-db-instance-identifier prod-postgres \
    --db-instance-class db.t3.medium \
    --publicly-accessible false
```

---

## Connection Management

Managing database connections correctly is critical — connection exhaustion is one of the most common production outages.

### PgBouncer (Connection Pooler)

```ini
# pgbouncer.ini
[databases]
prod_db = host=prod-postgres.cluster.us-east-1.rds.amazonaws.com port=5432 dbname=app_db

[pgbouncer]
listen_port = 5432
listen_addr = 0.0.0.0
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

; Transaction pooling: best for stateless web apps
pool_mode = transaction
max_client_conn = 1000    ; Total connections pgbouncer accepts from apps
default_pool_size = 25    ; Connections per database/user pair to PostgreSQL
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 3

; Performance
server_idle_timeout = 600
client_idle_timeout = 0
log_connections = 0
log_disconnections = 0
```

### Python Connection Pool (SQLAlchemy)

```python
import logging
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

DB_URL = os.environ["DATABASE_URL"]  # postgresql://user:pass@host:5432/db


def create_db_engine():
    """Create a SQLAlchemy engine with optimized connection pool settings."""
    engine = create_engine(
        DB_URL,
        poolclass=QueuePool,
        pool_size=10,          # Permanent connections in pool
        max_overflow=5,        # Extra connections under load (total max: 15)
        pool_timeout=30,       # Wait up to 30s to get a connection
        pool_recycle=1800,     # Recycle connections every 30 min (avoid stale)
        pool_pre_ping=True,    # Verify connection is alive before using
        echo=False,
        connect_args={
            "application_name": os.environ.get("SERVICE_NAME", "app"),
            "connect_timeout": 5,
            "options": "-c statement_timeout=30000",  # 30s statement timeout
        },
    )

    @event.listens_for(engine, "connect")
    def set_pg_session_settings(dbapi_connection, connection_record):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET TIME ZONE 'UTC'")
            cursor.execute("SET search_path = app, public")
        logger.debug("Database connection established")

    @event.listens_for(engine, "checkout")
    def log_pool_checkout(dbapi_connection, connection_record, connection_proxy):
        pool = connection_proxy._pool
        logger.debug(
            "DB connection checked out",
            extra={"pool_size": pool.size(), "overflow": pool.overflow(), "checked_in": pool.checkedin()},
        )

    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a database session, commits or rolls back."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
        logger.debug("DB transaction committed")
    except Exception as exc:
        session.rollback()
        logger.error("DB transaction rolled back", extra={"error": str(exc)}, exc_info=True)
        raise
    finally:
        session.close()
```

---

## Schema Design Essentials

```sql
-- Always include:
-- 1. Primary key (use UUID or BIGSERIAL)
-- 2. Timestamps (created_at, updated_at)
-- 3. Soft delete where applicable

CREATE TABLE orders (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    currency    CHAR(3) NOT NULL DEFAULT 'USD',
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ                              -- Soft delete
);

-- Trigger: auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Indexes: cover your most common queries
CREATE INDEX idx_orders_user_id ON orders (user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_orders_status ON orders (status) WHERE deleted_at IS NULL;
CREATE INDEX idx_orders_created_at ON orders (created_at DESC);

-- For range queries + status filter:
CREATE INDEX idx_orders_user_status ON orders (user_id, status) WHERE deleted_at IS NULL;

-- JSONB index (if querying into metadata)
CREATE INDEX idx_orders_metadata_source ON orders USING GIN (metadata jsonb_path_ops);
```

---

## Key PostgreSQL Settings (RDS)

```sql
-- Check current settings
SELECT name, setting, unit FROM pg_settings
WHERE name IN (
    'max_connections', 'shared_buffers', 'effective_cache_size',
    'work_mem', 'maintenance_work_mem', 'wal_buffers',
    'checkpoint_completion_target', 'random_page_cost',
    'effective_io_concurrency', 'statement_timeout', 'log_min_duration_statement'
);

-- Useful parameter group settings for RDS (via AWS console or Terraform):
-- shared_buffers:           25% of instance RAM
-- effective_cache_size:     75% of instance RAM
-- work_mem:                 RAM / (max_connections * 4) — careful with sorts
-- maintenance_work_mem:     512MB for VACUUM/ANALYZE
-- random_page_cost:         1.1 for SSDs (default 4 is for spinning disks)
-- effective_io_concurrency: 200 for SSDs
-- log_min_duration_statement: 1000 (log queries > 1 second)
-- statement_timeout:        30000 (30s hard limit)
-- idle_in_transaction_session_timeout: 30000 (kill idle transactions)
```

---

## References

- [PostgreSQL documentation](https://www.postgresql.org/docs/current/)
- [PgBouncer documentation](https://www.pgbouncer.org/config.html)
- [AWS RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [PGTune — configuration calculator](https://pgtune.leopard.in.ua/)

---

← [Previous: Databases Overview](./README.md) | [Home](../README.md) | [Next: NoSQL →](./nosql.md)
