← [Previous: Containers & Kubernetes](./containers-k8s.md) | [Home](../README.md) | [Next: CI/CD →](./cicd.md)

---

# Troubleshooting: Databases

Database problems in production usually manifest as one of: connection errors (exhaustion, refused), slow queries (missing index, bad plan), replication lag, or failover issues. This guide covers PostgreSQL/RDS diagnostics.

---

## Connection Problems

### Too Many Connections

```sql
-- Check current connections
SELECT count(*), state, wait_event_type, wait_event
FROM pg_stat_activity
GROUP BY state, wait_event_type, wait_event
ORDER BY count DESC;

-- Check max_connections setting
SHOW max_connections;

-- See who is holding connections
SELECT pid, usename, application_name, client_addr, state,
       now() - query_start AS query_age,
       left(query, 80) AS query_snippet
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start;

-- Kill idle connections older than 10 minutes
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND now() - state_change > INTERVAL '10 minutes'
  AND pid != pg_backend_pid();
```

```bash
# RDS: check connection count via CloudWatch
aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS \
    --metric-name DatabaseConnections \
    --dimensions Name=DBInstanceIdentifier,Value=prod-postgres \
    --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Maximum

# Root cause: connection pool size too large, PgBouncer not configured
# Fix: add PgBouncer in front of RDS (see 18-databases/relational.md)
# Quick fix: reduce pool size in application or restart hung connections
```

### Connection Refused / Can't Connect

```bash
# Check RDS instance status
aws rds describe-db-instances \
    --db-instance-identifier prod-postgres \
    --query 'DBInstances[0].{Status:DBInstanceStatus,Endpoint:Endpoint.Address,Port:Endpoint.Port}'

# Verify security group allows traffic from application
DB_SG=$(aws rds describe-db-instances \
    --db-instance-identifier prod-postgres \
    --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text)

aws ec2 describe-security-groups \
    --group-ids $DB_SG \
    --query 'SecurityGroups[0].IpPermissions[?FromPort==`5432`]'

# Test connectivity from EC2/ECS task
# (use AWS Systems Manager to avoid SSH key management)
aws ssm start-session --target $INSTANCE_ID
# On instance:
# nc -zv prod-postgres.xxxx.us-east-1.rds.amazonaws.com 5432
# psql -h prod-postgres.xxxx.us-east-1.rds.amazonaws.com -U appuser -d appdb -c "SELECT 1"

# Check if RDS is in a maintenance window
aws rds describe-db-instances \
    --db-instance-identifier prod-postgres \
    --query 'DBInstances[0].{
        MaintenanceWindow:PreferredMaintenanceWindow,
        BackupWindow:PreferredBackupWindow,
        PendingModifications:PendingModifiedValues
    }'
```

---

## Slow Queries

```sql
-- Enable pg_stat_statements (requires restart on RDS — use parameter group)
-- aws rds modify-db-parameter-group --db-parameter-group-name prod-pg16
--   --parameters ParameterName=shared_preload_libraries,ParameterValue=pg_stat_statements

-- Top slow queries by total time
SELECT
    substring(query, 1, 80) AS query_snippet,
    calls,
    round(total_exec_time::numeric, 2) AS total_ms,
    round(mean_exec_time::numeric, 2) AS avg_ms,
    round(stddev_exec_time::numeric, 2) AS stddev_ms,
    rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- Find queries with high cache miss ratio (going to disk)
SELECT
    substring(query, 1, 80) AS query,
    calls,
    shared_blks_hit,
    shared_blks_read,
    round(100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0), 1) AS cache_hit_pct
FROM pg_stat_statements
WHERE shared_blks_hit + shared_blks_read > 1000
ORDER BY cache_hit_pct ASC
LIMIT 10;

-- Diagnose a specific slow query
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders o
JOIN order_items oi ON o.id = oi.order_id
WHERE o.customer_id = 'cust-123'
  AND o.created_at > NOW() - INTERVAL '30 days';

-- Look for: Seq Scan on large tables, high "Rows Removed by Filter", Buffers: read >> hit
```

