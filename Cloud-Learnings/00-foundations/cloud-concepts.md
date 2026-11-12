← [Previous: Foundations](./README.md) | [Home](../README.md) | [Next: Service Models →](./service-models.md)

---

# Cloud Computing Concepts

## What Is Cloud Computing?

Cloud computing is the delivery of computing resources — servers, storage, databases, networking, software, analytics, and intelligence — over the internet on a pay-per-use basis.

Instead of owning and maintaining physical data centers, you access technology services from a cloud provider on demand.

**Simple analogy:** Cloud computing is to IT infrastructure what electricity is to power. You don't generate your own electricity — you plug in and pay for what you use. Cloud computing works the same way for servers, storage, and software.

---

## NIST Definition

The National Institute of Standards and Technology (NIST) defines cloud computing through five essential characteristics:

### 1. On-Demand Self-Service

Users can provision computing resources — like server instances or storage — without requiring human interaction with the service provider.

You spin up a server in the AWS Console without calling anyone.

### 2. Broad Network Access

Resources are available over the network and accessible through standard mechanisms (browsers, mobile apps, CLI tools).

You manage your entire infrastructure from a laptop anywhere in the world.

### 3. Resource Pooling

The provider's computing resources are pooled to serve multiple customers using a multi-tenant model. Physical and virtual resources are dynamically assigned and reassigned.

You share physical hardware with other customers, but your workloads are isolated.

### 4. Rapid Elasticity

Resources can be provisioned and released, in some cases automatically, to scale rapidly outward and inward with demand.

Your web application automatically adds servers during a traffic spike and removes them when traffic drops.

### 5. Measured Service

Resource usage is monitored, controlled, and reported — providing transparency for both the provider and consumer. You pay only for what you use.

Your monthly bill reflects exactly how many GB of storage and how many CPU-hours you consumed.

---

## Cloud vs Traditional IT

| Dimension | Traditional IT | Cloud |
|-----------|---------------|-------|
| Capital cost | High upfront (buy hardware) | Low upfront (rent resources) |
| Operational cost | Ongoing maintenance, power, cooling | Pay per use |
| Provisioning time | Days to weeks | Minutes to seconds |
| Scalability | Manual, limited by hardware | Elastic, automatic |
| Capacity planning | Over-provision to handle peak | Right-size, scale dynamically |
| Failure handling | Manual intervention | Automated failover |
| Global reach | Requires building data centers | Instant via provider's global network |

---

## Benefits of Cloud Computing

### Agility
Deploy new resources in minutes rather than weeks. Experiment cheaply — if an idea fails, shut it down.

### Elasticity
Scale up for peak demand (Black Friday, product launches) and scale down during quiet periods. Pay only for peak when it actually happens.

### Cost Efficiency
No upfront capital expenditure on hardware. Shift from CapEx (capital expenditure) to OpEx (operational expenditure). No wasted capacity.

### Global Reach
Cloud providers have data centers on every continent. Deploy your application close to your users in minutes.

### Reliability
Leading providers offer 99.99%+ uptime SLAs backed by redundant infrastructure across multiple physical locations.

### Security
Major cloud providers invest more in security than most organizations can afford on their own:
- Physical security of data centers
- Compliance certifications (SOC 2, ISO 27001, PCI DSS, HIPAA)
- Managed encryption, identity, and threat detection services

### Focus on Core Business
Offload undifferentiated heavy lifting (patching servers, replacing disks, managing networks) to the cloud provider and focus on what makes your business unique.

---

## Challenges and Trade-offs

### Vendor Lock-in
Using proprietary services (AWS Lambda, Azure Cosmos DB) makes it harder to migrate later. Mitigation: use open standards where possible, containerize workloads.

### Unpredictable Costs
Pay-per-use billing can produce surprise bills if workloads scale unexpectedly or resources are left running. Mitigation: set budget alerts, review costs regularly.

### Latency
Data must travel to and from a cloud data center. For latency-sensitive applications, choose a region close to users and use edge/CDN services.

### Compliance and Data Residency
Some industries (healthcare, finance, government) have strict rules about where data can be stored. Verify the cloud provider's compliance certifications and available regions.

### Shared Tenancy Concerns
Your workloads run on physical hardware shared with other customers. While modern hypervisors provide strong isolation, some regulated industries require dedicated hardware (available from all major providers at higher cost).

---

## Key Cloud Terminology

| Term | Definition |
|------|-----------|
| **Region** | A geographic area with one or more data centers |
| **Availability Zone (AZ)** | An isolated data center or cluster within a region |
| **Instance** | A single virtual server |
| **Tenant** | An organization or customer using shared cloud infrastructure |
| **Multi-tenancy** | Multiple customers sharing the same physical infrastructure with logical isolation |
| **Hypervisor** | Software that creates and manages virtual machines on physical hardware |
| **SLA** | Service Level Agreement — the uptime guarantee from the provider |
| **Elasticity** | The ability to automatically scale resources up or down |
| **Provisioning** | The process of allocating and configuring cloud resources |
| **CapEx** | Capital Expenditure — upfront investment in physical assets |
| **OpEx** | Operational Expenditure — ongoing costs for services consumed |

---

## Major Cloud Providers

| Provider | Full Name | Market Position |
|---------|-----------|----------------|
| AWS | Amazon Web Services | Largest by market share (~32%) |
| Azure | Microsoft Azure | Second largest (~23%) |
| GCP | Google Cloud Platform | Third largest (~11%) |
| OCI | Oracle Cloud Infrastructure | Strong in database workloads |
| IBM Cloud | IBM Cloud | Enterprise, hybrid focus |
| Alibaba Cloud | Alibaba Cloud | Dominant in China/APAC |
| DigitalOcean | DigitalOcean | Developer-focused, simpler pricing |

---

## References

- [NIST Definition of Cloud Computing (SP 800-145)](https://csrc.nist.gov/publications/detail/sp/800-145/final)
- [AWS: What is cloud computing?](https://aws.amazon.com/what-is-cloud-computing/)
- [Azure: What is cloud computing?](https://azure.microsoft.com/en-us/resources/cloud-computing-dictionary/what-is-cloud-computing/)
- [GCP: What is cloud computing?](https://cloud.google.com/learn/what-is-cloud-computing)
---

← [Previous: Foundations](./README.md) | [Home](../README.md) | [Next: Service Models →](./service-models.md)
