← [Previous: S3](./s3.md) | [Home](../../README.md) | [Next: EFS →](./efs.md)

---

# Amazon EBS — Elastic Block Store

EBS provides persistent block storage volumes for EC2 instances. Volumes persist independently from the instance lifecycle and are replicated within a single Availability Zone.

---

## EBS Volume Types

| Type | API Name | IOPS | Throughput | Use Case |
|------|----------|------|-----------|----------|
| General Purpose SSD | gp3 | Up to 16,000 | Up to 1,000 MB/s | Default choice for most workloads |
| General Purpose SSD (prev) | gp2 | Up to 16,000 (burst) | Up to 250 MB/s | Legacy; prefer gp3 |
| Provisioned IOPS SSD | io2 | Up to 64,000 (256K with Block Express) | Up to 4,000 MB/s | Databases requiring >16K IOPS |
| Provisioned IOPS SSD | io1 | Up to 64,000 | Up to 1,000 MB/s | Legacy io2 predecessor |
| Throughput Optimized HDD | st1 | 500 | 500 MB/s | Big data, log processing, data warehouses |
| Cold HDD | sc1 | 250 | 250 MB/s | Infrequently accessed data; cheapest |

**Key rule**: Only SSD types (gp3, io2) can be used as boot volumes. HDD types (st1, sc1) are data volumes only.

**gp3 advantage over gp2**: gp3 provides 3,000 IOPS and 125 MB/s baseline regardless of volume size. Additional IOPS and throughput can be provisioned independently. gp3 is ~20% cheaper than gp2.

---

## Creating and Attaching Volumes

```bash
INSTANCE_ID="i-0abc1234"
AZ="us-east-1a"   # Must be in the same AZ as the instance

# Create a gp3 data volume
VOLUME_ID=$(aws ec2 create-volume \
    --availability-zone $AZ \
    --size 100 \
    --volume-type gp3 \
    --iops 3000 \
    --throughput 125 \
    --encrypted \
    --tag-specifications 'ResourceType=volume,Tags=[{Key=Name,Value=app-data},{Key=Environment,Value=production}]' \
    --query 'VolumeId' --output text)

echo "Volume: $VOLUME_ID"

# Wait until available
aws ec2 wait volume-available --volume-ids $VOLUME_ID

# Attach to instance
aws ec2 attach-volume \
    --volume-id $VOLUME_ID \
    --instance-id $INSTANCE_ID \
    --device /dev/xvdf

# On the instance — format and mount (first time only)
# ssh to instance, then:
# lsblk                          # find the new device (e.g., /dev/nvme1n1)
# sudo mkfs.ext4 /dev/nvme1n1    # format (WARNING: destroys data)
# sudo mkdir -p /data
# sudo mount /dev/nvme1n1 /data
# echo '/dev/nvme1n1 /data ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab

# Verify
aws ec2 describe-volumes \
    --volume-ids $VOLUME_ID \
    --query 'Volumes[0].{ID:VolumeId,Size:Size,Type:VolumeType,State:State,AZ:AvailabilityZone,Attachment:Attachments[0].State}'
```

---

## Modifying Volumes (Live, No Downtime)

EBS allows modifying volume type, size, IOPS, and throughput while the volume is in use.

```bash
# Increase size from 100 GB to 200 GB (online, no restart)
aws ec2 modify-volume \
    --volume-id $VOLUME_ID \
    --size 200

# Upgrade from gp2 to gp3 and add IOPS
aws ec2 modify-volume \
    --volume-id $VOLUME_ID \
    --volume-type gp3 \
    --iops 6000 \
    --throughput 250

# Monitor the modification progress
aws ec2 describe-volumes-modifications \
    --volume-ids $VOLUME_ID \
    --query 'VolumesModifications[0].{State:ModificationState,Progress:Progress,Message:StatusMessage}'

# After the modification completes, extend the filesystem (no unmount needed):
# For ext4:  sudo resize2fs /dev/nvme1n1
# For xfs:   sudo xfs_growfs /data
# For NTFS:  handled automatically by Windows
```

---

## Snapshots

EBS snapshots are incremental backups stored in S3. They can be used to create new volumes in any AZ.

```bash
# Create a snapshot
SNAPSHOT_ID=$(aws ec2 create-snapshot \
    --volume-id $VOLUME_ID \
    --description "Pre-deployment backup $(date +%Y-%m-%d)" \
    --tag-specifications 'ResourceType=snapshot,Tags=[{Key=Name,Value=app-data-backup},{Key=AutoRetain,Value=false}]' \
    --query 'SnapshotId' --output text)

echo "Snapshot: $SNAPSHOT_ID"

# Wait for completion (can take minutes for large volumes)
aws ec2 wait snapshot-completed --snapshot-ids $SNAPSHOT_ID

# Create a new volume from the snapshot in a different AZ
RESTORE_VOL=$(aws ec2 create-volume \
    --snapshot-id $SNAPSHOT_ID \
    --availability-zone us-east-1b \
    --volume-type gp3 \
    --encrypted \
    --query 'VolumeId' --output text)

# Copy snapshot to another region
aws ec2 copy-snapshot \
    --source-region us-east-1 \
    --source-snapshot-id $SNAPSHOT_ID \
    --description "Cross-region copy" \
    --region eu-west-1 \
    --encrypted

# List snapshots for a volume
aws ec2 describe-snapshots \
    --filters Name=volume-id,Values=$VOLUME_ID \
    --query 'Snapshots[*].{ID:SnapshotId,Size:VolumeSize,State:State,Created:StartTime,Desc:Description}' \
    --output table

# Delete a snapshot
aws ec2 delete-snapshot --snapshot-id $SNAPSHOT_ID
```

