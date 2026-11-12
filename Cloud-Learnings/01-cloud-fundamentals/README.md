← [Previous: Account Safety Checklist](../00-foundations/account-safety-checklist.md) | [Home](../README.md) | [Next: Compute →](./compute.md)

---

# Cloud Fundamentals

Vendor-neutral deep dives into the core service categories that exist across all major cloud providers. Understanding these concepts means you can work with any provider — the implementations differ, but the underlying ideas are the same.

## Topics

| File | Description |
|------|-------------|
| [compute.md](./compute.md) | Virtual machines, containers, serverless, GPU — concepts and provider equivalents |
| [storage.md](./storage.md) | Object, block, file, archive — storage types and when to use each |
| [networking.md](./networking.md) | VPCs, subnets, routing, load balancing, DNS — cloud networking fundamentals |
| [databases.md](./databases.md) | SQL vs NoSQL, OLAP vs OLTP, managed vs self-hosted, caching |
| [iam.md](./iam.md) | Identity, authentication, authorization, least privilege across providers |
| [serverless.md](./serverless.md) | FaaS concepts, triggers, cold starts, event-driven architecture |
| [cross-cloud-comparison.md](./cross-cloud-comparison.md) | Side-by-side service equivalents across AWS, Azure, and GCP |

## How These Relate to Provider-Specific Sections

These docs explain the concept. The provider-specific sections explain the implementation:

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Virtual machines | [EC2](../05-aws/04-compute/ec2.md) | Azure VM | Compute Engine |
| Object storage | [S3](../05-aws/05-storage/s3.md) | Blob Storage | Cloud Storage |
| DNS / Traffic mgmt | [Route 53](../05-aws/03-networking/route53.md) | Azure DNS | Cloud DNS |
| SSM / Management | [Systems Manager](../05-aws/11-management/systems-manager.md) | Azure Arc | GCP Ops Agent |

Read this section first, then the provider-specific section for your target platform.
---

← [Previous: Account Safety Checklist](../00-foundations/account-safety-checklist.md) | [Home](../README.md) | [Next: Compute →](./compute.md)
