← [Previous: Shared Responsibility](./shared-responsibility.md) | [Home](../README.md) | [Next: Billing Basics →](./billing-basics.md)

---

# Regions, Availability Zones, and Cloud Geography

## Why Cloud Geography Matters

Where your infrastructure runs affects:

- **Latency** — physical distance to users
- **Compliance** — data residency regulations
- **Cost** — pricing differs by region
- **Availability** — redundancy against data center failures
- **Service availability** — not all services are available in every region

---

## Global Infrastructure Hierarchy

Cloud providers organize their infrastructure in layers, from largest to smallest:

```
Planet
  └── Geography / Geopolitical boundary
        └── Region (e.g., us-east-1)
              └── Availability Zone (e.g., us-east-1a)
                    └── Data Center(s)
                          └── Servers / Racks
```

---

## Regions

A **region** is a distinct geographic area where a cloud provider has infrastructure. Each region is a separate, independent cluster of data centers.

### Key Properties of Regions

- **Isolated**: Failures in one region do not affect other regions
- **Independent**: Each region has its own power, cooling, and networking
- **Self-contained**: Most services run entirely within a single region
- **Separate billing**: Data transfer between regions incurs egress costs

### Region Examples by Provider

**AWS regions** (selected):

| Region Code | Location |
|------------|---------|
| `us-east-1` | Northern Virginia (oldest, most services) |
| `us-west-2` | Oregon |
| `eu-west-1` | Ireland |
| `eu-central-1` | Frankfurt |
| `ap-southeast-1` | Singapore |
| `ap-northeast-1` | Tokyo |
| `ap-south-1` | Mumbai |
| `sa-east-1` | São Paulo |
| `me-south-1` | Bahrain |
| `af-south-1` | Cape Town |

**Azure regions** (selected): East US, West US 2, North Europe, West Europe, Southeast Asia, East Asia, Brazil South, Australia East

**GCP regions** (selected): us-central1 (Iowa), us-east1 (South Carolina), europe-west1 (Belgium), asia-east1 (Taiwan), australia-southeast1 (Sydney)

### Choosing a Region

Consider these factors in order:

1. **Compliance and data residency**: Some regulations require data to remain within a country or region. This is non-negotiable — check first.

