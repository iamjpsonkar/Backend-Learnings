← [Previous: Linux Cheatsheet](../24-cheatsheets/linux.md) | [Home](../README.md) | [Next: Roadmaps →](../26-roadmaps/README.md)

---

# Glossary

Definitions for cloud, DevOps, SRE, and infrastructure terms used throughout this repo. Terms are grouped by category.

---

## Availability and Reliability

| Term | Definition |
|------|-----------|
| **Availability** | Percentage of time a system is operational: `(total_time - downtime) / total_time` |
| **Five Nines** | 99.999% availability — allows 5.26 minutes of downtime per year |
| **SLA** | Service Level Agreement — contractual commitment on availability (e.g., 99.9%) |
| **SLO** | Service Level Objective — internal target, tighter than SLA (e.g., 99.95%) |
| **SLI** | Service Level Indicator — the metric measured (e.g., % of requests returning 2xx) |
| **Error Budget** | `1 - SLO` — time/failure budget available to spend on risk (deploys, experiments) |
| **RTO** | Recovery Time Objective — maximum acceptable downtime after a failure |
| **RPO** | Recovery Point Objective — maximum acceptable data loss (measured in time) |
| **MTTR** | Mean Time To Recover — average time from incident declaration to resolution |
| **MTBF** | Mean Time Between Failures — average time between incidents |
| **Toil** | Repetitive manual operational work that scales with service load |

---

## Infrastructure and Compute

| Term | Definition |
|------|-----------|
| **IaaS** | Infrastructure as a Service — raw VMs, networking, storage (EC2, GCE, Azure VMs) |
| **PaaS** | Platform as a Service — managed runtime/middleware (Elastic Beanstalk, App Engine) |
| **SaaS** | Software as a Service — full application delivered as service (Gmail, Salesforce) |
| **Serverless** | Compute model where provider manages scaling/provisioning; pay per execution (Lambda) |
| **Instance type** | AWS classification of VM size: family (m, c, r, t) + generation + size (small, large, xlarge) |
| **Spot/Preemptible** | Spare capacity offered at deep discount; can be reclaimed with short notice |
| **Reserved Instance (RI)** | 1- or 3-year commitment for EC2; cheaper than on-demand |
| **Savings Plans** | Flexible commitment ($/hour) covering EC2, Fargate, Lambda; 30-70% discount |
| **AMI** | Amazon Machine Image — snapshot of root volume + launch config used to start EC2 |
| **Auto Scaling Group (ASG)** | Manages fleet of EC2s; scales in/out based on policies |
| **Launch Template** | Version-controlled configuration for EC2 launch: AMI, instance type, user data |

---

## Networking

| Term | Definition |
|------|-----------|
| **VPC** | Virtual Private Cloud — isolated virtual network within a cloud account |
| **Subnet** | Sub-division of a VPC CIDR block; can be public (has IGW route) or private |
| **CIDR** | Classless Inter-Domain Routing — notation for IP ranges (e.g., `10.0.0.0/16`) |
| **Security Group** | Stateful firewall at instance/ENI level; allow rules only |
| **NACL** | Network Access Control List — stateless firewall at subnet level; allow + deny rules |
| **Internet Gateway (IGW)** | Enables internet access for public subnets |
| **NAT Gateway** | Allows private subnet instances to initiate outbound internet connections |
| **VPC Peering** | Direct networking between two VPCs (same or different accounts/regions) |
| **Transit Gateway** | Hub-and-spoke network connecting multiple VPCs and on-premises networks |
| **Direct Connect** | Dedicated private network connection between on-premises DC and AWS |
| **Route 53** | AWS DNS service; also provides health checks and traffic routing policies |
| **ALB** | Application Load Balancer — Layer 7; routes by host/path, supports gRPC |
| **NLB** | Network Load Balancer — Layer 4; ultra-low latency, static IP, handles millions of req/s |
| **CDN** | Content Delivery Network — caches content at edge locations near users |
| **Egress** | Outbound data transfer (leaving the cloud); usually billed |
| **Ingress** | Inbound data transfer (entering the cloud); usually free |

---

## Storage

| Term | Definition |
|------|-----------|
| **Object storage** | Flat key-value storage for unstructured data (S3, GCS, Azure Blob) |
| **Block storage** | Low-latency volumes attached to VMs (EBS, Persistent Disk, Azure Disk) |
| **File storage** | Shared filesystem mounted by multiple instances (EFS, Filestore, Azure Files) |
| **S3 Storage Classes** | Tiers: Standard → Standard-IA → Glacier Instant → Glacier Flexible → Deep Archive |
| **Bucket** | Top-level container in object storage; globally unique name within a provider |
| **Object Lock** | S3 feature that prevents object deletion/modification for a set period (WORM) |
| **Versioning** | Keeps all versions of an object in a bucket; enables rollback |
| **CRR** | Cross-Region Replication — automatic async replication of S3 objects to another region |
| **Lifecycle rule** | Policy to automatically transition or expire objects based on age |

---

## Containers and Kubernetes

