← [Previous: Service Models](./service-models.md) | [Home](../README.md) | [Next: Shared Responsibility →](./shared-responsibility.md)

---

# Cloud Deployment Models

A deployment model describes where the cloud infrastructure runs and who can access it. There are four primary models: public, private, hybrid, and multi-cloud.

---

## Public Cloud

### What It Is

Infrastructure owned and operated by a third-party provider, shared among multiple customers over the public internet. Resources are provisioned on demand and billed per use.

### Characteristics

- Infrastructure owned entirely by the cloud provider
- Multi-tenant (resources shared between customers with logical isolation)
- Accessible over the public internet
- Fully managed by the provider
- Pay-as-you-go pricing

### Examples

AWS, Azure, GCP, Alibaba Cloud, DigitalOcean — any service you access via an account on a provider's platform.

### When to Use

- Most web applications and SaaS products
- Startups and teams without large IT budgets
- Workloads with unpredictable or variable demand
- When you want to minimize infrastructure management

### Trade-offs

| Pro | Con |
|-----|-----|
| No upfront capital cost | Less control over underlying hardware |
| Instant global scale | Data sovereignty concerns for some industries |
| Massive service catalog | Potential vendor lock-in |
| Provider handles patching, hardware | Multi-tenancy not acceptable for some regulations |

---

## Private Cloud

### What It Is

Cloud infrastructure dedicated to a single organization — either hosted on-premises in the organization's own data centers or hosted by a third party exclusively for that organization.

### Characteristics

- Single-tenant (dedicated to one organization)
- Full control over hardware, OS, and network
- Can be run on-premises, in a colocation facility, or as a hosted private cloud
- Organization is responsible for managing the infrastructure

### Technologies

| Tool | Description |
|------|-------------|
| VMware vSphere / vCloud | Common on-prem virtualization platform |
| OpenStack | Open-source private cloud framework |
| Azure Stack Hub | Azure services running on your own hardware |
| AWS Outposts | AWS infrastructure deployed on-premises |
| Red Hat OpenShift | Kubernetes-based private PaaS |

### When to Use

- Highly regulated industries (government, defense, some healthcare/finance)
- Data residency requirements that prohibit use of public cloud
- Organizations with existing significant on-premises investments
- Workloads requiring dedicated hardware for compliance or performance

### Trade-offs

| Pro | Con |
|-----|-----|
| Full control over hardware and data | High upfront capital cost |
| Meets strict data sovereignty requirements | You manage everything (patches, failures, capacity) |
| No multi-tenancy exposure | Scaling is slow and expensive |
| Predictable performance | Limited geographic reach |

---

## Hybrid Cloud

### What It Is

A combination of public and private cloud, connected and coordinated so that workloads can move between them. Data and applications can be shared between the two environments.

### Characteristics

- Mix of on-premises / private cloud and public cloud
- Workloads distributed based on requirements (cost, compliance, latency)
- Connected via VPN, Direct Connect (AWS), ExpressRoute (Azure), or Cloud Interconnect (GCP)
- Single management plane (ideally) across both environments

### Common Hybrid Patterns

**Burst to cloud:** Run steady-state workloads on-premises. When demand spikes, overflow to public cloud (cloud bursting).

```
On-Premises (baseline load)
        ↕ (VPN / Direct Connect)
Public Cloud (peak overflow)
```

**Data sovereignty + cloud services:** Keep sensitive data on-premises while using cloud services for compute, AI/ML, or analytics.

```
Sensitive Data: On-Premises DB
        ↓ (encrypted connection)
Analytics: GCP BigQuery / AWS Athena
```

**Migration in progress:** Run legacy applications on-premises while migrating to cloud incrementally. This is temporary hybrid.

**Compliance boundary:** Keep regulated workloads on-prem or in a private cloud while running everything else in public cloud.

### Hybrid Cloud Services

| Provider | Hybrid Offering |
|---------|----------------|
| AWS | AWS Outposts, Direct Connect, Local Zones |
| Azure | Azure Arc, Azure Stack Hub, ExpressRoute |
| GCP | Google Distributed Cloud, Anthos, Dedicated Interconnect |

