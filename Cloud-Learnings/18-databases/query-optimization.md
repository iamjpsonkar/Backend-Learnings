← [Previous: Backups](./backups.md) | [Home](../README.md) | [Next: Disaster Recovery →](../19-disaster-recovery/README.md)

---

# Query Optimization

Slow queries are the most common database performance problem. Most can be fixed with indexes, query rewrites, or connection pool tuning — before you need to scale hardware.

---

## EXPLAIN ANALYZE

`EXPLAIN ANALYZE` is the primary tool for diagnosing slow queries.

```sql
-- Basic EXPLAIN ANALYZE
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT u.email, COUNT(o.id) as order_count, SUM(o.total_cents) as total_spent
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE o.created_at >= NOW() - INTERVAL '30 days'
  AND o.status = 'completed'
GROUP BY u.id, u.email
ORDER BY total_spent DESC
LIMIT 10;

-- Key things to look for in the output:
-- Seq Scan (bad for large tables) → missing index
-- Nested Loop (bad with large outer set) → consider Hash Join
-- "rows=X" vs "actual rows=Y" — large difference = stale statistics
-- "Buffers: shared hit=X read=Y" — 'read' means disk I/O, 'hit' means cache

-- Update statistics if estimates are very wrong
ANALYZE orders;
ANALYZE VERBOSE orders;

-- Find missing indexes (tables with many sequential scans)
SELECT schemaname, tablename, seq_scan, idx_scan,
       seq_scan - idx_scan AS missing_index_estimate,
       n_live_tup AS rows
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_scan - idx_scan DESC
LIMIT 20;
```

---

## Index Types

```sql
-- ─── B-tree (default) — equality, range, ORDER BY ─────────────────────────
CREATE INDEX idx_orders_created_at ON orders (created_at DESC);
CREATE INDEX idx_orders_user_status ON orders (user_id, status);

-- Partial index: only index rows you actually query
CREATE INDEX idx_orders_pending ON orders (created_at)
WHERE status = 'pending';    -- Much smaller, faster for pending-order queries

-- ─── GIN — JSONB, array, full-text search ────────────────────────────────────
CREATE INDEX idx_products_attributes ON products USING GIN (attributes);
CREATE INDEX idx_products_tags ON products USING GIN (tags);  -- text[]
CREATE INDEX idx_products_search ON products USING GIN (
    to_tsvector('english', name || ' ' || coalesce(description, ''))
);

-- ─── GiST — geometric, full-text, range types ────────────────────────────────
CREATE INDEX idx_locations_geo ON locations USING GIST (coordinates);  -- PostGIS
CREATE INDEX idx_events_time_range ON events USING GIST (duration);     -- tsrange

-- ─── BRIN — large sequential tables (time series, append-only) ──────────────
-- Very small, very fast for range queries on naturally-ordered data
CREATE INDEX idx_events_created_brin ON events USING BRIN (created_at)
WITH (pages_per_range = 128);

-- ─── Index on expression ─────────────────────────────────────────────────────
CREATE INDEX idx_users_email_lower ON users (LOWER(email));
-- Enables: WHERE LOWER(email) = 'alice@example.com'

-- ─── Covering index (INCLUDE) ────────────────────────────────────────────────
-- Index covers the WHERE clause AND returns columns without table lookup
CREATE INDEX idx_orders_user_covering ON orders (user_id, created_at DESC)
INCLUDE (id, status, total_cents);
-- SELECT id, status, total_cents FROM orders WHERE user_id = ? ORDER BY created_at DESC
-- → Index-only scan, no table access
```

---

## Common Anti-Patterns

```sql
-- ❌ Non-SARGable: function on indexed column breaks index use
SELECT * FROM users WHERE LOWER(email) = 'alice@example.com';
-- ✅ Fix: expression index or store lowercase in column
CREATE INDEX idx_users_email_lower ON users (LOWER(email));

-- ❌ Leading wildcard: cannot use B-tree index
SELECT * FROM products WHERE name LIKE '%shirt%';
-- ✅ Fix: use full-text search (GIN index on tsvector)
SELECT * FROM products
WHERE to_tsvector('english', name) @@ plainto_tsquery('english', 'shirt');

-- ❌ OR on different columns: prevents index use
SELECT * FROM orders WHERE user_id = $1 OR customer_email = $2;
-- ✅ Fix: UNION (each branch can use its own index)
SELECT * FROM orders WHERE user_id = $1
UNION
SELECT * FROM orders WHERE customer_email = $2;

-- ❌ SELECT *: fetches unnecessary columns, prevents index-only scans
SELECT * FROM orders WHERE user_id = $1;
-- ✅ Select only needed columns
SELECT id, status, total_cents, created_at FROM orders WHERE user_id = $1;

-- ❌ OFFSET pagination on large tables: scans all preceding rows
SELECT * FROM orders ORDER BY created_at DESC OFFSET 10000 LIMIT 20;
-- ✅ Keyset (cursor) pagination
SELECT * FROM orders
WHERE created_at < $last_seen_created_at  -- from previous page
ORDER BY created_at DESC LIMIT 20;
```

