← [Previous: Refactor](./refactor.md) | [Home](../README.md) | [Next: Multi-Cloud →](../21-multi-cloud/README.md)

---

# Data Migration

Moving data is often the hardest part of a migration. Unlike application code, data has zero tolerance for loss or corruption. This file covers AWS DMS for live database migration, AWS Snow Family for offline bulk transfer, and patterns for large-scale data movement.

---

## AWS Database Migration Service (DMS)

DMS supports homogeneous (MySQL→MySQL) and heterogeneous (Oracle→PostgreSQL) migrations with minimal downtime using Change Data Capture (CDC).

### Supported Engines

| Source | Target | Notes |
|--------|--------|-------|
| MySQL 5.6+ | RDS MySQL, Aurora MySQL | Homogeneous — low schema conversion effort |
| PostgreSQL 9.4+ | RDS PostgreSQL, Aurora PostgreSQL | Homogeneous |
| Oracle 11g+ | PostgreSQL, Aurora, RDS Oracle | Requires AWS SCT for schema conversion |
| SQL Server 2008+ | RDS SQL Server, PostgreSQL | Requires AWS SCT for cross-engine |
| MongoDB | DocumentDB, DynamoDB | Flexible schema mapping |
| S3 (CSV/Parquet) | Redshift, S3, DynamoDB | Bulk data load |

### Heterogeneous Migration: Oracle to PostgreSQL

```bash
# Step 1: Use AWS Schema Conversion Tool (SCT) offline
# SCT analyzes Oracle schema and generates equivalent PostgreSQL DDL
# Download SCT from: https://aws.amazon.com/dms/schema-conversion-tool/
# Run locally, connect to Oracle source, export converted schema

# Step 2: Apply converted schema to target RDS PostgreSQL
psql -h $RDS_ENDPOINT -U admin -d myapp -f converted_schema.sql

# Step 3: Create DMS replication instance
aws dms create-replication-instance \
    --replication-instance-identifier oracle-to-pg-dms \
    --replication-instance-class dms.c5.2xlarge \
    --allocated-storage 200 \
    --publicly-accessible false \
    --vpc-security-group-ids sg-dms \
    --replication-subnet-group-identifier dms-subnet-group

# Step 4: Source endpoint (Oracle)
aws dms create-endpoint \
    --endpoint-identifier source-oracle \
    --endpoint-type source \
    --engine-name oracle \
    --server-name oracle-db.internal \
    --port 1521 \
    --database-name ORCL \
    --username dms_user \
    --password $ORACLE_PASSWORD \
    --oracle-settings '{
        "UseLogminerReader": true,
        "SecurityDbEncryption": "NO",
        "DirectPathNoLog": true
    }'

# Step 5: Target endpoint (RDS PostgreSQL)
aws dms create-endpoint \
    --endpoint-identifier target-postgres \
    --endpoint-type target \
    --engine-name postgres \
    --server-name $RDS_ENDPOINT \
    --port 5432 \
    --database-name myapp \
    --username dms_user \
    --password $PG_PASSWORD

# Step 6: Create migration task — full load + CDC
aws dms create-replication-task \
    --replication-task-identifier oracle-to-pg-task \
    --source-endpoint-arn $SOURCE_ARN \
    --target-endpoint-arn $TARGET_ARN \
    --replication-instance-arn $REP_INSTANCE_ARN \
    --migration-type full-load-and-cdc \
    --table-mappings file://table-mappings.json \
    --replication-task-settings file://task-settings.json

# table-mappings.json: include all tables in the schema
# task-settings.json: configure LOB handling, logging, parallel load

aws dms start-replication-task \
    --replication-task-arn $TASK_ARN \
    --start-replication-task-type start-replication
```

### Monitor DMS Task Health

```bash
# Check task status and table statistics
watch -n 30 'aws dms describe-replication-tasks \
    --filters Name=replication-task-arn,Values=$TASK_ARN \
    --query "ReplicationTasks[0].{
        Status:Status,
        FullLoadProgress:ReplicationTaskStats.FullLoadProgressPercent,
        CDCLatency:ReplicationTaskStats.CDCLatencySource,
        TablesLoaded:ReplicationTaskStats.TablesLoaded,
        TablesErrored:ReplicationTaskStats.TablesErrored
    }" --output table'

# Get per-table statistics
aws dms describe-table-statistics \
    --replication-task-arn $TASK_ARN \
    --query 'TableStatistics[?TableState!=`Table completed`].{
        Schema:SchemaName,Table:TableName,State:TableState,
        FullLoadRows:FullLoadRows,Inserts:Inserts,Updates:Updates,Errors:ValidationPendingRecords
    }' --output table

# Watch for validation errors
aws dms describe-table-statistics \
    --replication-task-arn $TASK_ARN \
    --query 'TableStatistics[?ValidationFailedRecords>`0`]'
```

