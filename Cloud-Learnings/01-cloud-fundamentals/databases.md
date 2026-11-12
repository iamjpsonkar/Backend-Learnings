← [Previous: Networking](./networking.md) | [Home](../README.md) | [Next: IAM →](./iam.md)

---

# Cloud Database Fundamentals

## The Core Trade-off

Every database design involves trade-offs between consistency, availability, performance, and scalability. Cloud providers offer managed versions of most popular database types, removing the operational burden of patching, backups, and replication setup.

**Managed vs self-hosted:**

| Dimension | Self-hosted on EC2/VM | Managed (RDS/Cloud SQL) |
|-----------|----------------------|------------------------|
| Patching | You | Provider |
| Backups | You | Provider (automated) |
| Replication | You configure | Provider configures (Multi-AZ) |
| Failover | You implement | Provider automates |
| Monitoring | You set up | Built-in metrics |
| Cost | Lower unit cost | Higher cost, lower ops overhead |
| Control | Full | Limited (no superuser, no custom kernel params) |

---

## OLTP vs OLAP

**OLTP (Online Transaction Processing):** Handles many concurrent short transactions (INSERT, UPDATE, SELECT single rows). Examples: e-commerce orders, user authentication, financial transactions.

**OLAP (Online Analytical Processing):** Handles complex queries over large datasets. Scans millions of rows to compute aggregates. Examples: business intelligence, reporting, data warehousing.

| Dimension | OLTP | OLAP |
|-----------|------|------|
| Query type | Simple, indexed lookups | Complex aggregations, full scans |
| Concurrency | High (thousands of users) | Low (few analysts) |
| Data freshness | Real-time | Batch / near-real-time |
| Storage | Row-oriented | Column-oriented |
| Examples | PostgreSQL, MySQL, DynamoDB | Redshift, BigQuery, Snowflake |

---

## Relational Databases (SQL)

Relational databases store data in tables with defined schemas. Relationships between tables are expressed through foreign keys. Queries use SQL.

**Characteristics:**
- ACID transactions (Atomicity, Consistency, Isolation, Durability)
- Structured data with predefined schema
- Strong consistency
- Complex queries with JOINs

### Provider Equivalents

| Engine | AWS | Azure | GCP | Self-hosted |
|--------|-----|-------|-----|------------|
| PostgreSQL | RDS for PostgreSQL, Aurora PostgreSQL | Azure Database for PostgreSQL | Cloud SQL for PostgreSQL | EC2 + PostgreSQL |
| MySQL | RDS for MySQL, Aurora MySQL | Azure Database for MySQL | Cloud SQL for MySQL | EC2 + MySQL |
| SQL Server | RDS for SQL Server | Azure SQL Database | Cloud SQL for SQL Server | EC2 + SQL Server |
| Oracle | RDS for Oracle | — | — | EC2 + Oracle |

### AWS Aurora

Aurora is AWS's proprietary relational database engine, compatible with MySQL and PostgreSQL at the API level, but redesigned for the cloud.

Key differences from standard RDS:
- Up to 5x faster than MySQL, 3x faster than PostgreSQL (AWS claim)
- Storage automatically scales from 10GB to 128TB
- Up to 15 read replicas (vs 5 for standard RDS)
- Multi-AZ failover in ~30 seconds (vs ~60–120 for standard RDS)
- Serverless mode (Aurora Serverless v2) — scales compute to zero

### When to Use SQL

- You need ACID transactions (financial systems, inventory management)
- Your data has well-defined relationships (orders → line items → products)
- Your team is comfortable with SQL
- Your schema is stable

---

## NoSQL Databases

NoSQL databases use flexible schemas and are optimized for specific access patterns. They trade some SQL capabilities (complex JOINs, full ACID) for massive scalability and flexibility.

### Types of NoSQL Databases

#### Key-Value

Stores data as key-value pairs. Ultra-fast reads and writes by key. No query flexibility beyond key lookup.

| Provider | Service | Use case |
|---------|---------|---------|
| AWS | DynamoDB (can be used as KV), ElastiCache (Redis) | Session store, leaderboards, caching |
| Azure | Azure Cache for Redis, Cosmos DB | Caching, session management |
| GCP | Cloud Memorystore (Redis), Bigtable | Caching, time-series |
| Self-hosted | Redis, Memcached | In-memory caching |

#### Document

Stores data as JSON-like documents. Schema is flexible — documents in the same collection can have different fields.

| Provider | Service |
|---------|---------|
| AWS | DynamoDB (with complex item structures), DocumentDB (MongoDB-compatible) |
| Azure | Cosmos DB (document API) |
| GCP | Firestore |
| Self-hosted | MongoDB, CouchDB |

**When to use:** User profiles, product catalogs, content management, any data that doesn't fit neatly into rows and columns.

