← [Previous: FSx](../05-storage/fsx.md) | [Home](../../README.md) | [Next: RDS →](./rds.md)

---

# AWS Databases

AWS offers purpose-built database services for every access pattern — relational, NoSQL key-value, in-memory caching, and analytical data warehouses. This section covers the five most commonly used services.

---

## Contents

| File | Description |
|------|-------------|
| [rds.md](./rds.md) | RDS — managed MySQL, PostgreSQL, SQL Server, Oracle, MariaDB |
| [aurora.md](./aurora.md) | Aurora — MySQL/PostgreSQL-compatible, 5x faster, serverless option |
| [dynamodb.md](./dynamodb.md) | DynamoDB — serverless NoSQL, single-digit millisecond latency |
| [elasticache.md](./elasticache.md) | ElastiCache — Redis and Memcached in-memory caching |
| [redshift.md](./redshift.md) | Redshift — columnar data warehouse for analytics |

---

## Database Selection Guide

```
What's your workload?
├── Relational, ACID transactions, existing SQL app?
│   ├── Migrating from MySQL/PostgreSQL? → Aurora (higher perf, lower cost at scale)
│   └── Existing SQL Server/Oracle license? → RDS SQL Server / RDS Oracle
├── Variable or unpredictable scale, NoSQL, serverless?
│   └── DynamoDB (key-value + document, global tables, DAX for caching)
├── Caching, session store, leaderboards, pub/sub?
│   └── ElastiCache for Redis (or Memcached for pure caching only)
└── OLAP, business intelligence, ad-hoc analytics?
    └── Redshift (petabyte-scale, Redshift Spectrum for S3)
```

---

## Minimum Competency Checklist

- [ ] Create an RDS Multi-AZ PostgreSQL instance in a private subnet
- [ ] Configure automated backups and test a point-in-time restore
- [ ] Create an Aurora Serverless v2 cluster and explain auto-pause
- [ ] Design a DynamoDB table with a composite key and GSI
- [ ] Estimate DynamoDB costs for a given read/write pattern
- [ ] Deploy ElastiCache Redis with cluster mode and TLS
- [ ] Write a cache-aside pattern in Python/Node using Redis
- [ ] Launch a Redshift Serverless workgroup and query S3 via Spectrum

---

## Key Concepts Across Services

| Concept | RDS / Aurora | DynamoDB | ElastiCache | Redshift |
|---------|-------------|----------|-------------|---------|
| HA model | Multi-AZ replica | 3-AZ replication (built-in) | Multi-AZ replica groups | Multi-AZ + RA3 |
| Read scaling | Read replicas | DAX, eventually consistent reads | Read replicas / cluster | Concurrency scaling |
| Backup | Automated (1–35 days) + manual | PITR (35 days) + on-demand | Backup to S3 | Automated snapshots |
| Encryption | KMS at rest + TLS in transit | KMS at rest + TLS | KMS + TLS | KMS + TLS |
| Serverless | Aurora Serverless v2 | Yes (on-demand capacity) | No | Redshift Serverless |
---

← [Previous: FSx](../05-storage/fsx.md) | [Home](../../README.md) | [Next: RDS →](./rds.md)
