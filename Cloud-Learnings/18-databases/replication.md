← [Previous: Migrations](./migrations.md) | [Home](../README.md) | [Next: Backups →](./backups.md)

---

# Replication

Replication copies data from a primary database to one or more replicas. It serves two purposes: high availability (failover if primary fails) and read scaling (direct read queries to replicas).

---

## Replication Types

| Type | How it works | Use case |
|------|-------------|---------|
| **Streaming replication** (async) | WAL records streamed to replica; slight lag | Read scaling, HA |
| **Streaming replication** (sync) | Primary waits for replica acknowledgement | Zero data loss (higher latency) |
| **Logical replication** | Row-level changes replicated; partial table support | Cross-version upgrades, multi-region |
| **Physical replication** | Bit-for-bit copy of data files | Standby servers, backups |

---

## AWS RDS Multi-AZ vs Read Replicas

| Feature | Multi-AZ | Read Replica |
|---------|----------|-------------|
| Purpose | High availability (failover) | Read scaling |
| Sync mode | Synchronous | Asynchronous |
| Failover | Automatic (60–120s) | Manual promotion |
| Readable | No (standby not accessible) | Yes |
| Cross-region | Yes (Multi-AZ clusters) | Yes |

```bash
# Enable Multi-AZ (synchronous standby for failover)
aws rds modify-db-instance \
    --db-instance-identifier prod-postgres \
    --multi-az \
    --apply-immediately

# Create a read replica for read scaling
aws rds create-db-instance-read-replica \
    --db-instance-identifier prod-postgres-replica-1 \
    --source-db-instance-identifier prod-postgres \
    --db-instance-class db.t3.medium \
    --publicly-accessible false \
    --tags Key=role,Value=read-replica

# Monitor replication lag
aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS \
    --metric-name ReplicaLag \
    --dimensions Name=DBInstanceIdentifier,Value=prod-postgres-replica-1 \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Average \
    --query 'Datapoints[-1].Average'

# Promote read replica to standalone (for migration or failover testing)
aws rds promote-read-replica \
    --db-instance-identifier prod-postgres-replica-1
```

---

## Connection Routing (Read/Write Split)

```python
import logging
import os
from typing import Literal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

# Separate connection pools for write and read
_write_engine = create_engine(
    os.environ["DATABASE_WRITE_URL"],
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=1800,
)
_read_engine = create_engine(
    os.environ["DATABASE_READ_URL"],
    pool_size=20,    # Larger pool for read replica — more parallel reads
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
    execution_options={"isolation_level": "READ COMMITTED"},
)

WriteSession = sessionmaker(bind=_write_engine)
ReadSession = sessionmaker(bind=_read_engine)


def get_session(mode: Literal["write", "read"] = "write") -> Session:
    """
    Return a DB session. Use read session for SELECT-only operations.
    Important: Read replica has ~100ms lag — don't read your own writes via replica.
    """
    if mode == "read":
        logger.debug("Using read replica session")
        return ReadSession()
    logger.debug("Using write primary session")
    return WriteSession()


# Usage pattern: read from replica, write to primary
async def get_product_listing(category: str) -> list[dict]:
    """Can tolerate slight staleness — use read replica."""
    with get_session("read") as session:
        return session.execute(
            "SELECT id, name, price_cents FROM products WHERE category = :cat",
            {"cat": category}
        ).fetchall()


async def place_order(user_id: str, items: list) -> str:
    """Write must go to primary."""
    with get_session("write") as session:
        order_id = session.execute(
            "INSERT INTO orders (user_id, status) VALUES (:uid, 'pending') RETURNING id",
            {"uid": user_id}
        ).scalar()
        session.commit()
        logger.info("Order created", extra={"order_id": order_id, "user_id": user_id})
        return order_id
```

---

## PostgreSQL Streaming Replication (Self-Managed)

```bash
# Primary: postgresql.conf
# wal_level = replica
# max_wal_senders = 3
# wal_keep_size = 1GB
# synchronous_commit = on   # 'remote_apply' for stronger guarantee

# Primary: pg_hba.conf — allow replica to connect
# host replication replicator 10.0.11.5/32 md5

# Primary: create replication user
psql -c "CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'repl-pass';"

# Replica: take base backup from primary
pg_basebackup \
    -h 10.0.10.5 \            # Primary IP
    -U replicator \
    -D /var/lib/postgresql/data \
    -P -Xs -R                 # -R creates standby.signal + postgresql.auto.conf

# Replica: postgresql.auto.conf (created by -R flag)
# primary_conninfo = 'host=10.0.10.5 port=5432 user=replicator password=repl-pass application_name=replica1'
# primary_slot_name = 'replica1_slot'

# Primary: create replication slot (prevents WAL from being removed before replica consumes it)
psql -c "SELECT pg_create_physical_replication_slot('replica1_slot');"

# Monitor replication lag on primary
psql -c "
SELECT
    application_name,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    (sent_lsn - replay_lsn) AS replication_lag_bytes,
    replay_lag
FROM pg_stat_replication;
"
```

---

## Logical Replication (Cross-Version / Partial Table)

```sql
-- Source DB: enable logical replication
-- postgresql.conf: wal_level = logical

-- Source: create publication
CREATE PUBLICATION orders_pub FOR TABLE orders, order_items;

-- Target DB: create subscription
CREATE SUBSCRIPTION orders_sub
CONNECTION 'host=source-db port=5432 dbname=myapp user=replicator password=repl-pass'
PUBLICATION orders_pub
WITH (copy_data = true, synchronous_commit = 'off');

-- Check subscription status
SELECT subname, subenabled, received_lsn FROM pg_subscription;

-- Monitor logical replication lag
SELECT
    slot_name,
    pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)) AS lag_size
FROM pg_replication_slots
WHERE slot_type = 'logical';
```

---

## Automatic Failover (Patroni)

```yaml
# patroni.yml — HA PostgreSQL with etcd
scope: postgres-cluster
name: node1

restapi:
  listen: 0.0.0.0:8008
  connect_address: 10.0.10.5:8008

etcd3:
  hosts: 10.0.1.1:2379,10.0.1.2:2379,10.0.1.3:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 30
    maximum_lag_on_failover: 1048576  # 1MB max lag before failing over
    postgresql:
      use_pg_rewind: true

postgresql:
  listen: 0.0.0.0:5432
  connect_address: 10.0.10.5:5432
  data_dir: /var/lib/postgresql/data
  authentication:
    replication:
      username: replicator
      password: repl-pass
    superuser:
      username: postgres
      password: postgres-pass
```

```bash
# Check cluster status
patronictl -c patroni.yml list

# Manual failover
patronictl -c patroni.yml failover postgres-cluster --master node1 --candidate node2

# Reinitialize a lagging replica
patronictl -c patroni.yml reinit postgres-cluster node3
```

---

## References

- [PostgreSQL Streaming Replication](https://www.postgresql.org/docs/current/warm-standby.html)
- [PostgreSQL Logical Replication](https://www.postgresql.org/docs/current/logical-replication.html)
- [AWS RDS Read Replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)
- [Patroni (HA PostgreSQL)](https://github.com/patroni/patroni)

---

← [Previous: Migrations](./migrations.md) | [Home](../README.md) | [Next: Backups →](./backups.md)
