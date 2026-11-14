# Kubernetes Hands-on Lab

This file is a practical checklist for working through the Kubernetes notes and CKA topics in this directory.

## 1. Choose and inspect your cluster

Use either kind or Minikube for local exercises. Use kubeadm on Linux virtual machines for cluster administration exercises.

```bash
# kind
kind create cluster --name k8s-lab --config services/kind.yaml

# Verify
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -A
```

If you already have a cluster, do not create another one unnecessarily.

## 2. Practice safe kubectl basics

```bash
kubectl get namespaces
kubectl get nodes
kubectl get pods -A -o wide
kubectl get svc -A
kubectl get deployments -A
kubectl api-resources
kubectl explain pod.spec
kubectl config get-contexts
```

Before changing resources, confirm your current context:

```bash
kubectl config current-context
```

## 3. Create a namespace

```bash
kubectl apply -f namespaces/ns.yaml
kubectl get namespace demo
```

Create later exercises in the `demo` namespace by adding `-n demo` to kubectl commands or setting the namespace in the manifest.

## 4. Deploy an application

```bash
kubectl apply -n demo -f deployment/deploy.yaml
kubectl get deployment,pods -n demo -o wide
kubectl describe deployment nginx-deploy -n demo
kubectl rollout status deployment/nginx-deploy -n demo
```

Verify the deployment has three available replicas.

## 5. Practice Pods

The sample Pod manifest uses the default namespace. To keep this lab isolated, create it in the demo namespace:

```bash
kubectl apply -n demo -f kubectl_pod_creation/pod.yaml
kubectl get pods -n demo -o wide
kubectl describe pod nginx-pod -n demo
kubectl logs nginx-pod -n demo
kubectl exec -it nginx-pod -n demo -- sh
```

The Pod and Deployment examples both use nginx. They are separate exercises; do not confuse their lifecycle.

## 6. Practice replication controllers

The following examples create independently managed workloads. Apply one at a time, inspect the result, and clean it up before moving to the next example.

```bash
kubectl apply -n demo -f replication/rc.yaml
kubectl get rc,pods -n demo
kubectl scale rc/nginx-rc --replicas=5 -n demo
kubectl delete -n demo -f replication/rc.yaml

kubectl apply -n demo -f replication/rs.yaml
kubectl get rs,pods -n demo
kubectl scale rs/nginx-rs --replicas=5 -n demo
kubectl delete -n demo -f replication/rs.yaml
```

For new applications, prefer Deployments over creating a ReplicaSet directly. ReplicationController is a legacy API kept here for learning.

## 7. Practice Services

The service examples select Pods labeled `app: nginx-deploy`. Deploy the matching application first:

```bash
kubectl get pods -n demo --show-labels
```

Then apply one Service at a time:

```bash
kubectl apply -n demo -f services/clusterip.yaml
kubectl get svc,endpointslices -n demo
kubectl describe svc cluster-svc -n demo
```

Test it from a temporary in-cluster client:

```bash
kubectl run curl-client -n demo --image=curlimages/curl:8.12.1 --restart=Never --command -- sleep 3600
kubectl wait -n demo --for=condition=Ready pod/curl-client --timeout=90s
kubectl exec -n demo curl-client -- curl -sS http://cluster-svc
```

For NodePort, create the kind cluster using the port mapping in `services/kind.yaml` before creating the cluster. The NodePort Service exposes port 30001 on the node container; the kind port mapping forwards it to the host.

```bash
kubectl apply -n demo -f services/nodeport.yaml
kubectl get svc nodeport-svc -n demo
# When kind was created with the corresponding extraPortMapping:
curl http://localhost:30001
```

A LoadBalancer Service needs a load balancer implementation in a local cluster (for example, a supported MetalLB setup) or a cloud provider integration. It will commonly remain Pending without one.

ExternalName is a DNS alias (CNAME), not a proxy and not a selector-based Service. Test it using DNS lookup from a Pod; the hostname must exist and be reachable from your environment.

## 8. Debugging drill

For each workload, investigate these commands:

```bash
kubectl get pods -n demo -o wide
kubectl describe pod <pod-name> -n demo
kubectl logs <pod-name> -n demo
kubectl logs <pod-name> -n demo --previous
kubectl get events -n demo --sort-by=.metadata.creationTimestamp
kubectl get svc,endpointslices -n demo
```

Introduce one fault at a time (wrong image name, incorrect label selector, invalid container port, or too-high resource request), observe the failure, and fix it.

## 11. Configuration: ConfigMaps and Secrets

The example Pod mounts an HTML file from a ConfigMap and exposes ConfigMap/Secret keys as environment variables.

