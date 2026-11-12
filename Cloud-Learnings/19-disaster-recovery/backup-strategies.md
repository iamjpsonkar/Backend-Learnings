← [Previous: RPO & RTO](./rpo-rto.md) | [Home](../README.md) | [Next: Failover Patterns →](./failover-patterns.md)

---

# Backup Strategies

The 3-2-1 rule: **3** copies of data, on **2** different media types, with **1** copy off-site. In cloud terms: production + replica + cross-region/cross-account backup.

---

## AWS Backup (Centralized)

AWS Backup provides a single control plane for backing up EC2, RDS, EFS, DynamoDB, EBS, S3, and more.

```bash
# Create a backup vault in the DR region
aws backup create-backup-vault \
    --backup-vault-name prod-dr-vault \
    --encryption-key-arn arn:aws:kms:us-west-2:123456789012:key/mrk-abc123 \
    --region us-west-2

# Create a backup plan: daily + weekly + monthly
aws backup create-backup-plan \
    --backup-plan '{
        "BackupPlanName": "prod-dr-plan",
        "Rules": [
            {
                "RuleName": "daily-backup",
                "TargetBackupVaultName": "prod-dr-vault",
                "ScheduleExpression": "cron(0 3 * * ? *)",
                "StartWindowMinutes": 60,
                "CompletionWindowMinutes": 120,
                "Lifecycle": {
                    "DeleteAfterDays": 35
                },
                "CopyActions": [{
                    "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:123456789012:backup-vault:prod-dr-vault",
                    "Lifecycle": {"DeleteAfterDays": 35}
                }]
            },
            {
                "RuleName": "weekly-backup",
                "TargetBackupVaultName": "prod-dr-vault",
                "ScheduleExpression": "cron(0 4 ? * SUN *)",
                "Lifecycle": {"DeleteAfterDays": 90}
            },
            {
                "RuleName": "monthly-backup",
                "TargetBackupVaultName": "prod-dr-vault",
                "ScheduleExpression": "cron(0 5 1 * ? *)",
                "Lifecycle": {
                    "MoveToColdStorageAfterDays": 30,
                    "DeleteAfterDays": 365
                }
            }
        ]
    }'

PLAN_ID=$(aws backup create-backup-plan ... --query 'BackupPlanId' --output text)

# Assign resources to the plan (tag-based)
aws backup create-backup-selection \
    --backup-plan-id $PLAN_ID \
    --backup-selection '{
        "SelectionName": "prod-resources",
        "IamRoleArn": "arn:aws:iam::123456789012:role/AWSBackupRole",
        "ListOfTags": [{
            "ConditionType": "STRINGEQUALS",
            "ConditionKey": "environment",
            "ConditionValue": "production"
        }]
    }'

# Check backup compliance
aws backup list-backup-jobs \
    --by-state FAILED \
    --by-backup-vault-name prod-dr-vault \
    --query 'BackupJobs[*].{Resource:ResourceArn,StartTime:StartBy,Status:State}'
```

---

## Cross-Account Backup (Immutable)

```bash
# Cross-account backup: even if production account is compromised,
# backups in a separate account are safe

# In the BACKUP account: create vault with resource policy
aws backup put-backup-vault-access-policy \
    --backup-vault-name cross-account-vault \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::PROD-ACCOUNT-ID:root"},
            "Action": [
                "backup:CopyIntoBackupVault"
            ],
            "Resource": "*"
        }]
    }' \
    --region us-west-2

# Enable Backup Vault Lock (immutable — prevents deletion)
aws backup put-backup-vault-lock-configuration \
    --backup-vault-name cross-account-vault \
    --min-retention-days 7 \
    --max-retention-days 365 \
    --region us-west-2
# WARNING: vault lock is irreversible after cool-off period (72h default)
```

---

## S3 Cross-Region Replication

