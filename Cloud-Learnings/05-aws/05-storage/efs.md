← [Previous: EBS](./ebs.md) | [Home](../../README.md) | [Next: FSx →](./fsx.md)

---

# Amazon EFS — Elastic File System

EFS is a fully managed, elastic, shared POSIX-compatible filesystem for Linux workloads. Multiple EC2 instances, containers, and Lambda functions can mount and access the same filesystem concurrently.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **File system** | The EFS resource — elastic, grows/shrinks automatically |
| **Mount target** | An ENI in a specific AZ subnet through which instances access EFS |
| **Access point** | An application-specific entry point with enforced user/group permissions |
| **Storage class** | Standard (frequently accessed) or Infrequent Access (IA, cheaper) |
| **Performance mode** | General Purpose (default) or Max I/O (highly parallel, higher latency) |
| **Throughput mode** | Elastic (recommended), Bursting, or Provisioned |

---

## Creating a File System

```bash
VPC_ID="vpc-0abc1234"

# Create the EFS file system
EFS_ID=$(aws efs create-file-system \
    --performance-mode generalPurpose \
    --throughput-mode elastic \
    --encrypted \
    --tags Key=Name,Value=shared-app-fs Key=Environment,Value=production \
    --query 'FileSystemId' --output text)

echo "EFS: $EFS_ID"

# Wait until available
aws efs describe-file-systems \
    --file-system-id $EFS_ID \
    --query 'FileSystems[0].{ID:FileSystemId,State:LifeCycleState,Size:SizeInBytes.Value}'

# Enable Intelligent-Tiering (automatically moves unused files to IA after 30 days)
aws efs put-lifecycle-configuration \
    --file-system-id $EFS_ID \
    --lifecycle-policies \
        TransitionToIA=AFTER_30_DAYS \
        TransitionToPrimaryStorageClass=AFTER_1_ACCESS
```

### Create Mount Targets (One Per AZ)

```bash
SG_EFS="sg-0efs1234"    # security group allowing NFS (port 2049)

# Mount targets in each AZ where you have instances
EFS_MT_A=$(aws efs create-mount-target \
    --file-system-id $EFS_ID \
    --subnet-id subnet-private-1a \
    --security-groups $SG_EFS \
    --query 'MountTargetId' --output text)

EFS_MT_B=$(aws efs create-mount-target \
    --file-system-id $EFS_ID \
    --subnet-id subnet-private-1b \
    --security-groups $SG_EFS \
    --query 'MountTargetId' --output text)

echo "Mount targets: $EFS_MT_A $EFS_MT_B"

# Wait until available
aws efs describe-mount-targets \
    --file-system-id $EFS_ID \
    --query 'MountTargets[*].{ID:MountTargetId,AZ:AvailabilityZoneName,State:LifeCycleState,IP:IpAddress}'
```

### Security Group for EFS

```bash
# EFS mount target needs to accept NFS traffic from EC2 instances
SG_EFS=$(aws ec2 create-security-group \
    --group-name efs-mount-sg \
    --description "Allow NFS from app instances to EFS" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)

SG_APP="sg-0app1234"

aws ec2 authorize-security-group-ingress \
    --group-id $SG_EFS \
    --protocol tcp \
    --port 2049 \
    --source-group $SG_APP

echo "EFS SG: $SG_EFS"
```

---

## Mounting EFS on EC2

```bash
# Install the EFS mount helper (Amazon Linux 2023 / Amazon Linux 2)
sudo yum install -y amazon-efs-utils

# Get the EFS DNS name
EFS_DNS="${EFS_ID}.efs.us-east-1.amazonaws.com"

# Mount using TLS (recommended — encrypts data in transit)
sudo mkdir -p /mnt/efs
sudo mount -t efs -o tls $EFS_ID:/ /mnt/efs

# Verify the mount
df -h /mnt/efs
ls /mnt/efs

# Persist across reboots — add to /etc/fstab
echo "$EFS_ID:/ /mnt/efs efs defaults,_netdev,tls 0 0" | sudo tee -a /etc/fstab

# Mount a specific access point (enforces path and user)
ACCESS_POINT_ID="fsap-0abc1234"
sudo mount -t efs -o tls,accesspoint=$ACCESS_POINT_ID $EFS_ID:/ /mnt/app-data
```

---

## Access Points

Access points enforce a specific root directory, user identity (UID/GID), and file creation permissions. Useful for multi-tenant environments or container workloads.