```bash
kubectl apply -f configuration/configmap.yaml
kubectl apply -f configuration/secret.yaml
kubectl apply -f configuration/configured-pod.yaml
kubectl get pod configured-nginx -n demo
kubectl exec configured-nginx -n demo -- printenv APP_ENV
kubectl exec configured-nginx -n demo -- printenv API_TOKEN
kubectl exec configured-nginx -n demo -- cat /usr/share/nginx/html/index.html
```

The Secret contains a placeholder demo value. Do not put real credentials in this repository. Base64 encoding is not encryption.

## 12. Workload controllers

Run Jobs and CronJobs independently and inspect the Pods they create:

```bash
kubectl apply -f workloads/job.yaml
kubectl get jobs,pods -n demo
kubectl logs job/pi-calculation -n demo

kubectl apply -f workloads/cronjob.yaml
kubectl get cronjobs -n demo
kubectl get jobs -n demo --watch
```

A CronJob runs on its schedule; wait for its next execution. DaemonSet and StatefulSet examples:

```bash
kubectl apply -f workloads/daemonset.yaml
kubectl get daemonset,pods -n demo -o wide

kubectl apply -f workloads/headless-service.yaml
kubectl apply -f workloads/statefulset.yaml
kubectl get statefulset,pods,pvc -n demo -o wide
```

StatefulSet PVCs require a suitable StorageClass or pre-created volumes. A local kind cluster may need a dynamic storage provisioner.

## 13. Scheduling and resource controls

For the node selector and required node-affinity examples, label at least one schedulable node:

```bash
kubectl get nodes
kubectl label node <node-name> disktype=ssd --overwrite
kubectl apply -f scheduling/node-selector-pod.yaml
kubectl apply -f scheduling/affinity-pod.yaml
kubectl get pods -n demo -o wide
```

For tolerations, taint a lab node, then schedule the tolerating Pod:

```bash
kubectl taint node <node-name> dedicated=cka:NoSchedule
kubectl apply -f scheduling/toleration-pod.yaml
kubectl describe pod toleration-demo -n demo
```

A toleration permits a Pod onto a matching tainted node; it does not force the Pod onto that node. Use a node selector or affinity rule too when you need that placement.

Apply resource controls and priority examples:

```bash
kubectl apply -f scheduling/resources-pod.yaml
kubectl apply -f scheduling/priorityclass.yaml
kubectl apply -f scheduling/priority-pod.yaml
kubectl apply -f scheduling/limitrange.yaml
kubectl apply -f scheduling/resourcequota.yaml
kubectl describe resourcequota demo-quota -n demo
```

## 14. RBAC and Pod Security

Create a ServiceAccount with read-only Pod permissions:

```bash
kubectl apply -f security/serviceaccount.yaml
kubectl apply -f security/role.yaml
kubectl apply -f security/rolebinding.yaml
kubectl auth can-i list pods --as=system:serviceaccount:demo:pod-reader -n demo
kubectl auth can-i delete pods --as=system:serviceaccount:demo:pod-reader -n demo
```

The first authorization check should be allowed and the second denied.

Apply the restricted Pod Security namespace and compliant Pod:

```bash
kubectl apply -f security/pod-security-namespace.yaml
kubectl apply -f security/restricted-pod.yaml
kubectl get pod restricted-pod -n secure-demo
```

## 15. NetworkPolicy

NetworkPolicy enforcement depends on the CNI plugin. Confirm your cluster's CNI supports it before testing.

```bash
kubectl apply -f networking/default-deny-ingress.yaml
kubectl apply -f networking/allow-frontend.yaml
kubectl run frontend-client -n demo --image=busybox:1.36 --labels=role=frontend --restart=Never --command -- sleep 3600
kubectl exec frontend-client -n demo -- wget -qO- http://cluster-svc
kubectl get networkpolicies -n demo
```

The allow policy permits ingress to the matching nginx Pods only from Pods labeled `role=frontend` on TCP port 80. NetworkPolicies are additive; inspect all policies selecting a Pod when debugging.

## 16. Storage, Ingress, Helm, Kustomize and CRDs

See [operations/EXTENDED-TOPICS.md](operations/EXTENDED-TOPICS.md) for prerequisites and step-by-step commands covering StorageClasses/PVCs, Gateway API, Helm, Kustomize, CRDs, operators, Pod Security and metrics.

Selected hands-on commands:

```bash
# Persistent storage (requires a default StorageClass / provisioner)
kubectl apply -f storage/pvc.yaml
kubectl apply -f storage/pvc-pod.yaml
kubectl get pvc,pods -n demo

# Kustomize
kubectl kustomize kustomize/overlays/dev
kubectl apply -k kustomize/overlays/dev

# Custom resource (CRD must be applied first)
kubectl apply -f custom-resources/student-crd.yaml
kubectl apply -f custom-resources/student.yaml
kubectl get students -n demo

# Helm
helm lint helm/nginx
helm template demo-web helm/nginx
```

