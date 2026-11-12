← [Previous: Reserved & Savings Plans](./reserved-savings.md) | [Home](../README.md) | [Next: Kubernetes Costs →](./kubernetes-costs.md)

---

# Storage Optimization

Storage costs grow silently and predictably. Unmanaged logs, orphaned snapshots, old backups, and over-sized EBS volumes are common sources of avoidable spend.

---

## S3 Storage Classes & Lifecycle

```
Hot data:    S3 Standard          $0.023/GB/month    Access: any time
↓ 30 days   S3 Standard-IA        $0.0125/GB/month   Retrieval fee applies
↓ 90 days   S3 Glacier Instant    $0.004/GB/month    Retrieval: milliseconds
↓ 180 days  S3 Glacier Flexible   $0.0036/GB/month   Retrieval: 3-5 hours
↓ 365 days  S3 Glacier Deep Archive $0.00099/GB/month Retrieval: 12 hours
```

### S3 Lifecycle Policy

```bash
# Apply lifecycle rules: transition logs to cheaper tiers + expire old versions
aws s3api put-bucket-lifecycle-configuration \
    --bucket my-app-logs \
    --lifecycle-configuration '{
        "Rules": [
            {
                "ID": "log-tiering",
                "Status": "Enabled",
                "Filter": {"Prefix": "app-logs/"},
                "Transitions": [
                    {"Days": 30,  "StorageClass": "STANDARD_IA"},
                    {"Days": 90,  "StorageClass": "GLACIER_IR"},
                    {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
                ],
                "Expiration": {"Days": 2555}
            },
            {
                "ID": "delete-incomplete-multipart",
                "Status": "Enabled",
                "Filter": {},
                "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
            },
            {
                "ID": "expire-old-versions",
                "Status": "Enabled",
                "Filter": {},
                "NoncurrentVersionTransitions": [
                    {"NoncurrentDays": 30, "StorageClass": "STANDARD_IA"}
                ],
                "NoncurrentVersionExpiration": {"NoncurrentDays": 90}
            }
        ]
    }'
```

### S3 Intelligent-Tiering (Zero Effort)

```bash
# Intelligent-Tiering automatically moves objects between tiers based on access patterns
# No retrieval fees, no minimum storage duration penalty
# Best for data with unknown or changing access patterns

aws s3api put-bucket-intelligent-tiering-configuration \
    --bucket my-app-assets \
    --id all-objects \
    --intelligent-tiering-configuration '{
        "Id": "all-objects",
        "Status": "Enabled",
        "Tierings": [
            {"Days": 90,  "AccessTier": "ARCHIVE_ACCESS"},
            {"Days": 180, "AccessTier": "DEEP_ARCHIVE_ACCESS"}
        ]
    }'

# Convert existing bucket to use Intelligent-Tiering by default
aws s3api put-bucket-lifecycle-configuration \
    --bucket my-app-assets \
    --lifecycle-configuration '{
        "Rules": [{
            "ID": "intelligent-tiering",
            "Status": "Enabled",
            "Filter": {},
            "Transitions": [{"Days": 0, "StorageClass": "INTELLIGENT_TIERING"}]
        }]
    }'
```

---

## EBS Optimization

```bash
# Find unattached EBS volumes (paying for storage, attached to nothing)
aws ec2 describe-volumes \
    --filters Name=status,Values=available \
    --query 'Volumes[*].{VolumeId:VolumeId,Size:Size,Type:VolumeType,
             Created:CreateTime,Cost:Size}' \
    --output table

# Find gp2 volumes (migrate to gp3 — 20% cheaper, better performance baseline)
aws ec2 describe-volumes \
    --filters Name=volume-type,Values=gp2 \
    --query 'Volumes[*].{VolumeId:VolumeId,Size:Size}' \
    --output text | while read vol_id size; do
        echo "Migrating $vol_id ($size GB) to gp3"
        aws ec2 modify-volume --volume-id "$vol_id" --volume-type gp3
    done

# Find oversized EBS volumes (< 10% used)
# Requires CloudWatch agent installed on EC2 instances
aws cloudwatch get-metric-statistics \
    --namespace CWAgent \
    --metric-name disk_used_percent \
    --dimensions Name=device,Value=xvda1 Name=fstype,Value=xfs Name=path,Value=/ \
    --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-7d +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 86400 \
    --statistics Average \
    --query 'Datapoints[*].Average'
```

---

## Snapshot Cleanup

