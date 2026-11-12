← [Previous: Interview Overview](./README.md) | [Home](../README.md) | [Next: System Design →](./system-design.md)

---

# Interview Prep: AWS Fundamentals

---

## Networking

**Q: What is the difference between a Security Group and a NACL?**

Security Groups are **stateful** firewalls applied at the instance/ENI level — if you allow inbound traffic, the response is automatically allowed outbound. Rules are allow-only.

NACLs are **stateless** firewalls applied at the subnet level — you must explicitly allow both inbound AND outbound traffic, including ephemeral ports (1024–65535) for return traffic. They support both allow and deny rules and are evaluated in rule number order.

In practice: use Security Groups for most filtering. Use NACLs for broad subnet-level blocking (e.g., blocking a range of IPs across the entire subnet).

---

**Q: A private EC2 instance in a private subnet needs to download a package from the internet. What needs to be in place?**

1. A NAT Gateway in a **public subnet**
2. A route in the **private subnet's route table**: `0.0.0.0/0 → nat-gateway-id`
3. A route in the **public subnet's route table**: `0.0.0.0/0 → internet-gateway-id`
4. The EC2's security group must allow outbound traffic to the internet
5. The VPC must have `enableDnsSupport` and `enableDnsHostnames` enabled (for DNS resolution)

Follow-up: *Why does the NAT Gateway go in the public subnet?* — The NAT Gateway needs a public IP to communicate with the internet. It translates private IPs to its public IP (SNAT) for outbound connections.

---

**Q: What is VPC peering? What are its limitations?**

VPC peering creates a direct private network connection between two VPCs. Traffic flows through AWS's backbone network, not the internet.

Limitations:
- **Not transitive**: if VPC-A peers with VPC-B and VPC-B peers with VPC-C, VPC-A cannot reach VPC-C through VPC-B. Each pair needs its own peering connection.
- CIDR blocks cannot overlap
- One peering connection per VPC pair
- Works within a region and across regions (inter-region peering)

For hub-and-spoke topologies with many VPCs, use **Transit Gateway** instead (transitive routing).

---

## Compute

**Q: When would you choose Lambda over ECS Fargate?**

| Lambda | ECS Fargate |
|--------|------------|
| Event-driven, short-lived tasks (< 15 min) | Long-running services, APIs |
| Infrequent, spiky workloads (pay per execution) | Consistent or predictable traffic |
| Simple stateless functions | Stateful apps, complex startup |
| File processing, S3 triggers, API events | Container workloads, microservices |
| Cold start acceptable | Low-latency startup required |

Lambda is also simpler operationally — no cluster or task definition management.

---

**Q: What is the difference between horizontal and vertical scaling? When do you use each?**

**Vertical scaling** (scale up): increase CPU/RAM of a single instance. Fast to apply, simple, but has limits (largest instance type) and causes downtime for EC2 (can be minimal with RDS Multi-AZ failover).

**Horizontal scaling** (scale out): add more instances. Requires stateless application design, but unlimited theoretical ceiling and no single point of failure. EC2 Auto Scaling Groups, ECS desired count, Kubernetes HPA.

In practice: vertical first for databases (simpler), horizontal for application tiers (resilience + unlimited scale).

---

## Storage and Databases

**Q: What is the difference between RDS Multi-AZ and a Read Replica?**

**Multi-AZ** is for **high availability**:
- Synchronous replication to a standby in another AZ
- Automatic failover in 60–120 seconds on primary failure
- Standby is not accessible for reads
- Used for production reliability

**Read Replica** is for **read scaling and migration**:
- Asynchronous replication (replication lag exists)
- Readable endpoint for offloading SELECT queries
- Can be in the same region or cross-region
- Can be promoted to standalone primary (for migration or DR)

---

**Q: How does S3 achieve 11 nines of durability?**

S3 stores data redundantly across multiple devices in multiple Availability Zones within a region. When you upload an object, S3 automatically stores multiple copies. The 99.999999999% (11 nines) durability means ~0.000000001% chance of data loss per object per year.

Durability ≠ Availability. S3 Standard has 99.99% availability SLA — objects are accessible 99.99% of the time, but they're stored so redundantly that losing the data is essentially impossible.

---

## Security and IAM

**Q: Explain the principle of least privilege. How do you implement it in AWS?**

Least privilege means granting only the permissions needed to perform a specific task — no more, no less.

Implementation in AWS:
1. **IAM policies**: use specific Actions (not `*`), specific Resources (not `*`), add Conditions (IP, MFA required, time)
2. **IAM roles for services**: never use IAM users with long-lived keys for EC2/Lambda/ECS
3. **Permission boundaries**: cap what a role can do even if the attached policy allows more
4. **SCPs (Service Control Policies)**: org-level guard rails across all accounts
5. **Access Analyzer**: finds overly permissive policies and external access

Regularly run: `aws iam generate-service-last-accessed-details` to find permissions not used in 90+ days and remove them.

---

**Q: What is the difference between an IAM Role and an IAM User?**

**IAM User**: a persistent identity with long-lived credentials (access keys). For humans using the console or CLI.

**IAM Role**: a temporary identity assumed by AWS services, applications, or people. No long-lived keys — generates temporary credentials via STS (short-lived, rotate automatically). Used by EC2, Lambda, ECS tasks, cross-account access, federated identity.

Best practice: prefer roles over users for everything except human console access.

---

## High Availability and DR

**Q: What is the difference between high availability and disaster recovery?**

**High Availability** is about tolerating component failures **without downtime**. The system continues operating when a server, AZ, or service goes down. Achieved through redundancy: Multi-AZ RDS, Auto Scaling Groups across AZs, multi-target load balancers.

**Disaster Recovery** is about recovering from a catastrophic event (regional outage, data corruption, security incident) that takes down the primary system entirely. Involves a **separate region** (or account) and has explicit RTO/RPO targets. Requires more planning and cost than HA.

HA prevents downtime; DR limits downtime **after** a disaster.

---

**Q: Walk me through how you would design a system for 99.99% availability.**

1. **No single points of failure**: multi-AZ for every component (EC2 in ASG, RDS Multi-AZ, ALB across AZs, NAT Gateway per AZ)
2. **Health checks everywhere**: ALB health checks, Route 53 health checks for DNS failover
3. **Auto-recovery**: ASG replaces unhealthy instances, ECS/Kubernetes restarts crashed containers
4. **Graceful degradation**: circuit breakers, feature flags, cached fallbacks
5. **Data layer**: RDS Multi-AZ (60-120s failover) or Aurora (< 30s), cross-region replication for DR
6. **Monitoring**: alerting when error rate rises, before it hits SLA breach
7. **Load test**: validate that the system handles 2× expected peak traffic

99.99% = ~52 minutes downtime/year. Single-AZ failure + auto-recovery covers most of this.

---

## Cost

**Q: How do you reduce AWS costs for a production workload?**

1. **Right-size**: Compute Optimizer recommendations for EC2, RDS, Lambda
2. **Savings Plans / Reserved Instances**: 30–70% discount for committed usage
3. **Spot Instances**: 70–90% discount for fault-tolerant workloads (Karpenter on EKS, Spot in mixed ASGs)
4. **S3 lifecycle policies**: automatically move objects to cheaper storage classes
5. **Delete unused resources**: snapshots, unattached EBS volumes, idle RDS instances, old ECR images
6. **Tagging**: tag everything → Cost Explorer by team/project → accountability
7. **NAT Gateway**: aggregate egress through fewer NAT Gateways; avoid cross-AZ traffic

---

← [Previous: Interview Overview](./README.md) | [Home](../README.md) | [Next: System Design →](./system-design.md)
