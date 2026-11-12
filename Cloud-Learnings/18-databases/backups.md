← [Previous: Replication](./replication.md) | [Home](../README.md) | [Next: Query Optimization →](./query-optimization.md)

---

# Database Backups

A backup strategy that has never been tested is not a backup strategy. Define your RPO (Recovery Point Objective) and RTO (Recovery Time Objective) first, then choose the appropriate backup approach.

---

## RPO & RTO Targets

| Tier | RPO | RTO | Backup approach |
|------|-----|-----|----------------|
| Critical (payment, orders) | < 1 min | < 15 min | Continuous WAL archiving + standby |
| Important (user profiles) | < 1 hour | < 1 hour | PITR (Point-in-Time Recovery) |
| Standard (analytics) | < 24 hours | < 4 hours | Daily snapshots |
| Non-critical (dev/staging) | 1 day | 1 day | Daily snapshots only |

---

## AWS RDS Automated Backups

```bash
# Enable automated backups (1–35 days retention)
aws rds modify-db-instance \
    --db-instance-identifier prod-postgres \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --backup-target region \         # Copy to same region (default)
    --apply-immediately

# Enable cross-region backup copy
aws rds create-db-instance-automated-backups-replication \
    --source-db-instance-arn arn:aws:rds:us-east-1:123456789012:db:prod-postgres \
    --kms-key-id alias/prod/rds-key-us-west-2 \
    --source-region us-east-1 \
    --region us-west-2 \
    --backup-retention-period 7

# List available restore points
aws rds describe-db-instances \
    --db-instance-identifier prod-postgres \
    --query 'DBInstances[0].{
        LatestRestorableTime:LatestRestorableTime,
        EarliestRestorableTime:EarliestRestorableTime
    }'

# Point-in-time restore
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier prod-postgres \
    --target-db-instance-identifier prod-postgres-restored-2024-01-15 \
    --restore-time 2024-01-15T03:00:00Z \
    --db-instance-class db.t3.medium \
    --no-publicly-accessible \
    --vpc-security-group-ids sg-db-prod \
    --db-subnet-group-name prod-db-subnet-group

# Restore from snapshot
aws rds describe-db-snapshots \
    --db-instance-identifier prod-postgres \
    --query 'DBSnapshots[?Status==`available`].{Snap:DBSnapshotIdentifier,Time:SnapshotCreateTime}' \
    --output table

aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier prod-postgres-from-snap \
    --db-snapshot-identifier rds:prod-postgres-2024-01-15-03-00 \
    --db-instance-class db.t3.medium \
    --no-publicly-accessible
```

---

## Manual Snapshot (Pre-Migration)

```bash
# Always take a manual snapshot before any schema migration
aws rds create-db-snapshot \
    --db-instance-identifier prod-postgres \
    --db-snapshot-identifier "pre-migration-$(date +%Y%m%d-%H%M%S)" \
    --tags Key=reason,Value=pre-migration Key=migration,Value=v3.2.0

# Wait for snapshot to complete
aws rds wait db-snapshot-completed \
    --db-snapshot-identifier "pre-migration-$(date +%Y%m%d)" 2>/dev/null || \
    aws rds describe-db-snapshots \
        --db-snapshot-identifier "pre-migration-$(date +%Y%m%d)" \
        --query 'DBSnapshots[0].Status'
```

---

## pg_dump / pg_restore (Logical Backups)

```bash
# Full logical backup (all tables, schema + data)
pg_dump \
    --host=prod-postgres.cluster.us-east-1.rds.amazonaws.com \
    --port=5432 \
    --username=app_admin \
    --dbname=app_db \
    --format=custom \       # Custom format: compressed, parallelizable
    --compress=9 \
    --verbose \
    --file=app_db_$(date +%Y%m%d_%H%M%S).pgdump

# Parallel dump (much faster for large databases)
pg_dump \
    --format=directory \
    --jobs=4 \
    --file=app_db_backup_dir/ \
    app_db

# Restore (custom format)
pg_restore \
    --host=restore-target.us-east-1.rds.amazonaws.com \
    --port=5432 \
    --username=app_admin \
    --dbname=app_db_restored \
    --format=custom \
    --jobs=4 \             # Parallel restore
    --verbose \
    app_db_20240115.pgdump

# Schema only (for migration testing)
pg_dump --schema-only --format=plain app_db > schema.sql

# Single table
pg_dump --table=orders --format=custom app_db > orders_backup.pgdump

# Upload to S3 (stream directly, no disk needed)
pg_dump --format=custom app_db | \
    aws s3 cp - s3://my-db-backups/$(date +%Y%m%d)/app_db.pgdump \
    --expected-size 1073741824  # Hint for multipart upload (1GB estimate)
```

