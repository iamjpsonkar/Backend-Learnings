← [Previous: RDS](./rds.md) | [Home](../../README.md) | [Next: DynamoDB →](./dynamodb.md)

---

# Amazon Aurora

Aurora is a MySQL- and PostgreSQL-compatible relational database built for the cloud. Its storage layer decouples from compute — storage auto-scales up to 128 TiB, replicates 6 copies across 3 AZs, and repairs itself without manual intervention. Aurora is up to 5x faster than MySQL RDS and 3x faster than PostgreSQL RDS.

---

## Aurora Architecture

```
Writer instance (primary)
     │  (writes)
     ▼
Aurora Storage Layer (6 copies across 3 AZs, auto-heals)
     │  (reads)
     ├── Reader instance (replica) AZ-a
     ├── Reader instance (replica) AZ-b
     └── Reader instance (replica) AZ-c

Endpoints:
  Cluster endpoint  → always points to the current writer
  Reader endpoint   → load-balances across all readers
  Instance endpoint → specific instance (rarely used directly)
  Custom endpoint   → subset of instances (for different workload tiers)
```

**Key differences from standard RDS:**
- Storage is shared and auto-scales — no need to pre-allocate
- Failover to a replica is faster (~30s vs ~60–120s for RDS Multi-AZ)
- Up to 15 read replicas (vs 5 for RDS)
- Backtrack: rewind the cluster to a previous state without restoring a snapshot
- Aurora Global Database: primary region + up to 5 secondary regions with <1s replication lag

---

## Creating an Aurora Cluster

```bash
SUBNET_GROUP="my-db-subnet-group"
SG_DB="sg-0db1234"

# Create the Aurora PostgreSQL cluster
CLUSTER_ID=$(aws rds create-db-cluster \
    --db-cluster-identifier my-aurora-postgres \
    --engine aurora-postgresql \
    --engine-version 16.2 \
    --master-username dbadmin \
    --master-user-password "$(aws secretsmanager get-secret-value \
        --secret-id prod/aurora/master-password \
        --query SecretString --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")" \
    --db-subnet-group-name $SUBNET_GROUP \
    --vpc-security-group-ids $SG_DB \
    --storage-encrypted \
    --kms-key-id arn:aws:kms:us-east-1:123456789012:key/mrk-abc1234 \
    --backup-retention-period 14 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "sun:05:00-sun:06:00" \
    --deletion-protection \
    --enable-cloudwatch-logs-exports postgresql \
    --tags Key=Name,Value=my-aurora-postgres Key=Environment,Value=production \
    --query 'DBCluster.DBClusterIdentifier' --output text)

echo "Cluster: $CLUSTER_ID"

# Add the writer instance
aws rds create-db-instance \
    --db-instance-identifier my-aurora-postgres-writer \
    --db-cluster-identifier $CLUSTER_ID \
    --db-instance-class db.r6g.large \
    --engine aurora-postgresql \
    --enable-performance-insights \
    --performance-insights-retention-period 7 \
    --tags Key=Name,Value=my-aurora-postgres-writer

# Add a reader instance in a different AZ
aws rds create-db-instance \
    --db-instance-identifier my-aurora-postgres-reader-1 \
    --db-cluster-identifier $CLUSTER_ID \
    --db-instance-class db.r6g.large \
    --engine aurora-postgresql \
    --availability-zone us-east-1b \
    --tags Key=Name,Value=my-aurora-postgres-reader-1

# Wait for the cluster to be available
aws rds wait db-cluster-available --db-cluster-identifier $CLUSTER_ID

# Get endpoints
aws rds describe-db-clusters \
    --db-cluster-identifier $CLUSTER_ID \
    --query 'DBClusters[0].{
        Writer:Endpoint,
        Reader:ReaderEndpoint,
        Port:Port,
        Status:Status,
        Members:DBClusterMembers[*].{ID:DBInstanceIdentifier,Writer:IsClusterWriter}
    }'
```

---

## Aurora Serverless v2

Aurora Serverless v2 automatically scales ACUs (Aurora Capacity Units) between a minimum and maximum, with no cold starts and sub-second scaling. It is available for both MySQL and PostgreSQL.

```bash
# Create an Aurora Serverless v2 cluster
aws rds create-db-cluster \
    --db-cluster-identifier my-aurora-serverless \
    --engine aurora-postgresql \
    --engine-version 16.2 \
    --master-username dbadmin \
    --manage-master-user-password \
    --db-subnet-group-name $SUBNET_GROUP \
    --vpc-security-group-ids $SG_DB \
    --storage-encrypted \
    --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=16 \
    --backup-retention-period 7 \
    --deletion-protection

# Add a Serverless v2 instance (use db.serverless class)
aws rds create-db-instance \
    --db-instance-identifier my-aurora-serverless-instance \
    --db-cluster-identifier my-aurora-serverless \
    --db-instance-class db.serverless \
    --engine aurora-postgresql

# Update scaling range
aws rds modify-db-cluster \
    --db-cluster-identifier my-aurora-serverless \
    --serverless-v2-scaling-configuration MinCapacity=1,MaxCapacity=32
```

