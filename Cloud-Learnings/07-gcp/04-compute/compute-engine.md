← [Previous: GCP Compute](./README.md) | [Home](../../README.md) | [Next: Managed Instance Groups →](./managed-instance-groups.md)

---

# Compute Engine

Compute Engine is GCP's IaaS VM service. It offers predefined and custom machine types, Spot VMs, confidential computing, and tight integration with IAM and GCP networking.

---

## Machine Type Families

| Family | Series | Characteristics | Use Case |
|--------|--------|----------------|----------|
| **General Purpose** | E2, N2, N2D, N4 | Balanced CPU/memory | Web, app servers |
| **Compute-Optimized** | C2, C3 | High clock speed | HPC, game servers |
| **Memory-Optimized** | M1, M2, M3 | Up to 12 TB RAM | In-memory databases |
| **Accelerator-Optimized** | A2, A3, G2 | NVIDIA GPUs | ML training/inference |
| **Storage-Optimized** | Z3 | Local NVMe SSDs | Storage-intensive databases |

```bash
# List machine types in a zone
gcloud compute machine-types list \
    --filter="zone=us-central1-a AND name~'^n2-standard'" \
    --format="table(name,guestCpus,memoryMb)"

# Custom machine type: 6 vCPUs, 20 GB RAM
# --machine-type=custom-6-20480

# Extended memory (up to 8x RAM)
# --machine-type=n2-custom-4-32768-ext
```

---

## Creating a VM (Production Best Practices)

```bash
PROJECT="my-app-prod-123456"
ZONE="us-central1-a"
SA_EMAIL="sa-my-app@$PROJECT.iam.gserviceaccount.com"

# Production VM — no public IP, IAP SSH, shielded VM, service account attached
gcloud compute instances create vm-my-app-prod-001 \
    --project=$PROJECT \
    --zone=$ZONE \
    --machine-type=n2-standard-4 \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --boot-disk-size=50GB \
    --boot-disk-type=pd-ssd \
    --no-address \                            # No external IP
    --subnet=subnet-app-us-central1 \
    --network=vpc-my-app-prod \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform \
    --shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --metadata=enable-oslogin=TRUE \          # OS Login for centralized SSH auth
    --tags=allow-iap,backend \               # Network tags for firewall rules
    --labels=environment=production,service=my-app,team=platform \
    --deletion-protection                     # Prevent accidental deletion

# SSH via IAP (no need for bastion or public IP)
gcloud compute ssh vm-my-app-prod-001 \
    --project=$PROJECT \
    --zone=$ZONE \
    --tunnel-through-iap

# RDP via IAP (for Windows VMs)
gcloud compute start-iap-tunnel vm-windows-prod-001 3389 \
    --local-host-port=localhost:13389 \
    --zone=$ZONE \
    --project=$PROJECT
# Then connect RDP client to localhost:13389
```

---

## Cloud-init and Startup Scripts

```bash
# Startup script via metadata (runs on every boot)
gcloud compute instances create my-vm \
    --zone=$ZONE \
    --project=$PROJECT \
    --machine-type=e2-medium \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --metadata=startup-script='#!/bin/bash
apt-get update -y
apt-get install -y nginx
systemctl enable nginx
systemctl start nginx
echo "Server $(hostname)" > /var/www/html/index.html'

# Use a cloud-init config file
gcloud compute instances create my-vm \
    --zone=$ZONE \
    --project=$PROJECT \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --metadata-from-file=user-data=cloud-init.yaml

# cloud-init.yaml example:
# #cloud-config
# packages:
#   - nginx
#   - python3-pip
# runcmd:
#   - systemctl enable nginx
#   - systemctl start nginx
#   - pip3 install gunicorn
# write_files:
#   - path: /etc/nginx/conf.d/app.conf
#     content: |
#       server { listen 80; location / { proxy_pass http://localhost:8080; } }
```

---

## Disk Operations

