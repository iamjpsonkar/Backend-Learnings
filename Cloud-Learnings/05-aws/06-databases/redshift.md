← [Previous: ElastiCache](./elasticache.md) | [Home](../../README.md) | [Next: AWS Containers →](../07-containers/README.md)

---

# Amazon Redshift

Redshift is a fully managed, petabyte-scale columnar data warehouse optimised for OLAP (Online Analytical Processing) and business intelligence workloads. It uses PostgreSQL-compatible SQL and integrates with standard BI tools.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Cluster** | Leader node + one or more compute nodes |
| **Serverless** | Redshift without provisioned clusters; auto-scales RPUs |
| **RA3 nodes** | Managed storage (S3-backed); decouple compute from storage |
| **RPU** | Redshift Processing Unit — serverless compute unit |
| **Distribution style** | How table rows are distributed across compute nodes |
| **Sort key** | Column(s) used to sort rows for zone map-based query pruning |
| **Redshift Spectrum** | Query S3 directly from Redshift without loading data |
| **Concurrency Scaling** | Burst read capacity added automatically; 1 hour free/day |
| **Data Sharing** | Share live data between Redshift clusters without copying |

---

## Redshift Serverless (Recommended Starting Point)

Redshift Serverless provisions and scales capacity automatically based on workload. You pay only while queries run.

```bash
# Create a namespace (holds databases, users, schemas)
aws redshift-serverless create-namespace \
    --namespace-name my-analytics \
    --admin-username admin \
    --admin-user-password "$(aws secretsmanager get-secret-value \
        --secret-id analytics/redshift/admin \
        --query SecretString --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")" \
    --db-name analytics \
    --iam-roles arn:aws:iam::123456789012:role/RedshiftS3Role \
    --tags key=Environment,value=production

# Create a workgroup (defines compute, network, security)
aws redshift-serverless create-workgroup \
    --workgroup-name my-analytics-wg \
    --namespace-name my-analytics \
    --base-capacity 32 \
    --max-capacity 512 \
    --subnet-ids subnet-private-1a subnet-private-1b \
    --security-group-ids sg-0redshift1234 \
    --publicly-accessible false

# Get the endpoint
aws redshift-serverless get-workgroup \
    --workgroup-name my-analytics-wg \
    --query 'workgroup.endpoint.address'
```

**Pricing (us-east-1):**
- $0.36 per RPU-hour
- $0.024/GB/month for managed storage
- 32 RPU baseline, scales to your max automatically

---

## Provisioned Cluster

```bash
SUBNET_GROUP="my-redshift-subnet-group"
SG_RS="sg-0redshift1234"

# Create subnet group
aws redshift create-cluster-subnet-group \
    --cluster-subnet-group-name my-redshift-subnet-group \
    --description "Private subnets for Redshift" \
    --subnet-ids subnet-private-1a subnet-private-1b

# Create an RA3 cluster (managed storage, pay per GB)
CLUSTER_ID=$(aws redshift create-cluster \
    --cluster-identifier my-analytics-cluster \
    --cluster-type multi-node \
    --node-type ra3.xlplus \
    --number-of-nodes 2 \
    --master-username admin \
    --master-user-password "InitialPassword123!" \
    --db-name analytics \
    --cluster-subnet-group-name $SUBNET_GROUP \
    --vpc-security-group-ids $SG_RS \
    --encrypted \
    --iam-roles arn:aws:iam::123456789012:role/RedshiftS3Role \
    --automated-snapshot-retention-period 7 \
    --preferred-maintenance-window "sun:05:00-sun:06:00" \
    --no-publicly-accessible \
    --tags Key=Environment,Value=production \
    --query 'Cluster.ClusterIdentifier' --output text)

# Wait for available (5–10 minutes)
aws redshift wait cluster-available --cluster-identifier $CLUSTER_ID

# Get the endpoint
aws redshift describe-clusters \
    --cluster-identifier $CLUSTER_ID \
    --query 'Clusters[0].{Endpoint:Endpoint.Address,Port:Endpoint.Port,Status:ClusterStatus}'
```

---

## Table Design

