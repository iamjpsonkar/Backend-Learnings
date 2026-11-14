# Kubernetes Troubleshooting Playbook

Troubleshoot from the outside in: identify the failing object, inspect its events and state, check its owner/controller, then inspect scheduling, networking, storage, and node-level components.

## First-response commands

```bash
kubectl config current-context
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.metadata.creationTimestamp
kubectl get deployments,replicasets,statefulsets,daemonsets -A
```

Always check the context and namespace before running a mutating command.

## Pod failure states

| Symptom | Common causes | First checks |
|---|---|---|
| Pending | Unsatisfied requests, taints, affinity, PVC not bound | `kubectl describe pod`, events, PVC |
| ImagePullBackOff | Wrong image/tag, registry auth, network/DNS | Pod events, image reference, imagePullSecrets |
| CrashLoopBackOff | Process exits, bad config, failed probe | `kubectl logs`, `kubectl logs --previous`, describe |
| OOMKilled | Memory limit too low or leak | Last state, requests/limits, metrics |
| CreateContainerConfigError | Missing ConfigMap/Secret/key or invalid mount | Describe Pod, inspect referenced objects |
| ContainerCreating | Image pull, volume attach/mount, CNI | Events, PVC/PV, node conditions |

Useful commands:

```bash
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --previous
kubectl get pod <pod> -n <namespace> -o yaml
kubectl get events -n <namespace> --sort-by=.metadata.creationTimestamp
```

## Deployment and rollout failures

```bash
kubectl get deployment,replicaset,pods -n <namespace>
kubectl describe deployment <name> -n <namespace>
kubectl rollout status deployment/<name> -n <namespace>
kubectl rollout history deployment/<name> -n <namespace>
kubectl rollout undo deployment/<name> -n <namespace>
```

Check selector/template label consistency, image pull failures, readiness probes, resource limits, and rollout strategy.

## Service is not reachable

1. Confirm the Service exists and has the expected type and port.
2. Verify its selector matches the Pod labels.
3. Inspect EndpointSlices.
4. Test DNS and reachability from a Pod in the cluster.
5. Check NetworkPolicies and CNI behavior.

```bash
kubectl get svc <service> -n <namespace> -o yaml
kubectl get pods -n <namespace> --show-labels
kubectl get endpointslices -n <namespace> -l kubernetes.io/service-name=<service>
kubectl get networkpolicies -n <namespace>
kubectl run net-debug -n <namespace> --rm -it --restart=Never --image=busybox:1.36 -- sh
```

A Service with no endpoints commonly indicates a selector mismatch or no Ready backend Pods.

## DNS failure

From a temporary Pod:

```bash
nslookup kubernetes.default
nslookup <service>.<namespace>.svc.cluster.local
cat /etc/resolv.conf
```

Inspect CoreDNS:

```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl get svc -n kube-system kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns
```

Labels may differ by cluster distribution. Check actual labels before using selectors.

## PVC is Pending

```bash
kubectl get pvc,pv -A
kubectl describe pvc <claim> -n <namespace>
kubectl get storageclass
kubectl describe pod <pod> -n <namespace>
```

Check whether a default StorageClass exists, whether the provisioner is healthy, whether capacity and access modes are satisfiable, and whether topology constraints match.

## Node is NotReady

```bash
kubectl describe node <node>
kubectl get pods -A -o wide --field-selector spec.nodeName=<node>
```

On the node itself, inspect kubelet and container runtime health:

```bash
sudo systemctl status kubelet
sudo journalctl -u kubelet -n 100 --no-pager
sudo systemctl status containerd
sudo crictl info
```

The commands above require shell access to the affected Linux node.

## Practice drills

- [ ] Change a Pod image to a nonexistent tag and diagnose ImagePullBackOff.
- [ ] Break a Service selector and diagnose missing endpoints.
- [ ] Add an unsatisfied node selector and diagnose Pending.
- [ ] Configure a readiness probe against a wrong path and inspect rollout behavior.
- [ ] Reference a nonexistent ConfigMap and inspect events.
- [ ] Create a PVC with no matching provisioner and diagnose why it stays Pending.
- [ ] Apply a default-deny NetworkPolicy and restore only the required traffic.

Fix each scenario and verify the actual application behavior, not just the Pod status.
