← [Previous: Container Registries](../09-containers/container-registries.md) | [Home](../README.md) | [Next: Architecture →](./architecture.md)

---

# Kubernetes

Kubernetes (K8s) is an open-source container orchestration platform that automates deployment, scaling, and management of containerized workloads. Originally developed by Google, it is now the de-facto standard for running containers in production.

---

## Why Kubernetes

| Need | Kubernetes solution |
|------|---------------------|
| Run containers across many nodes | Scheduling and placement |
| Zero-downtime deploys | Rolling updates, readiness probes |
| Self-healing | Restart failed pods, reschedule on node failure |
| Scale on demand | HorizontalPodAutoscaler, KEDA |
| Service discovery | DNS-based discovery, ClusterIP services |
| Secret management | Secrets API, external integrations |
| Multi-tenant isolation | Namespaces, RBAC, NetworkPolicy |

---

## High-Level Architecture

```
┌─────────────────────────────────────────────┐
│                Control Plane                │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐ │
│  │ API Server│  │ etcd     │  │Scheduler │ │
│  └───────────┘  └──────────┘  └──────────┘ │
│  ┌───────────────────────────────────────┐  │
│  │       Controller Manager             │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
         │               │
┌────────┴──┐      ┌─────┴─────┐
│  Node 1   │      │  Node 2   │
│ kubelet   │      │ kubelet   │
│ kube-proxy│      │ kube-proxy│
│ [Pods...] │      │ [Pods...] │
└───────────┘      └───────────┘
```

---

## Contents

| File | Topics |
|------|--------|
| [architecture.md](./architecture.md) | Control plane, nodes, Pod lifecycle, CNI |
| [workloads.md](./workloads.md) | Pod, Deployment, StatefulSet, DaemonSet, Job, CronJob |
| [services-ingress.md](./services-ingress.md) | ClusterIP, NodePort, LoadBalancer, Ingress, TLS |
| [configmaps-secrets.md](./configmaps-secrets.md) | ConfigMap, Secret, env injection, volume mounts |
| [storage.md](./storage.md) | PV, PVC, StorageClass, CSI, access modes |
| [rbac.md](./rbac.md) | Role, ClusterRole, Binding, ServiceAccount |
| [helm.md](./helm.md) | Charts, values, install/upgrade, repositories |
| [kustomize.md](./kustomize.md) | Bases, overlays, patches, generators |
| [troubleshooting.md](./troubleshooting.md) | Pod states, common errors, debug commands |

---

## Quick Reference

```bash
# Cluster info
kubectl cluster-info
kubectl get nodes -o wide
kubectl get all -n <namespace>

# Context management
kubectl config get-contexts
kubectl config use-context <context>
kubectl config set-context --current --namespace=<ns>

# Apply / delete
kubectl apply -f manifest.yaml
kubectl delete -f manifest.yaml
kubectl apply -k ./overlays/prod   # kustomize

# Watch resources
kubectl get pods -w
kubectl get events --sort-by='.lastTimestamp'
```

---

## Key Concepts at a Glance

| Concept | What it is |
|---------|-----------|
| Pod | Smallest deployable unit — one or more containers sharing network/storage |
| Node | Worker machine (VM or physical) running a kubelet |
| Namespace | Virtual cluster for resource isolation |
| Deployment | Declarative Pod management with rolling updates |
| Service | Stable network endpoint for a set of Pods |
| Ingress | HTTP/HTTPS routing rules into the cluster |
| ConfigMap | Non-sensitive configuration data |
| Secret | Sensitive data (base64-encoded, optionally encrypted at rest) |
| PersistentVolume | Cluster-level storage resource |
| RBAC | Role-Based Access Control — who can do what |
| Helm | Kubernetes package manager |
| Kustomize | Template-free configuration customization |

---

## Cloud-Managed Kubernetes

| Provider | Service | Notes |
|----------|---------|-------|
| AWS | EKS | Managed control plane, Fargate for serverless nodes |
| Azure | AKS | Integrated with Entra ID, Azure CNI |
| GCP | GKE | Autopilot mode, best-in-class autoscaling |
| DigitalOcean | DOKS | Simpler, cost-effective |
| On-prem | kubeadm, k3s, RKE2 | Self-managed |

---

← [Previous: Container Registries](../09-containers/container-registries.md) | [Home](../README.md) | [Next: Architecture →](./architecture.md)
