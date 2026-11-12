← [Previous: Kubernetes](./README.md) | [Home](../README.md) | [Next: Workloads →](./workloads.md)

---

# Kubernetes Architecture

---

## Control Plane

The control plane manages the overall cluster state. In managed Kubernetes (EKS, AKS, GKE) the control plane is operated by the cloud provider.

### kube-apiserver

The single entry point for all Kubernetes API calls. Every `kubectl` command, controller, and component communicates through the API server.

- Validates and processes REST requests
- Persists state to etcd
- Handles authentication, authorization (RBAC), and admission control
- Horizontally scalable — multiple replicas behind a load balancer in HA setups

### etcd

Distributed key-value store that holds the entire cluster state.

- Strongly consistent using the Raft consensus algorithm
- All objects (Pods, Services, ConfigMaps, etc.) are stored here
- **Critical**: losing etcd without a backup = losing the cluster — back up regularly
- Runs on control plane nodes (typically 3 or 5 for HA)

```bash
# etcd health (run on control plane node)
ETCDCTL_API=3 etcdctl endpoint health \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

### kube-scheduler

Watches for newly created Pods with no assigned node and selects the best node to run them on.

Scheduling decisions consider:
- Resource requests (CPU, memory) vs node capacity
- Node affinity / anti-affinity rules
- Taints and tolerations
- Pod topology spread constraints
- Node selectors and labels

### kube-controller-manager

Runs all built-in controller loops as a single binary. Each controller watches the API server and reconciles actual state toward desired state.

| Controller | Responsibility |
|------------|----------------|
| Deployment controller | Manages ReplicaSets |
| ReplicaSet controller | Ensures correct Pod count |
| Node controller | Marks nodes as unreachable, evicts Pods |
| Service Account controller | Creates default service accounts |
| Job controller | Runs Pods to completion |
| EndpointSlice controller | Populates service endpoints |

### cloud-controller-manager

Integrates with the cloud provider API for:
- Node lifecycle (provision/delete cloud VMs)
- Load balancer provisioning (for `Service type: LoadBalancer`)
- Volume provisioning (for StorageClass dynamic provisioning)

---

## Worker Node Components

### kubelet

The primary node agent — runs on every worker node.

- Watches the API server for Pods assigned to its node
- Ensures containers are running and healthy (using liveness/readiness probes)
- Reports node and Pod status back to the API server
- Manages container lifecycle via the CRI (Container Runtime Interface)

### kube-proxy

Maintains network rules on each node to implement Kubernetes Service abstractions.

- Uses iptables (default) or ipvs to route traffic to the correct Pod endpoints
- Handles ClusterIP, NodePort, and LoadBalancer traffic routing
- Does NOT proxy traffic itself — it programs kernel rules

### Container Runtime

Implements the CRI. Kubernetes delegates all container operations to the runtime.

| Runtime | Notes |
|---------|-------|
| containerd | Default for most distributions (EKS, GKE, k3s) |
| CRI-O | Lightweight, designed for Kubernetes |
| Docker Engine | No longer supported directly; uses containerd underneath |

---

## Pod Lifecycle

```
Pending → Running → Succeeded
                 └→ Failed
         (CrashLoopBackOff if container keeps failing)
```

| Phase | Meaning |
|-------|---------|
| Pending | Scheduled but containers not yet started (image pull, init containers) |
| Running | At least one container is running |
| Succeeded | All containers exited with code 0 (Jobs) |
| Failed | At least one container exited non-zero |
| Unknown | Node communication lost |

### Container States

Within a running Pod, each container has its own state:

| State | Meaning |
|-------|---------|
| Waiting | Not yet running (e.g., pulling image, init container pending) |
| Running | Executing |
| Terminated | Completed or crashed |

### Probes

```yaml
livenessProbe:         # Restart container if this fails
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:        # Remove from Service endpoints if this fails
  httpGet:
    path: /ready
    port: 8080
  periodSeconds: 5

startupProbe:          # Allow slow-starting containers time to initialize
  httpGet:
    path: /healthz
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
```

---

## Cluster Networking

Kubernetes networking model requirements:
1. Every Pod gets its own IP address
2. All Pods can communicate with each other without NAT
3. Nodes can communicate with all Pods without NAT

### CNI (Container Network Interface)

The CNI plugin implements the networking model. Chosen at cluster creation time.

| Plugin | Notes |
|--------|-------|
| Calico | BGP-based, supports NetworkPolicy, widely used |
| Flannel | Simple overlay, minimal features |
| Cilium | eBPF-based, advanced observability and NetworkPolicy |
| AWS VPC CNI | Assigns real VPC IPs to Pods (EKS default) |
| Azure CNI | Assigns real VNet IPs to Pods (AKS option) |
| Weave Net | Simple mesh, supports encryption |

### DNS

CoreDNS runs as a Deployment in the `kube-system` namespace and provides cluster-internal DNS.

```
# Pod DNS lookup pattern
<service>.<namespace>.svc.cluster.local

# Examples
my-svc.default.svc.cluster.local
redis.cache.svc.cluster.local
```

---

## Node Affinity and Taints

### Node Selector (simple)

```yaml
spec:
  nodeSelector:
    disktype: ssd
```

### Node Affinity (expressive)

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: topology.kubernetes.io/zone
            operator: In
            values: [us-east-1a, us-east-1b]
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
          - key: node-type
            operator: In
            values: [high-memory]
```

### Taints and Tolerations

Taints prevent Pods from being scheduled on nodes unless the Pod tolerates the taint.

```bash
# Taint a node (e.g., GPU-only node)
kubectl taint nodes gpu-node-1 dedicated=gpu:NoSchedule

# Pod toleration
spec:
  tolerations:
  - key: dedicated
    operator: Equal
    value: gpu
    effect: NoSchedule
```

| Effect | Behavior |
|--------|----------|
| NoSchedule | New Pods without toleration won't be scheduled |
| PreferNoSchedule | Scheduler avoids the node but not guaranteed |
| NoExecute | Existing Pods without toleration are evicted |

---

## Resource Model

```yaml
resources:
  requests:           # Guaranteed allocation (used by scheduler)
    cpu: "250m"       # 250 millicores = 0.25 CPU
    memory: "256Mi"
  limits:             # Maximum allowed
    cpu: "500m"
    memory: "512Mi"
```

- CPU is compressible — throttled if over limit
- Memory is not compressible — OOMKilled if over limit
- Always set requests; set limits carefully to avoid unnecessary throttling

---

← [Previous: Kubernetes](./README.md) | [Home](../README.md) | [Next: Workloads →](./workloads.md)