#### Wide-Column

Stores data in tables with rows and dynamic columns. Designed for massive scale and time-series data.

| Provider | Service |
|---------|---------|
| AWS | Keyspaces (Cassandra-compatible) |
| Azure | Cosmos DB (Cassandra API) |
| GCP | Bigtable |
| Self-hosted | Apache Cassandra |

**When to use:** IoT time-series data, click streams, write-heavy workloads at massive scale.

#### Graph

Stores data as nodes and edges. Optimized for traversing relationships.

| Provider | Service |
|---------|---------|
| AWS | Neptune |
| Azure | Cosmos DB (Gremlin API) |
| Self-hosted | Neo4j, Amazon Neptune, ArangoDB |

**When to use:** Social networks, fraud detection, recommendation engines, knowledge graphs.

---

## DynamoDB (AWS) — Deep Concept

DynamoDB is AWS's flagship NoSQL database. Fully serverless — no cluster to manage, scales automatically.

**Data model:**
- **Table**: The top-level container
- **Item**: A row (equivalent to a document)
- **Partition key**: Required — determines how data is distributed across partitions
- **Sort key**: Optional — enables range queries within a partition

```
Table: Orders
  Partition key: customerId
  Sort key: orderId (timestamp-based)

→ Query: "all orders for customer X, sorted by date" = one partition read
→ Query: "all orders across all customers" = full table scan (expensive)
```

**Capacity modes:**
- **On-demand**: Pay per request, no planning needed. Best for unpredictable workloads.
- **Provisioned**: Specify Read Capacity Units (RCU) and Write Capacity Units (WCU) — cheaper if predictable.

---

## Caching

Caching stores frequently accessed data in memory for faster retrieval, reducing load on the primary database.

### When to Cache

- Database queries that return the same result frequently (product catalog, user sessions)
- Expensive computation results
- API responses from external services

### Cache Strategies

**Cache-aside (lazy loading):** Application checks cache first. On cache miss, reads from DB and writes to cache.

```
1. App checks Redis for user:123
2. Cache miss → App reads from RDS
3. App writes result to Redis (TTL: 60s)
4. Next request for user:123 → Cache hit (fast)
```

**Write-through:** On every write to DB, also write to cache. Cache is always up to date, but higher write latency.

**Cache eviction policies:**
- `LRU` (Least Recently Used): Evict the item not accessed for the longest time
- `LFU` (Least Frequently Used): Evict the item accessed the fewest times
- `TTL` (Time to Live): Expire items after a fixed duration

### Provider Cache Services

| Provider | Service | Engines |
|---------|---------|---------|
| AWS | ElastiCache | Redis, Memcached |
| Azure | Azure Cache for Redis | Redis |
| GCP | Memorystore | Redis, Memcached |

---

## Data Warehouse (OLAP)

For analytics and business intelligence at scale:

| Provider | Service | Notes |
|---------|---------|-------|
| AWS | Redshift | Column-oriented, petabyte-scale |
| Azure | Azure Synapse Analytics | Integrates with Azure data ecosystem |
| GCP | BigQuery | Serverless, pay-per-query, very fast |
| Independent | Snowflake | Multi-cloud, separates storage from compute |

**BigQuery vs Redshift:**
- BigQuery: Serverless, scales automatically, pay per TB scanned
- Redshift: Provision cluster, reserved instances available, better for steady workloads

---

## SQL vs NoSQL Decision Guide

```
Is your data relational? (entities with relationships via foreign keys)
  Yes → SQL (RDS, Aurora, Cloud SQL)
  No  → Continue

Do you need ACID transactions across multiple records?
  Yes → SQL or DynamoDB with transactions
  No  → Continue

Do you need massive scale (millions of writes/second)?
  Yes → NoSQL (DynamoDB, Bigtable, Cassandra)
  No  → Continue

Do you need flexible schema (different fields per document)?
  Yes → Document DB (DynamoDB, MongoDB, Firestore)
  No  → Continue

Are you doing analytics on large datasets?
  Yes → Data Warehouse (Redshift, BigQuery, Snowflake)
  No  → Key-Value or Relational depending on access pattern
```

---

## References

- [AWS Database services overview](https://aws.amazon.com/products/databases/)
- [AWS DynamoDB developer guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/)
- [AWS RDS documentation](https://docs.aws.amazon.com/rds/)
- [GCP Database options](https://cloud.google.com/products/databases)
- [Azure database services](https://azure.microsoft.com/en-us/products/category/databases/)
- [NoSQL Distilled (book by Fowler and Sadalage)](https://www.martinfowler.com/books/nosql.html)
---

← [Previous: Networking](./networking.md) | [Home](../README.md) | [Next: IAM →](./iam.md)
