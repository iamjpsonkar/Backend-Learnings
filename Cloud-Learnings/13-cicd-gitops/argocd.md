← [Previous: Jenkins](./jenkins.md) | [Home](../README.md) | [Next: FluxCD →](./fluxcd.md)

---

# ArgoCD

ArgoCD is a declarative GitOps continuous delivery tool for Kubernetes. It pulls desired state from Git and continuously reconciles the cluster to match.

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Application** | A Kubernetes app defined by a Git source + destination cluster/namespace |
| **Project** | Group of applications with shared RBAC and resource quotas |
| **Sync** | Apply Git state to the cluster |
| **Health** | ArgoCD checks if deployed resources are healthy |
| **App-of-Apps** | An Application whose manifests define other Applications |
| **Sync Policy** | Automated or manual sync; prune/self-heal options |
| **Wave** | Sync phase ordering within an application |

---

## Installation

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd \
    -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Install CLI
brew install argocd                          # macOS
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd && sudo mv argocd /usr/local/bin/

# Port-forward UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get initial admin password
argocd admin initial-password -n argocd

# Login
argocd login localhost:8080 --username admin --insecure
```

---

## Application Manifest

```yaml
# apps/my-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io  # Cascade-deletes resources on app deletion
  annotations:
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: deployments
    notifications.argoproj.io/subscribe.on-sync-failed.slack: alerts
spec:
  project: production

  source:
    repoURL: https://github.com/my-org/my-app-config.git
    targetRevision: main
    path: kubernetes/production/my-app

  destination:
    server: https://kubernetes.default.svc   # In-cluster
    namespace: production

  syncPolicy:
    automated:
      prune: true          # Delete resources removed from Git
      selfHeal: true       # Revert manual changes to cluster
      allowEmpty: false    # Don't sync if Git yields zero resources
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - ApplyOutOfSyncOnly=true   # Only apply changed resources
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas   # Ignore HPA-managed replica count
    - group: ""
      kind: ConfigMap
      name: my-app-config
      jsonPointers:
        - /data/LAST_UPDATED
```

---

## App-of-Apps Pattern

The App-of-Apps pattern uses a parent ArgoCD Application that manages child Application manifests.

```
git-repo/
└── apps/
    ├── root.yaml          ← ArgoCD Application pointing to apps/
    ├── my-app.yaml
    ├── my-worker.yaml
    └── my-scheduler.yaml
```

```yaml
# apps/root.yaml — the "app of apps"
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root
  namespace: argocd
spec:
  project: production
  source:
    repoURL: https://github.com/my-org/my-app-config.git
    targetRevision: main
    path: apps
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

```bash
# Bootstrap: apply the root app once
kubectl apply -f apps/root.yaml
# From now on, adding files to apps/ creates new ArgoCD applications automatically
```

---

## AppProject — RBAC and Resource Limits

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  description: Production workloads

  sourceRepos:
    - 'https://github.com/my-org/*'
    - 'https://charts.bitnami.com/bitnami'

  destinations:
    - namespace: production
      server: https://kubernetes.default.svc
    - namespace: monitoring
      server: https://kubernetes.default.svc

  # Whitelist allowed Kubernetes resource types
  clusterResourceWhitelist:
    - group: ''
      kind: Namespace
    - group: 'rbac.authorization.k8s.io'
      kind: ClusterRole

  namespaceResourceWhitelist:
    - group: '*'
      kind: '*'

  # Block dangerous operations
  namespaceResourceBlacklist:
    - group: ''
      kind: ResourceQuota

  roles:
    - name: developer
      description: Can sync but not delete
      policies:
        - p, proj:production:developer, applications, get, production/*, allow
        - p, proj:production:developer, applications, sync, production/*, allow
      groups:
        - my-org:developers

    - name: admin
      description: Full access
      policies:
        - p, proj:production:admin, applications, *, production/*, allow
      groups:
        - my-org:platform-engineers
```

---

## Sync Waves and Phases

```yaml
# Apply resources in order using sync-wave annotation
# Lower wave number = applied first; all resources in a wave must be healthy before next wave

# Wave 0: Namespace and RBAC
apiVersion: v1
kind: Namespace
metadata:
  name: production
  annotations:
    argocd.argoproj.io/sync-wave: "0"
---
# Wave 1: Secrets and ConfigMaps
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-app-config
  namespace: production
  annotations:
    argocd.argoproj.io/sync-wave: "1"
---
# Wave 2: Database migrations (Job)
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  namespace: production
  annotations:
    argocd.argoproj.io/sync-wave: "2"
    argocd.argoproj.io/hook: Sync          # Run as sync hook
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
---
# Wave 3: Application Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: production
  annotations:
    argocd.argoproj.io/sync-wave: "3"
```

---

## CLI Operations

```bash
# Add a Git repository
argocd repo add https://github.com/my-org/my-app-config.git \
    --ssh-private-key-path ~/.ssh/argocd-deploy-key

# Create an application
argocd app create my-app \
    --repo https://github.com/my-org/my-app-config.git \
    --path kubernetes/production/my-app \
    --dest-server https://kubernetes.default.svc \
    --dest-namespace production \
    --sync-policy automated \
    --auto-prune \
    --self-heal

# Sync an application
argocd app sync my-app

# Sync with rollout wait
argocd app sync my-app --timeout 300 --health

# List applications
argocd app list

# Check application status
argocd app get my-app

# View diff (what will change on next sync)
argocd app diff my-app

# Rollback to a previous revision
argocd app rollback my-app --revision 15

# Delete application (cascade-deletes all Kubernetes resources)
argocd app delete my-app --cascade

# Register an external cluster
argocd cluster add prod-cluster-context
argocd cluster list
```

---

## Image Updater (Automated Image Tag Updates)

```yaml
# Automatically update Deployment image when a new tag is pushed
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  annotations:
    argocd-image-updater.argoproj.io/image-list: api=my-registry/my-app/api
    argocd-image-updater.argoproj.io/api.tag-semver: ">=1.0.0"
    argocd-image-updater.argoproj.io/api.update-strategy: semver
    argocd-image-updater.argoproj.io/write-back-method: git
    argocd-image-updater.argoproj.io/git-branch: main
```

---

## References

- [ArgoCD documentation](https://argo-cd.readthedocs.io/)
- [App-of-apps pattern](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/)
- [Sync waves and hooks](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)
- [ArgoCD Image Updater](https://argocd-image-updater.readthedocs.io/)

---

← [Previous: Jenkins](./jenkins.md) | [Home](../README.md) | [Next: FluxCD →](./fluxcd.md)