### Cutover Procedure

```bash
# 1. Wait for CDC latency < 5 seconds
# 2. Stop writes on source (maintenance mode / traffic drain)

# 3. Wait for replication to catch up (lag = 0)
while true; do
    LAG=$(aws dms describe-replication-tasks \
        --filters Name=replication-task-arn,Values=$TASK_ARN \
        --query 'ReplicationTasks[0].ReplicationTaskStats.CDCLatencySource' \
        --output text)
    echo "CDC lag: ${LAG}s"
    [ "$LAG" -le 5 ] && break
    sleep 10
done

# 4. Stop the DMS task
aws dms stop-replication-task --replication-task-arn $TASK_ARN

# 5. Run row count validation
psql -h $RDS_ENDPOINT -U admin -d myapp -c "
SELECT
    (SELECT COUNT(*) FROM orders) AS pg_orders,
    $ORACLE_ORDER_COUNT AS oracle_orders;
"

# 6. Update connection strings in application config
# 7. Deploy new application version pointing to RDS
# 8. Verify application health
curl -sf https://api.myapp.com/health/ready

# 9. Keep DMS task paused for 24h (rollback option)
# 10. Decommission Oracle source after validation period
```

---

## AWS Snow Family

Use Snow devices when network transfer would take too long or is cost-prohibitive (> 10 TB over typical corporate WAN).

### Transfer Time Decision Matrix

```python
def estimate_transfer_method(
    data_size_tb: float,
    available_bandwidth_mbps: float,
    max_acceptable_days: int = 14,
) -> str:
    """
    Recommend transfer method based on data size and available bandwidth.
    """
    # Calculate network transfer time
    data_size_mb = data_size_tb * 1024 * 1024
    usable_bandwidth = available_bandwidth_mbps * 0.7  # 70% utilization cap
    transfer_seconds = data_size_mb / (usable_bandwidth / 8)
    transfer_days = transfer_seconds / 86400

    print(f"Data size: {data_size_tb:.1f} TB")
    print(f"Available bandwidth: {available_bandwidth_mbps:.0f} Mbps")
    print(f"Estimated network transfer: {transfer_days:.1f} days")

    if transfer_days <= max_acceptable_days:
        return f"Network transfer via Direct Connect or VPN — {transfer_days:.1f} days"
    elif data_size_tb <= 80:
        return "Snowball Edge Storage Optimized (80 TB usable)"
    elif data_size_tb <= 500:
        return f"Multiple Snowball Edge devices ({int(data_size_tb / 80) + 1} units)"
    else:
        return "Snowmobile (exabyte-scale — for 100+ PB)"


# Examples
print(estimate_transfer_method(5, 1000))    # 5 TB, 1 Gbps → network
print(estimate_transfer_method(50, 100))    # 50 TB, 100 Mbps → Snowball
print(estimate_transfer_method(300, 1000))  # 300 TB, 1 Gbps → multiple Snowballs
```

### Snowball Edge Workflow

```bash
# Step 1: Order Snowball Edge from AWS Console
# Choose: Snowball Edge Storage Optimized (80 TB usable)
# Provide: S3 bucket, IAM role, shipping address, KMS key

# Step 2: When device arrives, unlock it
# Download client: https://aws.amazon.com/snowball/resources/
snowballEdge configure
# Enter: Manifest file + unlock code (from AWS console)

snowballEdge unlock-device \
    --endpoint https://192.168.1.200 \
    --manifest-file manifest.bin \
    --unlock-code $UNLOCK_CODE

# Step 3: Copy data to device
# Configure AWS CLI to use Snowball endpoint
aws configure --profile snowball
# Set endpoint: http://192.168.1.200:8080

# List virtual S3 buckets on device
aws s3 ls --profile snowball --endpoint-url http://192.168.1.200:8080

# Copy data
aws s3 sync /data/archive/ s3://migration-bucket/ \
    --profile snowball \
    --endpoint-url http://192.168.1.200:8080 \
    --no-verify-ssl

# Step 4: Check transfer status
snowballEdge describe-transfer-status \
    --endpoint https://192.168.1.200

# Step 5: Ship device back to AWS
# AWS imports data into your S3 bucket automatically

# Step 6: Verify data in S3 after import
aws s3 ls s3://migration-bucket --recursive --human-readable \
    --query 'sum([].Size)'
```

