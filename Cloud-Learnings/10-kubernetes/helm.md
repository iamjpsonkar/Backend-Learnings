← [Previous: RBAC](./rbac.md) | [Home](../README.md) | [Next: Kustomize →](./kustomize.md)

---

# Helm

Helm is the package manager for Kubernetes. It bundles Kubernetes manifests into reusable, versioned packages called **charts**.

---

## Core Concepts

| Term | Definition |
|------|-----------|
| Chart | Package of Kubernetes manifests with templating |
| Release | A running instance of a chart in the cluster |
| Repository | Collection of charts (like a package registry) |
| Values | Configuration inputs to a chart |
| Template | Go-template YAML that renders to Kubernetes manifests |
| Hook | Chart lifecycle actions (pre-install, post-upgrade, etc.) |

---

## Installation

```bash
# macOS
brew install helm

# Linux
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify
helm version
```

---

## Chart Structure

```
my-chart/
├── Chart.yaml          # Chart metadata (name, version, description)
├── values.yaml         # Default values
├── values-prod.yaml    # Environment-specific overrides (convention)
├── templates/
│   ├── _helpers.tpl    # Named templates / helper functions
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── serviceaccount.yaml
│   ├── hpa.yaml
│   └── NOTES.txt       # Printed after install/upgrade
├── charts/             # Chart dependencies (subcharts)
└── .helmignore
```

### Chart.yaml

```yaml
apiVersion: v2
name: my-app
description: My application Helm chart
type: application     # application or library
version: "1.4.0"      # Chart version (semver)
appVersion: "2.1.3"   # App version (informational)
dependencies:
- name: postgresql
  version: "12.5.6"
  repository: https://charts.bitnami.com/bitnami
  condition: postgresql.enabled
```

### values.yaml

```yaml
replicaCount: 2

image:
  repository: my-registry/my-app
  tag: ""            # Defaults to Chart.appVersion if empty
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: false
  className: nginx
  host: app.example.com
  tls: false

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi

autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

postgresql:
  enabled: true
  auth:
    database: myapp
    existingSecret: db-secret
```

---

## Templates

### Deployment Template

```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "my-app.fullname" . }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "my-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "my-app.selectorLabels" . | nindent 8 }}
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - containerPort: 8080
        resources:
          {{- toYaml .Values.resources | nindent 10 }}
```

### _helpers.tpl

```
{{/* Expand the name of the chart */}}
{{- define "my-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Full name */}}
{{- define "my-app.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/* Common labels */}}
{{- define "my-app.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{ include "my-app.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "my-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "my-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
```

---

## Common Commands

### Repositories

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add cert-manager https://charts.jetstack.io
helm repo update               # Refresh all repo indexes
helm repo list
helm search repo nginx          # Search for charts
helm search repo bitnami/postgres --versions
```

### Install & Upgrade

```bash
# Install
helm install my-release ./my-chart \
  --namespace production \
  --create-namespace \
  --values values-prod.yaml \
  --set image.tag=1.3.0

# Upgrade
helm upgrade my-release ./my-chart \
  --namespace production \
  --values values-prod.yaml \
  --set image.tag=1.4.0

# Install or upgrade (idempotent)
helm upgrade --install my-release ./my-chart \
  --namespace production \
  --create-namespace \
  --values values-prod.yaml

# Dry-run (render templates without applying)
helm upgrade --install my-release ./my-chart \
  --dry-run --debug \
  --values values-prod.yaml
```

### Inspect & Debug

```bash
# List releases
helm list -n production
helm list --all-namespaces

# Show release status
helm status my-release -n production

# Show rendered templates
helm template my-release ./my-chart --values values-prod.yaml

# Show current values
helm get values my-release -n production
helm get values my-release -n production --all    # Includes defaults

# Show generated manifests applied to cluster
helm get manifest my-release -n production
```

### Rollback

```bash
helm history my-release -n production
helm rollback my-release 2 -n production    # Roll back to revision 2
helm rollback my-release 0                  # Roll back to previous revision
```

### Uninstall

```bash
helm uninstall my-release -n production
helm uninstall my-release -n production --keep-history    # Retain history
```

---

## Dependencies

```bash
# After editing Chart.yaml dependencies:
helm dependency update ./my-chart    # Downloads charts to charts/
helm dependency list ./my-chart
```

---

## Hooks

Hooks run Jobs at specific points in the release lifecycle.

```yaml
# templates/pre-upgrade-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate-{{ .Release.Revision }}
  annotations:
    "helm.sh/hook": pre-upgrade
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: migrate
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        command: ["python", "manage.py", "migrate"]
```

| Hook | When |
|------|------|
| pre-install | Before any resources are created |
| post-install | After all resources are created |
| pre-upgrade | Before upgrade |
| post-upgrade | After upgrade |
| pre-delete | Before uninstall |
| post-delete | After uninstall |
| pre-rollback | Before rollback |

---

## Create a Chart from Scratch

```bash
helm create my-app        # Scaffold a chart with boilerplate
helm lint ./my-app        # Validate chart syntax
helm package ./my-app     # Create my-app-0.1.0.tgz

# Push to OCI registry (Helm 3.8+)
helm push my-app-0.1.0.tgz oci://registry.example.com/charts
helm install my-release oci://registry.example.com/charts/my-app --version 0.1.0
```

---

## Helmfile

Declaratively manage multiple Helm releases.

```yaml
# helmfile.yaml
repositories:
- name: bitnami
  url: https://charts.bitnami.com/bitnami

releases:
- name: postgres
  namespace: data
  chart: bitnami/postgresql
  version: "12.5.6"
  values:
  - values/postgres.yaml

- name: my-app
  namespace: production
  chart: ./charts/my-app
  values:
  - values/my-app-prod.yaml
  needs:
  - data/postgres
```

```bash
helmfile sync           # Apply all releases
helmfile diff           # Show changes
helmfile destroy        # Remove all releases
```

---

← [Previous: RBAC](./rbac.md) | [Home](../README.md) | [Next: Kustomize →](./kustomize.md)
