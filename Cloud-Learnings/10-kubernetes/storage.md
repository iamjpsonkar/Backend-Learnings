← [Previous: ConfigMaps & Secrets](./configmaps-secrets.md) | [Home](../README.md) | [Next: RBAC →](./rbac.md)

---

# Kubernetes Storage

Kubernetes provides a pluggable storage system for persistent, shared, and ephemeral data.

---

## Storage Concepts

| Concept | What it is |
|---------|-----------|
| Volume | Storage attached to a Pod's lifecycle |
| PersistentVolume (PV) | Cluster-level storage resource (pre-provisioned or dynamic) |
| PersistentVolumeClaim (PVC) | Request for storage by a Pod or user |
| StorageClass | Dynamic provisioning profile (which plugin, which tier) |
| CSI Driver | Container Storage Interface plugin connecting k8s to a storage system |

---

## Volume Types (Pod-Scoped)

These volumes live and die with the Pod.

### emptyDir

Ephemeral scratch space shared between containers in the same Pod.

```yaml
volumes:
- name: cache
  emptyDir: {}

# Or use memory-backed (faster but counts against memory limits)
- name: fast-cache
  emptyDir:
    medium: Memory
    sizeLimit: 256Mi
```

### hostPath

Mounts a directory from the node filesystem. Use only for DaemonSets or trusted system workloads.

```yaml
volumes:
- name: docker-sock
  hostPath:
    path: /var/run/docker.sock
    type: Socket
```

### configMap / secret

Mount ConfigMap or Secret data as files (covered in configmaps-secrets.md).

### projected

Combine multiple volume sources (serviceAccountToken, ConfigMap, Secret, downwardAPI) into a single mount.

```yaml
volumes:
- name: app-config
  projected:
    sources:
    - configMap:
        name: app-config
    - secret:
        name: db-secret
    - serviceAccountToken:
        path: token
        expirationSeconds: 3600
```

---

## PersistentVolume (PV)

A PV is a piece of storage in the cluster provisioned by an admin or dynamically by a StorageClass.

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-postgres-data
spec:
  capacity:
    storage: 100Gi
  volumeMode: Filesystem
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain   # Retain | Delete | Recycle
  storageClassName: fast-ssd
  csi:
    driver: ebs.csi.aws.com
    volumeHandle: vol-0abc123def456789
    fsType: ext4
```

### Access Modes

| Mode | Abbreviation | Meaning |
|------|-------------|---------|
| ReadWriteOnce | RWO | One node can read and write |
| ReadOnlyMany | ROX | Many nodes can read |
| ReadWriteMany | RWX | Many nodes can read and write |
| ReadWriteOncePod | RWOP | Only one Pod can read and write (k8s 1.22+) |

Not all storage types support all access modes:
- EBS (AWS): RWO only
- EFS (AWS), NFS, CephFS: RWX supported
- Azure Disk: RWO only
- Azure Files, GCS Fuse: RWX supported

### Reclaim Policy

| Policy | Behavior when PVC deleted |
|--------|--------------------------|
| Retain | PV stays, data intact — manual cleanup required |
| Delete | PV and underlying storage deleted (default for dynamic) |
| Recycle | Deprecated — basic scrub then make available again |

---

## PersistentVolumeClaim (PVC)

A request for storage. Kubernetes binds it to a matching PV.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
  namespace: production
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
  storageClassName: fast-ssd
  volumeMode: Filesystem
```

```bash
kubectl get pvc -n production
# NAME            STATUS   VOLUME         CAPACITY   ACCESS MODES   STORAGECLASS
# postgres-data   Bound    pvc-abc123...  20Gi       RWO            fast-ssd
```

### Use PVC in a Pod

```yaml
spec:
  containers:
  - name: postgres
    volumeMounts:
    - name: data
      mountPath: /var/lib/postgresql/data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: postgres-data
```

---

## StorageClass

Defines how storage is dynamically provisioned.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"   # Default SC
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer    # Provision in same AZ as Pod
reclaimPolicy: Delete
allowVolumeExpansion: true
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
```

```bash
kubectl get storageclass
kubectl describe storageclass fast-ssd
```

### Common Provisioners

| Cloud | Provisioner | Storage types |
|-------|------------|--------------|
| AWS | ebs.csi.aws.com | gp2, gp3, io1, io2 |
| AWS | efs.csi.aws.com | EFS (RWX) |
| Azure | disk.csi.azure.com | Premium_LRS, Standard_SSD |
| Azure | file.csi.azure.com | Azure Files (RWX) |
| GCP | pd.csi.storage.gke.io | pd-standard, pd-ssd, pd-balanced |
| On-prem | rook.io/block | Ceph RBD |
| On-prem | nfs.csi.k8s.io | NFS |

---

## Volume Expansion

```yaml
# StorageClass must have allowVolumeExpansion: true
# Then edit the PVC:
spec:
  resources:
    requests:
      storage: 50Gi   # Increase from 20Gi
```

```bash
kubectl patch pvc postgres-data -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}'
# The PV expands online for supported drivers (no restart required for filesystem resize in most cases)
```

---

## StatefulSet Volume Claim Templates

StatefulSets use `volumeClaimTemplates` to create a dedicated PVC for each Pod.

```yaml
volumeClaimTemplates:
- metadata:
    name: data
  spec:
    accessModes: [ReadWriteOnce]
    storageClassName: fast-ssd
    resources:
      requests:
        storage: 20Gi
```

PVCs created: `data-postgres-0`, `data-postgres-1`, `data-postgres-2`
PVCs are NOT deleted when StatefulSet is deleted — protect against accidental data loss.

---

## Volume Snapshots

Kubernetes supports point-in-time snapshots via the `VolumeSnapshot` API (requires CSI driver support).

```yaml
# Take a snapshot
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-snapshot-2024-01
spec:
  volumeSnapshotClassName: csi-aws-vsc
  source:
    persistentVolumeClaimName: postgres-data

---
# Restore from snapshot
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data-restored
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 20Gi
  dataSource:
    name: postgres-snapshot-2024-01
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

---

## CSI Drivers

The Container Storage Interface (CSI) decouples Kubernetes from storage implementations. Drivers run as Pods in the cluster.

```bash
# List installed CSI drivers
kubectl get csidriver
kubectl get csistoragecapacities -A

# Verify EBS CSI driver (EKS example)
kubectl get pods -n kube-system -l app=ebs-csi-controller
```

### EBS CSI Driver (EKS)

```bash
helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::ACCOUNT:role/EBSCSIRole
```

---

## Storage Troubleshooting

```bash
# PVC stuck in Pending
kubectl describe pvc my-pvc
# Common causes:
#   - No matching PV (check storageClass, accessMode, size)
#   - WaitForFirstConsumer: Pod not scheduled yet
#   - StorageClass provisioner not installed

# Pod stuck due to volume
kubectl describe pod my-pod | grep -A 5 Events
# Look for: FailedMount, FailedAttachVolume

# Check PV binding
kubectl get pv | grep my-pvc

# Force-delete a stuck PVC (last resort — ensure no Pod is using it)
kubectl patch pvc my-pvc -p '{"metadata":{"finalizers":null}}'
```

---

← [Previous: ConfigMaps & Secrets](./configmaps-secrets.md) | [Home](../README.md) | [Next: RBAC →](./rbac.md)