### Distribution Styles

```sql
-- EVEN: rows distributed evenly (good for tables without a clear join key)
CREATE TABLE page_views (
    view_id     BIGINT NOT NULL,
    user_id     BIGINT,
    page_url    VARCHAR(2000),
    viewed_at   TIMESTAMP
)
DISTSTYLE EVEN
SORTKEY (viewed_at);

-- KEY: rows with the same distribution key go to the same node
-- Use this when tables are frequently joined on the same column
CREATE TABLE orders (
    order_id    BIGINT NOT NULL,
    user_id     BIGINT NOT NULL,
    total       DECIMAL(10,2),
    created_at  TIMESTAMP
)
DISTSTYLE KEY
DISTKEY (user_id)
SORTKEY (created_at);

-- ALL: entire table replicated to every node
-- Use for small dimension tables (<1M rows) to avoid redistribute joins
CREATE TABLE countries (
    country_code CHAR(2) NOT NULL,
    country_name VARCHAR(100)
)
DISTSTYLE ALL;

-- AUTO: Redshift chooses (start here, optimize later)
CREATE TABLE events (
    event_id    BIGINT NOT NULL,
    event_type  VARCHAR(50),
    payload     SUPER,
    created_at  TIMESTAMP
)
DISTSTYLE AUTO
SORTKEY AUTO;
```

### Compression

```sql
-- ENCODE AUTO lets Redshift choose column compression automatically (recommended)
CREATE TABLE sales (
    sale_id     BIGINT ENCODE AZ64,
    product_id  INTEGER ENCODE AZ64,
    amount      DECIMAL(10,2) ENCODE AZ64,
    sale_date   DATE ENCODE AZ64,
    region      VARCHAR(50) ENCODE ZSTD
)
DISTSTYLE KEY
DISTKEY (product_id);

-- Analyze and apply best compression to an existing table
ANALYZE COMPRESSION sales;
```

---

## Loading Data

### COPY from S3 (Most Efficient)

```sql
-- Load CSV from S3
COPY sales
FROM 's3://my-data-bucket/sales/2026/'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3Role'
FORMAT AS CSV
IGNOREHEADER 1
TIMEFORMAT 'auto'
STATUPDATE ON;

-- Load Parquet (most efficient — native columnar format)
COPY sales
FROM 's3://my-data-bucket/sales/parquet/'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3Role'
FORMAT AS PARQUET;

-- Monitor COPY progress
SELECT query, status, rows, bytes, elapsed, filename
FROM stl_load_commits
ORDER BY starttime DESC
LIMIT 10;
```

### AWS CLI COPY trigger

```bash
# Run a COPY command via the Redshift Data API (no client needed)
EXECUTION_ID=$(aws redshift-data execute-statement \
    --workgroup-name my-analytics-wg \
    --database analytics \
    --sql "COPY sales FROM 's3://my-data-bucket/sales/' IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3Role' FORMAT AS PARQUET STATUPDATE ON;" \
    --query 'Id' --output text)

# Poll for completion
aws redshift-data describe-statement --id $EXECUTION_ID \
    --query '{Status:Status,Duration:Duration,Error:Error}'
```

---

## Redshift Spectrum — Query S3 Directly

Spectrum allows querying data in S3 without loading it into Redshift tables. Ideal for cold data, ad-hoc queries on historical data, and lake house architectures.

```sql
-- Create an external schema pointing to a Glue Data Catalog database
CREATE EXTERNAL SCHEMA spectrum_schema
FROM DATA CATALOG
DATABASE 'my_glue_database'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3Role'
CREATE EXTERNAL DATABASE IF NOT EXISTS;

-- Create an external table pointing to S3
CREATE EXTERNAL TABLE spectrum_schema.raw_events (
    event_id    BIGINT,
    user_id     BIGINT,
    event_type  VARCHAR(50),
    created_at  TIMESTAMP
)
PARTITIONED BY (dt VARCHAR(10))
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION 's3://my-data-lake/events/';

-- Add partitions (or let Glue Crawler handle it automatically)
ALTER TABLE spectrum_schema.raw_events ADD PARTITION (dt='2026-05-31')
LOCATION 's3://my-data-lake/events/dt=2026-05-31/';

-- Join Redshift table with S3 data via Spectrum
SELECT
    s.sale_id,
    s.amount,
    e.event_type,
    e.created_at
FROM sales s
JOIN spectrum_schema.raw_events e ON s.user_id = e.user_id
WHERE e.dt BETWEEN '2026-05-01' AND '2026-05-31'
LIMIT 100;
```

