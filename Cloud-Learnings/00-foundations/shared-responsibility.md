← [Previous: Deployment Models](./deployment-models.md) | [Home](../README.md) | [Next: Regions & Zones →](./regions-zones-geography.md)

---

# Shared Responsibility Model

## The Core Idea

When you use a cloud provider, security and compliance responsibilities are split between you and the provider. The provider is responsible for securing the infrastructure that runs your workloads. You are responsible for securing what you put on top of it.

**The provider secures the cloud. You secure what's in the cloud.**

Getting this boundary wrong is one of the most common causes of cloud security incidents.

---

## Why It Matters

Most cloud breaches are not caused by the provider's infrastructure being compromised. They are caused by customer misconfigurations:

- S3 buckets set to public when they shouldn't be
- Overly permissive IAM policies
- Unpatched guest operating systems
- Exposed credentials in code repositories
- Missing encryption on sensitive data

These are all customer responsibilities — the provider cannot fix them for you.

---

## AWS Shared Responsibility Model

```
─────────────────────────────────────────────
  CUSTOMER RESPONSIBILITY ("Security IN the cloud")
─────────────────────────────────────────────
  Customer Data
  Platform, Applications, Identity & Access Management
  Operating System, Network & Firewall Configuration
  Client-Side Data Encryption
  Server-Side Data Encryption
  Network Traffic Protection (TLS)
─────────────────────────────────────────────
  AWS RESPONSIBILITY ("Security OF the cloud")
─────────────────────────────────────────────
  Compute | Storage | Database | Networking
  Hardware / AWS Global Infrastructure
  Regions | Availability Zones | Edge Locations
─────────────────────────────────────────────
```

### What AWS Manages

- Physical security of data centers (guards, cameras, biometric access)
- Hardware lifecycle (servers, storage, networking equipment)
- The hypervisor (the software that runs virtual machines)
- The host operating system on physical servers
- Managed service software (e.g., the database engine in RDS, the runtime in Lambda)

### What You Manage

| Area | Your Responsibility |
|------|-------------------|
| Guest OS | Patching, hardening, SSH key management (EC2) |
| Application | Code security, dependency scanning, secrets |
| Data | Encryption at rest and in transit, backup, data classification |
| IAM | Users, roles, policies, MFA, least privilege |
| Network | VPC configuration, security groups, NACLs, firewall rules |
| Configuration | Public/private access on S3 buckets, RDS parameter groups |

### The Boundary Shifts by Service Model

The more managed the service, the more AWS takes on:

| Service Type | Example | You Manage | AWS Manages |
|-------------|---------|-----------|------------|
| IaaS | EC2 | OS, runtime, app, data, network config | Hardware, hypervisor |
| Container | ECS / EKS | App, container, runtime config | Underlying hosts (Fargate) |
| PaaS / Managed | RDS, Aurora | Data, DB config, IAM | DB engine, OS, patching |
| Serverless | Lambda | Function code, IAM, data | Runtime, OS, scaling |
| SaaS | S3 | Data, bucket policies, encryption settings | Storage infrastructure |

---

## Azure Shared Responsibility Model

Azure uses the same principle with slight differences in terminology and scope:

| Layer | On-Premises | IaaS | PaaS | SaaS |
|-------|------------|------|------|------|
| Data governance & rights management | Customer | Customer | Customer | Customer |
| Client endpoints | Customer | Customer | Customer | Customer |
| Account & access management | Customer | Customer | Customer | Shared |
| Identity & directory infrastructure | Customer | Customer | Shared | Microsoft |
| Application | Customer | Customer | Shared | Microsoft |
| Network controls | Customer | Customer | Shared | Microsoft |
| Operating system | Customer | Customer | Microsoft | Microsoft |
| Physical hosts | Customer | Microsoft | Microsoft | Microsoft |
| Physical network | Customer | Microsoft | Microsoft | Microsoft |
| Physical datacenter | Customer | Microsoft | Microsoft | Microsoft |

Key Azure note: "Shared" responsibility means both you and Microsoft have obligations — typically you configure the control and Microsoft provides and enforces the capability.

---

## GCP Shared Responsibility Model

GCP follows the same principle. Key points:

- **GCP manages:** Physical infrastructure, network security, hardware, hypervisor, and fully managed service software
- **You manage:** IAM, data, application code, OS (for Compute Engine), network configuration, encryption key management (optional)
- **Shared:** In services like GKE (Google Kubernetes Engine), node security is customer-managed but the control plane is Google-managed

---

## Common Customer Failures (What Goes Wrong)

### 1. Public S3 Buckets (AWS)
Misconfigured bucket policies expose data to the internet. AWS provides Block Public Access settings — enable them by default.

### 2. No MFA on Root/Admin Accounts
The most privileged account is protected only by a password. Enable MFA immediately on creation.

### 3. Overly Permissive IAM Policies
`"Action": "*", "Resource": "*"` gives full access to everything. Apply least-privilege instead.

### 4. Unrotated Access Keys
Long-lived access keys sitting in `.env` files, GitHub repos, or CI systems. Rotate regularly or use IAM roles instead.

### 5. Unpatched Guest Operating Systems (EC2)
AWS patches the hypervisor; you must patch the OS inside your EC2 instance. Use SSM Patch Manager or automation to stay current.

### 6. No Encryption on Sensitive Data
Cloud providers offer encryption at rest and in transit — but it often isn't enabled by default on all services. Explicitly enable it.

### 7. Security Groups with 0.0.0.0/0 Inbound
Open security groups expose services to the entire internet. Restrict inbound rules to the minimum required IPs and ports.

### 8. Credentials in Source Code
Hard-coded access keys or passwords committed to version control. Use secrets management (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager) instead.

---

## Practical Checklist

Use this to verify you're meeting your side of the shared responsibility model:

- [ ] Root/admin account has MFA enabled
- [ ] No long-lived access keys for human users — use IAM roles or SSO
- [ ] All IAM policies follow least-privilege
- [ ] S3 buckets have Block Public Access enabled (enable on account level, not just per bucket)
- [ ] Encryption at rest enabled on all storage containing sensitive data
- [ ] TLS enforced for all external-facing services
- [ ] Guest OS patching is automated or regularly scheduled
- [ ] CloudTrail / audit logging enabled in all regions
- [ ] No secrets or credentials in application code or environment variables
- [ ] Security groups follow minimal access rules
- [ ] Data backups tested (not just created)
- [ ] Incident response plan exists and has been exercised

---

## References

- [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/)
- [Azure Shared Responsibility](https://learn.microsoft.com/en-us/azure/security/fundamentals/shared-responsibility)
- [GCP Shared Responsibility](https://cloud.google.com/architecture/framework/security/shared-responsibility-shared-fate)
- [CISA Cloud Security Best Practices](https://www.cisa.gov/sites/default/files/2023-03/CISA_Cloud-Security-Best-Practices_FINAL_508c.pdf)
---

← [Previous: Deployment Models](./deployment-models.md) | [Home](../README.md) | [Next: Regions & Zones →](./regions-zones-geography.md)