**ACU pricing (us-east-1):**
- $0.12 per ACU-hour (each ACU = ~2 GB RAM + proportional CPU)
- $0.10/GB/month for storage
- No charge when paused (min = 0)

---

## Backtrack

Backtrack rewinds the cluster to a specific point within the backtrack window without restoring a snapshot. Much faster than PITR — takes seconds.

```bash
# Enable backtrack at cluster creation (MySQL only — not PostgreSQL)
aws rds create-db-cluster \
    --db-cluster-identifier my-aurora-mysql \
    --engine aurora-mysql \
    --engine-version 8.0 \
    --backtrack-window 86400 \   # 24 hours in seconds (max: 259200 = 72h)
    --master-username dbadmin \
    --master-user-password "ChangeMe123!" \
    --db-subnet-group-name $SUBNET_GROUP

# Backtrack to 30 minutes ago
aws rds backtrack-db-cluster \
    --db-cluster-identifier my-aurora-mysql \
    --backtrack-to "$(date -u -v-30M +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ)" \
    --use-earliest-time-on-point-in-time-unavailable

# View backtrack status
aws rds describe-db-cluster-backtracks \
    --db-cluster-identifier my-aurora-mysql \
    --query 'DBClusterBacktracks[0].{Status:Status,Time:BacktrackTo}'
```

---

## Aurora Global Database

Global Database spans multiple AWS regions. One primary region handles writes; secondary regions (read-only) serve local reads with <1s lag. Failover to a secondary takes ~1 minute.

```bash
# Create a global database from an existing cluster
GLOBAL_ID=$(aws rds create-global-cluster \
    --global-cluster-identifier my-aurora-global \
    --source-db-cluster-identifier arn:aws:rds:us-east-1:123456789012:cluster:my-aurora-postgres \
    --query 'GlobalCluster.GlobalClusterIdentifier' --output text)

# Add a secondary region
aws rds create-db-cluster \
    --db-cluster-identifier my-aurora-eu-secondary \
    --global-cluster-identifier $GLOBAL_ID \
    --engine aurora-postgresql \
    --engine-version 16.2 \
    --db-subnet-group-name my-db-subnet-group-eu \
    --vpc-security-group-ids sg-0eu-db \
    --region eu-west-1

aws rds create-db-instance \
    --db-instance-identifier my-aurora-eu-reader \
    --db-cluster-identifier my-aurora-eu-secondary \
    --db-instance-class db.r6g.large \
    --engine aurora-postgresql \
    --region eu-west-1

# Promote secondary to primary (for planned regional failover)
aws rds failover-global-cluster \
    --global-cluster-identifier $GLOBAL_ID \
    --target-db-cluster-identifier arn:aws:rds:eu-west-1:123456789012:cluster:my-aurora-eu-secondary \
    --allow-data-loss    # only if replication lag > 0

# Remove a secondary region from the global cluster
aws rds remove-from-global-cluster \
    --global-cluster-identifier $GLOBAL_ID \
    --db-cluster-identifier arn:aws:rds:eu-west-1:123456789012:cluster:my-aurora-eu-secondary \
    --region eu-west-1
```

---

## Custom Endpoints

Custom endpoints route traffic to a specific subset of cluster instances — useful for separating OLAP (analytics) queries from OLTP (application) queries.

```bash
# Create a custom endpoint for reporting queries (point to large reader instances)
aws rds create-db-cluster-endpoint \
    --db-cluster-identifier $CLUSTER_ID \
    --db-cluster-endpoint-identifier analytics-endpoint \
    --endpoint-type READER \
    --static-members my-aurora-postgres-reader-2    # the larger reader instance

# Applications use different endpoints for different workloads:
# OLTP: use the cluster reader endpoint (fast, shared)
# OLAP: use the custom analytics endpoint (dedicated large instances)
aws rds describe-db-cluster-endpoints \
    --db-cluster-identifier $CLUSTER_ID \
    --query 'DBClusterEndpoints[*].{
        ID:DBClusterEndpointIdentifier,
        Type:EndpointType,
        Endpoint:Endpoint,
        Status:Status
    }' \
    --output table
```

---

## Aurora vs RDS — When to Choose Aurora

| Factor | Choose Aurora | Choose RDS |
|--------|--------------|------------|
| Performance | Need >5x MySQL or >3x PostgreSQL speed | Standard RDBMS performance is sufficient |
| Storage auto-scaling | Need to grow beyond a fixed allocation | Predictable, manageable storage growth |
| Read replicas | Need up to 15 readers | 5 replicas is sufficient |
| Failover time | Need <30s failover | 60–120s is acceptable |
| Backtrack | MySQL — need fast rewind without snapshot | N/A (PostgreSQL backtrack not supported) |
| Cost | At scale (>50GB), Aurora is cheaper per GB | For small DBs (<50GB), RDS may be cheaper |
| Serverless | Variable/unpredictable load, dev/test | Steady, predictable load |
| Engine compatibility | MySQL 8.0 or PostgreSQL 16 | Any engine including SQL Server, Oracle |

---

## References

- [Aurora documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)
- [Aurora Serverless v2](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html)
- [Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)
- [Aurora best practices](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.BestPractices.html)
---

← [Previous: RDS](./rds.md) | [Home](../../README.md) | [Next: DynamoDB →](./dynamodb.md)
