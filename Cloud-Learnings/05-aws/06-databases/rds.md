← [Previous: AWS Databases](./README.md) | [Home](../../README.md) | [Next: Aurora →](./aurora.md)

---

# Amazon RDS — Relational Database Service

RDS is a managed relational database service supporting MySQL, PostgreSQL, MariaDB, SQL Server, Oracle, and Db2. AWS handles provisioning, patching, automated backups, failover, and hardware management.

---

## Supported Engines

| Engine | Versions | Notable feature |
|--------|----------|-----------------|
| PostgreSQL | 13–16 | Best open-source feature set; PgBouncer compatible |
| MySQL | 8.0 | Most widely used; compatible with Aurora MySQL |
| MariaDB | 10.6–11 | MySQL fork; open-source |
| SQL Server | 2019, 2022 | Windows Authentication; always encrypted |
| Oracle | 19c, 21c | Bring your own license (BYOL) or license included |
| Db2 | 11.5 | IBM Db2 managed |

---

## Creating an RDS Instance

```bash
VPC_ID="vpc-0abc1234"
SUBNET_GROUP="my-db-subnet-group"
SG_DB="sg-0db1234"

# Create DB subnet group (must span at least 2 AZs)
aws rds create-db-subnet-group \
    --db-subnet-group-name my-db-subnet-group \
    --db-subnet-group-description "Private subnets for RDS" \
    --subnet-ids subnet-db-1a subnet-db-1b \
    --tags Key=Environment,Value=production

# Create a PostgreSQL Multi-AZ instance
DB_INSTANCE_ID=$(aws rds create-db-instance \
    --db-instance-identifier my-postgres-prod \
    --db-instance-class db.t3.medium \
    --engine postgres \
    --engine-version 16.2 \
    --master-username dbadmin \
    --master-user-password "$(aws secretsmanager get-secret-value \
        --secret-id prod/rds/master-password \
        --query SecretString --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")" \
    --allocated-storage 100 \
    --max-allocated-storage 1000 \
    --storage-type gp3 \
    --iops 3000 \
    --storage-encrypted \
    --kms-key-id arn:aws:kms:us-east-1:123456789012:key/mrk-abc1234 \
    --db-subnet-group-name $SUBNET_GROUP \
    --vpc-security-group-ids $SG_DB \
    --multi-az \
    --backup-retention-period 14 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "sun:05:00-sun:06:00" \
    --deletion-protection \
    --enable-cloudwatch-logs-exports postgresql upgrade \
    --enable-performance-insights \
    --performance-insights-retention-period 7 \
    --tags Key=Name,Value=my-postgres-prod Key=Environment,Value=production \
    --query 'DBInstance.DBInstanceIdentifier' --output text)

echo "Creating: $DB_INSTANCE_ID"

# Wait until available (10–20 minutes)
aws rds wait db-instance-available --db-instance-identifier $DB_INSTANCE_ID

# Get the connection endpoint
aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_ID \
    --query 'DBInstances[0].{
        Endpoint:Endpoint.Address,
        Port:Endpoint.Port,
        Status:DBInstanceStatus,
        AZ:AvailabilityZone,
        MultiAZ:MultiAZ,
        Engine:Engine,
        Version:EngineVersion
    }'
```

---

## Parameter Groups and Option Groups

```bash
# Create a custom parameter group for PostgreSQL tuning
aws rds create-db-parameter-group \
    --db-parameter-group-name my-postgres-params \
    --db-parameter-group-family postgres16 \
    --description "Tuned parameters for production PostgreSQL 16"

# Tune key parameters
aws rds modify-db-parameter-group \
    --db-parameter-group-name my-postgres-params \
    --parameters \
        "ParameterName=max_connections,ParameterValue=200,ApplyMethod=pending-reboot" \
        "ParameterName=shared_buffers,ParameterValue={DBInstanceClassMemory/4},ApplyMethod=pending-reboot" \
        "ParameterName=log_min_duration_statement,ParameterValue=1000,ApplyMethod=immediate" \
        "ParameterName=log_connections,ParameterValue=1,ApplyMethod=immediate" \
        "ParameterName=log_disconnections,ParameterValue=1,ApplyMethod=immediate"

# Apply parameter group to the instance
aws rds modify-db-instance \
    --db-instance-identifier $DB_INSTANCE_ID \
    --db-parameter-group-name my-postgres-params \
    --apply-immediately
```

