← [Previous: Compute](./compute.md) | [Home](../README.md) | [Next: Networking →](./networking.md)

---

# Cloud Storage Fundamentals

## Storage Types

Cloud storage comes in three primary types, each solving a different problem. Choosing the wrong type causes performance issues, unnecessary cost, or architectural friction.

```
Object Storage  → Files, blobs, media, backups (S3, GCS, Azure Blob)
Block Storage   → OS disks, databases (EBS, Azure Disk, GCE Persistent Disk)
File Storage    → Shared filesystems, NFS (EFS, Azure Files, Filestore)
Archive Storage → Long-term cold storage (S3 Glacier, Azure Archive)
```

---

## Object Storage

### What It Is

Object storage stores data as flat, unstructured objects. Each object consists of:
- **Data**: the file content (image, video, JSON, log, etc.)
- **Metadata**: key-value pairs describing the object
- **Unique key**: the object's identifier (acts like a filename path)

There is no real directory hierarchy — bucket + key is the only addressing mechanism (though the key can contain `/` to simulate folders).

### How It Differs from a Filesystem

```
Filesystem: /home/user/images/photo.jpg
Object storage: bucket-name + key "images/photo.jpg"

Filesystem: supports in-place modification (update one byte)
Object storage: you replace the entire object (no partial updates)
```

### Provider Equivalents

| Provider | Service | Max object size |
|---------|---------|----------------|
| AWS | S3 (Simple Storage Service) | 5TB |
| Azure | Azure Blob Storage | 4.75TB |
| GCP | Cloud Storage (GCS) | 5TB |
| Other | MinIO (self-hosted, S3-compatible) | Unlimited |

### Storage Classes / Tiers

All providers offer tiered pricing based on access frequency:

| Tier | Access pattern | Retrieval time | Use case |
|------|---------------|---------------|---------|
| Hot / Standard | Frequent | Immediate | Active websites, app data |
| Cool / Infrequent | < 1x/month | Immediate | Backups, older data |
| Archive | Rarely | Minutes to hours | Compliance, DR archives |
| Deep Archive | Almost never | 12+ hours | Long-term legal retention |

**AWS S3 storage class progression:**
```
Standard → Standard-IA → Intelligent-Tiering → Glacier Instant → Glacier Flexible → Deep Archive
(hot)                                                                              (cold)
```

### Key Features

- **Unlimited scale**: No capacity planning needed
- **High durability**: 11 nines (99.999999999%) — AWS S3, GCS
- **HTTP access**: Every object has a URL
- **Versioning**: Keep every version of an object
- **Lifecycle rules**: Auto-transition between tiers or delete after N days
- **Presigned URLs**: Generate time-limited URLs for secure temporary access
- **Event notifications**: Trigger Lambda/Cloud Functions on object upload

### When to Use Object Storage

- Storing media files (images, videos, audio)
- Static website hosting
- Application backups and snapshots
- Data lake / analytics raw data
- Log storage
- Distributing software artifacts and packages

---

## Block Storage

### What It Is

Block storage presents raw storage as a disk to an operating system. The OS formats it with a filesystem (ext4, xfs, NTFS) and treats it like a physical hard drive.

```
Cloud Block Storage → Attached to VM → Formatted as ext4 → /dev/xvda → Your OS sees it as /
```

### Provider Equivalents

| Provider | Service |
|---------|---------|
| AWS | EBS (Elastic Block Store) |
| Azure | Azure Managed Disks |
| GCP | GCE Persistent Disk |

### EBS Volume Types (AWS)

| Type | Use case | IOPS | Throughput |
|------|---------|------|-----------|
| `gp3` | General purpose (default) | Up to 16,000 | Up to 1,000 MB/s |
| `gp2` | Older general purpose | Burst to 3,000 | Up to 250 MB/s |
| `io2 Block Express` | High-performance databases | Up to 256,000 | Up to 4,000 MB/s |
| `st1` | Throughput-optimized HDD | 500 | 500 MB/s |
| `sc1` | Cold HDD (cheapest) | 250 | 250 MB/s |

### Key Properties of Block Storage

- **Attached to a single instance** (typically) — one EBS volume to one EC2 instance
- **Low latency** — milliseconds for random I/O
- **Persistence** — data survives instance stop/start; lost only on explicit delete
- **Snapshots** — point-in-time backup stored in S3, used to create new volumes
- **Region-scoped** — volumes are tied to an AZ; you must create a snapshot to move across AZs

