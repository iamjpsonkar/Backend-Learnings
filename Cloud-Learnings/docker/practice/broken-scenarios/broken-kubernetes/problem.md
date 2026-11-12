# Broken Scenario: Kubernetes Pod CrashLoop

**Difficulty**: Advanced
**Profile**: Kubernetes (kind/k3d via run.sh)

---

## Scenario

A deployment was applied to the Kubernetes cluster but the pod is in `CrashLoopBackOff`. The team says it was working last week. Your job: find root cause and fix it.

---

## Setup

```bash
# Create local cluster if not already running
./run.sh kubernetes create

# Apply the broken deployment
kubectl apply -f practice/broken-scenarios/broken-kubernetes/broken-deploy.yaml

# Observe the crash loop
kubectl get pods -n cloud-learnings
kubectl describe pod -n cloud-learnings -l app=broken-app
```

---

## Broken manifest

Save this as `broken-deploy.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: broken-app
  namespace: cloud-learnings
spec:
  replicas: 1
  selector:
    matchLabels:
      app: broken-app
  template:
    metadata:
      labels:
        app: broken-app
    spec:
      containers:
        - name: broken-app
          image: nginx:alpine
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: password   # Bug: Secret does not exist
          readinessProbe:
            httpGet:
              path: /ready        # Bug: nginx does not have this path
              port: 80
            initialDelaySeconds: 1
            periodSeconds: 2
          resources:
            limits:
              memory: "32Mi"      # Bug: May be too low for nginx
              cpu: "10m"
```

---

## Constraints

- Fix the manifest, not the image
- All fixes must be in the YAML (no kubectl patch hacks)
- The fixed pod must pass readiness check

---

## Investigation commands

```bash
# Pod status and events
kubectl describe pod -n cloud-learnings -l app=broken-app

# Pod logs (even if crashing)
kubectl logs -n cloud-learnings -l app=broken-app --previous

# Events in namespace
kubectl get events -n cloud-learnings --sort-by='.lastTimestamp'

# Check if secrets exist
kubectl get secrets -n cloud-learnings
```

---

## How many bugs are there?

There are 3 bugs in the manifest. Find and fix all three.

---

## Solution validation

```bash
kubectl get pods -n cloud-learnings
# NAME                          READY   STATUS    RESTARTS   AGE
# broken-app-xxxxx-xxxxx        1/1     Running   0          30s

kubectl rollout status deployment/broken-app -n cloud-learnings
# deployment "broken-app" successfully rolled out
```
