# Kubernetes Cluster Operations

This section is a checklist and command reference for cluster-level administration. Run destructive commands only in a disposable lab or during an explicitly planned maintenance window.

## Node maintenance

Inspect a node and its workloads:

```bash
kubectl get nodes -o wide
kubectl describe node <node>
kubectl get pods -A -o wide --field-selector spec.nodeName=<node>
```

Prevent new ordinary Pods from being scheduled:

```bash
kubectl cordon <node>
kubectl get nodes
```

Drain workloads before maintenance. Review PodDisruptionBudgets and workload controllers first. DaemonSet Pods are not deleted by a normal drain:

```bash
kubectl drain <node> --ignore-daemonsets
```

After maintenance, make the node schedulable again:

```bash
kubectl uncordon <node>
```

Do not casually add `--delete-emptydir-data` or `--force`. Understand what data and unmanaged Pods those flags may remove.

## Kubeadm cluster lifecycle

Use the exact upgrade procedure and package versions documented for the source and target Kubernetes minor versions. A typical upgrade includes:

1. Read the release notes and version-skew policy.
2. Back up etcd and important configuration.
3. Upgrade the control-plane components in the supported order.
4. Drain each worker node.
5. Upgrade kubelet and kubectl packages on that node.
6. Restart kubelet, uncordon the node, and verify workloads.
7. Repeat for remaining workers and confirm cluster health.

Official guide: https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/

## etcd backup and restore

An etcd snapshot is a critical recovery artifact. Store snapshots securely outside the cluster, protect access to them, and regularly test restores.

For kubeadm clusters, etcd is commonly secured with the API server's etcd CA and client certificate. Use the paths and endpoint from your cluster configuration.

Example snapshot command (adapt endpoint and certificate paths to your environment):

```bash
ETCDCTL_API=3 etcdctl snapshot save /secure-backup/etcd-snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key

etcdutl snapshot status /secure-backup/etcd-snapshot.db
```

Restore is a cluster-recovery operation, not a routine command. Follow the Kubernetes version-matched etcd documentation and your cluster's topology. Stop the affected etcd member(s), restore into a new data directory, update the static Pod or service configuration as required, then verify API server health. Never overwrite a live etcd data directory without a tested recovery plan.

Official guidance: https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/

## Certificates and kubeconfig

```bash
# Inspect certificate expiration on kubeadm clusters
sudo kubeadm certs check-expiration

# Inspect the current user's contexts
kubectl config get-contexts
kubectl config view --minify
```

Kubeconfig files can contain credentials. Do not commit real kubeconfig files, client private keys, tokens, or certificates to Git.

## Useful cluster-health checks

```bash
kubectl get nodes
kubectl get pods -A
kubectl get events -A --sort-by=.metadata.creationTimestamp
kubectl get --raw='/readyz?verbose'
kubectl get --raw='/livez?verbose'
```

The readiness and liveness endpoints require suitable API permissions. Some control-plane components run as static Pods, so inspect their manifests and logs on the control-plane host when the API is unavailable.

## Further reading

- https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/
- https://kubernetes.io/docs/tasks/administer-cluster/
- https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/
- https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/