### When to Use Block Storage

- OS boot volumes (required for VMs)
- Relational databases (PostgreSQL, MySQL) running on VMs
- Applications requiring raw block I/O with low latency
- Situations where you need to format the disk yourself

---

## File Storage (Shared Filesystems)

### What It Is

File storage provides a POSIX-compliant filesystem that multiple compute instances can mount simultaneously over a network.

```
EC2 Instance A ─┐
EC2 Instance B ─┤── NFS Mount ──→ EFS / Azure Files / GCP Filestore
EC2 Instance C ─┘
```

All instances see the same filesystem, the same files, in real time.

### Provider Equivalents

| Provider | Service | Protocol |
|---------|---------|---------|
| AWS | EFS (Elastic File System) | NFS v4.1 |
| AWS | FSx for Windows | SMB (Samba) |
| AWS | FSx for Lustre | Lustre (HPC) |
| Azure | Azure Files | SMB 3.0 / NFS 4.1 |
| GCP | Filestore | NFS v3 |

### When to Use File Storage

- Content management systems where multiple web servers share uploaded files
- Home directories for users in shared workstations / HPC clusters
- Machine learning training jobs that need shared dataset access
- Applications that use a shared filesystem API and can't be easily refactored to use object storage

### EFS vs S3 vs EBS (AWS)

| Dimension | EFS | S3 | EBS |
|-----------|-----|-----|-----|
| Type | File (NFS) | Object | Block |
| Multi-instance access | Yes | Yes (via SDK) | No (usually) |
| Filesystem interface | POSIX | HTTP API | POSIX (after mount) |
| Latency | ~1ms | ~10–100ms | ~0.1–1ms |
| Cost | ~$0.30/GB-month | ~$0.023/GB-month | ~$0.08/GB-month |
| Use case | Shared files for multiple EC2s | Unstructured data, media | OS disk, databases |

---

## Archive Storage

Long-term, write-once-read-rarely storage optimized for the lowest possible cost per GB.

| Provider | Service | Retrieval time | Cost |
|---------|---------|---------------|------|
| AWS | S3 Glacier Deep Archive | 12 hours | ~$0.001/GB-month |
| Azure | Azure Archive | 1–15 hours | ~$0.00099/GB-month |
| GCP | Cloud Storage Archive | Hours | ~$0.0012/GB-month |

**Use case:** Regulatory compliance data that must be retained for 7 years, raw video archives, scientific datasets.

---

## Storage Decision Guide

```
Do multiple instances need to mount the same filesystem simultaneously?
  Yes → File Storage (EFS / Azure Files / Filestore)
  No  → Continue

Is this a VM's OS disk or a database volume requiring raw block I/O?
  Yes → Block Storage (EBS / Managed Disk / Persistent Disk)
  No  → Continue

Will the data be accessed very rarely (< 1x/year) and must be kept long-term?
  Yes → Archive (Glacier Deep Archive / Azure Archive)
  No  → Object Storage (S3 / GCS / Blob)
```

---

## Key Storage Concepts

| Concept | Definition |
|---------|-----------|
| Durability | Probability data is not lost (11 nines = 0.000000001% annual loss) |
| Availability | Probability the service is accessible (S3 Standard = 99.99%) |
| Throughput | Amount of data transferred per second (MB/s) |
| IOPS | Input/Output Operations Per Second — relevant for databases |
| Latency | Time for a single I/O operation to complete |
| Snapshot | Point-in-time copy of a block volume, stored as an object |
| Lifecycle policy | Rules that automatically move or delete objects based on age |
| Presigned URL | Time-limited URL granting access to a private object |
| Cross-region replication | Automatically copying objects to another region for DR |
| Object lock | WORM (Write Once Read Many) — prevents object deletion for compliance |

---

## References

- [AWS S3 documentation](https://docs.aws.amazon.com/s3/)
- [AWS EBS volume types](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html)
- [AWS EFS documentation](https://docs.aws.amazon.com/efs/)
- [GCP Storage options comparison](https://cloud.google.com/storage-options)
- [Azure storage overview](https://learn.microsoft.com/en-us/azure/storage/common/storage-introduction)
---

← [Previous: Compute](./compute.md) | [Home](../README.md) | [Next: Networking →](./networking.md)
