← [Previous: Lambda](../04-compute/lambda.md) | [Home](../../README.md) | [Next: S3 →](./s3.md)

---

# AWS Storage

AWS offers multiple storage types to match different access patterns, performance requirements, and cost profiles. This section covers block (EBS), file (EFS, FSx), and object (S3) storage.

---

## Contents

| File | Description |
|------|-------------|
| [s3.md](./s3.md) | S3 buckets, storage classes, versioning, policies, replication |
| [ebs.md](./ebs.md) | EBS volume types, snapshots, encryption, performance |
| [efs.md](./efs.md) | Elastic File System — shared POSIX filesystem for Linux |
| [fsx.md](./fsx.md) | FSx for Windows File Server, Lustre, NetApp ONTAP, OpenZFS |

---

## Storage Type Decision Guide

```
What are you storing?
├── Files for a single EC2 instance (boot volume, database)?
│   └── EBS (gp3 general purpose, io2 for high IOPS)
├── Shared filesystem for multiple Linux instances or containers?
│   └── EFS (POSIX, multi-AZ, elastic capacity)
├── Shared filesystem for Windows or SMB clients?
│   └── FSx for Windows File Server
├── High-performance computing, ML training datasets?
│   └── FSx for Lustre (sub-ms latency, GB/s throughput)
├── Objects, backups, static assets, data lake?
│   └── S3 (infinitely scalable, lifecycle management)
└── NetApp migration or ONTAP features?
    └── FSx for NetApp ONTAP
```

---

## Minimum Competency Checklist

- [ ] Create a gp3 EBS volume and attach it to an EC2 instance
- [ ] Snapshot an EBS volume and restore it in another AZ
- [ ] Encrypt an EBS volume with a KMS key
- [ ] Mount an EFS filesystem on two EC2 instances simultaneously
- [ ] Set S3 lifecycle rules to transition objects to Glacier
- [ ] Enable S3 versioning and understand delete markers
- [ ] Configure S3 replication (same-region and cross-region)
- [ ] Choose the correct FSx variant for a given workload

---

## Cost Comparison (us-east-1, approximate)

| Storage | Price | Notes |
|---------|-------|-------|
| S3 Standard | $0.023/GB/mo | Retrieval: $0.0004/1K GET |
| S3 Glacier Instant | $0.004/GB/mo | Retrieval: ms |
| EBS gp3 | $0.08/GB/mo | Baseline 3,000 IOPS included |
| EBS io2 | $0.125/GB/mo + $0.065/IOPS/mo | For >16K IOPS |
| EFS Standard | $0.30/GB/mo | Pay for what you use |
| EFS IA | $0.025/GB/mo | Infrequent access tier |
| FSx for Windows | ~$0.13/GB/mo | SSD, includes NTFS |
| FSx for Lustre | ~$0.14/GB/mo | Scratch tier |
---

← [Previous: Lambda](../04-compute/lambda.md) | [Home](../../README.md) | [Next: S3 →](./s3.md)