---

## Large-Scale S3 Data Transfer

### S3 Transfer Acceleration

```bash
# Enable Transfer Acceleration on destination bucket
aws s3api put-bucket-accelerate-configuration \
    --bucket migration-destination \
    --accelerate-configuration Status=Enabled

# Use accelerate endpoint for uploads
aws s3 cp large-file.tar.gz \
    s3://migration-destination/ \
    --endpoint-url https://migration-destination.s3-accelerate.amazonaws.com

# Multi-part upload for files > 5 GB
aws s3 cp /data/large-dataset.tar.gz s3://migration-destination/ \
    --expected-size 107374182400 \  # 100 GB
    --multipart-threshold 1GB \
    --multipart-chunksize 100MB
```

### Parallel S3 Sync with GNU Parallel

```bash
# Split directory listing and sync in parallel (10 concurrent streams)
aws s3 ls s3://source-bucket --recursive \
    | awk '{print $4}' \
    | split -l 1000 - /tmp/s3-batch-

ls /tmp/s3-batch-* \
    | parallel -j 10 'cat {} | while read KEY; do
        aws s3 cp s3://source-bucket/$KEY s3://dest-bucket/$KEY
    done'

# Use s5cmd for high-throughput parallel operations (faster than AWS CLI)
# Install: https://github.com/peak/s5cmd
s5cmd cp --concurrency 256 's3://source/*' s3://destination/
```

### S3 Batch Operations

```bash
# Use S3 Batch for large-scale operations on existing objects
# (copy, tag, restore from Glacier, invoke Lambda)

# Create manifest: list of objects to process
aws s3api list-objects-v2 \
    --bucket source-bucket \
    --prefix data/2022/ \
    --query 'Contents[*].Key' \
    --output json > object-keys.json

# Create S3 Batch job
aws s3control create-job \
    --account-id $ACCOUNT_ID \
    --operation '{
        "S3CopyObject": {
            "TargetResource": "arn:aws:s3:::destination-bucket",
            "StorageClass": "INTELLIGENT_TIERING"
        }
    }' \
    --manifest '{
        "Spec": {"Format": "S3BatchOperations_CSV_20180820", "Fields": ["Bucket","Key"]},
        "Location": {
            "ObjectArn": "arn:aws:s3:::migration-manifests/object-keys.csv",
            "ETag": "abc123"
        }
    }' \
    --report '{
        "Bucket": "arn:aws:s3:::migration-reports",
        "Format": "Report_CSV_20180820",
        "Enabled": true,
        "ReportScope": "FailedTasksOnly"
    }' \
    --priority 10 \
    --role-arn arn:aws:iam::123456789012:role/S3BatchRole \
    --region us-east-1

# Monitor job progress
aws s3control describe-job \
    --account-id $ACCOUNT_ID \
    --job-id $JOB_ID \
    --query 'Job.{Status:Status,Progress:ProgressSummary}'
```

---

## DataSync for NFS/SMB/EFS/S3

AWS DataSync automates and accelerates data transfer between on-premises storage and AWS.

