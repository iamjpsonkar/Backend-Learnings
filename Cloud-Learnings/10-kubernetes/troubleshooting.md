← [Previous: Kustomize](./kustomize.md) | [Home](../README.md) | [Next: Terraform / OpenTofu (Batch 18) →](../11-terraform-opentofu/README.md)

---

# Kubernetes Troubleshooting

A systematic approach to diagnosing and fixing common Kubernetes issues.

---

## First Steps: Always Start Here

```bash
# 1. What is the cluster state?
kubectl get nodes
kubectl get pods --all-namespaces | grep -v Running | grep -v Completed

# 2. Recent events (sorted by time)
kubectl get events --sort-by='.lastTimestamp' -n <namespace>
kubectl get events --sort-by='.lastTimestamp' --all-namespaces | tail -30

# 3. Describe the failing resource
kubectl describe pod <pod-name> -n <namespace>
kubectl describe node <node-name>
```

---

## Pod Troubleshooting

### Pod States

| Status | Likely cause |
|--------|-------------|
| Pending | No node available, PVC unbound, resource quota exceeded |
| ImagePullBackOff | Image not found, registry auth failure |
| ErrImagePull | First pull attempt failed (before backoff) |
| CrashLoopBackOff | Container crashes on startup repeatedly |
| OOMKilled | Container exceeded memory limit |
| Error | Container exited with non-zero code |
| Terminating (stuck) | Finalizer blocking deletion, node unreachable |
| Evicted | Node was under memory/disk pressure |
| CreateContainerConfigError | Bad Secret/ConfigMap reference |
| InvalidImageName | Typo in image name |

---

### ImagePullBackOff

```bash
kubectl describe pod <pod> -n <ns>
# Look in Events for "Failed to pull image"

# Common causes:
# 1. Image tag doesn't exist
docker pull my-registry/my-app:missing-tag   # Test locally

# 2. Private registry — missing imagePullSecrets
kubectl get pod <pod> -o jsonpath='{.spec.imagePullSecrets}'

# 3. Wrong registry credentials
kubectl describe secret regcred -n <ns>
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com \
  --docker-username=user \
  --docker-password=token \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

### CrashLoopBackOff

Container keeps crashing. The kubelet backs off restarts exponentially (10s → 20s → 40s → ... → 5m).

```bash
# 1. Read the logs from the crash
kubectl logs <pod> -n <ns>                          # Current container
kubectl logs <pod> -n <ns> --previous              # Previous (crashed) container
kubectl logs <pod> -n <ns> -c <container>          # Specific container
kubectl logs <pod> -n <ns> --tail=100              # Last 100 lines

# 2. Describe for events
kubectl describe pod <pod> -n <ns> | grep -A 20 Events

# 3. Exec into a working version to test
kubectl debug <pod> -n <ns> --image=busybox -it --copy-to=debug-pod

# 4. Common root causes:
#   - Application startup error (check logs)
#   - Missing env var or Secret
#   - Liveness probe failing too early (increase initialDelaySeconds)
#   - Wrong command / entrypoint
#   - OOMKilled immediately
```

---

### OOMKilled

Container exceeded its memory limit and was killed.

```bash
kubectl describe pod <pod> -n <ns>
# Look for: Last State: Terminated  Reason: OOMKilled

# Check actual memory usage before killing
kubectl top pod <pod> -n <ns>
kubectl top pod <pod> -n <ns> --containers

# Fix: increase memory limit or find the memory leak
# In deployment spec:
resources:
  limits:
    memory: "512Mi"   # Increase from current value
```

---

### Pod Stuck in Pending

```bash
kubectl describe pod <pod> -n <ns>
# Look in Events section for scheduling failure

# Common causes and checks:
# 1. Insufficient resources
kubectl describe node <node> | grep -A 10 "Allocated resources"

# 2. No nodes match nodeSelector/affinity
kubectl get nodes --show-labels
kubectl describe pod <pod> | grep "Node-Selectors\|Affinity"

# 3. Taint not tolerated
kubectl describe nodes | grep Taints

# 4. PVC not bound
kubectl get pvc -n <ns>
kubectl describe pvc <pvc-name> -n <ns>

# 5. Resource quota exceeded
kubectl describe resourcequota -n <ns>
```

---

### Stuck Terminating Pod

```bash
# Caused by finalizers not completing or node unreachable

# Check finalizers
kubectl get pod <pod> -n <ns> -o jsonpath='{.metadata.finalizers}'

# Force delete (last resort — may cause orphaned resources)
kubectl delete pod <pod> -n <ns> --force --grace-period=0
```

---

## Node Troubleshooting

```bash
# Node status
kubectl get nodes -o wide
kubectl describe node <node-name>

# Node conditions to check
kubectl get node <node> -o jsonpath='{.status.conditions[*].type}'
# MemoryPressure, DiskPressure, PIDPressure, Ready

# Pods on the node
kubectl get pods --all-namespaces --field-selector spec.nodeName=<node>

# SSH into node (if accessible)
# Check kubelet
systemctl status kubelet
journalctl -u kubelet -f