---

## Automated Backup Script

```python
#!/usr/bin/env python3
"""
Automated PostgreSQL backup to S3 with retention management.
Run daily via cron or EventBridge + Lambda.
"""
import logging
import os
import subprocess
import tempfile
from datetime import date, timedelta

import boto3

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ["BACKUP_S3_BUCKET"]
DB_HOST = os.environ["DB_HOST"]
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))

s3 = boto3.client("s3")


def run_backup() -> str:
    """Run pg_dump and upload to S3. Returns S3 key."""
    today = date.today().isoformat()
    s3_key = f"postgresql/{DB_NAME}/{today}/{DB_NAME}_{today}.pgdump"

    logger.info("Starting database backup", extra={
        "db": DB_NAME, "host": DB_HOST, "s3_key": s3_key,
    })

    with tempfile.NamedTemporaryFile(suffix=".pgdump", delete=True) as tmp:
        result = subprocess.run(
            [
                "pg_dump",
                f"--host={DB_HOST}",
                f"--port=5432",
                f"--username={DB_USER}",
                f"--dbname={DB_NAME}",
                "--format=custom",
                "--compress=9",
                f"--file={tmp.name}",
            ],
            env={**os.environ, "PGPASSWORD": os.environ["DB_PASSWORD"]},
            capture_output=True,
            text=True,
            timeout=3600,
        )

        if result.returncode != 0:
            logger.error("pg_dump failed", extra={
                "returncode": result.returncode,
                "stderr": result.stderr[:500],
            })
            raise RuntimeError(f"pg_dump failed: {result.stderr}")

        file_size = os.path.getsize(tmp.name)
        logger.info("Backup file created", extra={"size_bytes": file_size})

        s3.upload_file(
            tmp.name,
            S3_BUCKET,
            s3_key,
            ExtraArgs={
                "ServerSideEncryption": "aws:kms",
                "StorageClass": "STANDARD_IA",
                "Metadata": {"db_name": DB_NAME, "backup_date": today},
            },
        )
        logger.info("Backup uploaded to S3", extra={"s3_key": s3_key, "size_bytes": file_size})

    return s3_key


def cleanup_old_backups() -> int:
    """Delete backups older than RETENTION_DAYS. Returns count deleted."""
    cutoff = date.today() - timedelta(days=RETENTION_DAYS)
    prefix = f"postgresql/{DB_NAME}/"

    deleted = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            # Key format: postgresql/db_name/YYYY-MM-DD/...
            parts = key.split("/")
            if len(parts) >= 3:
                try:
                    backup_date = date.fromisoformat(parts[2])
                    if backup_date < cutoff:
                        s3.delete_object(Bucket=S3_BUCKET, Key=key)
                        deleted += 1
                        logger.debug("Deleted old backup", extra={"key": key})
                except ValueError:
                    pass

    logger.info("Backup cleanup complete", extra={"deleted": deleted, "retention_days": RETENTION_DAYS})
    return deleted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    s3_key = run_backup()
    cleanup_old_backups()
```

---

## Restore Testing

A backup that has never been tested is not a backup.

```bash
# Monthly restore test: automated via CI or Lambda

# 1. Restore to a test instance
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier prod-postgres \
    --target-db-instance-identifier backup-test-$(date +%Y%m) \
    --restore-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
    --db-instance-class db.t3.medium \
    --no-publicly-accessible

# 2. Wait for restore
aws rds wait db-instance-available --db-instance-identifier backup-test-$(date +%Y%m)

# 3. Run validation queries
psql -h backup-test-$(date +%Y%m).cluster.rds.amazonaws.com \
    -U app_admin -d app_db << 'EOF'
-- Verify row counts match production estimates
SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;
-- Verify latest data exists (within RPO)
SELECT MAX(created_at) FROM orders;
-- Verify schema matches expected version
SELECT version_num FROM alembic_version;
EOF

# 4. Delete test instance
aws rds delete-db-instance \
    --db-instance-identifier backup-test-$(date +%Y%m) \
    --skip-final-snapshot
```

---

## References

- [AWS RDS backup and restore](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_CommonTasks.BackupRestore.html)
- [pg_dump documentation](https://www.postgresql.org/docs/current/app-pgdump.html)
- [PostgreSQL continuous archiving](https://www.postgresql.org/docs/current/continuous-archiving.html)

---

← [Previous: Replication](./replication.md) | [Home](../README.md) | [Next: Query Optimization →](./query-optimization.md)