```sql
-- Tables missing indexes (high seq scan count relative to idx scan)
SELECT
    schemaname,
    tablename,
    seq_scan,
    idx_scan,
    seq_tup_read,
    n_live_tup,
    CASE WHEN seq_scan > 0
         THEN round(100.0 * idx_scan / (seq_scan + idx_scan), 1)
    END AS idx_pct
FROM pg_stat_user_tables
WHERE n_live_tup > 10000
ORDER BY seq_tup_read DESC
LIMIT 15;

-- Check bloat: tables and indexes with lots of dead rows
SELECT
    tablename,
    n_live_tup,
    n_dead_tup,
    round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
    last_autovacuum,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY dead_pct DESC;

-- Manual VACUUM if autovacuum is behind
VACUUM (ANALYZE, VERBOSE) orders;
```

---

## RDS Performance Insights

```bash
# Get top SQL by load (requires Performance Insights enabled)
aws pi get-resource-metrics \
    --service-type RDS \
    --identifier db-ABCDEFGHIJKLMNOPQRSTU \
    --metric-queries '[{
        "Metric": "db.load.avg",
        "GroupBy": {"Group": "db.sql_tokenized", "Dimensions": ["db.sql_tokenized.statement"], "Limit": 10}
    }]' \
    --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period-in-seconds 60

# Check wait events
aws pi get-resource-metrics \
    --service-type RDS \
    --identifier db-ABCDEFGHIJKLMNOPQRSTU \
    --metric-queries '[{
        "Metric": "db.load.avg",
        "GroupBy": {"Group": "db.wait_event", "Limit": 10}
    }]' \
    --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period-in-seconds 60
```

---

## Replication Lag

```bash
# Check RDS read replica lag (seconds)
aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS \
    --metric-name ReplicaLag \
    --dimensions Name=DBInstanceIdentifier,Value=prod-postgres-replica \
    --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Maximum \
    --query 'Datapoints[-1].Maximum'

# Check replication slot lag (PostgreSQL)
SELECT
    slot_name,
    active,
    restart_lsn,
    confirmed_flush_lsn,
    pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS lag_bytes
FROM pg_replication_slots;

# Common causes of lag:
# 1. Long-running transaction on primary blocking WAL cleanup
SELECT pid, now() - xact_start AS duration, state, query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_start ASC
LIMIT 5;

# 2. Replica under-provisioned (can't apply WAL fast enough)
# Fix: scale up replica instance class

# 3. Bulk operation on primary (large INSERT/UPDATE)
# Fix: batch operations, use logical replication with filters
```

---

## RDS Failover

```bash
# Force a Multi-AZ failover (for testing or when primary is degraded)
aws rds reboot-db-instance \
    --db-instance-identifier prod-postgres \
    --force-failover

# Monitor failover progress
watch -n 5 'aws rds describe-db-instances \
    --db-instance-identifier prod-postgres \
    --query "DBInstances[0].{Status:DBInstanceStatus,AZ:AvailabilityZone,Endpoint:Endpoint.Address}"'

# Typical failover time: 60-120 seconds for RDS Multi-AZ

# After failover: verify application reconnects
# Applications using connection pooling (PgBouncer, SQLAlchemy) should auto-reconnect
# Applications holding persistent connections may need a restart

# Check CloudWatch for failover event
aws rds describe-events \
    --source-identifier prod-postgres \
    --source-type db-instance \
    --duration 60 \
    --query 'Events[*].{Time:Date,Message:Message}'
```

---

## DynamoDB Troubleshooting

```bash
# Check throttling (ConsumedCapacity vs ProvisionedCapacity)
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name UserErrors \
    --dimensions Name=TableName,Value=myapp-table \
    --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum

# Check for hot partitions (uneven access pattern)
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name ThrottledRequests \
    --dimensions Name=TableName,Value=myapp-table Name=Operation,Value=GetItem \
    --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum

# Scan table size and item count
aws dynamodb describe-table \
    --table-name myapp-table \
    --query 'Table.{Items:ItemCount,SizeBytes:TableSizeBytes,Status:TableStatus,BillingMode:BillingModeSummary.BillingMode}'

# Common fixes for throttling:
# 1. Switch to on-demand billing (PAY_PER_REQUEST) for unpredictable workloads
aws dynamodb update-table \
    --table-name myapp-table \
    --billing-mode PAY_PER_REQUEST

# 2. Add exponential backoff + jitter in application code
# 3. Review partition key design (avoid hot keys like user_id with heavy hitter)
```

---

## References

- [RDS troubleshooting](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Troubleshooting.html)
- [PostgreSQL pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html)
- [RDS Performance Insights](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.html)

---

← [Previous: Containers & Kubernetes](./containers-k8s.md) | [Home](../README.md) | [Next: CI/CD →](./cicd.md)