---

## Query Optimization

```sql
-- Explain plan: understand how Redshift executes a query
EXPLAIN
SELECT user_id, SUM(amount) AS total
FROM sales
WHERE sale_date >= '2026-01-01'
GROUP BY user_id
ORDER BY total DESC
LIMIT 100;

-- Find slow queries
SELECT
    query,
    trim(querytxt) AS sql,
    starttime,
    endtime,
    DATEDIFF(seconds, starttime, endtime) AS duration_s
FROM stl_query
WHERE userid > 1
ORDER BY duration_s DESC
LIMIT 20;

-- Find tables with high scan cost (candidates for sort key improvement)
SELECT
    trim(name) AS table_name,
    SUM(rows_pre_filter) AS total_rows_scanned,
    SUM(rows) AS rows_returned,
    SUM(rows_pre_filter) - SUM(rows) AS rows_filtered
FROM svl_query_summary qsm
JOIN pg_class pc ON qsm.table_id = pc.oid
WHERE is_diskbased = 'f'
GROUP BY table_name
ORDER BY rows_filtered DESC
LIMIT 20;

-- VACUUM and ANALYZE (run after bulk inserts/deletes)
VACUUM SORT ONLY sales;
ANALYZE sales;
```

---

## Snapshots and DR

```bash
# Create a manual snapshot
SNAPSHOT_ID=$(aws redshift create-cluster-snapshot \
    --cluster-identifier $CLUSTER_ID \
    --snapshot-identifier my-cluster-pre-migration \
    --query 'Snapshot.SnapshotIdentifier' --output text)

# Copy snapshot to another region
aws redshift copy-cluster-snapshot \
    --source-snapshot-identifier $SNAPSHOT_ID \
    --source-snapshot-cluster-identifier $CLUSTER_ID \
    --target-snapshot-identifier my-cluster-dr-copy \
    --region eu-west-1

# Restore cluster from snapshot
aws redshift restore-from-cluster-snapshot \
    --cluster-identifier my-cluster-restored \
    --snapshot-identifier $SNAPSHOT_ID \
    --cluster-subnet-group-name $SUBNET_GROUP \
    --vpc-security-group-ids $SG_RS
```

---

## Monitoring

```bash
CLUSTER_ID="my-analytics-cluster"

# Key CloudWatch metrics for Redshift:
# CPUUtilization              — alert at >80% sustained
# PercentageDiskSpaceUsed     — alert at >80%
# HealthStatus                — 1 = healthy
# MaintenanceMode             — 1 = in maintenance window
# QueryDuration               — p99 query time
# NumExceededSchemaQuotas     — schema limit breached

aws cloudwatch put-metric-alarm \
    --alarm-name redshift-disk-space \
    --namespace AWS/Redshift \
    --metric-name PercentageDiskSpaceUsed \
    --dimensions Name=ClusterIdentifier,Value=$CLUSTER_ID \
    --statistic Average \
    --period 300 \
    --evaluation-periods 3 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts
```

---

## References

- [Redshift documentation](https://docs.aws.amazon.com/redshift/latest/dg/)
- [Redshift Serverless](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-overview.html)
- [Redshift Spectrum](https://docs.aws.amazon.com/redshift/latest/dg/c-using-spectrum.html)
- [Table design best practices](https://docs.aws.amazon.com/redshift/latest/dg/c_designing-tables-best-practices.html)
- [Redshift pricing](https://aws.amazon.com/redshift/pricing/)
---

← [Previous: ElastiCache](./elasticache.md) | [Home](../../README.md) | [Next: AWS Containers →](../07-containers/README.md)
