← [Previous: Helm](./helm.md) | [Home](../README.md) | [Next: Troubleshooting →](./troubleshooting.md)

---

# Kustomize

Kustomize is a template-free configuration customization tool built into `kubectl`. It lets you maintain a base configuration and layer environment-specific overrides without modifying the originals.

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| Base | Reusable, environment-agnostic manifests |
| Overlay | Environment-specific patches applied on top of a base |
| Patch | Modification to a resource (strategic merge or JSON 6902) |
| Generator | Produces ConfigMaps or Secrets from files or literals |
| Transformer | Modifies resources (labels, annotations, image tags) |
| Component | Reusable, opt-in feature module |

---

## Directory Structure

```
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
└── overlays/
    ├── staging/
    │   ├── kustomization.yaml
    │   └── deployment-patch.yaml
    └── prod/
        ├── kustomization.yaml
        ├── deployment-patch.yaml
        └── ingress.yaml
```

---

## Base

```yaml
# base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- deployment.yaml
- service.yaml
- hpa.yaml

commonLabels:
  app: my-app
  managed-by: kustomize

images:
- name: my-registry/my-app
  newTag: latest              # Overridden in overlays
```

```yaml
# base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-registry/my-app:latest
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
```

---

## Overlay

### Staging Overlay

```yaml
# overlays/staging/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: staging

resources:
- ../../base

namePrefix: staging-

images:
- name: my-registry/my-app
  newTag: "1.4.0-rc1"

patches:
- path: deployment-patch.yaml

configMapGenerator:
- name: app-config
  literals:
  - LOG_LEVEL=debug
  - APP_ENV=staging
```

```yaml
# overlays/staging/deployment-patch.yaml (Strategic Merge Patch)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app           # Must match the base resource name
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: app
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi
```

### Production Overlay

```yaml
# overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: production

resources:
- ../../base
- ingress.yaml

images:
- name: my-registry/my-app
  newTag: "1.4.0"

replicas:
- name: my-app
  count: 3

patches:
- path: deployment-patch.yaml

configMapGenerator:
- name: app-config
  literals:
  - LOG_LEVEL=info
  - APP_ENV=production
  options:
    disableNameSuffixHash: true   # Stable name (no content hash)

secretGenerator:
- name: db-secret
  envs:
  - secrets.env       # File with KEY=VALUE lines (not committed to git)
  options:
    disableNameSuffixHash: true
```

---

## Patch Types

### Strategic Merge Patch (default)

Merges with the base using Kubernetes-aware rules. Arrays are merged by key, not replaced.

```yaml
# Adds an env var to existing list
spec:
  template:
    spec:
      containers:
      - name: app
        env:
        - name: NEW_VAR
          value: "added"
```

### JSON 6902 Patch

Precise operations (add, remove, replace, move, copy, test).

```yaml
# overlays/prod/kustomization.yaml
patches:
- target:
    kind: Deployment
    name: my-app
  patch: |-
    - op: replace
      path: /spec/replicas
      value: 5
    - op: add
      path: /spec/template/spec/containers/0/env/-
      value:
        name: EXTRA_VAR
        value: "prod-value"
    - op: remove
      path: /spec/template/spec/containers/0/livenessProbe
```

---

## Generators

### ConfigMapGenerator

```yaml
configMapGenerator:
- name: app-config
  files:
  - config/app.properties       # File content as key
  - nginx.conf=config/nginx.conf  # Custom key name
  literals:
  - LOG_LEVEL=info
  - APP_PORT=8080
  options:
    disableNameSuffixHash: true
    labels:
      managed-by: kustomize
```

By default, Kustomize appends a content hash suffix to ConfigMap names (e.g., `app-config-9t6b8c`). This triggers rolling updates when config changes — a useful behavior. Use `disableNameSuffixHash: true` when you need a stable name.

### SecretGenerator

```yaml
secretGenerator:
- name: db-credentials
  type: Opaque
  literals:
  - username=myapp
  envs:
  - .secrets.env     # KEY=VALUE file
  files:
  - tls.crt
  - tls.key
```

> Never commit `.secrets.env` to Git. Use `.gitignore` and inject via CI.

---

## Transformers

```yaml
# Add labels to ALL resources
commonLabels:
  env: prod
  team: platform

# Add annotations to ALL resources
commonAnnotations:
  contact: platform@example.com

# Add namespace prefix to all resource names
namePrefix: prod-

# Set namespace for all resources
namespace: production

# Image tag replacement
images:
- name: my-registry/my-app
  newName: my-registry/my-app     # Optional rename
  newTag: "1.4.0"
  digest: sha256:abc123...         # Pin to digest (most secure)

# Replica count override
replicas:
- name: my-app
  count: 3
```

---

## Apply Kustomize

```bash
# Preview rendered output
kubectl kustomize overlays/prod

# Apply to cluster
kubectl apply -k overlays/prod

# Delete
kubectl delete -k overlays/prod

# With kustomize CLI (more options)
kustomize build overlays/prod | kubectl apply -f -
kustomize build overlays/prod | kubectl diff -f -
```

---

## Components

Reusable, opt-in feature modules that can be included in multiple overlays.

```yaml
# components/monitoring/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
- servicemonitor.yaml

patches:
- path: deployment-metrics-patch.yaml
```

```yaml
# overlays/prod/kustomization.yaml
resources:
- ../../base

components:
- ../../components/monitoring
- ../../components/autoscaling
```

---

## Kustomize vs Helm

| Aspect | Kustomize | Helm |
|--------|-----------|------|
| Templating | None — pure overlay patches | Go templates |
| Learning curve | Low | Medium |
| Reusability | Bases and components | Charts with values |
| Conditional logic | Limited (patches) | Full Go template logic |
| Versioning | Git-based | Chart versions in repos |
| Release management | None | `helm history`, rollback |
| GitOps (ArgoCD/Flux) | Native support | Native support |
| Best for | Simple env differences | Complex parameterized apps |

Many teams use both: Helm charts for third-party dependencies, Kustomize for their own app configs.

---

## ArgoCD Integration

ArgoCD natively supports Kustomize overlays.

```yaml
# ArgoCD Application pointing to a kustomize overlay
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app-prod
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/my-org/my-app.git
    targetRevision: main
    path: k8s/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

---

← [Previous: Helm](./helm.md) | [Home](../README.md) | [Next: Troubleshooting →](./troubleshooting.md)