```python
import boto3
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
ec2 = boto3.client("ec2")

ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]
RETENTION_DAYS = 30


def delete_old_snapshots(dry_run: bool = True) -> list[str]:
    """
    Delete EBS snapshots older than RETENTION_DAYS that are not:
    - Shared with other accounts
    - Used by any AMI
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)

    # Get all AMI snapshot IDs (cannot delete these)
    used_snapshot_ids = set()
    for image in ec2.describe_images(Owners=["self"])["Images"]:
        for block_device in image.get("BlockDeviceMappings", []):
            snap_id = block_device.get("Ebs", {}).get("SnapshotId")
            if snap_id:
                used_snapshot_ids.add(snap_id)

    logger.info("AMI-protected snapshots", extra={"count": len(used_snapshot_ids)})

    deleted = []
    paginator = ec2.get_paginator("describe_snapshots")
    for page in paginator.paginate(OwnerIds=["self"]):
        for snapshot in page["Snapshots"]:
            snap_id = snapshot["SnapshotId"]
            created = snapshot["StartTime"]
            size_gb = snapshot["VolumeSize"]

            if snap_id in used_snapshot_ids:
                continue
            if created > cutoff:
                continue
            if snapshot.get("Description", "").startswith("Copied"):
                continue

            age_days = (datetime.now(timezone.utc) - created).days
            logger.info(
                "Deleting old snapshot" if not dry_run else "Would delete snapshot",
                extra={"snapshot_id": snap_id, "age_days": age_days, "size_gb": size_gb},
            )

            if not dry_run:
                ec2.delete_snapshot(SnapshotId=snap_id)
            deleted.append(snap_id)

    logger.info(
        "Snapshot cleanup complete",
        extra={"deleted": len(deleted), "dry_run": dry_run},
    )
    return deleted
```

---

## CloudWatch Logs Cost Control

```bash
# CloudWatch Logs is often a hidden cost ($0.50/GB ingest, $0.03/GB storage)

# Find log groups without retention policy (stored forever)
aws logs describe-log-groups \
    --query 'logGroups[?!retentionInDays].{Name:logGroupName,SizeBytes:storedBytes}' \
    --output table

# Set retention on all log groups missing it
aws logs describe-log-groups --query 'logGroups[?!retentionInDays].logGroupName' --output text | \
    tr '\t' '\n' | while read lg; do
        echo "Setting 90-day retention on: $lg"
        aws logs put-retention-policy --log-group-name "$lg" --retention-in-days 90
    done

# Export and delete old logs to S3 instead
aws logs create-export-task \
    --log-group-name /apps/order-api \
    --from $(($(date +%s) - 7776000))000 \   # 90 days ago
    --to $(date +%s)000 \
    --destination my-log-archive-bucket \
    --destination-prefix logs/order-api/

# Switch to Loki or CloudWatch Logs Insights + S3 for long-term storage
# CloudWatch: $0.50/GB ingest  →  S3 Glacier: $0.004/GB/month
```

---

## ECR Image Cleanup

```bash
# Container registries accumulate untagged images quickly
# AWS ECR: add a lifecycle policy

aws ecr put-lifecycle-policy \
    --repository-name my-app/order-api \
    --lifecycle-policy '{
        "rules": [
            {
                "rulePriority": 1,
                "description": "Remove untagged images after 7 days",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "sinceImagePushed",
                    "countUnit": "days",
                    "countNumber": 7
                },
                "action": {"type": "expire"}
            },
            {
                "rulePriority": 2,
                "description": "Keep only last 20 tagged images per release",
                "selection": {
                    "tagStatus": "tagged",
                    "tagPrefixList": ["release-"],
                    "countType": "imageCountMoreThan",
                    "countNumber": 20
                },
                "action": {"type": "expire"}
            }
        ]
    }'

# GCP: Artifact Registry cleanup policy
gcloud artifacts repositories set-cleanup-policies my-docker-repo \
    --project=my-project \
    --location=us-east1 \
    --policy='[{
        "name": "delete-untagged",
        "action": {"type": "Delete"},
        "condition": {
            "tagState": "UNTAGGED",
            "olderThan": "604800s"
        }
    }]'
```

---

## References

- [S3 Storage Classes](https://aws.amazon.com/s3/storage-classes/)
- [S3 Lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [S3 Intelligent-Tiering](https://aws.amazon.com/s3/storage-classes/intelligent-tiering/)
- [Amazon EBS pricing](https://aws.amazon.com/ebs/pricing/)

---

← [Previous: Reserved & Savings Plans](./reserved-savings.md) | [Home](../README.md) | [Next: Kubernetes Costs →](./kubernetes-costs.md)