---

## N+1 Query Problem

```python
# ❌ N+1: 1 query for users, then 1 per user for orders (100 users = 101 queries)
users = session.query(User).limit(100).all()
for user in users:
    orders = session.query(Order).filter(Order.user_id == user.id).all()
    # Each loop iteration = 1 query

# ✅ Fix: JOIN or subquery in one query
from sqlalchemy.orm import joinedload, subqueryload

# Eager loading with JOIN
users = (
    session.query(User)
    .options(joinedload(User.orders))   # JOIN in the same query
    .limit(100)
    .all()
)
# user.orders is now populated — no extra queries

# For large collections: subquery load (avoids Cartesian product)
users = (
    session.query(User)
    .options(subqueryload(User.orders))  # Separate query with IN clause
    .limit(100)
    .all()
)

# ✅ Or: aggregate in SQL
from sqlalchemy import func
result = (
    session.query(
        User.id,
        User.email,
        func.count(Order.id).label("order_count"),
        func.sum(Order.total_cents).label("total_cents"),
    )
    .join(Order, Order.user_id == User.id, isouter=True)
    .group_by(User.id, User.email)
    .all()
)
```

---

## Slow Query Log

```bash
# PostgreSQL: find slow queries via pg_stat_statements
# Enable in postgresql.conf: shared_preload_libraries = 'pg_stat_statements'

psql -c "
SELECT
    calls,
    round(mean_exec_time::numeric, 2) AS avg_ms,
    round(total_exec_time::numeric, 2) AS total_ms,
    round(stddev_exec_time::numeric, 2) AS stddev_ms,
    rows,
    left(query, 100) AS query_snippet
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
"

# Identify tables with most sequential scans
psql -c "
SELECT schemaname, relname AS table, seq_scan, idx_scan,
       seq_tup_read, idx_tup_fetch,
       n_live_tup AS live_rows
FROM pg_stat_user_tables
WHERE seq_scan > 10
ORDER BY seq_tup_read DESC
LIMIT 20;
"

# Find unused indexes (wasting space, slowing writes)
psql -c "
SELECT schemaname, relname AS table, indexrelname AS index,
       idx_scan AS times_used,
       pg_size_pretty(pg_relation_size(i.indexrelid)) AS index_size
FROM pg_stat_user_indexes ui
JOIN pg_index i ON ui.indexrelid = i.indexrelid
WHERE idx_scan < 50          -- Used fewer than 50 times
  AND NOT i.indisunique      -- Not a unique constraint (can't drop those)
  AND NOT EXISTS (           -- Not used as a foreign key
      SELECT 1 FROM pg_constraint c
      WHERE c.conindid = i.indexrelid
  )
ORDER BY pg_relation_size(i.indexrelid) DESC;
"
```

---

## Connection Pool Sizing

```
PostgreSQL max_connections: 200 (typical)

PgBouncer (transaction mode):
  max_client_conn = 1000    # App-facing connections
  default_pool_size = 20    # Actual PostgreSQL connections

Application:
  pool_size = 10 per instance
  max_overflow = 5

With 5 app instances:
  Active PostgreSQL connections: 5 × (10 + 5) = 75
  PostgreSQL max_connections used: 75 / 200 = 37.5% ← healthy

Rule of thumb:
  PostgreSQL connections used = 3-5 × vCPU count
  For 4 vCPU: target 12-20 active connections to Postgres
```

---

## References

- [EXPLAIN documentation](https://www.postgresql.org/docs/current/using-explain.html)
- [Use The Index, Luke](https://use-the-index-luke.com/)
- [pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html)
- [PostgreSQL index types](https://www.postgresql.org/docs/current/indexes-types.html)

---

← [Previous: Backups](./backups.md) | [Home](../README.md) | [Next: Disaster Recovery →](../19-disaster-recovery/README.md)