| Term | Definition |
|------|-----------|
| **Container** | Isolated process with its own filesystem, network, and PID namespace |
| **Image** | Read-only template for a container; built from a Dockerfile |
| **Registry** | Repository for container images (ECR, Docker Hub, GCR, ACR) |
| **Pod** | Smallest deployable unit in Kubernetes; one or more containers sharing network/storage |
| **Deployment** | Kubernetes resource managing a ReplicaSet; handles rolling updates and rollbacks |
| **Service** | Kubernetes stable network endpoint for a set of pods (ClusterIP, NodePort, LoadBalancer) |
| **Ingress** | Kubernetes resource exposing HTTP(S) routes to services via an ingress controller |
| **HPA** | Horizontal Pod Autoscaler — scales pod replicas based on CPU/memory/custom metrics |
| **VPA** | Vertical Pod Autoscaler — recommends/sets right CPU/memory requests for pods |
| **DaemonSet** | Kubernetes resource ensuring one pod runs on every (or selected) node |
| **StatefulSet** | Like Deployment but with stable pod identity and persistent storage per pod |
| **Helm** | Kubernetes package manager; charts are parameterized templates |
| **Kustomize** | Kubernetes configuration management; overlays patches on base manifests |
| **IRSA** | IAM Roles for Service Accounts — binds AWS IAM role to Kubernetes service account |
| **Fargate** | Serverless container runtime; no EC2 nodes to manage (ECS and EKS) |

---

## CI/CD and DevOps

| Term | Definition |
|------|-----------|
| **CI** | Continuous Integration — automated build, test, and static analysis on every commit |
| **CD** | Continuous Delivery — deployable artifact ready after every CI pass; deploy is manual |
| **CD** | Continuous Deployment — every passing commit deploys to production automatically |
| **GitOps** | Using Git as the single source of truth for infrastructure and app state |
| **ArgoCD** | GitOps CD tool for Kubernetes; syncs cluster state with Git repo |
| **Blue/Green** | Two identical environments; traffic switches from blue (current) to green (new) |
| **Canary** | Gradual traffic shift: 1% → 10% → 100% to new version |
| **Feature flag** | Runtime toggle to enable/disable features without deployment |
| **OIDC** | OpenID Connect — identity layer on top of OAuth 2.0; used for keyless CI/CD auth |
| **Artifact** | Build output stored for deployment: Docker image, ZIP, JAR, AMI |

---

## Security

| Term | Definition |
|------|-----------|
| **IAM** | Identity and Access Management — controls who can do what to which resources |
| **Least privilege** | Grant only the minimum permissions needed; no more |
| **MFA** | Multi-Factor Authentication — requires 2+ proof factors (password + TOTP/hardware key) |
| **KMS** | Key Management Service — managed cryptographic keys; used for envelope encryption |
| **CMK** | Customer Managed Key — KMS key you control vs AWS-managed key |
| **Envelope encryption** | Encrypt data with a data key (DEK); encrypt the DEK with KMS |
| **Secret** | Sensitive value (password, API key, token) — never hardcoded or in version control |
| **SAST** | Static Application Security Testing — analyzes source code for vulnerabilities |
| **DAST** | Dynamic Application Security Testing — tests running application for vulnerabilities |
| **SBOM** | Software Bill of Materials — inventory of all components and dependencies |
| **SLSA** | Supply chain Levels for Software Artifacts — framework for supply chain security |
| **Zero Trust** | Never trust, always verify — no implicit trust based on network location |
| **WAF** | Web Application Firewall — filters HTTP requests to block OWASP Top 10 attacks |

---

## Databases

| Term | Definition |
|------|-----------|
| **ACID** | Atomicity, Consistency, Isolation, Durability — properties of reliable transactions |
| **BASE** | Basically Available, Soft state, Eventually consistent — NoSQL trade-off model |
| **PITR** | Point-in-Time Recovery — restore database to any moment within retention period |
| **Read replica** | Read-only copy of database for offloading read traffic |
| **Replication lag** | Delay between write on primary and appearance on replica |
| **Sharding** | Horizontal partitioning of data across multiple database instances |
| **Connection pool** | Reusable set of database connections; avoids per-request connection overhead |
| **VACUUM** | PostgreSQL process to reclaim dead row space; prevents transaction ID wraparound |
| **WAL** | Write-Ahead Log — PostgreSQL's transaction log; used for replication and PITR |
| **Index** | Data structure that speeds up queries at the cost of write overhead |

---

## Observability

| Term | Definition |
|------|-----------|
| **Three pillars** | Metrics, Logs, Traces — the three signals of observability |
| **Metric** | Numeric measurement sampled over time (CPU %, request count, latency histogram) |
| **Log** | Timestamped record of a discrete event (structured JSON preferred) |
| **Trace** | Record of a request's path through distributed services; composed of spans |
| **Span** | Single unit of work within a trace; has start time, duration, and attributes |
| **RED method** | Rate + Errors + Duration — three key metrics for any service |
| **USE method** | Utilization + Saturation + Errors — three key metrics for any resource |
| **Cardinality** | Number of unique label combinations in a metric; high cardinality kills Prometheus |
| **Burn rate** | Rate at which error budget is being consumed (1.0 = sustainable, >1.0 = burning fast) |

---

## Migration

| Term | Definition |
|------|-----------|
| **6Rs** | Migration strategies: Retire, Retain, Rehost, Replatform, Repurchase, Refactor |
| **Lift & Shift** | Move workload to cloud without changes (Rehost) |
| **Strangler Fig** | Incrementally replace monolith by routing traffic to new services |
| **TCO** | Total Cost of Ownership — all costs over a period (hardware, staff, licenses, cloud) |
| **Wave plan** | Groups of applications migrated together based on dependencies and complexity |
| **CDC** | Change Data Capture — stream database changes in real time (Debezium, DMS) |

---

← [Previous: Linux Cheatsheet](../24-cheatsheets/linux.md) | [Home](../README.md) | [Next: Roadmaps →](../26-roadmaps/README.md)
