← [Previous: Static Website on AWS](../05-aws/14-projects/static-website.md) | [Home](../README.md) | [Next: Azure Account Setup →](./01-account-setup/README.md)

---

# Microsoft Azure

Azure is Microsoft's cloud platform, second largest by market share. It excels in enterprise Windows/Active Directory workloads, hybrid connectivity, and .NET ecosystems. This section covers the services and patterns you need for production Azure deployments.

---

## Azure vs AWS Equivalents (Quick Reference)

| AWS | Azure | Purpose |
|-----|-------|---------|
| IAM | Entra ID + RBAC | Identity and access management |
| Organizations | Management Groups | Multi-account/subscription hierarchy |
| VPC | Virtual Network (VNet) | Private network |
| Security Group | Network Security Group (NSG) | Stateful traffic filtering |
| ALB | Application Gateway | L7 load balancer |
| NLB | Azure Load Balancer | L4 load balancer |
| EC2 | Azure Virtual Machines | Compute |
| Lambda | Azure Functions | Serverless compute |
| ECS/EKS | AKS / ACI | Container orchestration |
| ECR | Azure Container Registry (ACR) | Container registry |
| S3 | Azure Blob Storage | Object storage |
| EBS | Azure Managed Disks | Block storage |
| EFS | Azure Files | File storage |
| RDS | Azure SQL / Azure Database for PostgreSQL | Managed relational DB |
| DynamoDB | Cosmos DB | Managed NoSQL DB |
| ElastiCache | Azure Cache for Redis | Managed Redis |
| CloudWatch | Azure Monitor + Log Analytics | Observability |
| CloudTrail | Azure Activity Log | Audit log |
| KMS | Azure Key Vault | Key management |
| Secrets Manager | Azure Key Vault (secrets) | Secrets management |
| GuardDuty | Microsoft Defender for Cloud | Threat detection |
| CloudFormation | ARM Templates / Bicep | IaC |
| CodePipeline | Azure DevOps Pipelines | CI/CD |
| Route 53 | Azure DNS | DNS |
| CloudFront | Azure CDN / Front Door | CDN |
| Direct Connect | ExpressRoute | Dedicated connectivity |
| VPN Gateway | Azure VPN Gateway | Site-to-site VPN |

---

## Sections

| Directory | Description |
|-----------|-------------|
| [01-account-setup/](./01-account-setup/) | Subscriptions, management groups, Azure CLI, cost management |
| [02-entra-id/](./02-entra-id/) | Identity: users, groups, service principals, managed identities, RBAC |
| [03-networking/](./03-networking/) | VNet, NSGs, peering, load balancers, Application Gateway, Private Endpoint |
| [04-compute/](./04-compute/) | Virtual Machines, VMSS, Azure Bastion |
| [05-storage/](./05-storage/) | Blob Storage, Azure Files, Managed Disks, Data Lake Gen2 |
| [06-databases/](./06-databases/) | Azure SQL, PostgreSQL Flexible Server, Cosmos DB, Azure Cache for Redis |
| [07-containers/](./07-containers/) | ACR, AKS, Azure Container Instances |
| [08-serverless/](./08-serverless/) | Azure Functions, API Management, Service Bus, Event Grid, Event Hubs |
| [09-security/](./09-security/) | Key Vault, Defender for Cloud, Microsoft Sentinel |
| [10-observability/](./10-observability/) | Azure Monitor, Log Analytics, Application Insights, Alerts |
| [11-iac/](./11-iac/) | Bicep, ARM templates, Terraform on Azure |
| [12-projects/](./12-projects/) | Hands-on projects combining multiple services |

---

## Azure Fundamentals

### Global Infrastructure

| Concept | Description |
|---------|-------------|
| **Region** | Geographic area with one or more datacenters (e.g., East US, West Europe) |
| **Region pair** | Two regions paired for disaster recovery (e.g., East US ↔ West US) |
| **Availability Zone** | Physically separate datacenter within a region — 3 zones per region |
| **Geography** | Data-residency boundary (Americas, Europe, Asia Pacific, etc.) |
| **Sovereign cloud** | Government-isolated regions: Azure Government, Azure China |

### Subscription Hierarchy

```
Tenant (Entra ID)
└── Root Management Group
    ├── Management Group (Production)
    │   ├── Subscription A (prod-workloads)
    │   └── Subscription B (prod-shared-services)
    └── Management Group (Development)
        └── Subscription C (dev-workloads)
```

### Pricing

- **Pay-as-you-go** — Billed per second/hour, no commitment
- **Reserved Instances** — 1-year or 3-year commitment, up to 72% savings
- **Azure Hybrid Benefit** — Use existing Windows Server/SQL Server licenses in Azure
- **Spot VMs** — Unused capacity at up to 90% discount (can be evicted)

---

## References

- [Azure documentation](https://docs.microsoft.com/azure/)
- [Azure Architecture Center](https://docs.microsoft.com/azure/architecture/)
- [Azure CLI reference](https://docs.microsoft.com/cli/azure/)
- [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/)
- [Azure Well-Architected Framework](https://docs.microsoft.com/azure/architecture/framework/)
---

← [Previous: Static Website on AWS](../05-aws/14-projects/static-website.md) | [Home](../README.md) | [Next: Azure Account Setup →](./01-account-setup/README.md)