# Check disk space (DiskPressure)
df -h
du -sh /var/lib/docker/*   # or /var/lib/containerd

# Drain node for maintenance
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
kubectl cordon <node>      # Stop new Pods being scheduled
kubectl uncordon <node>    # Re-enable scheduling
```

---

## Service & Networking Troubleshooting

```bash
# Service not reachable
kubectl get svc <svc> -n <ns>
kubectl describe svc <svc> -n <ns>

# Check endpoints — empty = no Pods match selector
kubectl get endpoints <svc> -n <ns>
# If empty: label selector mismatch between Service and Pods
kubectl get pods -n <ns> --show-labels
kubectl get svc <svc> -n <ns> -o jsonpath='{.spec.selector}'

# Test connectivity from inside the cluster
kubectl run debug --image=busybox --rm -it --restart=Never -- sh
# Inside pod:
wget -qO- http://my-svc.my-namespace.svc.cluster.local
nslookup my-svc.my-namespace

# Port-forward for direct local access
kubectl port-forward pod/<pod> 8080:8080 -n <ns>
kubectl port-forward svc/<svc> 8080:80 -n <ns>
kubectl port-forward deployment/<deploy> 8080:8080 -n <ns>

# Check kube-proxy
kubectl get pods -n kube-system | grep kube-proxy
kubectl logs -n kube-system kube-proxy-<id>

# Check CoreDNS
kubectl get pods -n kube-system | grep coredns
kubectl logs -n kube-system coredns-<id>
```

---

## Ingress Troubleshooting

```bash
# Check Ingress resource
kubectl describe ingress <name> -n <ns>

# Check ingress controller logs
kubectl logs -n ingress-nginx deploy/ingress-nginx-controller --tail=100

# Check if IngressClass is correct
kubectl get ingressclass

# Test from inside cluster
kubectl run debug --image=curlimages/curl --rm -it --restart=Never -- sh
curl -v http://my-svc -H "Host: app.example.com"

# Check TLS certificate
kubectl describe certificate <name> -n <ns>    # cert-manager
kubectl get certificaterequest -n <ns>
```

---

## Storage Troubleshooting

```bash
# PVC stuck in Pending
kubectl describe pvc <pvc> -n <ns>
# Look for: ProvisioningFailed, no StorageClass

# PV/PVC binding issues
kubectl get pv | grep <pvc-name>
kubectl describe pv <pv-name>

# Pod can't mount volume
kubectl describe pod <pod> -n <ns> | grep -A 20 Events
# Look for: FailedMount, FailedAttachVolume

# Multi-attach error (RWO volume attached to wrong node)
kubectl get volumeattachment
kubectl delete volumeattachment <va-name>   # Force detach (risky)
```

---

## RBAC Troubleshooting

```bash
# Forbidden error — test what a user/SA can do
kubectl auth can-i get pods --namespace=production --as=alice@example.com
kubectl auth can-i --list --namespace=production --as=alice@example.com

# Check SA used by a pod
kubectl get pod <pod> -o jsonpath='{.spec.serviceAccountName}' -n <ns>

# Audit logs for Forbidden
# grep apiserver audit log for "Forbidden" or "authorization.k8s.io"
```

---

## Resource & Performance Troubleshooting

```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n <ns>
kubectl top pods -n <ns> --containers

# Check resource quotas and limits
kubectl describe resourcequota -n <ns>
kubectl describe limitrange -n <ns>

# Find resource hogs
kubectl top pods --all-namespaces --sort-by=memory | head -20
kubectl top pods --all-namespaces --sort-by=cpu | head -20

# Check HPA status
kubectl describe hpa -n <ns>
# Look for: unable to fetch metrics, ScalingActive condition
```

---

## Useful Debug Commands

```bash
# Execute command in running Pod
kubectl exec -it <pod> -n <ns> -- bash
kubectl exec -it <pod> -n <ns> -c <container> -- sh

# Copy files to/from Pod
kubectl cp <pod>:/path/to/file ./local-file -n <ns>
kubectl cp ./local-file <pod>:/path/to/file -n <ns>

# Run a temporary debug Pod
kubectl run debug \
  --image=nicolaka/netshoot \    # Has dig, curl, tcpdump, etc.
  --rm -it \
  --restart=Never \
  -n <ns> \
  -- bash

# Debug a crashed Pod (ephemeral container, k8s 1.23+)
kubectl debug <pod> -n <ns> \
  -it \
  --image=busybox \
  --target=<container>

# Watch all events in real time
kubectl get events -n <ns> -w --sort-by='.lastTimestamp'

# Check API server availability
kubectl cluster-info
kubectl get componentstatuses    # Deprecated but still works in some versions

# Get raw API response
kubectl get pod <pod> -n <ns> -o json | jq .status

# Dump all resources in a namespace
kubectl get all -n <ns> -o yaml > namespace-dump.yaml
```

---

## Common Error Quick Reference

| Error message | First thing to check |
|--------------|---------------------|
| `ImagePullBackOff` | `kubectl describe pod` Events → image name / registry creds |
| `CrashLoopBackOff` | `kubectl logs --previous` → app startup error |
| `OOMKilled` | `kubectl top pod` → increase memory limit |
| `Pending` | `kubectl describe pod` → scheduling failure reason |
| `0/N nodes available` | Taints, affinity, resource exhaustion |
| `connection refused` | Service selector mismatch, app not listening on declared port |
| `no endpoints available` | `kubectl get endpoints` → all Pods failing readiness probe |
| `Forbidden` | `kubectl auth can-i` → RBAC binding missing |
| `FailedMount` | `kubectl describe pod` Events → PVC not bound, wrong access mode |
| `context deadline exceeded` | Network policy blocking, DNS failure, service mesh issue |

---

← [Previous: Kustomize](./kustomize.md) | [Home](../README.md) | [Next: Terraform / OpenTofu (Batch 18) →](../11-terraform-opentofu/README.md)
