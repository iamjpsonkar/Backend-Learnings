← [Previous: EFS](./efs.md) | [Home](../../README.md) | [Next: AWS Databases →](../06-databases/README.md)

---

# Amazon FSx

FSx provides fully managed third-party file systems as a service. Choose the variant based on your workload requirements — Windows File Server for SMB, Lustre for HPC, NetApp ONTAP for enterprise NAS migration, and OpenZFS for POSIX workloads requiring advanced data management.

---

## FSx Variants at a Glance

| Variant | Protocol | OS | Use Case |
|---------|----------|----|----------|
| **FSx for Windows File Server** | SMB 2.0–3.1.1 | Windows, Linux (via SMB) | Windows apps, AD-integrated shares, NTFS |
| **FSx for Lustre** | Lustre | Linux | HPC, ML training, genomics, rendering |
| **FSx for NetApp ONTAP** | NFS, SMB, iSCSI | Linux, Windows, macOS | Enterprise NAS migration, multi-protocol |
| **FSx for OpenZFS** | NFS | Linux, macOS | POSIX workloads, ZFS snapshots, cloning |

---

## FSx for Windows File Server

### When to Use

- Windows applications that require SMB/CIFS file shares (e.g., home directories, departmental shares)
- Workloads requiring Active Directory integration, Windows ACLs, NTFS
- SQL Server or other Windows services needing a shared file location
- Migration of on-premises Windows file servers to AWS

### Create a Windows File Server

```bash
# Prerequisites: Active Directory (Managed AD or self-managed), VPC with subnets

MANAGED_AD_ID="d-1234567890"    # AWS Managed Microsoft AD directory ID
SUBNET_A="subnet-private-1a"
SUBNET_B="subnet-private-1b"
SG_FSX="sg-0fsx1234"

FSX_WIN_ID=$(aws fsx create-file-system \
    --file-system-type WINDOWS \
    --storage-capacity 300 \
    --storage-type SSD \
    --subnet-ids $SUBNET_A $SUBNET_B \
    --security-group-ids $SG_FSX \
    --windows-configuration '{
        "ActiveDirectoryId": "'$MANAGED_AD_ID'",
        "ThroughputCapacity": 32,
        "WeeklyMaintenanceStartTime": "1:05:00",
        "DailyAutomaticBackupStartTime": "02:00",
        "AutomaticBackupRetentionDays": 14,
        "DeploymentType": "MULTI_AZ_1",
        "PreferredSubnetId": "'$SUBNET_A'",
        "SelfManagedActiveDirectoryConfiguration": null
    }' \
    --tags Key=Name,Value=windows-file-server Key=Environment,Value=production \
    --query 'FileSystem.FileSystemId' --output text)

echo "FSx Windows: $FSX_WIN_ID"

# Wait for creation (10–20 minutes)
aws fsx describe-file-systems \
    --file-system-ids $FSX_WIN_ID \
    --query 'FileSystems[0].{ID:FileSystemId,State:Lifecycle,DNS:DNSName}'
```

### Mounting on Windows

```powershell
# On a Windows EC2 instance joined to the AD:
# Map drive from the FSx DNS name
$FSxDNS = "amznfsxXXXXXXXX.example.com"
New-PSDrive -Name Z -PSProvider FileSystem -Root "\\$FSxDNS\share" -Persist

# Or via net use (persistent across reboots):
net use Z: \\amznfsxXXXXXXXX.example.com\share /persistent:yes
```

### Mounting on Linux (SMB)

```bash
# Install cifs-utils
sudo yum install -y cifs-utils

# Mount the Windows share
sudo mkdir -p /mnt/windows-share
sudo mount -t cifs //amznfsxXXXXXXXX.example.com/share /mnt/windows-share \
    -o username=Admin,password=PASS,domain=EXAMPLE

# Persist with credentials file
echo "username=Admin" | sudo tee /etc/samba/creds
echo "password=PASS" | sudo tee -a /etc/samba/creds
sudo chmod 600 /etc/samba/creds

echo "//amznfsxXXXXXXXX.example.com/share /mnt/windows-share cifs credentials=/etc/samba/creds,_netdev 0 0" | \
    sudo tee -a /etc/fstab
```

---

## FSx for Lustre

### When to Use

- HPC workloads requiring parallel I/O: CFD, weather modeling, seismic processing
- Machine learning training with datasets stored in S3 (S3-linked filesystem)
- Genomics, video rendering, EDA (electronic design automation)
- Any workload that needs >1 GB/s throughput at sub-millisecond latency

### Deployment Types