```bash
# Enable versioning (required for replication)
aws s3api put-bucket-versioning \
    --bucket my-app-data \
    --versioning-configuration Status=Enabled

# Create replication bucket in DR region
aws s3api create-bucket \
    --bucket my-app-data-dr \
    --region us-west-2 \
    --create-bucket-configuration LocationConstraint=us-west-2

aws s3api put-bucket-versioning \
    --bucket my-app-data-dr \
    --versioning-configuration Status=Enabled

# Enable S3 Object Lock on DR bucket (immutable — prevents ransomware)
aws s3api put-object-lock-configuration \
    --bucket my-app-data-dr \
    --object-lock-configuration '{
        "ObjectLockEnabled": "Enabled",
        "Rule": {
            "DefaultRetention": {
                "Mode": "COMPLIANCE",
                "Days": 30
            }
        }
    }'

# Enable cross-region replication
aws s3api put-bucket-replication \
    --bucket my-app-data \
    --replication-configuration '{
        "Role": "arn:aws:iam::123456789012:role/S3ReplicationRole",
        "Rules": [{
            "ID": "replicate-all",
            "Status": "Enabled",
            "Filter": {},
            "Destination": {
                "Bucket": "arn:aws:s3:::my-app-data-dr",
                "ReplicationTime": {
                    "Status": "Enabled",
                    "Time": {"Minutes": 15}
                },
                "Metrics": {
                    "Status": "Enabled",
                    "EventThreshold": {"Minutes": 15}
                }
            },
            "DeleteMarkerReplication": {"Status": "Enabled"}
        }]
    }'
```

---

## RDS Automated Cross-Region Backup

```bash
# Automated backup copy to DR region
aws rds create-db-instance-automated-backups-replication \
    --source-db-instance-arn arn:aws:rds:us-east-1:123456789012:db:prod-postgres \
    --kms-key-id arn:aws:kms:us-west-2:123456789012:key/mrk-def456 \
    --backup-retention-period 7 \
    --source-region us-east-1 \
    --region us-west-2

# Verify replication
aws rds describe-db-instance-automated-backups \
    --db-instance-identifier prod-postgres \
    --region us-west-2 \
    --query 'DBInstanceAutomatedBackups[*].{DB:DBInstanceIdentifier,Status:Status,Region:Region}'

# Take a manual snapshot and copy to DR region
aws rds create-db-snapshot \
    --db-instance-identifier prod-postgres \
    --db-snapshot-identifier prod-postgres-dr-$(date +%Y%m%d)

aws rds copy-db-snapshot \
    --source-db-snapshot-identifier arn:aws:rds:us-east-1:123456789012:snapshot:prod-postgres-dr-$(date +%Y%m%d) \
    --target-db-snapshot-identifier prod-postgres-dr-$(date +%Y%m%d)-us-west-2 \
    --kms-key-id arn:aws:kms:us-west-2:123456789012:key/mrk-def456 \
    --source-region us-east-1 \
    --region us-west-2
```

---

## DynamoDB Backup

```bash
# Enable PITR (Point-in-Time Recovery)
aws dynamodb update-continuous-backups \
    --table-name my-app-table \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# On-demand backup
aws dynamodb create-backup \
    --table-name my-app-table \
    --backup-name my-app-table-$(date +%Y%m%d)

# Restore to a new table (in same or different region)
aws dynamodb restore-table-to-point-in-time \
    --source-table-name my-app-table \
    --target-table-name my-app-table-restored \
    --restore-date-time 2024-01-15T03:00:00Z

# Copy backup to another region
aws dynamodb create-backup \
    --table-name my-app-table \
    --backup-name cross-region-backup

aws dynamodb copy-backup \
    --source-backup-arn arn:aws:dynamodb:us-east-1:123456789012:table/my-app-table/backup/abc \
    --destination-table-name my-app-table-dr \
    --destination-region us-west-2
```

---

## Backup Testing Cadence

| Backup type | Test frequency | Test method |
|------------|---------------|------------|
| RDS PITR | Monthly | Restore to test instance, verify row counts + latest timestamp |
| S3 cross-region replication | Monthly | Download sample of objects from DR bucket, verify checksums |
| DynamoDB PITR | Quarterly | Restore to test table, run validation queries |
| EC2 AMI | Semi-annually | Launch test instance from AMI, verify application starts |
| AWS Backup jobs | Weekly | Check backup job completion status, alert on failures |

---

## References

- [AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/)
- [S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)
- [S3 Cross-Region Replication](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html)
- [AWS Backup Vault Lock](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html)

---

← [Previous: RPO & RTO](./rpo-rto.md) | [Home](../README.md) | [Next: Failover Patterns →](./failover-patterns.md)
