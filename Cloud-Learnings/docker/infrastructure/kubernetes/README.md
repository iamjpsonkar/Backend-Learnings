# Kubernetes Manifests

Kubernetes manifests for the Cloud-Learnings Lab Platform.

## Prerequisites

```bash
# Create a cluster
./run.sh kubernetes create kind
# or
./run.sh kubernetes create k3d

# Verify
kubectl get nodes
```

## Apply All Manifests

```bash
kubectl apply -f infrastructure/kubernetes/
```

## Directories

- `pods/` — basic pod examples
- `deployments/` — deployment and rolling update examples
- `services/` — ClusterIP, NodePort, LoadBalancer examples
- `ingress/` — Ingress rules (requires ingress-nginx)
- `configmaps/` — ConfigMap examples
- `secrets/` — Secret examples (fake values)
- `volumes/` — PersistentVolume and PVC examples