An Ingress object requires an installed Ingress controller. A Gateway API resource requires Gateway API CRDs and a compatible controller. The manifest alone does not create a working data plane.

## 17. Cleanup

Run cleanup after completing the exercises you intend to keep. Confirm the active context first. These commands remove the lab resources in the `demo` and `secure-demo` namespaces.

```bash
kubectl config current-context

# Workloads and Services
kubectl delete -n demo -f services/clusterip.yaml --ignore-not-found
kubectl delete -n demo -f services/nodeport.yaml --ignore-not-found
kubectl delete -n demo -f services/lb.yaml --ignore-not-found
kubectl delete -n demo -f services/externalname.yaml --ignore-not-found
kubectl delete -n demo -f deployment/deploy.yaml --ignore-not-found
kubectl delete -n demo -f kubectl_pod_creation/pod.yaml --ignore-not-found
kubectl delete -n demo -f replication/rc.yaml --ignore-not-found
kubectl delete -n demo -f replication/rs.yaml --ignore-not-found
kubectl delete -n demo -f workloads/job.yaml --ignore-not-found
kubectl delete -n demo -f workloads/cronjob.yaml --ignore-not-found
kubectl delete -n demo -f workloads/daemonset.yaml --ignore-not-found
kubectl delete -n demo -f workloads/statefulset.yaml --ignore-not-found
kubectl delete -n demo -f workloads/headless-service.yaml --ignore-not-found

# Configuration, security, and networking
kubectl delete -n demo -f configuration/configured-pod.yaml --ignore-not-found
kubectl delete -n demo -f configuration/configmap.yaml --ignore-not-found
kubectl delete -n demo -f configuration/secret.yaml --ignore-not-found
kubectl delete -n demo -f security/rolebinding.yaml --ignore-not-found
kubectl delete -n demo -f security/role.yaml --ignore-not-found
kubectl delete -n demo -f security/serviceaccount.yaml --ignore-not-found
kubectl delete -n secure-demo -f security/restricted-pod.yaml --ignore-not-found
kubectl delete -f security/pod-security-namespace.yaml --ignore-not-found
kubectl delete -n demo -f networking/allow-frontend.yaml --ignore-not-found
kubectl delete -n demo -f networking/default-deny-ingress.yaml --ignore-not-found
kubectl delete -n demo -f networking/ingress.yaml --ignore-not-found

# Scheduling and storage
kubectl delete -n demo -f scheduling/resources-pod.yaml --ignore-not-found
kubectl delete -n demo -f scheduling/node-selector-pod.yaml --ignore-not-found
kubectl delete -n demo -f scheduling/affinity-pod.yaml --ignore-not-found
kubectl delete -n demo -f scheduling/toleration-pod.yaml --ignore-not-found
kubectl delete -n demo -f scheduling/priority-pod.yaml --ignore-not-found
kubectl delete -f scheduling/priorityclass.yaml --ignore-not-found
kubectl delete -n demo -f scheduling/limitrange.yaml --ignore-not-found
kubectl delete -n demo -f scheduling/resourcequota.yaml --ignore-not-found
kubectl delete -n demo -f storage/pvc-pod.yaml --ignore-not-found
kubectl delete -n demo -f storage/pvc.yaml --ignore-not-found

# Packaging and custom API
helm uninstall demo-web -n demo 2>/dev/null || true
kubectl delete -k kustomize/overlays/dev --ignore-not-found
kubectl delete -n demo -f custom-resources/student.yaml --ignore-not-found
kubectl delete -f custom-resources/student-crd.yaml --ignore-not-found
# Temporary client Pod
kubectl delete pod curl-client frontend-client -n demo --ignore-not-found

# Remove test node labels/taints (replace with the node you modified)
kubectl label node <node-name> disktype-
kubectl taint node <node-name> dedicated=cka:NoSchedule-

# Inspect remaining namespaced resources before deleting the lab namespace
kubectl get all -n demo
kubectl delete namespace demo
```

The placeholder `<node-name>` must be replaced with the actual node you labeled or tainted. The namespace deletion also deletes namespaced resources that may not appear in `kubectl get all`. Inspect PVC/PV reclaim behavior before deleting persistent data. Remove the kind cluster only when you no longer need it:

```bash
kind delete cluster --name k8s-lab
```


## 18. Continue through the full roadmap

Use [ROADMAP.md](ROADMAP.md) for the complete topic checklist and [notes.md](notes.md) for the detailed beginner concept guide. Follow the [CKA-2024 course](https://github.com/piyushsachdeva/CKA-2024/) for day-wise lectures, notes, and assignments.

Do not mark a topic complete until you can explain it, implement it, verify it, and troubleshoot it independently.