```bash
# List disk types available in a zone
gcloud compute disk-types list \
    --filter="zone=us-central1-a" \
    --format="table(name,description,validDiskSize)"

# Add a data disk to a running VM (for pd-ssd and pd-balanced)
gcloud compute disks create disk-data-001 \
    --project=$PROJECT \
    --zone=$ZONE \
    --type=pd-ssd \
    --size=200GB \
    --labels=environment=production

gcloud compute instances attach-disk vm-my-app-prod-001 \
    --project=$PROJECT \
    --zone=$ZONE \
    --disk=disk-data-001 \
    --mode=rw \
    --device-name=data

# On the VM, format and mount:
# sudo mkfs.ext4 -m 0 -E lazy_itable_init=0,lazy_journal_init=0,discard /dev/disk/by-id/google-data
# sudo mkdir -p /mnt/data
# sudo mount -o discard,defaults /dev/disk/by-id/google-data /mnt/data

# Resize a disk (no downtime for Linux persistent disks)
gcloud compute disks resize disk-data-001 \
    --project=$PROJECT \
    --zone=$ZONE \
    --size=400GB

# Create a snapshot for backup
gcloud compute disks snapshot disk-data-001 \
    --project=$PROJECT \
    --zone=$ZONE \
    --snapshot-names=snap-disk-data-001-$(date +%Y%m%d) \
    --storage-location=us-central1 \
    --labels=environment=production

# List snapshots
gcloud compute snapshots list --project=$PROJECT --format="table(name,diskSizeGb,creationTimestamp,storageBytes)"
```

---

## VM Lifecycle Operations

```bash
# Stop a VM (compute billing stops, disk/IP still billed)
gcloud compute instances stop vm-my-app-prod-001 \
    --project=$PROJECT --zone=$ZONE

# Start a VM
gcloud compute instances start vm-my-app-prod-001 \
    --project=$PROJECT --zone=$ZONE

# Reset (hard reboot)
gcloud compute instances reset vm-my-app-prod-001 \
    --project=$PROJECT --zone=$ZONE

# Delete a VM (leaves disk by default)
gcloud compute instances delete vm-my-app-prod-001 \
    --project=$PROJECT --zone=$ZONE \
    --quiet

# Delete a VM AND its boot disk
gcloud compute instances delete vm-my-app-prod-001 \
    --project=$PROJECT --zone=$ZONE \
    --delete-disks=boot \
    --quiet

# Change machine type (must stop first)
gcloud compute instances stop vm-my-app-prod-001 --zone=$ZONE
gcloud compute instances set-machine-type vm-my-app-prod-001 \
    --zone=$ZONE --machine-type=n2-standard-8
gcloud compute instances start vm-my-app-prod-001 --zone=$ZONE
```

---

## Spot VMs (Preemptible)

```bash
# Create a Spot VM (up to 91% cheaper, can be preempted)
gcloud compute instances create spot-worker-001 \
    --project=$PROJECT \
    --zone=$ZONE \
    --machine-type=n2-standard-8 \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --provisioning-model=SPOT \
    --instance-termination-action=DELETE \
    --max-run-duration=3600s \  # Optional: auto-stop after 1 hour
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform \
    --no-address \
    --subnet=subnet-app-us-central1

# Handle preemption in startup script:
# curl -s -H "Metadata-Flavor: Google" \
#   "http://metadata.google.internal/computeMetadata/v1/instance/preempted"
# → Returns "TRUE" when preemption notice is received
```

---

## OS Login (Centralized SSH Management)

OS Login ties SSH access to Entra/Google Workspace identities and supports 2FA.

```bash
# Enable OS Login at project level (applies to all VMs)
gcloud compute project-info add-metadata \
    --project=$PROJECT \
    --metadata=enable-oslogin=TRUE

# Grant SSH access to a user (no need to manage SSH keys manually)
gcloud compute os-login ssh-keys add \
    --key-file=$HOME/.ssh/id_rsa.pub \
    --project=$PROJECT

# Grant OS login permissions
gcloud projects add-iam-policy-binding $PROJECT \
    --member="user:alice@example.com" \
    --role="roles/compute.osLogin"  # Regular SSH access

gcloud projects add-iam-policy-binding $PROJECT \
    --member="user:admin@example.com" \
    --role="roles/compute.osAdminLogin"  # sudo access
```

---

## References

- [Compute Engine documentation](https://cloud.google.com/compute/docs)
- [Machine types](https://cloud.google.com/compute/docs/machine-resource)
- [Spot VMs](https://cloud.google.com/compute/docs/instances/spot)
- [OS Login](https://cloud.google.com/compute/docs/oslogin)

---

← [Previous: GCP Compute](./README.md) | [Home](../../README.md) | [Next: Managed Instance Groups →](./managed-instance-groups.md)