| Type | Description | Use |
|------|-------------|-----|
| SCRATCH_1 | No replication, highest throughput/price | Short HPC jobs |
| SCRATCH_2 | No replication, 6x faster data access | Short HPC jobs |
| PERSISTENT_1 | SSD, 200–800 MB/s/TiB, replicated | Long-running jobs |
| PERSISTENT_2 | SSD, up to 1,000 MB/s/TiB, replicated | High-performance persistent |

### Create a Lustre Filesystem Linked to S3

```bash
S3_BUCKET="my-ml-datasets"
SUBNET_HPC="subnet-hpc-1a"
SG_LUSTRE="sg-0lustre1234"

FSX_LUSTRE_ID=$(aws fsx create-file-system \
    --file-system-type LUSTRE \
    --storage-capacity 1200 \
    --storage-type SSD \
    --subnet-ids $SUBNET_HPC \
    --security-group-ids $SG_LUSTRE \
    --lustre-configuration '{
        "ImportPath": "s3://'$S3_BUCKET'",
        "ExportPath": "s3://'$S3_BUCKET'/exports",
        "DeploymentType": "SCRATCH_2",
        "DataCompressionType": "LZ4"
    }' \
    --tags Key=Name,Value=ml-training-fs \
    --query 'FileSystem.FileSystemId' --output text)

echo "FSx Lustre: $FSX_LUSTRE_ID"
```

### Mounting Lustre on Linux

```bash
# Install Lustre client (Amazon Linux 2023)
sudo yum install -y lustre-client

# Get the mount name
MOUNT_NAME=$(aws fsx describe-file-systems \
    --file-system-ids $FSX_LUSTRE_ID \
    --query 'FileSystems[0].LustreConfiguration.MountName' --output text)

FSX_DNS=$(aws fsx describe-file-systems \
    --file-system-ids $FSX_LUSTRE_ID \
    --query 'FileSystems[0].DNSName' --output text)

# Mount
sudo mkdir -p /mnt/lustre
sudo mount -t lustre -o relatime,flock \
    $FSX_DNS@tcp:/$MOUNT_NAME /mnt/lustre

# Persist
echo "$FSX_DNS@tcp:/$MOUNT_NAME /mnt/lustre lustre relatime,flock,_netdev 0 0" | \
    sudo tee -a /etc/fstab

# Verify throughput
dd if=/dev/zero of=/mnt/lustre/test bs=1G count=4 oflag=direct   # write test
dd if=/mnt/lustre/test of=/dev/null bs=1G count=4 iflag=direct   # read test
```

### Synchronizing with S3

```bash
# Import data from S3 into the Lustre cache
aws fsx create-data-repository-task \
    --file-system-id $FSX_LUSTRE_ID \
    --type IMPORT_METADATA_FROM_REPOSITORY \
    --paths / \
    --report '{
        "Enabled": true,
        "Scope": "FAILED_FILES_ONLY",
        "Format": "REPORT_CSV_20191124",
        "Path": "s3://'$S3_BUCKET'/fsx-reports/"
    }'

# Export data from Lustre back to S3
aws fsx create-data-repository-task \
    --file-system-id $FSX_LUSTRE_ID \
    --type EXPORT_TO_REPOSITORY \
    --paths /outputs/ \
    --report '{
        "Enabled": true,
        "Scope": "FAILED_FILES_ONLY",
        "Format": "REPORT_CSV_20191124",
        "Path": "s3://'$S3_BUCKET'/fsx-reports/"
    }'

# Check task status
aws fsx describe-data-repository-tasks \
    --filters Name=file-system-id,Values=$FSX_LUSTRE_ID \
    --query 'DataRepositoryTasks[*].{ID:TaskId,Type:Type,State:Lifecycle}'
```

---

## FSx for NetApp ONTAP

### When to Use

- Migrate on-premises NetApp NAS to AWS with minimal change
- Need multi-protocol access (NFS + SMB + iSCSI simultaneously)
- Require ONTAP-specific features: SnapMirror replication, FlexClone, deduplication, compression
- Enterprise database storage requiring iSCSI block protocol