```bash
# Create an access point for the application
AP_ID=$(aws efs create-access-point \
    --file-system-id $EFS_ID \
    --posix-user Uid=1000,Gid=1000 \
    --root-directory '{
        "Path": "/app-data",
        "CreationInfo": {
            "OwnerUid": 1000,
            "OwnerGid": 1000,
            "Permissions": "755"
        }
    }' \
    --tags Key=Name,Value=app-access-point \
    --query 'AccessPointId' --output text)

echo "Access point: $AP_ID"

# List access points
aws efs describe-access-points \
    --file-system-id $EFS_ID \
    --query 'AccessPoints[*].{ID:AccessPointId,Path:RootDirectory.Path,UID:PosixUser.Uid}'
```

---

## EFS with ECS / Fargate

EFS is commonly used with ECS and Fargate to provide persistent storage for containers.

```json
{
    "volumes": [{
        "name": "app-data",
        "efsVolumeConfiguration": {
            "fileSystemId": "fs-0abc1234",
            "rootDirectory": "/",
            "transitEncryption": "ENABLED",
            "authorizationConfig": {
                "accessPointId": "fsap-0abc1234",
                "iam": "ENABLED"
            }
        }
    }],
    "containerDefinitions": [{
        "name": "my-app",
        "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:latest",
        "mountPoints": [{
            "sourceVolume": "app-data",
            "containerPath": "/data",
            "readOnly": false
        }]
    }]
}
```

---

## EFS File System Policy

The file system policy controls access at the resource level (similar to S3 bucket policies).

```bash
# Enforce TLS encryption in transit and allow access only from the VPC
aws efs put-file-system-policy \
    --file-system-id $EFS_ID \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "EnforceTLS",
                "Effect": "Deny",
                "Principal": {"AWS": "*"},
                "Action": "*",
                "Condition": {
                    "Bool": {"aws:SecureTransport": "false"}
                }
            },
            {
                "Sid": "AllowVPCAccess",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": [
                    "elasticfilesystem:ClientMount",
                    "elasticfilesystem:ClientWrite"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:SourceVpc": "vpc-0abc1234"
                    }
                }
            }
        ]
    }'
```

---

## Performance Modes and Throughput Modes

### Performance Mode

| Mode | IOPS | Latency | Use |
|------|------|---------|-----|
| General Purpose | Up to 35,000 | Low (sub-ms) | Default; web serving, CMS, home directories |
| Max I/O | Unlimited (scales linearly) | Higher | Thousands of parallel connections; big data, HPC |

**Note:** You cannot change the performance mode after creation. General Purpose is sufficient for most workloads.

### Throughput Mode

| Mode | Throughput | Cost |
|------|-----------|------|
| Elastic (recommended) | Up to 3 GB/s read, 1 GB/s write | Pay per GB transferred |
| Bursting | Scales with storage size (baseline 50 KB/s per GB) | Included in storage cost |
| Provisioned | Fixed value you set | Per MB/s provisioned |

```bash
# Switch from Bursting to Elastic throughput mode (no recreation required)
aws efs update-file-system \
    --file-system-id $EFS_ID \
    --throughput-mode elastic
```

---

## Monitoring

```bash
EFS_ID="fs-0abc1234"

# Storage usage by class
aws efs describe-file-systems \
    --file-system-id $EFS_ID \
    --query 'FileSystems[0].SizeInBytes'

# CloudWatch metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/EFS \
    --metric-name BurstCreditBalance \
    --dimensions Name=FileSystemId,Value=$EFS_ID \
    --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 3600 \
    --statistics Average \
    --output table

# Key EFS CloudWatch metrics:
# ClientConnections     — active connections
# DataReadIOBytes       — read throughput
# DataWriteIOBytes      — write throughput
# MetadataIOBytes       — metadata operations
# PercentIOLimit        — % of max IOPS used (General Purpose mode)
# BurstCreditBalance    — burst throughput credits remaining (Bursting mode)
```

---

## EFS vs EBS vs S3

| | EFS | EBS | S3 |
|--|-----|-----|----|
| Access | Multiple instances (NFS) | Single instance (block) | API / SDK (HTTP) |
| OS | Linux only | Linux + Windows | Any |
| Protocol | NFS | Block device | REST/S3 API |
| Performance | Elastic, shared | High IOPS, low latency | High throughput, high latency |
| Capacity | Elastic (auto-grows) | Fixed (modify online) | Unlimited |
| AZ scope | Multi-AZ | Single AZ | Regional |
| Cost | $0.30/GB (Standard) | $0.08/GB (gp3) | $0.023/GB |
| Best for | Shared config, CMS, containers | Databases, OS volumes | Backups, static assets, data lake |

---

## References

- [EFS documentation](https://docs.aws.amazon.com/efs/latest/ug/)
- [EFS performance](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
- [EFS access points](https://docs.aws.amazon.com/efs/latest/ug/efs-access-points.html)
- [EFS with ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/efs-volumes.html)
---

← [Previous: EBS](./ebs.md) | [Home](../../README.md) | [Next: FSx →](./fsx.md)
