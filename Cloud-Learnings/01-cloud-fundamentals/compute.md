← [Previous: Cloud Fundamentals](./README.md) | [Home](../README.md) | [Next: Storage →](./storage.md)

---

# Cloud Compute Fundamentals

## What Is Cloud Compute?

Compute is the processing power that runs your code. In the cloud, compute comes in several forms — from full virtual machines where you control the OS, to serverless functions where you only write code. Choosing the right compute type affects cost, performance, operational overhead, and how your team works.

---

## Compute Types

### Virtual Machines (VMs)

A virtual machine is a software emulation of a physical computer. It has its own OS, CPU allocation, memory, and storage.

**How it works:**

```
Physical Host
  └── Hypervisor (KVM, Xen, Hyper-V)
        ├── VM 1: Ubuntu 22.04 + your app
        ├── VM 2: Windows Server 2022 + IIS
        └── VM 3: Amazon Linux 2 + database
```

**You control:** The OS and everything above it. The hypervisor and physical hardware are managed by the cloud provider.

**Provider equivalents:**

| Provider | Service | Notes |
|---------|---------|-------|
| AWS | EC2 (Elastic Compute Cloud) | Broadest instance type catalog |
| Azure | Azure Virtual Machines | Strong Windows Server support |
| GCP | Google Compute Engine (GCE) | Per-second billing, live migration |
| Other | DigitalOcean Droplets, Hetzner Cloud | Simpler, cheaper for small workloads |

**Instance families (AWS EC2 naming pattern):**

| Family | Optimized for | Examples |
|--------|-------------|---------|
| General purpose | Balanced CPU/memory | t3, m6i, m7g |
| Compute optimized | High CPU ratio | c6i, c7g |
| Memory optimized | High memory ratio | r6i, x2iedn |
| Storage optimized | High I/O | i3, i4i |
| GPU | ML training, rendering | p4, g5 |
| ARM (Graviton) | Cost-efficient compute | t4g, m7g, c7g |

**When to use VMs:**
- Legacy applications that require a specific OS or kernel version
- Applications that need persistent local storage or GPU access
- Workloads requiring fine-grained OS and network configuration
- When you need to run software the cloud provider doesn't offer as a managed service

---

### Containers

Containers are lightweight, portable packages that include application code, runtime, libraries, and configuration — but share the host OS kernel.

**Container vs VM:**

```
VM:
  Hardware → Hypervisor → Guest OS → App
  (heavy: full OS per workload, seconds to start)

Container:
  Hardware → Host OS → Container Runtime → App
  (light: shared OS kernel, milliseconds to start)
```

**Container runtime:** Docker is the most common format. containerd and CRI-O are common in Kubernetes.

**Container registries (where images are stored):**

| Provider | Registry |
|---------|---------|
| AWS | ECR (Elastic Container Registry) |
| Azure | ACR (Azure Container Registry) |
| GCP | Artifact Registry |
| Public | Docker Hub, GitHub Container Registry |

**Container orchestration (running many containers at scale):**

| Tool | What it does |
|------|-------------|
| Docker Compose | Multi-container apps on a single host (dev/test) |
| Kubernetes (K8s) | Production container orchestration at scale |
| AWS ECS | AWS-native container orchestration (simpler than K8s) |
| AWS EKS | Managed Kubernetes on AWS |
| Azure AKS | Managed Kubernetes on Azure |
| GCP GKE | Managed Kubernetes on GCP (most mature) |

**When to use containers:**
- Microservices architecture
- When you need deployment portability across environments (dev → staging → prod)
- When you want faster startup than VMs
- Teams adopting DevOps and CI/CD practices

---

### Serverless (FaaS)

Functions-as-a-Service allows you to run individual functions in response to events without managing any server. The cloud provider handles all infrastructure, scaling, and availability.

```
Event (HTTP request, S3 upload, queue message)
       ↓
Cloud Provider: Spin up container, execute function
       ↓
Return result, container may stay warm or be destroyed
```

**Provider equivalents:**

| Provider | Service | Max timeout |
|---------|---------|------------|
| AWS | Lambda | 15 minutes |
| Azure | Azure Functions | 10 minutes (consumption plan) |
| GCP | Cloud Functions / Cloud Run | 60 minutes (Cloud Run) |
| Edge | Cloudflare Workers, Vercel | 30–50ms (strict) |

**When to use serverless:**
- Event-driven processing (file uploads, webhooks, queue consumers)
- APIs with highly variable or unpredictable traffic
- Scheduled jobs and cron tasks
- Glue code connecting services
- When idle cost is a concern (serverless scales to zero)

**Serverless limitations:**
- Cold start latency (first invocation after idle period is slower)
- Execution time limits
- No persistent in-memory state between invocations
- Harder to run long-running or stateful processes

---

### Managed Kubernetes

Kubernetes (K8s) is the de facto standard for container orchestration at scale. All major cloud providers offer a managed Kubernetes service that handles the control plane for you.

| Component | Self-managed K8s | Managed K8s (EKS/AKS/GKE) |
|-----------|-----------------|--------------------------|
| API server | You manage | Provider manages |
| etcd | You manage | Provider manages |
| Worker nodes | You manage | You manage (or use Fargate/virtual nodes) |
| Upgrades | You manage | Provider assists/automates |
| High availability | You configure | Provider configures control plane HA |

---

### Bare Metal

Physical servers dedicated entirely to your workload — no hypervisor overhead, no shared tenancy.

| Provider | Service |
|---------|---------|
| AWS | EC2 Bare Metal instances (e.g., `i3.metal`) |
| Azure | Azure Dedicated Hosts |
| GCP | Bare Metal Solution |

**When to use bare metal:**
- Compliance requirements that prohibit shared tenancy
- Applications that require hardware-level access (specific CPU features, SR-IOV networking)
- Database workloads sensitive to hypervisor overhead

---

## Choosing the Right Compute

```
Does the workload need a full OS with specific OS-level config?
  Yes → EC2 / Virtual Machine

Is the workload event-driven and short-lived (< 15 min)?
  Yes → Lambda / Serverless

Is the application already containerized?
  Yes → ECS (simple) or EKS/GKE/AKS (Kubernetes at scale)

Does the workload need GPU for ML?
  Yes → GPU instance (p4, g5 on AWS)

Is maximum performance with no virtualization overhead required?
  Yes → Bare Metal
```

---

## Key Compute Concepts

| Concept | Definition |
|---------|-----------|
| vCPU | Virtual CPU — a thread on a physical core |
| Instance type | A specific combination of vCPUs, RAM, network, storage |
| AMI / Image | A pre-built OS snapshot used to launch an instance |
| Spot / Preemptible | Spare capacity at discount; can be reclaimed |
| Auto Scaling | Automatically add/remove instances based on load |
| Load Balancer | Distributes traffic across multiple compute instances |
| Placement Group | Controls how instances are physically placed (close for low latency, spread for redundancy) |
| Elastic IP | A static public IP address that persists across instance stop/start |
| Dedicated Host | A physical server dedicated to your account |

---

## References

- [AWS EC2 instance types](https://aws.amazon.com/ec2/instance-types/)
- [AWS Lambda documentation](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [GCP Compute Engine overview](https://cloud.google.com/compute/docs/overview)
- [Azure VM sizes](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes)
- [Kubernetes concepts](https://kubernetes.io/docs/concepts/)
---

← [Previous: Cloud Fundamentals](./README.md) | [Home](../README.md) | [Next: Storage →](./storage.md)
