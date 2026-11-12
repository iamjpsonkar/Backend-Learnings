← [Previous: Caching](./caching.md) | [Home](../README.md) | [Next: Replication →](./replication.md)

---

# Database Migrations

Database migrations track and apply schema changes over time. Every change must be versioned, reviewed, and deployable without downtime in production.

---

## Zero-Downtime Migration Patterns

Most schema changes can be done without locking tables if you follow these patterns:

### Pattern 1: Add Column (safe)
```sql
-- Adding a nullable column is instant in PostgreSQL
ALTER TABLE orders ADD COLUMN fulfillment_region TEXT;
-- Never add NOT NULL without a default on an existing table with data
-- Always add nullable first, backfill, then add constraint
```

### Pattern 2: Add NOT NULL Column (requires steps)
```sql
-- Step 1 (deploy 1): Add nullable column
ALTER TABLE orders ADD COLUMN fulfillment_region TEXT;

-- Step 2: Backfill existing rows (do this in batches, not one UPDATE)
DO $$
DECLARE
  batch_size INT := 1000;
  last_id UUID := '00000000-0000-0000-0000-000000000000';
BEGIN
  LOOP
    UPDATE orders
    SET fulfillment_region = 'US'
    WHERE id IN (
      SELECT id FROM orders
      WHERE fulfillment_region IS NULL AND id > last_id
      ORDER BY id LIMIT batch_size
    );
    EXIT WHEN NOT FOUND;
    SELECT MAX(id) INTO last_id FROM orders WHERE fulfillment_region = 'US';
    PERFORM pg_sleep(0.01); -- brief pause to avoid lock contention
  END LOOP;
END $$;

-- Step 3 (deploy 2): Add NOT NULL constraint (after all rows are backfilled)
ALTER TABLE orders ALTER COLUMN fulfillment_region SET DEFAULT 'US';
ALTER TABLE orders ALTER COLUMN fulfillment_region SET NOT NULL;
```

### Pattern 3: Rename Column (expand-contract)
```sql
-- Step 1: Add new column
ALTER TABLE orders ADD COLUMN customer_id UUID;

-- Step 2: Write to both columns (application code update)
-- Step 3: Backfill new column
UPDATE orders SET customer_id = user_id WHERE customer_id IS NULL;

-- Step 4: Read from new column, stop writing to old
-- Step 5: Drop old column
ALTER TABLE orders DROP COLUMN user_id;
```

### Pattern 4: Add Index (non-blocking)
```sql
-- CONCURRENTLY avoids table lock (PostgreSQL)
-- Takes longer but doesn't block reads/writes
CREATE INDEX CONCURRENTLY idx_orders_customer_id ON orders (customer_id);
```

---

## Alembic (Python/SQLAlchemy)

```bash
# Initialize
pip install alembic sqlalchemy
alembic init alembic

# Create migration
alembic revision --autogenerate -m "add_fulfillment_region_to_orders"

# Apply migrations
alembic upgrade head

# Check current version
alembic current

# Show history
alembic history --verbose

# Downgrade one step
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade abc123
```

```python
# alembic/env.py — configure for async SQLAlchemy
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
import asyncio

from myapp.models import Base  # Import all models here

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online() -> None:
    """Use async engine for migrations."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async def do_run():
        async with connectable.connect() as connection:
            await connection.run_sync(
                lambda conn: context.configure(
                    connection=conn,
                    target_metadata=target_metadata,
                    compare_type=True,
                    compare_server_default=True,
                )
            )
            async with connection.begin():
                await connection.run_sync(lambda conn: context.run_migrations())

    asyncio.get_event_loop().run_until_complete(do_run())
```

```python
# alembic/versions/2024_01_15_add_fulfillment_region.py
"""add fulfillment_region to orders

Revision ID: abc123
Revises: prev456
Create Date: 2024-01-15 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger("alembic.runtime.migration")
revision = "abc123"
down_revision = "prev456"
branch_labels = None
depends_on = None


def upgrade() -> None:
    logger.info("Adding fulfillment_region column to orders")
    # Step 1: Add nullable (safe, no lock)
    op.add_column("orders", sa.Column("fulfillment_region", sa.Text, nullable=True))
    # Note: NOT NULL constraint added in a follow-up migration after backfill


def downgrade() -> None:
    logger.info("Dropping fulfillment_region column from orders")
    op.drop_column("orders", "fulfillment_region")
```

---

## Flyway (Java/multi-language)

```bash
# Install
brew install flyway

# Project layout
# db/migrations/
#   V1__create_users.sql
#   V2__create_orders.sql
#   V3__add_fulfillment_region.sql
#   R__refresh_user_stats.sql    # Repeatable migration (prefix R)

# flyway.conf
flyway.url=jdbc:postgresql://localhost:5432/myapp
flyway.user=app_admin
flyway.password=${DB_PASSWORD}
flyway.locations=filesystem:db/migrations
flyway.validateOnMigrate=true
flyway.outOfOrder=false

# Apply
flyway migrate

# Validate (check applied matches files)
flyway validate

# Info
flyway info

# Repair (mark failed migration as resolved)
flyway repair
```

```sql
-- V3__add_fulfillment_region.sql
-- Migration: add fulfillment_region column (nullable)
-- Safe for zero-downtime deployment — no table lock

ALTER TABLE orders ADD COLUMN IF NOT EXISTS fulfillment_region TEXT;

COMMENT ON COLUMN orders.fulfillment_region IS 'AWS region where order is fulfilled';

-- Create index concurrently (run separately if on busy table)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_fulfillment_region
--     ON orders (fulfillment_region);
```

---

## CI/CD Integration

```yaml
# GitHub Actions: run migrations before deploying the application
jobs:
  migrate:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Run database migrations
        run: |
          # Wait for DB to be reachable
          timeout 30 bash -c 'until pg_isready -h $DB_HOST -p 5432; do sleep 1; done'

          # Run migrations
          alembic upgrade head
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Verify migration applied
        run: |
          alembic current | grep -q "head" || (echo "Migration not at head" && exit 1)

  deploy:
    needs: migrate    # Deploy only after migration succeeds
    runs-on: ubuntu-latest
    steps:
      - name: Deploy application
        run: |
          aws ecs update-service --cluster prod --service my-app --force-new-deployment
```

---

## Migration Safety Checklist

Before running any migration in production:

- [ ] Migration tested in staging against a copy of production data
- [ ] Migration is idempotent (uses `IF NOT EXISTS`, `IF EXISTS`)
- [ ] No `ALTER TABLE ... REWRITE` on large tables (rewrites lock the entire table)
- [ ] No `ADD COLUMN NOT NULL` without default on existing table with data
- [ ] Indexes created with `CONCURRENTLY`
- [ ] Estimated duration measured in staging
- [ ] Rollback script tested
- [ ] DB backup taken before applying
- [ ] Team notified (especially on-call)

---

## References

- [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/)
- [Flyway documentation](https://documentation.red-gate.com/fd)
- [Zero-downtime migrations (Strong Migrations gem patterns)](https://github.com/ankane/strong_migrations)
- [PostgreSQL ALTER TABLE locking](https://www.postgresql.org/docs/current/sql-altertable.html)

---

← [Previous: Caching](./caching.md) | [Home](../README.md) | [Next: Replication →](./replication.md)
