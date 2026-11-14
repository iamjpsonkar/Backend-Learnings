# Kubernetes Learning Path

A practical, hands-on Kubernetes learning space covering container orchestration fundamentals through CKA-oriented administration, operations, and troubleshooting.

The goal is to understand Kubernetes by building clusters, writing manifests, inspecting resources, intentionally breaking things, and fixing them.

## Learning sources

- **Primary course and hands-on assignments:** [CKA-2024 by Piyush Sachdeva](https://github.com/piyushsachdeva/CKA-2024/)
- **Course videos:** [40 Days of Kubernetes playlist](https://www.youtube.com/watch?v=6_gMoe7Ik8k&list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC)
- **Official Kubernetes documentation:** https://kubernetes.io/docs/
- **Official kubectl reference:** https://kubernetes.io/docs/reference/kubectl/
- **CKA curriculum:** https://github.com/cncf/curriculum

> Course note: the original Day 1–40 videos were recorded on older Kubernetes versions. The upstream CKA-2024 repository has newer notes for later curriculum topics and version-specific changes. Always verify commands against the Kubernetes version used by your lab and exam.

## How to study

For each topic:

1. Watch the corresponding lecture or read the official documentation.
2. Read the notes in this directory.
3. Create the resource using a YAML manifest where practical.
4. Apply it to your own cluster.
5. Inspect the resource with `kubectl get`, `kubectl describe`, and `kubectl get -o yaml`.
6. Test failure scenarios and troubleshoot them.
7. Complete the hands-on checklist before moving ahead.
8. Add your own observations, commands, and fixes to the notes.

Do not stop after a manifest returns `created` or `configured`. Verify that the workload is healthy and that the intended behavior actually works.

## Lab setup

Use one of the following local environments for learning:

| Tool | Best use | Documentation |
|---|---|---|
| kind | Lightweight multi-node Kubernetes clusters using containers | https://kind.sigs.k8s.io/docs/user/quick-start/ |
| Minikube | Local single-node or multi-node learning cluster | https://minikube.sigs.k8s.io/docs/start/ |
| kubeadm | Build and operate a cluster on Linux virtual machines | https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/ |

Install `kubectl` using the official guide: https://kubernetes.io/docs/tasks/tools/

### Recommended progression

- **Local cluster:** Start with kind or Minikube for Pods, Deployments, Services, configuration, scheduling, and application troubleshooting.
- **Multi-node lab:** Use kubeadm on Linux virtual machines for node operations, certificates, control-plane components, upgrades, etcd backup/restore, and cluster troubleshooting.
- **Version discipline:** Keep the client and server versions compatible. Pin lab node images rather than silently pulling `latest`.

## Topics and progress

The following checklist is a learning tracker. Mark a topic complete only after you have run and verified the hands-on exercise.

### 1. Foundations and architecture

- [ ] Containers, images, registries, and container runtimes
- [ ] Why orchestration is needed
- [ ] Kubernetes cluster, control plane, and worker nodes
- [ ] API server, scheduler, controller manager, and etcd
- [ ] kubelet, kube-proxy, CNI, CSI, and CRI
- [ ] Declarative desired state and reconciliation loops
- [ ] Kubernetes API objects, metadata, labels, selectors, and namespaces
- [ ] YAML syntax and manifest structure

### 2. Cluster installation and kubectl

- [ ] Install and configure kubectl
- [ ] Create and delete a kind cluster
- [ ] Create a multi-node kind cluster
- [ ] Start and inspect a Minikube cluster
- [ ] Read kubeconfig and contexts
- [ ] Switch contexts and namespaces safely
- [ ] Use imperative commands and declarative manifests
- [ ] Generate manifests with `kubectl create --dry-run=client -o yaml`
- [ ] Explain `apply` versus `create` and imperative versus declarative workflows

### 3. Workloads and controllers

- [ ] Pods: create, inspect, logs, exec, port-forward, delete
- [ ] Multi-container Pods and shared volumes
- [ ] Init containers and sidecar pattern
- [ ] Labels, selectors, and annotations
- [ ] ReplicationController and ReplicaSet
- [ ] Deployments, scaling, rollout status, history, pause, resume, rollback
- [ ] Rolling update strategy
- [ ] Namespaces and resource organization
- [ ] Jobs and CronJobs
- [ ] DaemonSets
- [ ] Static Pods
- [ ] StatefulSets and headless Services

### 4. Scheduling and resource management

- [ ] Scheduler workflow and scheduling phases
- [ ] Node selectors
- [ ] Node affinity and anti-affinity
- [ ] Pod affinity and anti-affinity
- [ ] Taints and tolerations
- [ ] Resource requests and limits
- [ ] Pod QoS classes
- [ ] LimitRange and ResourceQuota
- [ ] PriorityClass and preemption
- [ ] Manual scheduling and `nodeName`
- [ ] Topology spread constraints
- [ ] Horizontal Pod Autoscaler fundamentals

### 5. Services and networking

- [ ] Pod networking fundamentals
- [ ] ClusterIP Service
- [ ] NodePort Service
- [ ] LoadBalancer Service
- [ ] ExternalName Service and DNS CNAME behavior
- [ ] Service selectors and EndpointSlices
- [ ] CoreDNS and cluster DNS
- [ ] Container Network Interface (CNI)
- [ ] NetworkPolicy ingress and egress
- [ ] Ingress, IngressClass, and controller
- [ ] Gateway API: GatewayClass, Gateway, HTTPRoute
- [ ] Troubleshoot DNS, Services, endpoints, routes, and connectivity

### 6. Configuration and security

- [ ] Environment variables in Pods
- [ ] ConfigMaps
- [ ] Secrets and safe handling
- [ ] ServiceAccounts and projected tokens
- [ ] Authentication versus authorization
- [ ] kubeconfig users, clusters, and contexts
- [ ] RBAC: Role, RoleBinding, ClusterRole, ClusterRoleBinding
- [ ] TLS certificates and CertificateSigningRequest
- [ ] API server authentication and authorization flow
- [ ] SecurityContext, Linux capabilities, and user IDs
- [ ] Pod Security Standards and admission
- [ ] Admission controllers and admission webhooks

### 7. Storage

- [ ] Container filesystem and volume lifecycle
- [ ] emptyDir and hostPath
- [ ] PersistentVolume (PV)
- [ ] PersistentVolumeClaim (PVC)
- [ ] StorageClass
- [ ] Static and dynamic provisioning
- [ ] Access modes, volume modes, reclaim policies
- [ ] Volume binding modes
- [ ] StatefulSet volumeClaimTemplates
- [ ] Container Storage Interface (CSI) concepts
- [ ] Troubleshoot Pending PVCs and mount failures

### 8. Cluster maintenance and administration

- [ ] kubeadm cluster installation
- [ ] Control plane and worker node roles
- [ ] Drain, cordon, and uncordon nodes
- [ ] Cluster version upgrade
- [ ] etcd snapshot backup and restore
- [ ] Control-plane component configuration
- [ ] Certificates and certificate renewal
- [ ] Highly available control plane fundamentals
- [ ] Container runtime configuration and CRI
- [ ] Helm charts, releases, install, upgrade, rollback
- [ ] Kustomize bases, overlays, and patches
- [ ] CustomResourceDefinitions and custom resources
- [ ] Operator pattern and reconciliation

### 9. Observability and troubleshooting

- [ ] Pod lifecycle and common failure states
- [ ] Events, logs, and previous container logs
- [ ] Describe resources and inspect YAML
- [ ] Debug CrashLoopBackOff, ImagePullBackOff, Pending, OOMKilled
- [ ] Debug Services, selectors, EndpointSlices, and DNS
- [ ] Debug scheduling and resource pressure
- [ ] Debug node NotReady and kubelet issues
- [ ] Inspect control-plane components
- [ ] Understand metrics-server and resource metrics
- [ ] Application and node logging
- [ ] JSONPath and custom kubectl columns
- [ ] Shell pipelines and fast kubectl workflows

### 10. CKA practice

- [ ] Practice each domain with timed tasks
- [ ] Cluster Architecture, Installation & Configuration
- [ ] Workloads & Scheduling
- [ ] Services & Networking
- [ ] Storage
- [ ] Troubleshooting
- [ ] Practice on a clean cluster without relying on copied solutions
- [ ] Review the current official exam curriculum and allowed documentation

## Existing notes and manifests

| Path | Purpose |
|---|---|
| [README.md](README.md) | Beginner concepts, architecture, YAML, cluster setup, and command examples |
| [notes.md](notes.md) | Longer practical learning guide with explanations and examples |
| [Handson.md](Handson.md) | Minikube setup and first Deployment exercise |
| [deployment/](deployment/) | Deployment manifest |
| [kubectl_pod_creation/](kubectl_pod_creation/) | Pod manifest |
| [replication/](replication/) | ReplicationController and ReplicaSet manifests |
| [namespaces/](namespaces/) | Namespace manifest |
| [kind_cluster/](kind_cluster/) | Multi-node kind configuration |
| [services/](services/) | Service manifests and supporting Deployment |
| [assets/](assets/) | Architecture and concept diagrams |

## Useful kubectl command reference

```bash
# Cluster and context
kubectl cluster-info
kubectl get nodes -o wide
kubectl config get-contexts
kubectl config current-context
kubectl config use-context <context>

# Resources
kubectl get namespaces
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.metadata.creationTimestamp
kubectl get <resource> <name> -o yaml
kubectl describe <resource> <name>

# Workloads
kubectl apply -f manifest.yaml
kubectl diff -f manifest.yaml
kubectl rollout status deployment/<name>
kubectl rollout history deployment/<name>
kubectl rollout undo deployment/<name>
kubectl scale deployment/<name> --replicas=3

# Debugging
kubectl logs <pod>
kubectl logs <pod> --previous
kubectl exec -it <pod> -- sh
kubectl get endpointslices

# Cleanup
kubectl delete -f manifest.yaml
```

Replace placeholders before running commands. Be deliberate about the current context and namespace, especially before deleting or modifying resources.

## Completion standard

A topic is complete when you can:

- Explain what problem the Kubernetes feature solves.
- Create and inspect the resource without copying a finished manifest.
- Predict how it interacts with other resources.
- Diagnose at least one intentionally introduced failure.
- Explain the relevant trade-offs and limitations.

---

**Keep learning by building, testing, troubleshooting, and documenting.**
