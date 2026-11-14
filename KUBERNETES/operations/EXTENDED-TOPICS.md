# Extended Kubernetes Topics

This guide adds practical entry points for topics that appear later in the CKA course and are not covered by the original beginner notes.

## 1. Helm

Helm packages Kubernetes manifests into versioned Charts and manages installed releases.

The repository contains a small sample Chart in [helm/nginx](../helm/nginx/).

```bash
# Install Helm using the official instructions for your OS:
# https://helm.sh/docs/intro/install/

helm lint helm/nginx
helm template demo-web helm/nginx
helm install demo-web helm/nginx --namespace demo --create-namespace
helm list -n demo
helm get values demo-web -n demo
helm upgrade demo-web helm/nginx --set replicaCount=3 -n demo
helm history demo-web -n demo
helm rollback demo-web 1 -n demo
helm uninstall demo-web -n demo
```

Use `helm template` before installation to inspect the rendered YAML. A release name is part of the resource identity; chart selectors should distinguish separate releases.

## 2. Kustomize

Kustomize overlays let you customize a shared set of plain YAML resources without templating.

The example in [kustomize/](../kustomize/) contains a base Deployment/Service and a development overlay.

```bash
kubectl kustomize kustomize/base
kubectl kustomize kustomize/overlays/dev
kubectl diff -k kustomize/overlays/dev
kubectl apply -k kustomize/overlays/dev
kubectl get all -n demo -l environment=development
kubectl delete -k kustomize/overlays/dev
```

Understand the difference between a base, an overlay, a strategic merge patch, and a JSON 6902 patch.

## 3. CustomResourceDefinitions and custom resources

A CRD extends the Kubernetes API with a new resource type. The repository includes a learning example:

- [Student CRD](../custom-resources/student-crd.yaml)
- [Student custom resource](../custom-resources/student.yaml)

Apply and inspect it:

```bash
kubectl apply -f custom-resources/student-crd.yaml
kubectl get crds students.learning.example.com
kubectl api-resources --api-group=learning.example.com
kubectl apply -f custom-resources/student.yaml
kubectl get students -n demo
kubectl describe student student-one -n demo
kubectl delete -f custom-resources/student.yaml
kubectl delete -f custom-resources/student-crd.yaml
```

A CRD defines and validates the API schema. It does not by itself run application logic.

## 4. Operators and controllers

An Operator combines a custom API (often a CRD) with one or more controllers that continuously reconcile actual state toward desired state.

Learn these terms:

- **Watch:** observe changes to Kubernetes objects.
- **Reconcile:** compare desired state with observed state and take corrective action.
- **Idempotency:** repeating reconciliation should converge on the same intended state.
- **Finalizer:** coordinate cleanup before an object is removed.
- **Status:** report observed state and conditions to the API.

A custom resource without a controller is stored and validated, but nothing automatically performs application-specific actions for it.

## 5. Gateway API

Gateway API is a family of resources for expressing network routing. The key objects are:

- **GatewayClass:** identifies the controller implementation and configuration class.
- **Gateway:** represents a listener and infrastructure entry point.
- **HTTPRoute:** attaches HTTP routing rules to a Gateway.
- **Parent reference:** connects a route to its parent Gateway.
- **Backend reference:** selects a Service and port as a route destination.

Gateway API CRDs and a compatible Gateway controller must be installed before these resources can become functional. The exact controller installation and GatewayClass settings are implementation-specific; use the controller's official documentation. Do not assume that installing the CRDs alone creates a working data plane.

Reference: https://gateway-api.sigs.k8s.io/

## 6. PriorityClass, LimitRange and ResourceQuota

Examples are available in [scheduling/](../scheduling/):

```bash
kubectl apply -f scheduling/priorityclass.yaml
kubectl apply -f scheduling/priority-pod.yaml
kubectl get pod high-priority-demo -n demo -o wide
kubectl describe pod high-priority-demo -n demo

kubectl apply -f scheduling/limitrange.yaml
kubectl apply -f scheduling/resourcequota.yaml
kubectl describe limitrange container-defaults -n demo
kubectl describe resourcequota demo-quota -n demo
```

PriorityClass is cluster-scoped. LimitRange and ResourceQuota are namespace-scoped. Preemption occurs only when the scheduler needs to make room and the relevant scheduling constraints permit it; a high priority does not guarantee immediate scheduling.

## 7. Pod Security Admission

The repository includes:

- [Namespace with restricted enforcement](../security/pod-security-namespace.yaml)
- [Pod satisfying restricted controls](../security/restricted-pod.yaml)

```bash
kubectl apply -f security/pod-security-namespace.yaml
kubectl apply -f security/restricted-pod.yaml
kubectl get pod restricted-pod -n secure-demo
```

Try a deliberately privileged Pod in the same namespace and inspect the admission rejection. Pod Security Standards are defined by Kubernetes; the Restricted profile is intentionally strict.

## 8. NetworkPolicy prerequisites

The examples in [networking/](../networking/) demonstrate default-deny ingress and a targeted allow rule.

```bash
kubectl apply -f networking/default-deny-ingress.yaml
kubectl apply -f networking/allow-frontend.yaml
kubectl get networkpolicies -n demo
```

NetworkPolicy enforcement requires a CNI implementation that supports NetworkPolicy. Creating a NetworkPolicy object on a cluster whose network plugin does not enforce it may have no effect. The allow rule requires client Pods labeled `role: frontend`.

## 9. Storage prerequisites

The [PVC example](../storage/pvc.yaml) uses dynamic provisioning by relying on the cluster's default StorageClass.

```bash
kubectl get storageclass
kubectl apply -f storage/pvc.yaml
kubectl get pvc -n demo
kubectl describe pvc web-data-pvc -n demo
kubectl apply -f storage/pvc-pod.yaml
kubectl logs pvc-consumer -n demo
```

A kind cluster may not have a default dynamic provisioner. Install and configure a compatible local provisioner or use a cluster with a default StorageClass before expecting the claim to bind. StatefulSet volumeClaimTemplates have the same requirement unless a matching StorageClass or suitable pre-created volumes exist.

## 10. Metrics and observability

```bash
kubectl top nodes
kubectl top pods -A
kubectl get events -A --sort-by=.metadata.creationTimestamp
kubectl get --raw='/readyz?verbose'
```

The resource metrics commands require metrics-server or another compatible metrics pipeline. Metrics-server is not a full logging, tracing, or long-term monitoring solution.

## Official references

- https://helm.sh/docs/
- https://kubectl.docs.kubernetes.io/references/kustomize/
- https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/
- https://kubernetes.io/docs/concepts/extend-kubernetes/operator/
- https://gateway-api.sigs.k8s.io/
- https://kubernetes.io/docs/concepts/security/pod-security-admission/
- https://kubernetes.io/docs/concepts/services-networking/network-policies/
