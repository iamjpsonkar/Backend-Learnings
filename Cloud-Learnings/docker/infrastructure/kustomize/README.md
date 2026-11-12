# Kustomize — Environment Overlays

Kustomize patches for deploying to different environments without duplicating YAML.

---

## Structure

```
kustomize/
├── base/                   # Shared base resources
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
└── overlays/
    ├── dev/                # Dev: 1 replica, DEBUG logging, OTel enabled
    └── staging/            # Staging: 2 replicas, more CPU/memory
```

---

## Usage

```bash
# Prerequisites: kubectl + kustomize (or kubectl >= 1.14 which has kustomize built-in)

# Preview what will be applied
kubectl kustomize overlays/dev
kubectl kustomize overlays/staging

# Apply to cluster
kubectl apply -k overlays/dev
kubectl apply -k overlays/staging

# Tear down
kubectl delete -k overlays/dev
```

---

## How it works

1. `base/` defines the canonical resource definitions
2. `overlays/*/kustomization.yaml` declares which patches to apply
3. Patches use strategic merge — only override specified fields
4. `namePrefix` avoids name collisions between environments

---

## Adding a new environment

```bash
mkdir overlays/production
cp overlays/staging/kustomization.yaml overlays/production/
# Edit to set namePrefix: prod-, replicas: 3, etc.
```