---

## Read Replicas

Read replicas offload read traffic from the primary. They use asynchronous replication and can be promoted to standalone instances.

```bash
# Create a read replica in the same region
RR_ID=$(aws rds create-db-instance-read-replica \
    --db-instance-identifier my-postgres-read-1 \
    --source-db-instance-identifier $DB_INSTANCE_ID \
    --db-instance-class db.t3.medium \
    --availability-zone us-east-1b \
    --enable-performance-insights \
    --tags Key=Name,Value=my-postgres-read-1 \
    --query 'DBInstance.DBInstanceIdentifier' --output text)

# Cross-region read replica (for DR or geo-local reads)
aws rds create-db-instance-read-replica \
    --db-instance-identifier my-postgres-eu-read \
    --source-db-instance-identifier arn:aws:rds:us-east-1:123456789012:db:my-postgres-prod \
    --region eu-west-1 \
    --db-instance-class db.t3.medium

# Promote a read replica to standalone (for failover or migration)
aws rds promote-read-replica \
    --db-instance-identifier my-postgres-read-1

# View all read replicas
aws rds describe-db-instances \
    --query 'DBInstances[?ReadReplicaSourceDBInstanceIdentifier!=`null`].{
        ID:DBInstanceIdentifier,
        Source:ReadReplicaSourceDBInstanceIdentifier,
        Lag:StatusInfos[?StatusType==`read replication`].Message|[0]
    }' \
    --output table
```

---

## Automated Backups and Point-in-Time Recovery

```bash
DB_ID="my-postgres-prod"

# Automated backups are taken daily during the backup window
# View available automated backups
aws rds describe-db-instance-automated-backups \
    --db-instance-identifier $DB_ID \
    --query 'DBInstanceAutomatedBackups[0].{
        ID:DBInstanceIdentifier,
        Earliest:RestoreWindow.EarliestTime,
        Latest:RestoreWindow.LatestTime,
        Retention:BackupRetentionPeriod
    }'

# Restore to a specific point in time (creates a new instance)
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier $DB_ID \
    --target-db-instance-identifier my-postgres-restored \
    --restore-time "2026-05-30T14:30:00Z" \
    --db-instance-class db.t3.medium \
    --db-subnet-group-name $SUBNET_GROUP \
    --vpc-security-group-ids $SG_DB

# Create a manual snapshot (survives instance deletion)
SNAPSHOT_ID=$(aws rds create-db-snapshot \
    --db-instance-identifier $DB_ID \
    --db-snapshot-identifier my-postgres-pre-migration \
    --query 'DBSnapshot.DBSnapshotIdentifier' --output text)

aws rds wait db-snapshot-completed --db-snapshot-identifier $SNAPSHOT_ID

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier my-postgres-from-snapshot \
    --db-snapshot-identifier $SNAPSHOT_ID \
    --db-instance-class db.t3.medium \
    --db-subnet-group-name $SUBNET_GROUP

# Copy snapshot to another region
aws rds copy-db-snapshot \
    --source-db-snapshot-identifier arn:aws:rds:us-east-1:123456789012:snapshot:my-postgres-pre-migration \
    --target-db-snapshot-identifier my-postgres-dr-copy \
    --region eu-west-1 \
    --copy-tags
```

---

## Secrets Manager Integration

Store credentials in Secrets Manager and rotate them automatically.

```bash
# Store the master password in Secrets Manager
aws secretsmanager create-secret \
    --name prod/rds/my-postgres/master \
    --description "RDS master credentials for my-postgres-prod" \
    --secret-string '{"username":"dbadmin","password":"InitialPassword123!","engine":"postgres","host":"my-postgres-prod.abc.us-east-1.rds.amazonaws.com","port":5432,"dbname":"myapp"}'

# Enable automatic rotation (built-in Lambda rotator for RDS)
aws secretsmanager rotate-secret \
    --secret-id prod/rds/my-postgres/master \
    --rotation-rules AutomaticallyAfterDays=30

# Application connection pattern (Python)
```

