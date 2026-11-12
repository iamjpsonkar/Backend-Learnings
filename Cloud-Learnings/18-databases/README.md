← [Previous: FinOps Culture](../17-finops/finops-culture.md) | [Home](../README.md) | [Next: Relational Databases →](./relational.md)

---

# Databases

Databases are the most critical stateful component in any system. Choosing the right database, operating it correctly, and knowing how to migrate and recover it are essential skills for any cloud engineer.

---

## Database Taxonomy

```
                    ┌─────────────────────────────────────┐
                    │         Choose by access pattern     │
                    └──────────────┬──────────────────────┘
                                   │
             ┌─────────────────────┼─────────────────────┐
             │                     │                     │
     Relational (SQL)          Key-Value             Document
    Structured, ACID          Ultra-fast            Flexible schema
  PostgreSQL, MySQL,RDS    Redis, DynamoDB       DynamoDB, MongoDB,
  Azure SQL, Cloud SQL      (simple lookups)        Firestore
             │                     │                     │
    ─────────┼─────────────────────┼─────────────────────┼──────────
             │                     │                     │
         Wide Column          Time Series             Search
       Cassandra, Bigtable   InfluxDB, TimescaleDB   Elasticsearch
       (write-heavy scale)   (metrics, IoT)          OpenSearch
```

---

## Topics

| File | Topics |
|------|--------|
| [Relational Databases](./relational.md) | PostgreSQL, RDS, connection pooling, indexing, EXPLAIN |
| [NoSQL](./nosql.md) | DynamoDB patterns, Firestore, MongoDB, choosing between them |
| [Caching](./caching.md) | Redis, Memcached, cache-aside, write-through, TTL, eviction |
| [Migrations](./migrations.md) | Alembic, Flyway, zero-downtime migration patterns |
| [Replication](./replication.md) | Primary/replica, read replicas, failover, logical replication |
| [Backups](./backups.md) | RDS automated backups, PITR, snapshot strategies, restore testing |
| [Query Optimization](./query-optimization.md) | EXPLAIN ANALYZE, index types, N+1, connection pooling |

---

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [AWS RDS User Guide](https://docs.aws.amazon.com/rds/latest/userguide/)
- [DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/)
- [Use The Index, Luke](https://use-the-index-luke.com/)

---

← [Previous: FinOps Culture](../17-finops/finops-culture.md) | [Home](../README.md) | [Next: Relational Databases →](./relational.md)
