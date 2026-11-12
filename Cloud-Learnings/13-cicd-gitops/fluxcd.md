← [Previous: ArgoCD](./argocd.md) | [Home](../README.md) | [Next: Deployment Strategies →](./deployment-strategies.md)

---

# FluxCD

FluxCD is a set of GitOps operators for Kubernetes. It uses CRDs (Custom Resource Definitions) to reconcile cluster state from Git repositories, Helm charts, and OCI artifacts.

---

## Flux Components

| Component | Description |
|-----------|-------------|
| **source-controller** | Fetches Git repos, Helm charts, OCI artifacts |
| **kustomize-controller** | Applies Kustomizations to the cluster |
| **helm-controller** | Manages HelmReleases |
| **notification-controller** | Sends alerts and receives webhooks |
| **image-reflector-controller** | Scans container registries for new image tags |
| **image-automation-controller** | Updates image tags in Git based on policy |

---

## Bootstrap

```bash
# Install Flux CLI
brew install fluxcd/tap/flux    # macOS
curl -s https://fluxcd.io/install.sh | sudo bash   # Linux

# Verify cluster prerequisites
flux check --pre

# Bootstrap with GitHub
export GITHUB_TOKEN=ghp_your_token
flux bootstrap github \
    --owner=my-org \
    --repository=my-app-gitops \
    --branch=main \
    --path=clusters/production \
    --personal   # use --personal for user repos, omit for org repos

# Bootstrap with GitLab
flux bootstrap gitlab \
    --owner=my-group \
    --repository=my-app-gitops \
    --branch=main \
    --path=clusters/production \
    --token-auth

# Bootstrap creates:
# - A 'flux-system' namespace with all controllers
# - A deploy key on the Git repo
# - A Kustomization pointing to clusters/production/
```

---

## Repository Structure

```
my-app-gitops/
├── clusters/
│   ├── production/
│   │   ├── flux-system/     ← Auto-managed by Flux bootstrap
│   │   │   ├── gotk-components.yaml
│   │   │   ├── gotk-sync.yaml
│   │   │   └── kustomization.yaml
│   │   └── apps.yaml        ← Kustomization pointing to apps/production/
│   └── staging/
│       └── apps.yaml
├── apps/
│   ├── base/
│   │   └── my-app/
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       └── kustomization.yaml
│   ├── production/
│   │   ├── my-app/
│   │   │   ├── kustomization.yaml
│   │   │   └── patch-replicas.yaml
│   │   └── kustomization.yaml
│   └── staging/
│       └── my-app/
│           ├── kustomization.yaml
│           └── patch-resources.yaml
└── infrastructure/
    ├── base/
    │   ├── ingress-nginx/
    │   └── cert-manager/
    └── production/
```

---

## GitRepository Source

```yaml
# infrastructure/sources/my-app-config.yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: my-app-config
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/my-org/my-app-config
  ref:
    branch: main
  secretRef:
    name: my-app-config-auth    # Kubernetes Secret with SSH key or token
```

---

## Kustomization

```yaml
# clusters/production/apps.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: apps-production
  namespace: flux-system
spec:
  interval: 5m
  timeout: 5m
  retryInterval: 2m

  sourceRef:
    kind: GitRepository
    name: flux-system

  path: ./apps/production

  prune: true            # Delete resources removed from Git
  wait: true             # Wait for health checks before marking ready

  postBuild:
    substituteFrom:
      - kind: ConfigMap
        name: cluster-vars         # Substitute ${VAR} in manifests
      - kind: Secret
        name: cluster-secrets

  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: my-app
      namespace: production
```

---

## HelmRelease

```yaml
# apps/production/ingress-nginx/helmrelease.yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: ingress-nginx
  namespace: ingress-nginx
spec:
  interval: 1h
  timeout: 10m
  releaseName: ingress-nginx
  targetNamespace: ingress-nginx
  createNamespace: true

  chart:
    spec:
      chart: ingress-nginx
      version: ">=4.10.0 <5.0.0"
      sourceRef:
        kind: HelmRepository
        name: ingress-nginx
        namespace: flux-system
      interval: 12h

  values:
    controller:
      replicaCount: 2
      resources:
        requests:
          cpu: 100m
          memory: 90Mi
      metrics:
        enabled: true

  install:
    remediation:
      retries: 3

  upgrade:
    remediation:
      retries: 3
      remediateLastFailure: true
    cleanupOnFail: true

  rollback:
    cleanupOnFail: true
```

```yaml
# HelmRepository source
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: ingress-nginx
  namespace: flux-system
spec:
  interval: 12h
  url: https://kubernetes.github.io/ingress-nginx
```

---

## Image Automation

```yaml
# Scan a container registry for new tags
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: my-app-api
  namespace: flux-system
spec:
  interval: 1m
  image: ghcr.io/my-org/my-app/api
  secretRef:
    name: ghcr-auth
---
# Policy: select the latest semver tag
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: my-app-api
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: my-app-api
  policy:
    semver:
      range: ">=1.0.0"
---
# Update the image tag in Git when a new tag matches the policy
apiVersion: image.toolkit.fluxcd.io/v1beta1
kind: ImageUpdateAutomation
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 5m
  sourceRef:
    kind: GitRepository
    name: my-app-config
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        email: fluxbot@my-org.com
        name: Flux Bot
      messageTemplate: |
        Auto-update image: {{ range .Updated.Images -}}
        {{ println . }}
        {{- end }}
    push:
      branch: main
  update:
    path: ./apps/production
    strategy: Setters
```

```yaml
# Deployment annotated for image-automation
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
        - name: api
          image: ghcr.io/my-org/my-app/api:1.2.3 # {"$imagepolicy": "flux-system:my-app-api"}
```

---

## Notifications

```yaml
# Send Slack alerts on reconciliation failures
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: slack-bot
  namespace: flux-system
spec:
  type: slack
  channel: "#deployments"
  secretRef:
    name: slack-bot-token
---
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: on-call-alert
  namespace: flux-system
spec:
  summary: "Production cluster reconciliation alert"
  providerRef:
    name: slack-bot
  eventSeverity: error
  eventSources:
    - kind: Kustomization
      name: '*'
      namespace: flux-system
    - kind: HelmRelease
      name: '*'
      namespace: flux-system
```

---

## CLI Operations

```bash
# Check Flux status
flux check
flux get all -A

# Get sources
flux get sources git -A
flux get sources helm -A

# Get kustomizations
flux get kustomizations -A

# Get HelmReleases
flux get helmreleases -A

# Force reconciliation
flux reconcile source git flux-system
flux reconcile kustomization apps-production
flux reconcile helmrelease ingress-nginx -n ingress-nginx

# Suspend/resume reconciliation
flux suspend kustomization apps-production
flux resume kustomization apps-production

# Export to YAML
flux export source git flux-system
flux export helmrelease ingress-nginx -n ingress-nginx

# Trace an image
flux trace image ghcr.io/my-org/my-app/api --namespace production
```

---

## References

- [FluxCD documentation](https://fluxcd.io/flux/)
- [Bootstrap guide](https://fluxcd.io/flux/installation/bootstrap/)
- [Image automation](https://fluxcd.io/flux/guides/image-update/)
- [Flux vs ArgoCD](https://fluxcd.io/blog/2022/11/flux-argocd-comparison/)

---

← [Previous: ArgoCD](./argocd.md) | [Home](../README.md) | [Next: Deployment Strategies →](./deployment-strategies.md)