### When to Use

- You have existing on-premises infrastructure that isn't ready to migrate
- Regulations require some data on-premises
- You need dedicated high-bandwidth connectivity between on-prem and cloud
- Running a phased cloud migration

### Trade-offs

| Pro | Con |
|-----|-----|
| Flexibility to place workloads optimally | Most complex to manage |
| Satisfies compliance while using cloud services | Networking between environments adds latency and cost |
| Gradual migration path | Two sets of tools and skills required |
| Burst capacity on demand | Security surface spans two environments |

---

## Multi-Cloud

### What It Is

Using services from two or more cloud providers simultaneously. Unlike hybrid cloud (which combines cloud with on-premises), multi-cloud is entirely in the cloud — just across multiple providers.

### Characteristics

- Workloads distributed across multiple public cloud providers
- No single provider dependency
- Requires multi-cloud management tooling (Terraform, Pulumi, Anthos)

### Common Multi-Cloud Patterns

**Best-of-breed services:** Use GCP BigQuery for analytics, AWS for primary application hosting, and Azure for Active Directory integration.

**Disaster recovery:** Primary workload on AWS; DR environment on Azure. Failover across providers if an entire provider region fails (rare but possible).

**Avoid vendor lock-in:** Keep critical workloads portable by using containers and Kubernetes across providers.

**Geographic coverage:** A provider with data centers in a country required by a customer may not be your primary provider. Deploy that workload on the provider with presence there.

**Negotiating leverage:** Using multiple providers gives you pricing leverage when renewing contracts.

### Multi-Cloud Management Tools

| Tool | Purpose |
|------|---------|
| Terraform / OpenTofu | Provision infrastructure across multiple providers |
| Kubernetes | Run containerized workloads portably across providers |
| Anthos (GCP) | Manage Kubernetes clusters on GCP, AWS, Azure, on-prem |
| Azure Arc | Manage resources across multiple clouds from Azure |
| Pulumi | Infrastructure as code supporting all major providers |
| Datadog / Grafana | Unified observability across clouds |

### When to Use

- You have a strategic reason to avoid dependency on a single provider
- Different business units have different provider preferences
- Specific services or geographic coverage only available from a particular provider
- M&A: acquired company uses different provider — multi-cloud is the interim state

### Trade-offs

| Pro | Con |
|-----|-----|
| Avoids single-vendor lock-in | Significantly higher operational complexity |
| Negotiate pricing with leverage | Staff need skills in multiple platforms |
| Best-of-breed service selection | Data transfer costs between providers (egress fees) |
| Resilience against provider outages | Harder to achieve unified observability |

---

## Comparison Summary

| Model | Who owns infra | Tenancy | Managed by | Best for |
|-------|---------------|---------|-----------|---------|
| Public | Provider | Multi-tenant | Provider | Most workloads, startups, SaaS |
| Private | Customer or provider (dedicated) | Single-tenant | Customer | Regulated industries, compliance |
| Hybrid | Split | Mixed | Split | Migration, compliance + scale |
| Multi-cloud | Multiple providers | Multi-tenant | Customer | Avoid lock-in, best-of-breed |

---

## How to Choose

```
Does your regulation require data on-premises?
    Yes → Private Cloud or Hybrid
    No  → Continue

Do you have workloads on-premises you cannot fully migrate yet?
    Yes → Hybrid
    No  → Continue

Do you need services only available on a specific provider?
    Multiple providers → Multi-cloud
    One provider → Public Cloud
```

---

## References

- [AWS: Types of cloud computing deployment models](https://aws.amazon.com/types-of-cloud-computing/)
- [Azure: What is hybrid cloud?](https://azure.microsoft.com/en-us/resources/cloud-computing-dictionary/what-is-hybrid-cloud-computing/)
- [GCP: Public cloud vs private cloud vs hybrid cloud](https://cloud.google.com/learn/public-cloud-vs-private-cloud-vs-hybrid-cloud)
---

← [Previous: Service Models](./service-models.md) | [Home](../README.md) | [Next: Shared Responsibility →](./shared-responsibility.md)
