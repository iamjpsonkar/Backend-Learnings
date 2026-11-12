← [Previous: Organizations & SCP](../02-iam/organizations-scp.md) | [Home](../../README.md) | [Next: VPC →](./vpc.md)

---

# AWS Networking

VPC is the foundational networking layer for all AWS workloads. This section covers everything from creating a VPC to advanced connectivity patterns like Transit Gateway and PrivateLink.

---

## Contents

| File | Description |
|------|-------------|
| [vpc.md](./vpc.md) | VPC concepts, CIDR planning, flow logs, VPC endpoints |
| [subnets-route-tables.md](./subnets-route-tables.md) | Subnet design, route tables, AZ patterns |
| [igw-natgw.md](./igw-natgw.md) | Internet Gateway, NAT Gateway, Elastic IPs |
| [security-groups-nacl.md](./security-groups-nacl.md) | Security Groups vs NACLs, rules, troubleshooting |
| [vpc-peering-tgw.md](./vpc-peering-tgw.md) | VPC Peering and Transit Gateway hub-and-spoke |
| [privatelink.md](./privatelink.md) | AWS PrivateLink, Interface endpoints, custom services |
| [route53.md](./route53.md) | DNS, hosted zones, routing policies, Resolver |
| [cloudfront.md](./cloudfront.md) | CloudFront CDN, caching, OAC, Lambda@Edge |

---

## VPC Architecture Quick Reference

```
Region
└── VPC 10.0.0.0/16
    ├── AZ us-east-1a
    │   ├── Public subnet 10.0.0.0/24  ──→ Internet Gateway ──→ Internet
    │   └── Private subnet 10.0.10.0/24 ──→ NAT Gateway ──→ IGW ──→ Internet
    ├── AZ us-east-1b
    │   ├── Public subnet 10.0.1.0/24
    │   └── Private subnet 10.0.11.0/24
    └── VPC Endpoints (S3, DynamoDB, SSM — bypass internet)
```

---

## Minimum Competency Checklist

- [ ] Design a VPC CIDR with room for future subnets
- [ ] Create public and private subnets across two or more AZs
- [ ] Attach an Internet Gateway and configure route tables
- [ ] Deploy NAT Gateways (one per AZ) for private subnet internet access
- [ ] Write Security Group rules using least-privilege
- [ ] Distinguish Security Groups (stateful) from NACLs (stateless)
- [ ] Create Gateway endpoints for S3 and DynamoDB
- [ ] Set up VPC Peering and update route tables on both sides
- [ ] Explain when to use Transit Gateway over VPC Peering
- [ ] Configure Route 53 private hosted zones for internal DNS

---

## Key Concepts Summary

| Concept | Scope | Stateful | Default |
|---------|-------|----------|---------|
| Security Group | ENI (instance) | Yes | Deny all inbound, allow all outbound |
| NACL | Subnet | No | Allow all (default NACL) |
| Route Table | Subnet | N/A | Local VPC route only |
| IGW | VPC | N/A | None (must attach) |
| NAT Gateway | AZ | N/A | None (must create per AZ) |
---

← [Previous: Organizations & SCP](../02-iam/organizations-scp.md) | [Home](../../README.md) | [Next: VPC →](./vpc.md)
