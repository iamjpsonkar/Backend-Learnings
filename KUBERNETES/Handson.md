# Kubernetes Hands-on Lab

This file is a practical checklist for working through the Kubernetes notes and CKA topics in this directory.

## 1. Choose and inspect your cluster

Use either kind or Minikube for local exercises. Use kubeadm on Linux virtual machines for cluster administration exercises.

```bash
# kind
kind create cluster --name k8s-lab --config kind_cluster/kind-example-config.yaml

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
kubectl apply -n demo -f services/deploy.yaml
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

## 9. Cleanup

Delete only the resources created for this lab:

```bash
kubectl delete -n demo -f services/clusterip.yaml --ignore-not-found
kubectl delete -n demo -f services/nodeport.yaml --ignore-not-found
kubectl delete -n demo -f services/lb.yaml --ignore-not-found
kubectl delete -n demo -f services/externalname.yaml --ignore-not-found
kubectl delete -n demo -f services/deploy.yaml --ignore-not-found
kubectl delete -n demo -f deployment/deploy.yaml --ignore-not-found
kubectl delete -n demo -f replication/rc.yaml --ignore-not-found
kubectl delete -n demo -f replication/rs.yaml --ignore-not-found
kubectl delete -n demo -f kubectl_pod_creation/pod.yaml --ignore-not-found
kubectl delete pod curl-client -n demo --ignore-not-found
```

Delete the namespace only after verifying that it contains no resources you need:

```bash
kubectl get all -n demo
kubectl delete namespace demo
```

Delete a kind cluster only when you no longer need it:

```bash
kind delete cluster --name k8s-lab
```

## 10. Continue through the full roadmap

Use [README.md](README.md) for the full topic checklist and [notes.md](notes.md) for the detailed concept guide. Follow the [CKA-2024 course](https://github.com/piyushsachdeva/CKA-2024/) for day-wise lectures, notes, and assignments.

Do not mark a topic complete until you can explain it, implement it, verify it, and troubleshoot it independently.