2. **Latency to end users**: Choose the region geographically closest to your largest user base. Use [cloudping.info](https://cloudping.info) to measure.

3. **Service availability**: Not all services are available in all regions. Verify before choosing (e.g., AWS Bedrock, some GPU instance types are region-limited).

4. **Cost**: Some regions are cheaper than others. `us-east-1` and `us-west-2` are typically the cheapest AWS regions. EU and APAC regions cost 5–20% more.

5. **Paired region for DR**: Choose a region with a paired/nearby region for disaster recovery.

---

## Availability Zones (AZs)

An **availability zone** is one or more discrete data centers within a region, each with redundant power, networking, and cooling. AZs within a region are physically separated from each other — typically kilometers apart — connected by low-latency, high-bandwidth fiber.

### Key Properties of AZs

- **Isolated failure domains**: An AZ failure (power outage, fire, flooding) does not affect other AZs in the same region
- **Low-latency interconnect**: AZs within a region are connected by fiber with sub-millisecond latency
- **Independent networking**: Each AZ has independent network paths to the internet
- **Opaque naming**: AWS maps AZ names (us-east-1a, us-east-1b) to physical data centers differently per account to distribute load

### AZ Count per Region

| Provider | Typical AZ count per region |
|---------|---------------------------|
| AWS | 3–6 AZs per region (most have 3) |
| Azure | Typically 3 zones in supported regions |
| GCP | Typically 3 zones per region |

### Why AZs Matter

A workload in a single AZ is vulnerable to that AZ failing. Best practice is to **deploy across at least 2 AZs**:

```
Single AZ (vulnerable):
  AZ-A: [EC2] [EC2] [RDS]
  AZ-B: (empty)
  Risk: AZ-A failure takes down everything

Multi-AZ (resilient):
  AZ-A: [EC2] [EC2] [RDS Primary]
  AZ-B: [EC2] [EC2] [RDS Standby]
  Risk: AZ-A failure → traffic routes to AZ-B automatically
```

---

## Edge Locations and CDN Points of Presence

Beyond regions and AZs, cloud providers have a much larger number of **edge locations** — smaller facilities distributed worldwide used for content delivery (CDN) and DNS.

| Provider | Edge network | Count (approx.) |
|---------|-------------|----------------|
| AWS | CloudFront CDN + Route 53 | 450+ POPs globally |
| Azure | Azure CDN / Front Door | 190+ POPs globally |
| GCP | Cloud CDN + Cloud Armor | 160+ edge nodes |
| Cloudflare | Cloudflare Workers, CDN | 330+ cities |

Edge locations cache content closer to end users, reducing latency for static assets, APIs, and DNS lookups.

### AWS-Specific Edge Concepts

**Local Zones**: AWS infrastructure placed in metropolitan areas outside of standard regions, for applications requiring single-digit millisecond latency (e.g., gaming, live video, AR/VR).

**Wavelength Zones**: AWS infrastructure embedded within telecom 5G networks for ultra-low latency mobile applications.

**AWS Outposts**: AWS hardware installed in your own data center — extends a region into your on-premises environment.

---

## Data Transfer Costs

Understanding geography helps understand billing:

| Transfer type | Typical cost |
|--------------|-------------|
| Within same AZ | Free |
| Between AZs in same region | ~$0.01–0.02/GB |
| Between regions | ~$0.02–0.09/GB (varies by region pair) |
| Internet egress (out to internet) | $0.09/GB (first 10TB, AWS us-east-1) |
| Internet ingress (in from internet) | Free |

**Key insight**: Keep workloads that communicate frequently in the same AZ to avoid inter-AZ transfer costs. But spread stateless compute across AZs for availability.

---

## Multi-Region Architecture

For the highest availability and disaster recovery, deploy across multiple regions:

```
Region: us-east-1 (Primary)          Region: us-west-2 (DR)
├── AZ-A: App, DB Primary             ├── AZ-A: App (standby)
├── AZ-B: App, DB Standby             └── AZ-B: App (standby)
└── Route 53 (Global DNS)
           ↓
     Health Checks
           ↓
    Failover to us-west-2 if us-east-1 is unhealthy
```

Multi-region comes with trade-offs:
- Higher cost (duplicated infrastructure)
- Database replication complexity (cross-region latency ~60–80ms between US regions)
- Application must handle eventual consistency

---

## GCP-Specific: Zones vs Regions vs Multi-Regions

GCP uses slightly different terminology:

- **Zone**: Smallest unit (equivalent to AZ) — e.g., `us-central1-a`
- **Region**: Group of zones — e.g., `us-central1`
- **Multi-region**: Group of regions used for globally replicated services (e.g., GCS multi-region `US`, `EU`, `ASIA`)

GCP Cloud Storage and BigQuery support multi-region configurations where data is automatically replicated across regions for maximum durability.

---

## Azure-Specific: Region Pairs and Availability Sets

**Region Pairs**: Azure pairs each region with another region in the same geography for disaster recovery. Updates are rolled out to region pairs sequentially to reduce risk (e.g., East US ↔ West US, North Europe ↔ West Europe).

**Availability Zones vs Availability Sets**:
- **Availability Zones**: Physical zone isolation (like AWS AZs) — supported in select regions
- **Availability Sets**: Older concept — logical grouping ensuring VMs are distributed across fault domains and update domains within a single data center

---

## References

- [AWS Global Infrastructure](https://aws.amazon.com/about-aws/global-infrastructure/)
- [AWS Regions and AZs docs](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)
- [Azure geographies and regions](https://azure.microsoft.com/en-us/explore/global-infrastructure/geographies/)
- [GCP locations](https://cloud.google.com/about/locations)
- [Cloud Ping — measure latency to cloud regions](https://cloudping.info)
---

← [Previous: Shared Responsibility](./shared-responsibility.md) | [Home](../README.md) | [Next: Billing Basics →](./billing-basics.md)
