← [Previous: Cloud Storage](./cloud-storage.md) | [Home](../../README.md) | [Next: GCP Databases →](../06-databases/README.md)

---

# Cloud Filestore

Cloud Filestore is a managed NFS file server. It provides a shared POSIX filesystem accessible from multiple GCE VMs and GKE nodes simultaneously. Use it for workloads that need shared file access (CMS, render farms, shared config).

---

## Filestore Tiers

| Tier | Capacity | IOPS | Use Case |
|------|---------|------|----------|
| **Basic HDD** | 1–63 TB | ~600/TB | Dev/test, less frequent access |
| **Basic SSD** | 2.5–63 TB | ~30K/TB | General file serving |
| **Zonal** | 1–9.75 TB | ~100K | High performance, zonal |
| **Regional** | 1–9.75 TB | ~100K | High performance, multi-zone HA |
| **Enterprise** | 1–10 TB | ~120K | Business-critical, HA |

---

## Creating a Filestore Instance

```bash
PROJECT="my-app-prod-123456"
ZONE="us-central1-a"
REGION="us-central1"

# Create a Basic SSD instance
gcloud filestore instances create nfs-my-app-prod \
    --project=$PROJECT \
    --zone=$ZONE \
    --tier=BASIC_SSD \
    --file-share=name=shared,capacity=2.5TB \
    --network=name=vpc-my-app-prod,reserved-ip-range=10.0.50.0/29

# Create a Regional (HA) instance
gcloud filestore instances create nfs-my-app-ha \
    --project=$PROJECT \
    --location=$REGION \
    --tier=REGIONAL \
    --file-share=name=shared,capacity=5TB \
    --network=name=vpc-my-app-prod,reserved-ip-range=10.0.51.0/29

# Get the NFS mount point IP
gcloud filestore instances describe nfs-my-app-prod \
    --project=$PROJECT \
    --zone=$ZONE \
    --format="json(networks[0].ipAddresses[0])"
```

---

## Mounting on Compute Engine VMs

```bash
# Install NFS client on Debian/Ubuntu
sudo apt-get install -y nfs-common

# Mount the Filestore share
NFS_IP="10.0.50.2"  # From instance describe above
sudo mkdir -p /mnt/shared
sudo mount -t nfs -o vers=3,nolock,proto=tcp $NFS_IP:/shared /mnt/shared

# Verify mount
df -h /mnt/shared
ls /mnt/shared

# Make permanent (persist across reboots)
echo "$NFS_IP:/shared /mnt/shared nfs vers=3,nolock,proto=tcp,_netdev 0 0" | sudo tee -a /etc/fstab

# Unmount
sudo umount /mnt/shared
```

---

## Mounting in GKE via PersistentVolume

```yaml
# filestore-pv.yaml — pre-provisioned static PV
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-filestore-shared
spec:
  capacity:
    storage: 2.5Ti
  accessModes:
    - ReadWriteMany  # Multiple pods can mount simultaneously
  nfs:
    path: /shared
    server: 10.0.50.2  # Filestore IP
  persistentVolumeReclaimPolicy: Retain
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-shared
  namespace: my-app
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  volumeName: pv-filestore-shared
```

```yaml
# Dynamic provisioning with Filestore CSI driver
# (gke-filestore-csi-driver addon must be enabled)
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: filestore-rwx
provisioner: filestore.csi.storage.gke.io
parameters:
  tier: standard
  network: vpc-my-app-prod
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-shared-dynamic
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: filestore-rwx
  resources:
    requests:
      storage: 1Ti
```

---

## Snapshots and Backups

```bash
# Create a snapshot (point-in-time copy)
gcloud filestore snapshots create snap-$(date +%Y%m%d) \
    --project=$PROJECT \
    --instance=nfs-my-app-prod \
    --instance-zone=$ZONE \
    --file-system=shared

# List snapshots
gcloud filestore snapshots list \
    --project=$PROJECT \
    --instance=nfs-my-app-prod \
    --instance-zone=$ZONE

# Restore a snapshot (creates new instance from snapshot)
gcloud filestore instances restore nfs-my-app-restored \
    --project=$PROJECT \
    --zone=$ZONE \
    --tier=BASIC_SSD \
    --source-snapshot=snap-20240615 \
    --source-snapshot-instance=nfs-my-app-prod \
    --source-snapshot-zone=$ZONE \
    --file-share=name=shared,capacity=2.5TB \
    --network=name=vpc-my-app-prod

# Create a backup to Cloud Storage
gcloud filestore backups create backup-$(date +%Y%m%d) \
    --project=$PROJECT \
    --region=$REGION \
    --instance=nfs-my-app-prod \
    --instance-zone=$ZONE \
    --file-system=shared
```

---

## Resizing

```bash
# Expand Filestore capacity (cannot shrink)
gcloud filestore instances update nfs-my-app-prod \
    --project=$PROJECT \
    --zone=$ZONE \
    --file-share=name=shared,capacity=5TB
```

---

## References

- [Cloud Filestore documentation](https://cloud.google.com/filestore/docs)
- [Filestore tiers](https://cloud.google.com/filestore/docs/service-tiers)
- [GKE Filestore CSI driver](https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/filestore-csi-driver)
- [Snapshots and backups](https://cloud.google.com/filestore/docs/snapshots)

---

← [Previous: Cloud Storage](./cloud-storage.md) | [Home](../../README.md) | [Next: GCP Databases →](../06-databases/README.md)