```bash
# Deploy DataSync agent (on-premises VM or EC2)
# Deploy as OVA (VMware), VHD (Hyper-V), or AMI

# Activate the agent
aws datasync create-agent \
    --activation-key $ACTIVATION_KEY \
    --agent-name prod-datasync-agent \
    --vpc-endpoint-id $VPC_ENDPOINT_ID \
    --subnet-arns arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc \
    --security-group-arns arn:aws:ec2:us-east-1:123456789012:security-group/sg-datasync

AGENT_ARN=$(aws datasync list-agents \
    --query 'Agents[0].AgentArn' --output text)

# Create source location (NFS on-premises)
aws datasync create-location-nfs \
    --server-hostname nfs-server.internal \
    --subdirectory /exports/data \
    --on-prem-config "AgentArns=[\"$AGENT_ARN\"]"

SOURCE_LOCATION_ARN=$(aws datasync list-locations \
    --query 'Locations[?LocationType==`NFS`].LocationArn' --output text)

# Create destination location (S3)
aws datasync create-location-s3 \
    --s3-bucket-arn arn:aws:s3:::migration-destination \
    --s3-config "BucketAccessRoleArn=arn:aws:iam::123456789012:role/DataSyncS3Role" \
    --subdirectory /migrated-data

DEST_LOCATION_ARN=$(aws datasync list-locations \
    --query 'Locations[?LocationType==`S3`].LocationArn' --output text)

# Create and start the task
aws datasync create-task \
    --source-location-arn $SOURCE_LOCATION_ARN \
    --destination-location-arn $DEST_LOCATION_ARN \
    --name on-prem-nfs-to-s3 \
    --options '{
        "VerifyMode": "ONLY_FILES_TRANSFERRED",
        "Atime": "BEST_EFFORT",
        "Mtime": "PRESERVE",
        "Uid": "INT_VALUE",
        "Gid": "INT_VALUE",
        "PreserveDeletedFiles": "PRESERVE",
        "OverwriteMode": "ALWAYS",
        "TaskQueueing": "ENABLED",
        "TransferMode": "CHANGED"
    }'

TASK_ARN=$(aws datasync list-tasks --query 'Tasks[0].TaskArn' --output text)

aws datasync start-task-execution --task-arn $TASK_ARN

# Monitor
aws datasync describe-task-execution \
    --task-execution-arn $TASK_EXECUTION_ARN \
    --query '{
        Status:Status,
        FilesTransferred:FilesTransferred,
        BytesTransferred:BytesTransferred,
        FilesVerified:FilesVerified
    }'
```

---

## Data Validation

Always validate after migration — never assume completeness.

```python
import hashlib
import logging
from typing import Iterator

import boto3
import psycopg2

logger = logging.getLogger(__name__)


def validate_row_counts(
    source_dsn: str,
    target_dsn: str,
    tables: list[str],
) -> dict[str, bool]:
    """Compare row counts between source and target databases."""
    results = {}

    with psycopg2.connect(source_dsn) as src_conn, \
         psycopg2.connect(target_dsn) as tgt_conn:

        for table in tables:
            src_count = _count_rows(src_conn, table)
            tgt_count = _count_rows(tgt_conn, table)
            match = src_count == tgt_count

            logger.info("Row count comparison", extra={
                "table": table,
                "source_count": src_count,
                "target_count": tgt_count,
                "match": match,
            })

            if not match:
                logger.warning("Row count mismatch", extra={
                    "table": table,
                    "delta": tgt_count - src_count,
                })

            results[table] = match

    return results


def _count_rows(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608 — internal trusted input
        return cur.fetchone()[0]


def validate_s3_checksums(
    source_bucket: str,
    dest_bucket: str,
    prefix: str,
) -> dict:
    """Verify S3 object ETags match between source and destination."""
    s3 = boto3.client("s3")
    mismatches = []
    total = 0

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=source_bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            total += 1
            key = obj["Key"]
            src_etag = obj["ETag"]

            try:
                dest_obj = s3.head_object(Bucket=dest_bucket, Key=key)
                dest_etag = dest_obj["ETag"]
                if src_etag != dest_etag:
                    mismatches.append({"key": key, "src_etag": src_etag, "dest_etag": dest_etag})
                    logger.warning("ETag mismatch", extra={"key": key})
            except s3.exceptions.NoSuchKey:
                mismatches.append({"key": key, "error": "missing_in_dest"})
                logger.error("Object missing in destination", extra={"key": key})

    logger.info("S3 validation complete", extra={
        "total_objects": total,
        "mismatches": len(mismatches),
        "prefix": prefix,
    })

    return {"total": total, "mismatches": len(mismatches), "details": mismatches}
```

---

## References

- [AWS DMS documentation](https://docs.aws.amazon.com/dms/latest/userguide/)
- [AWS Snow Family](https://aws.amazon.com/snow/)
- [AWS DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/)
- [S3 Batch Operations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html)

---

← [Previous: Refactor](./refactor.md) | [Home](../README.md) | [Next: Multi-Cloud →](../21-multi-cloud/README.md)