```bash
# Create an ONTAP file system (Multi-AZ)
FSX_ONTAP_ID=$(aws fsx create-file-system \
    --file-system-type ONTAP \
    --storage-capacity 1024 \
    --storage-type SSD \
    --subnet-ids $SUBNET_A $SUBNET_B \
    --security-group-ids $SG_FSX \
    --ontap-configuration '{
        "DeploymentType": "MULTI_AZ_1",
        "ThroughputCapacity": 128,
        "PreferredSubnetId": "'$SUBNET_A'",
        "RouteTableIds": ["rtb-private-1a", "rtb-private-1b"],
        "AutomaticBackupRetentionDays": 30,
        "DailyAutomaticBackupStartTime": "03:00",
        "WeeklyMaintenanceStartTime": "1:04:00",
        "FsxAdminPassword": "ChangeMe123!"
    }' \
    --tags Key=Name,Value=ontap-nas \
    --query 'FileSystem.FileSystemId' --output text)

echo "FSx ONTAP: $FSX_ONTAP_ID"

# Create a Storage Virtual Machine (SVM) — namespace/tenant within ONTAP
SVM_ID=$(aws fsx create-storage-virtual-machine \
    --file-system-id $FSX_ONTAP_ID \
    --name my-svm \
    --query 'StorageVirtualMachine.StorageVirtualMachineId' --output text)

# Create a volume within the SVM
aws fsx create-volume \
    --volume-type ONTAP \
    --name app-data \
    --ontap-configuration '{
        "SizeInMegabytes": 102400,
        "StorageVirtualMachineId": "'$SVM_ID'",
        "JunctionPath": "/app-data",
        "StorageEfficiencyEnabled": true,
        "TieringPolicy": {
            "Name": "AUTO",
            "CoolingPeriod": 31
        }
    }'
```

---

## FSx for OpenZFS

### When to Use

- POSIX-compliant workloads currently on ZFS that need cloud migration
- Workloads needing point-in-time snapshots with instant cloning (space-efficient)
- Dev/test environments that need quick clone of production data
- Linux-based file services requiring NFS v3/v4.1/v4.2

```bash
# Create an OpenZFS file system
FSX_ZFS_ID=$(aws fsx create-file-system \
    --file-system-type OPENZFS \
    --storage-capacity 512 \
    --storage-type SSD \
    --subnet-ids $SUBNET_A \
    --security-group-ids $SG_FSX \
    --open-zfs-configuration '{
        "DeploymentType": "SINGLE_AZ_1",
        "ThroughputCapacity": 64,
        "RootVolumeConfiguration": {
            "RecordSizeKiB": 128,
            "DataCompressionType": "LZ4",
            "NfsExports": [{
                "ClientConfigurations": [{
                    "Clients": "10.0.0.0/16",
                    "Options": ["rw", "crossmnt"]
                }]
            }]
        },
        "AutomaticBackupRetentionDays": 7
    }' \
    --tags Key=Name,Value=openzfs-fs \
    --query 'FileSystem.FileSystemId' --output text)

# Create a child volume with its own settings
aws fsx create-volume \
    --volume-type OPENZFS \
    --name dev-clone \
    --open-zfs-configuration '{
        "ParentVolumeId": "fsvol-root",
        "StorageCapacityQuotaGiB": 100,
        "DataCompressionType": "LZ4"
    }'
```

---

## Backups

All FSx variants support automatic daily backups and manual backups.

```bash
# Create a manual backup
BACKUP_ID=$(aws fsx create-backup \
    --file-system-id $FSX_WIN_ID \
    --tags Key=Name,Value=pre-patching-backup \
    --query 'Backup.BackupId' --output text)

# List backups
aws fsx describe-backups \
    --filters Name=file-system-id,Values=$FSX_WIN_ID \
    --query 'Backups[*].{ID:BackupId,Type:Type,State:Lifecycle,Created:CreationTime}' \
    --output table

# Restore from backup (creates a new file system)
aws fsx create-file-system-from-backup \
    --backup-id $BACKUP_ID \
    --subnet-ids $SUBNET_A \
    --security-group-ids $SG_FSX
```

---

## FSx Variant Selection Guide

| Requirement | FSx Variant |
|-------------|-------------|
| Windows apps, AD integration, SMB | Windows File Server |
| HPC, ML training, S3-linked parallel FS | Lustre |
| Multi-protocol NFS+SMB+iSCSI, NetApp features | NetApp ONTAP |
| POSIX NFS, ZFS snapshots and clones | OpenZFS |
| Shared storage for ECS/EKS on Linux | Lustre or NetApp ONTAP |
| Home directories for Windows users | Windows File Server |
| Genomics / bioinformatics pipeline | Lustre |

---

## References

- [FSx for Windows File Server](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/)
- [FSx for Lustre](https://docs.aws.amazon.com/fsx/latest/LustreGuide/)
- [FSx for NetApp ONTAP](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/)
- [FSx for OpenZFS](https://docs.aws.amazon.com/fsx/latest/OpenZFSGuide/)
---

← [Previous: EFS](./efs.md) | [Home](../../README.md) | [Next: AWS Databases →](../06-databases/README.md)
