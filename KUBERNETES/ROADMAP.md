# Kubernetes Learning Path

This directory is a practical learning workspace for Kubernetes fundamentals, CKA-oriented administration, and production operations.

## Learning sources

- [CKA-2024 by Piyush Sachdeva](https://github.com/piyushsachdeva/CKA-2024/) — day-wise videos, notes, YAML and assignments.
- [40 Days of Kubernetes playlist](https://www.youtube.com/watch?v=6_gMoe7Ik8k&list=PLl4APkPHzsUUOkOv3i62UidrLmSB8DcGC)
- [Official Kubernetes documentation](https://kubernetes.io/docs/)
- [kubectl reference](https://kubernetes.io/docs/reference/kubectl/)
- [Official CKA curriculum](https://github.com/cncf/curriculum)

The upstream course videos for Days 1–40 were originally recorded on older Kubernetes versions. Use the updated upstream notes and official documentation to verify version-sensitive commands and APIs.

## Recommended learning workflow

For every topic:

1. Understand the problem the Kubernetes feature solves.
2. Watch the corresponding lecture and read the relevant notes.
3. Inspect the manifest and explain each important field.
4. Apply it to your own cluster.
5. Verify the resulting resources and application behavior.
6. Break one thing intentionally and troubleshoot it.
7. Clean up the resources you created.
8. Record the commands, observations, and mistakes you learned from.

A resource is not “done” just because `kubectl apply` succeeds. Verify readiness, endpoints, scheduling, events, logs, and the real application behavior.

## Lab environments

| Environment | Use it for | Reference |
|---|---|---|
| kind | Local single/multi-node cluster and everyday manifest practice | [kind quick start](https://kind.sigs.k8s.io/docs/user/quick-start/) |
| Minikube | Local Kubernetes with a convenient single-node starting point | [Minikube start](https://minikube.sigs.k8s.io/docs/start/) |
| kubeadm | Cluster installation and administration on Linux VMs | [kubeadm documentation](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/) |

Install kubectl using the [official tools guide](https://kubernetes.io/docs/tasks/tools/). Pin Kubernetes node images to an explicit version for reproducible labs.

### Create a kind cluster for the NodePort exercise

The provided [services/kind.yaml](services/kind.yaml) includes a host port mapping for NodePort 30001:

```bash
kind create cluster --name k8s-lab --config services/kind.yaml
kubectl cluster-info
kubectl get nodes -o wide
```

The separate [kind_cluster/kind-example-config.yaml](kind_cluster/kind-example-config.yaml) is a multi-node example without the NodePort host mapping. Use it for general cluster exercises, not the `localhost:30001` test.

## Topic checklist

Mark a box only after you can explain, implement, verify, and troubleshoot the concept independently.

### 1. Foundations and architecture

- [ ] Containers, images, registries, and runtimes
- [ ] Why container orchestration is needed
- [ ] Cluster, control plane, and worker nodes
- [ ] API server, scheduler, controller manager, etcd
- [ ] kubelet, kube-proxy, CRI, CNI, and CSI
- [ ] Declarative desired state and reconciliation
- [ ] Kubernetes API objects, metadata, labels, selectors
- [ ] YAML syntax, lists, maps, and manifest structure

### 2. Cluster installation and kubectl

- [ ] Install kubectl, kind, and/or Minikube
- [ ] Create, inspect, and delete local clusters
- [ ] Create a multi-node kind cluster
- [ ] kubeconfig, contexts, users, and clusters
- [ ] Safely switch contexts and namespaces
- [ ] Imperative versus declarative resource creation
- [ ] `kubectl apply`, `create`, `diff`, `explain`, and dry-run
- [ ] API discovery with `api-resources` and `api-versions`

### 3. Workloads and controllers

- [ ] Pods, container lifecycle, logs, exec, and port-forward
- [ ] Multi-container Pods, init containers, and sidecars
- [ ] Labels, selectors, and annotations
- [ ] ReplicationController and ReplicaSet
- [ ] Deployments, scaling, rolling updates, and rollback
- [ ] Namespaces
- [ ] Jobs and CronJobs
- [ ] DaemonSets and static Pods
- [ ] StatefulSets and headless Services

### 4. Scheduling and resource management

- [ ] Scheduler workflow and scheduling constraints
- [ ] nodeSelector and node affinity/anti-affinity
- [ ] Pod affinity and anti-affinity
- [ ] Taints, tolerations, and effects
- [ ] Resource requests and limits
- [ ] QoS classes, LimitRange, and ResourceQuota
- [ ] PriorityClass and preemption
- [ ] Manual scheduling and nodeName
- [ ] Topology spread constraints
- [ ] Horizontal Pod Autoscaler fundamentals

### 5. Services and networking

- [ ] Pod IP and cluster networking model
- [ ] ClusterIP, NodePort, LoadBalancer, ExternalName
- [ ] Service selectors and EndpointSlices
- [ ] CoreDNS and service discovery
- [ ] CNI plugins and NetworkPolicy
- [ ] Ingress, IngressClass, and controller
- [ ] Gateway API: GatewayClass, Gateway, HTTPRoute
- [ ] DNS, Service, endpoint, and connectivity troubleshooting

### 6. Configuration and security

- [ ] Environment variables and command/args
- [ ] ConfigMaps and Secrets
- [ ] ServiceAccounts and projected tokens
- [ ] Authentication versus authorization
- [ ] kubeconfig credentials and contexts
- [ ] RBAC: Role, RoleBinding, ClusterRole, ClusterRoleBinding
- [ ] TLS certificates and CertificateSigningRequest
- [ ] SecurityContext, Linux capabilities, and seccomp
- [ ] Pod Security Standards and admission
- [ ] Admission controllers, webhooks, and policies

### 7. Storage

- [ ] Container filesystem and ephemeral volumes
- [ ] emptyDir and hostPath
- [ ] PersistentVolume and PersistentVolumeClaim
- [ ] StorageClass and dynamic provisioning
- [ ] Access modes, volume modes, and reclaim policies
- [ ] Volume binding modes
- [ ] StatefulSet volumeClaimTemplates
- [ ] CSI concepts and storage troubleshooting

### 8. Cluster administration and maintenance

- [ ] kubeadm cluster setup
- [ ] Control-plane and worker-node components
- [ ] cordon, drain, and uncordon
- [ ] Kubernetes version upgrades
- [ ] etcd backup and restore
- [ ] Certificates and certificate renewal
- [ ] Container runtime and CRI troubleshooting
- [ ] Highly available control-plane architecture
- [ ] Helm charts and release lifecycle
- [ ] Kustomize bases, overlays, and patches
- [ ] CRDs, custom resources, and operators

### 9. Observability and troubleshooting

- [ ] Events, logs, metrics, and resource usage
- [ ] Pending, CrashLoopBackOff, ImagePullBackOff, OOMKilled
- [ ] Pod probes and container exit codes
- [ ] Scheduling and resource pressure
- [ ] Service selectors, EndpointSlices, DNS, and NetworkPolicy
- [ ] Node NotReady and kubelet issues
- [ ] Control-plane component troubleshooting
- [ ] JSONPath, custom columns, and kubectl output formats
- [ ] Timed troubleshooting drills

### 10. CKA practice

The CKA curriculum is organized around five domains. The weights may change; consult the current official curriculum before the exam.

- [ ] Cluster Architecture, Installation & Configuration
- [ ] Workloads & Scheduling
- [ ] Services & Networking
- [ ] Storage
- [ ] Troubleshooting

Practice from a clean cluster, work without copied solutions, and get comfortable with the official exam environment and allowed documentation.

## Repository map

| Path | What it contains |
|---|---|
| [README.md](README.md) | Original notes: Docker, Kubernetes architecture, YAML, kubectl, Pods, replication, Deployments and Services |
| [notes.md](notes.md) | Longer beginner Kubernetes learning guide |
| [Handson.md](Handson.md) | Guided local-cluster exercises and verification commands |
| [deployment/](deployment/) | Deployment example |
| [kubectl_pod_creation/](kubectl_pod_creation/) | Pod example |
| [replication/](replication/) | ReplicationController and ReplicaSet examples |
| [namespaces/](namespaces/) | Namespace example |
| [kind_cluster/](kind_cluster/) | Multi-node kind configuration |
| [services/](services/) | Service examples and kind NodePort configuration |
| [configuration/](configuration/) | ConfigMap and Secret exercises |
| [workloads/](workloads/) | Job, CronJob, DaemonSet and StatefulSet exercises |
| [scheduling/](scheduling/) | Requests/limits, node selection, affinity and tolerations |
| [security/](security/) | ServiceAccount, RBAC and Pod security examples |
| [networking/](networking/) | NetworkPolicy and Ingress examples |
| [storage/](storage/) | PVC and Pod volume exercises |
| [operations/](operations/) | Cluster maintenance, upgrades, etcd, administration and extended CKA topics |
| [custom-resources/](custom-resources/) | CRD and custom-resource example |
| [helm/](helm/) | Starter Helm chart |
| [kustomize/](kustomize/) | Base manifests and development overlay |
| [troubleshooting/](troubleshooting/) | Repeatable debugging workflow and fault drills |
| [assets/](assets/) | Architecture and concept diagrams |

## kubectl quick reference

```bash
# Context and cluster
kubectl config get-contexts
kubectl config current-context
kubectl config use-context <context>
kubectl cluster-info
kubectl get nodes -o wide

# Inspect resources
kubectl get all -A
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.metadata.creationTimestamp
kubectl get <resource> <name> -o yaml
kubectl describe <resource> <name>
kubectl explain pod.spec

# Apply and compare manifests
kubectl apply -f manifest.yaml
kubectl diff -f manifest.yaml
kubectl delete -f manifest.yaml

# Deployment operations
kubectl rollout status deployment/<name>
kubectl rollout history deployment/<name>
kubectl rollout undo deployment/<name>
kubectl scale deployment/<name> --replicas=3

# Debug a container
kubectl logs <pod>
kubectl logs <pod> --previous
kubectl exec -it <pod> -- sh
kubectl get endpointslices
```

Always confirm the current context and namespace before modifying or deleting resources. Replace placeholders before executing commands.

## Completion standard

You have completed a topic when you can:

- Explain the problem the feature solves and its limitations.
- Create the resource without copying a finished solution.
- Inspect the generated Kubernetes objects and their relationships.
- Verify actual runtime behavior.
- Introduce and diagnose at least one failure.
- Explain the commands and trade-offs to another engineer.
