← [Previous: Storage](./storage.md) | [Home](../README.md) | [Next: Databases →](./databases.md)

---

# Cloud Networking Fundamentals

## Why Cloud Networking Matters

Networking determines:
- **Security**: what traffic can reach your resources and from where
- **Availability**: whether traffic fails over when a zone goes down
- **Cost**: data transfer fees for cross-AZ, cross-region, and internet egress
- **Performance**: latency between components

Misconfigured networking is one of the most common causes of both security breaches and application outages.

---

## Virtual Private Cloud (VPC)

A **VPC** is a logically isolated network within a cloud provider's infrastructure. It's your private section of the cloud where you define IP address ranges, subnets, routing, and network access controls.

```
AWS Account
  └── Region (us-east-1)
        └── VPC (10.0.0.0/16)
              ├── Public Subnet (10.0.1.0/24) — AZ-A
              ├── Private Subnet (10.0.2.0/24) — AZ-A
              ├── Public Subnet (10.0.3.0/24) — AZ-B
              └── Private Subnet (10.0.4.0/24) — AZ-B
```

**Provider equivalents:**

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Isolated network | VPC | Virtual Network (VNet) | VPC Network |
| IP range | CIDR block | Address space | CIDR range |
| Sub-network | Subnet | Subnet | Subnet |

**Default VPC:** AWS creates a default VPC in each region. It has permissive defaults — fine for learning, but replace with a properly designed VPC for production.

---

## CIDR and IP Addressing

**CIDR (Classless Inter-Domain Routing)** notation defines IP address ranges.

```
10.0.0.0/16   → 65,536 addresses (10.0.0.0 to 10.0.255.255)
10.0.1.0/24   → 256 addresses (10.0.1.0 to 10.0.1.255)
10.0.1.0/28   → 16 addresses (10.0.1.0 to 10.0.1.15)
```

**Private IP ranges (RFC 1918):**

```
10.0.0.0/8      — 16 million addresses
172.16.0.0/12   — 1 million addresses
192.168.0.0/16  — 65,536 addresses
```

Always use private IP ranges for VPC CIDR blocks. Choose a range that won't overlap with:
- Other VPCs you might peer with
- Your on-premises network if you plan to use VPN/Direct Connect

**AWS reserves 5 IPs per subnet** (network address, VPC router, DNS, future use, broadcast). A `/24` subnet gives you 251 usable addresses, not 256.

---

## Subnets

A subnet is a range of IP addresses within a VPC, tied to a single AZ.

### Public vs Private Subnets

| Property | Public Subnet | Private Subnet |
|----------|--------------|----------------|
| Route to internet | Via Internet Gateway (direct) | Via NAT Gateway (outbound only) |
| Resources | Load balancers, bastion hosts, NAT Gateway | App servers, databases |
| Public IPs | Can be assigned | Not typically used |
| Inbound from internet | Yes (with security group allowing) | No direct inbound |

**Three-tier subnet design:**

```
Public Subnet:    Load Balancer, NAT Gateway, Bastion
                           ↓
Private Subnet:   App servers (EC2, ECS tasks)
                           ↓
Data Subnet:      RDS, ElastiCache (most restrictive)
```

---

## Internet Gateway and NAT Gateway

### Internet Gateway (IGW)

Allows bidirectional communication between resources in a VPC and the internet.

- Attached to a VPC (one IGW per VPC)
- Resources in public subnets with a public IP can communicate directly through IGW
- Horizontally scaled, redundant — no availability concern

### NAT Gateway

Allows resources in private subnets to initiate outbound connections to the internet (e.g., to download packages), while preventing inbound connections from the internet.

```
Private EC2 → NAT Gateway (in public subnet) → Internet Gateway → Internet
Internet    → Internet Gateway → (blocked — no inbound to private subnet via NAT)
```

**Cost:** NAT Gateway charges per hour + per GB processed. For high-throughput workloads, this can be significant. Use VPC endpoints to avoid routing AWS API traffic through NAT Gateway.

---

## Route Tables

A route table contains rules that determine where network traffic is directed.

**Public subnet route table:**

| Destination | Target |
|------------|--------|
| `10.0.0.0/16` | `local` (VPC internal) |
| `0.0.0.0/0` | `igw-xxxxxxxxx` (internet gateway) |

**Private subnet route table:**

| Destination | Target |
|------------|--------|
| `10.0.0.0/16` | `local` |
| `0.0.0.0/0` | `nat-xxxxxxxxx` (NAT gateway) |

Every subnet must be associated with a route table. If not explicitly associated, it uses the VPC's main route table.

---

## Security Groups

A security group is a **stateful** virtual firewall at the instance (ENI) level.

**Stateful**: If you allow inbound traffic on port 443, the response traffic is automatically allowed outbound — you don't need a separate outbound rule.

```
Inbound rules:
  TCP 443 from 0.0.0.0/0   (HTTPS from anywhere)
  TCP 22 from 10.0.0.0/8   (SSH from internal only)

Outbound rules:
  All traffic to 0.0.0.0/0  (default: allow all outbound)
```

