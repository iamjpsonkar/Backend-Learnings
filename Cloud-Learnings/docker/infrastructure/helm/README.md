# Helm Charts

Sample Helm chart for deploying the cloud-learnings sample app to Kubernetes.

---

## Prerequisites

```bash
# Install Helm
brew install helm   # macOS
# or
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Create a local Kubernetes cluster
kind create cluster --name cloud-learnings
# or
k3d cluster create cloud-learnings
```

---

## Install the chart

```bash
# Dry run first
helm install sample-app ./cloud-learnings --dry-run --debug

# Install
helm install sample-app ./cloud-learnings \
  --set replicaCount=2 \
  --set env.LOG_LEVEL=DEBUG

# Install with custom values
helm install sample-app ./cloud-learnings -f my-values.yaml
```

---

## Upgrade

```bash
helm upgrade sample-app ./cloud-learnings --set image.tag=v2
```

---

## Uninstall

```bash
helm uninstall sample-app
```

---

## Chart contents

| Template | Purpose |
|---|---|
| deployment.yaml | App pods with security context |
| service.yaml | ClusterIP service |
| secret.yaml | Database URL (placeholder) |
| _helpers.tpl | Name/label helpers |

---

## Production notes

- Replace the Secret template with [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) or [External Secrets Operator](https://external-secrets.io/)
- Enable Ingress and set `ingress.enabled=true` with your ingress controller
- Set resource limits appropriate for your cluster
