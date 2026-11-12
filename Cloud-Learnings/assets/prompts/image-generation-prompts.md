# Image Generation Prompts

Prompts for generating diagram and illustration assets for Cloud-Learnings using AI image generation tools (DALL-E, Midjourney, Stable Diffusion, etc.).

## Usage Guidelines

- Generated images must be reviewed for accuracy before committing
- Save all generated images to the appropriate `assets/images/{provider}/{service}/` path
- Add an entry to `assets/ATTRIBUTIONS.md` noting the tool and date used
- Maximum file size: 500KB — run `./scripts/optimize-images.sh` if needed
- Prefer Mermaid diagrams in `assets/diagrams/mermaid/` over AI-generated images for architecture diagrams

---

## AWS Architecture Diagrams

### VPC Architecture

```
Create a clean, professional cloud architecture diagram showing an AWS VPC.
Include: Internet Gateway, two public subnets and two private subnets across
two Availability Zones, a NAT Gateway in the public subnet, an Application Load
Balancer spanning public subnets, EC2 instances in private subnets, and an RDS
Multi-AZ database in the data layer. Use the official AWS icon style with a white
background. Label each component clearly. Color code: yellow for public subnets,
blue for private subnets, orange for compute, purple for databases.
```

### EC2 Instance Hierarchy

```
Create a hierarchical diagram showing the relationship between AWS regions,
Availability Zones, VPCs, subnets, and EC2 instances. Show the containment
relationship: Region contains AZs, AZs contain subnets, subnets contain EC2
instances. Use clean flat design with AWS orange color palette. White background,
no drop shadows. Each level should be clearly labeled.
```

### S3 Storage Classes Comparison

```
Create an infographic comparing AWS S3 storage classes side by side.
Show 6 tiers: Standard, Intelligent-Tiering, Standard-IA, One Zone-IA,
Glacier Instant Retrieval, Glacier Deep Archive. For each tier display:
cost (bar chart), retrieval speed (icon), and primary use case (short label).
Use a horizontal layout. Color gradient from green (frequently accessed) to
blue (archived). Clean, minimal design with sans-serif font.
```

### IAM Policy Evaluation Flow

```
Create a flowchart showing how AWS IAM evaluates a permission request.
Steps: 1) Deny by default, 2) Check SCP (Organizations), 3) Check resource
policy, 4) Check identity policy, 5) Check permission boundaries, 6) Allow
or deny. Use red for deny paths, green for allow path. Include the explicit
deny override. Clean white background, professional style.
```

---

## Azure Architecture Diagrams

### Azure Resource Hierarchy

```
Create a diagram showing the Azure resource organization hierarchy.
Levels from top to bottom: Management Groups → Subscriptions → Resource Groups
→ Resources. Show that multiple subscriptions can belong to a management group
and multiple resource groups can exist per subscription. Use Azure blue color
scheme. Clean flat design, white background.
```

### Azure Networking Overview

```
Create a diagram showing Azure networking components: Virtual Network (VNet)
containing subnets, Network Security Groups attached to subnets and NICs,
an Azure Load Balancer in the frontend, VNet peering to another VNet, and
an Azure Firewall. Use Azure blue and teal color palette. Include clear labels
for each component.
```

---

## GCP Architecture Diagrams

### GCP Project Hierarchy

```
Create a hierarchy diagram showing GCP organization structure.
Levels: Organization → Folders → Projects → Resources (GCE, GKE, Cloud Storage,
BigQuery). Show that IAM policies are inherited down the hierarchy. Use Google
Cloud's color palette (blue, red, yellow, green). Clean flat design.
```

---

## Kubernetes Architecture Diagrams

### Kubernetes Cluster Architecture

```
Create a Kubernetes cluster architecture diagram showing:
Control Plane: API Server, etcd, Scheduler, Controller Manager.
Worker Nodes (2 shown): kubelet, kube-proxy, Container Runtime, Pods.
Show the connection between kubectl → API Server → Node components.
Show a Pod containing two containers sharing a network namespace.
Use official Kubernetes blue (#326CE5) color scheme. White background.
```

### Pod Networking

```
Create a diagram showing how Kubernetes pod networking works.
Show two nodes, each with pods. Show: pod-to-pod communication within a node
(via virtual ethernet bridge), pod-to-pod communication across nodes (via the
CNI overlay network), and pod-to-service communication (via kube-proxy/iptables).
Use clean colors with clear labels. Include IP addresses as examples (10.244.x.x range).
```

---

## General Cloud Concepts

### Shared Responsibility Model

```
Create a visual split showing the cloud shared responsibility model.
Left half labeled "Customer responsibility" in blue: data, applications,
identity, access management, OS configuration (for IaaS).
Right half labeled "Cloud provider responsibility" in orange: physical
hardware, data center facilities, hypervisor, network infrastructure.
Show the boundary line clearly. The customer responsibility portion grows
smaller as you move from IaaS to PaaS to SaaS (show 3 columns).
```

### Multi-AZ High Availability

```
Create a diagram illustrating multi-AZ high availability in a cloud environment.
Show an Active-Active setup with: a load balancer in front, two application
servers in two different availability zones, two database instances (primary
in AZ1, standby in AZ2) with synchronous replication. Show the failover
arrow when AZ1 fails. Use traffic flow arrows. Clean white background.
```

---

## Prompt Writing Tips

When writing new prompts for technical architecture diagrams:

1. **Specify exact components** — name every service or resource to be shown
2. **Specify layout** — horizontal, vertical, hierarchical, left-to-right
3. **Specify colors** — reference official brand colors or specific hex codes
4. **Specify labels** — ask for labeled components, not just visual shapes
5. **Specify background** — "white background" prevents gradient/dark outputs
6. **Specify style** — "flat design", "professional", "technical diagram" reduces artistic interpretation
7. **Add accuracy review** — always check generated output against official documentation