```python
import boto3
import json
import psycopg2
import logging

logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Retrieve RDS credentials from Secrets Manager and return a connection.
    Credentials are cached by the Secrets Manager SDK for 5 minutes.
    """
    logger.info("Fetching database credentials from Secrets Manager")
    client = boto3.client("secretsmanager", region_name="us-east-1")

    try:
        secret = client.get_secret_value(SecretId="prod/rds/my-postgres/master")
        creds = json.loads(secret["SecretString"])
        logger.debug("Credentials retrieved: host=%s port=%s dbname=%s user=%s",
                     creds["host"], creds["port"], creds["dbname"], creds["username"])
    except Exception as e:
        logger.error("Failed to retrieve DB credentials: error=%s", str(e))
        raise

    try:
        conn = psycopg2.connect(
            host=creds["host"],
            port=creds["port"],
            dbname=creds["dbname"],
            user=creds["username"],
            password=creds["password"],
            sslmode="require",
        )
        logger.info("Database connection established: host=%s", creds["host"])
        return conn
    except Exception as e:
        logger.error("Failed to connect to database: host=%s error=%s", creds.get("host"), str(e))
        raise
```

---

## Scaling

```bash
DB_ID="my-postgres-prod"

# Vertical scaling (instance class change — causes brief downtime for Multi-AZ failover)
aws rds modify-db-instance \
    --db-instance-identifier $DB_ID \
    --db-instance-class db.r6g.large \
    --apply-immediately

# Storage scaling — increase disk size (online, no downtime)
aws rds modify-db-instance \
    --db-instance-identifier $DB_ID \
    --allocated-storage 500 \
    --apply-immediately

# Storage autoscaling is set at creation (--max-allocated-storage)
# RDS auto-expands storage when free space < 10% or 5GB (whichever is smaller)

# Enable Multi-AZ after the fact (causes brief failover)
aws rds modify-db-instance \
    --db-instance-identifier $DB_ID \
    --multi-az \
    --apply-immediately
```

---

## RDS Proxy

RDS Proxy pools and multiplexes application connections to RDS, reducing connection overhead and improving resilience during failover.

```bash
PROXY_ARN=$(aws rds create-db-proxy \
    --db-proxy-name my-postgres-proxy \
    --engine-family POSTGRESQL \
    --auth '[{
        "AuthScheme": "SECRETS",
        "SecretArn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/rds/my-postgres/master",
        "IAMAuth": "REQUIRED"
    }]' \
    --role-arn arn:aws:iam::123456789012:role/RDSProxyRole \
    --vpc-subnet-ids subnet-private-1a subnet-private-1b \
    --vpc-security-group-ids $SG_DB \
    --require-tls \
    --query 'DBProxy.DBProxyArn' --output text)

# Register the DB instance as a target
aws rds register-db-proxy-targets \
    --db-proxy-name my-postgres-proxy \
    --db-instance-identifiers $DB_ID

# Applications connect to the proxy endpoint instead of the DB endpoint
PROXY_ENDPOINT=$(aws rds describe-db-proxies \
    --db-proxy-name my-postgres-proxy \
    --query 'DBProxies[0].Endpoint' --output text)

echo "Connect applications to: $PROXY_ENDPOINT"
```

---

## Monitoring

```bash
DB_ID="my-postgres-prod"

# Enable Enhanced Monitoring (1-second granularity via CloudWatch Logs)
aws rds modify-db-instance \
    --db-instance-identifier $DB_ID \
    --monitoring-interval 60 \
    --monitoring-role-arn arn:aws:iam::123456789012:role/rds-monitoring-role

# Key CloudWatch metrics to alarm on:
# CPUUtilization          — spike → queries need optimization or scale up
# FreeStorageSpace        — alert at <20% of total
# DatabaseConnections     — near max_connections → use RDS Proxy
# ReadLatency / WriteLatency — alert at >20ms
# ReplicaLag              — alert at >60s for read replicas

aws cloudwatch put-metric-alarm \
    --alarm-name rds-low-storage \
    --namespace AWS/RDS \
    --metric-name FreeStorageSpace \
    --dimensions Name=DBInstanceIdentifier,Value=$DB_ID \
    --statistic Average \
    --period 300 \
    --evaluation-periods 3 \
    --threshold 10737418240 \  # 10 GB in bytes
    --comparison-operator LessThanThreshold \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts
```

---

## References

- [RDS documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/)
- [RDS best practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [RDS Proxy](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html)
- [Secrets Manager rotation for RDS](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotate-secrets_turn-on-for-db.html)
---

← [Previous: AWS Databases](./README.md) | [Home](../../README.md) | [Next: Aurora →](./aurora.md)