### Automated Snapshot Lifecycle (AWS DLM)

```bash
# Create a lifecycle policy: daily snapshots, retain 7 days
aws dlm create-lifecycle-policy \
    --description "Daily EBS snapshots — retain 7 days" \
    --state ENABLED \
    --execution-role-arn arn:aws:iam::123456789012:role/AWSDataLifecycleManagerDefaultRole \
    --policy-details '{
        "PolicyType": "EBS_SNAPSHOT_MANAGEMENT",
        "ResourceTypes": ["VOLUME"],
        "TargetTags": [{"Key": "Environment", "Value": "production"}],
        "Schedules": [{
            "Name": "daily-snapshot",
            "CreateRule": {
                "Interval": 24,
                "IntervalUnit": "HOURS",
                "Times": ["02:00"]
            },
            "RetainRule": {"Count": 7},
            "CopyTags": true,
            "TagsToAdd": [{"Key": "CreatedBy", "Value": "DLM"}]
        }]
    }'
```

---

## Encryption

EBS encryption uses AWS KMS to encrypt data at rest, data in transit between the volume and the instance, and all snapshots.

```bash
# Create an encrypted volume with a customer-managed KMS key
KMS_KEY_ID="arn:aws:kms:us-east-1:123456789012:key/mrk-abc1234"

aws ec2 create-volume \
    --availability-zone $AZ \
    --size 100 \
    --volume-type gp3 \
    --encrypted \
    --kms-key-id $KMS_KEY_ID \
    --tag-specifications 'ResourceType=volume,Tags=[{Key=Name,Value=encrypted-data}]'

# Enable encryption by default for all new volumes in the region
aws ec2 enable-ebs-encryption-by-default

# Verify encryption-by-default status
aws ec2 get-ebs-encryption-by-default

# Encrypt an existing unencrypted volume:
# 1. Snapshot the unencrypted volume
SNAP_UNENCRYPTED=$(aws ec2 create-snapshot \
    --volume-id vol-unencrypted \
    --query 'SnapshotId' --output text)

# 2. Copy the snapshot with encryption
SNAP_ENCRYPTED=$(aws ec2 copy-snapshot \
    --source-region us-east-1 \
    --source-snapshot-id $SNAP_UNENCRYPTED \
    --description "Encrypted copy" \
    --encrypted \
    --kms-key-id $KMS_KEY_ID \
    --query 'SnapshotId' --output text)

# 3. Create a new encrypted volume from the encrypted snapshot
aws ec2 create-volume \
    --snapshot-id $SNAP_ENCRYPTED \
    --availability-zone $AZ \
    --volume-type gp3
```

---

## Multi-Attach (io1/io2 Only)

Multi-Attach allows a single io2 volume to be attached to multiple instances in the same AZ. Requires a cluster-aware filesystem (e.g., GFS2, OCFS2) — not ext4 or xfs.

```bash
# Create a multi-attach capable io2 volume
MULTI_VOL=$(aws ec2 create-volume \
    --availability-zone $AZ \
    --size 100 \
    --volume-type io2 \
    --iops 5000 \
    --multi-attach-enabled \
    --encrypted \
    --query 'VolumeId' --output text)

# Attach to multiple instances
aws ec2 attach-volume --volume-id $MULTI_VOL --instance-id i-0instance1 --device /dev/xvdf
aws ec2 attach-volume --volume-id $MULTI_VOL --instance-id i-0instance2 --device /dev/xvdf
```

---

## Performance Tuning

```bash
# View current IOPS and throughput configuration
aws ec2 describe-volumes \
    --volume-ids $VOLUME_ID \
    --query 'Volumes[0].{Type:VolumeType,IOPS:Iops,Throughput:Throughput,Size:Size}'

# Monitor volume I/O performance via CloudWatch
aws cloudwatch get-metric-statistics \
    --namespace AWS/EBS \
    --metric-name VolumeReadOps \
    --dimensions Name=VolumeId,Value=$VOLUME_ID \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Average \
    --output table

# Key EBS CloudWatch metrics:
# VolumeReadOps / VolumeWriteOps    — IOPS consumed
# VolumeReadBytes / VolumeWriteBytes — throughput consumed
# VolumeTotalReadTime / VolumeTotalWriteTime — latency
# BurstBalance (gp2 only) — % of burst IOPS bucket remaining
```

### gp2 vs gp3 Migration (Cost Saving)

```bash
# Find all gp2 volumes and migrate to gp3 (saves ~20%)
aws ec2 describe-volumes \
    --filters Name=volume-type,Values=gp2 \
    --query 'Volumes[*].VolumeId' --output text | \
    tr '\t' '\n' | \
    while read vol; do
        echo "Migrating $vol to gp3..."
        aws ec2 modify-volume \
            --volume-id $vol \
            --volume-type gp3 \
            --iops 3000 \
            --throughput 125
    done
```

---

## EBS vs Instance Store

| | EBS | Instance Store |
|--|-----|----------------|
| Persistence | Survives instance stop/start | Lost when instance stops/terminates |
| Performance | Up to 256K IOPS (io2 Block Express) | Highest (NVMe directly attached) |
| Replication | Within AZ only | None |
| Snapshots | Yes | No |
| Cost | Per GB + IOPS/throughput | Included in instance price |
| Use for | Root volumes, databases, persistent data | Temporary scratch, buffer, cache |

---

## References

- [EBS volume types](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html)
- [EBS snapshots](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EBSSnapshots.html)
- [EBS encryption](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EBSEncryption.html)
- [Data Lifecycle Manager](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snapshot-lifecycle.html)
---

← [Previous: S3](./s3.md) | [Home](../../README.md) | [Next: EFS →](./efs.md)