**Key properties:**
- Default: deny all inbound, allow all outbound
- Rules can reference other security groups (e.g., "allow port 5432 from the app-server security group")
- No explicit deny — to block traffic, simply don't allow it
- Changes take effect immediately

---

## Network ACLs (NACLs)

NACLs are **stateless** firewall rules at the subnet level.

**Stateless**: You must explicitly allow both inbound and outbound traffic. Return traffic is not automatically permitted.

| Dimension | Security Group | NACL |
|-----------|---------------|------|
| Level | Instance (ENI) | Subnet |
| State | Stateful | Stateless |
| Rules | Allow only | Allow and Deny |
| Rule evaluation | All rules evaluated | Rules evaluated in number order, first match wins |
| Use case | Primary security control | Additional defense, blocking specific IPs |

**When to use NACLs:** As an additional layer to explicitly deny known bad IP ranges or restrict traffic between subnets. Don't rely on NACLs as your primary security control.

---

## VPC Peering and Transit Gateway

### VPC Peering

Connects two VPCs so resources can communicate using private IP addresses. Traffic stays on the AWS backbone — no internet exposure.

```
VPC A (10.0.0.0/16) ←——peering——→ VPC B (10.1.0.0/16)
```

Limitations:
- Not transitive — if A peers with B and B peers with C, A cannot reach C through B
- VPC CIDR blocks cannot overlap
- Works cross-account and cross-region

### Transit Gateway

A hub-and-spoke network transit hub that connects multiple VPCs and on-premises networks.

```
VPC A ──┐
VPC B ──┤── Transit Gateway ──── On-Premises (VPN/Direct Connect)
VPC C ──┘
```

Solves the peering scalability problem — instead of N × (N-1)/2 peering connections, each VPC connects to one Transit Gateway.

---

## Load Balancing

A load balancer distributes incoming traffic across multiple backend targets, improving availability and scalability.

**Types:**

| Type | Layer | Use case |
|------|-------|---------|
| Application LB (ALB) | Layer 7 (HTTP/HTTPS) | Web apps, API routing by path/header |
| Network LB (NLB) | Layer 4 (TCP/UDP) | High performance, static IP, gaming, IoT |
| Gateway LB (GWLB) | Layer 3 | Deploying third-party network appliances |

**ALB routing:**

```
/ → Target Group A (web frontend)
/api/* → Target Group B (API servers)
/admin/* → Target Group C (admin servers) — restricted by IP
```

**Provider equivalents:**

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Application LB | ALB | Application Gateway | Cloud Load Balancing (HTTP) |
| Network LB | NLB | Azure Load Balancer | Cloud Load Balancing (TCP/UDP) |
| Global HTTP LB | CloudFront + ALB | Azure Front Door | Cloud Load Balancing (global) |

---

## DNS

DNS translates domain names to IP addresses. In cloud networking, DNS handles both external (public) and internal (private) resolution.

**Provider DNS services:**

| Provider | Public DNS | Private DNS |
|---------|-----------|------------|
| AWS | Route 53 | Route 53 Private Hosted Zones |
| Azure | Azure DNS | Azure Private DNS Zones |
| GCP | Cloud DNS | Cloud DNS (private zones) |

**Internal service discovery:** Use private DNS zones so services call each other by name (`db.internal`, `auth.svc.prod`) rather than hardcoded IPs.

---

## VPC Endpoints

VPC endpoints allow private connectivity from your VPC to AWS services without traffic leaving the AWS network — no internet gateway, NAT gateway, or public IP required.

```
Without endpoint: Private EC2 → NAT Gateway → Internet → S3 endpoint
With endpoint:    Private EC2 → VPC Endpoint → S3 (stays on AWS network)
```

**Benefits:**
- Improved security (traffic never touches internet)
- Eliminates NAT Gateway data processing charges for AWS service traffic
- Lower latency

**Types:**
- **Interface endpoints** (PrivateLink): Creates an ENI in your subnet with a private IP
- **Gateway endpoints**: Route table entry for S3 and DynamoDB (free)

---

## CDN (Content Delivery Network)

A CDN caches content at edge locations closer to users, reducing latency and origin server load.

```
User in Tokyo
  ↓ (request)
CloudFront edge: Tokyo POP
  ↓ (cache miss — first request only)
Origin: S3 bucket in us-east-1
  ↓ (response cached at edge)
User receives response — subsequent requests served from Tokyo
```

**Provider CDN services:**

| Provider | Service |
|---------|---------|
| AWS | CloudFront |
| Azure | Azure CDN / Azure Front Door |
| GCP | Cloud CDN |
| Independent | Cloudflare, Fastly, Akamai |

---

## References

- [AWS VPC documentation](https://docs.aws.amazon.com/vpc/latest/userguide/)
- [AWS Networking fundamentals](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Networking.html)
- [Azure networking overview](https://learn.microsoft.com/en-us/azure/networking/fundamentals/networking-overview)
- [GCP VPC overview](https://cloud.google.com/vpc/docs/overview)
- [Subnet CIDR calculator](https://www.subnet-calculator.com/)
---

← [Previous: Storage](./storage.md) | [Home](../README.md) | [Next: Databases →](./databases.md)
