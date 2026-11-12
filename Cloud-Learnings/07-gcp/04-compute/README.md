← [Previous: Cloud DNS](../03-networking/cloud-dns.md) | [Home](../../README.md) | [Next: Compute Engine →](./compute-engine.md)

---

# GCP Compute

---

## Service Overview

| Service | AWS Equivalent | Use Case |
|---------|----------------|---------|
| **Compute Engine** | EC2 | General-purpose VMs — full control |
| **Managed Instance Groups (MIG)** | Auto Scaling Group | Autoscaled, self-healing VM fleet |
| **Cloud Run** | ECS Fargate / App Runner | Serverless containers — preferred for stateless workloads |
| **GKE** | EKS | Managed Kubernetes |
| **App Engine** | Elastic Beanstalk | PaaS — fully managed runtime |
| **Batch** | AWS Batch | Managed batch processing |

---

## Machine Types

| Family | AWS Equivalent | Use Case |
|--------|----------------|---------|
| **e2** | t3/t4g | Cost-optimized — general workloads, dev/test |
| **n2 / n2d** | m5 / m6g | Balanced — production general-purpose |
| **c3 / c3d** | c5 / c6g | Compute-optimized — CPU-intensive |
| **m3** | r5 / r6g | Memory-optimized — databases, in-memory |
| **a2 / g2** | p3 / p4d | Accelerator — GPU workloads |
| **t2d / t2a** | t4g | Scale-out — ARM-based (Tau T2A = Ampere Altra) |

```bash
# List all machine types in a zone
gcloud compute machine-types list \
    --filter="zone:us-central1-a" \
    --format="table(name,guestCpus,memoryMb)"
```

---

## Compute Engine Instances

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"
ZONE="us-central1-a"
SA_EMAIL="api-backend@${PROJECT_ID}.iam.gserviceaccount.com"

# Create a VM with no external IP (private only — recommended for production)
gcloud compute instances create vm-my-app-prod-001 \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=n2-standard-4 \
    --image-project=ubuntu-os-cloud \
    --image-family=ubuntu-2204-lts \
    --boot-disk-size=50GB \
    --boot-disk-type=pd-ssd \
    --network=vpc-my-app-prod \
    --subnet=snet-app-us-central1 \
    --no-address \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform \
    --tags=app-server,iap-access \
    --metadata-from-file=startup-script=startup.sh \
    --labels=environment=production,service=my-app \
    --shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring

# SSH via Identity-Aware Proxy (no public IP needed)
gcloud compute ssh vm-my-app-prod-001 \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --tunnel-through-iap

# Stop / start / restart
gcloud compute instances stop vm-my-app-prod-001 --zone=$ZONE --project=$PROJECT_ID
gcloud compute instances start vm-my-app-prod-001 --zone=$ZONE --project=$PROJECT_ID
gcloud compute instances reset vm-my-app-prod-001 --zone=$ZONE --project=$PROJECT_ID

# List instances
gcloud compute instances list --project=$PROJECT_ID --format="table(name,zone,status,networkInterfaces[0].networkIP)"

# Run a command without SSH (OS Login or metadata-based)
gcloud compute ssh vm-my-app-prod-001 \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --tunnel-through-iap \
    --command="systemctl status my-app"
```

### startup.sh Example

```bash
#!/bin/bash
set -euo pipefail

echo "Starting VM initialization..."
apt-get update -y
apt-get install -y python3-pip python3-venv

# Install application
cd /opt
python3 -m venv my-app-venv
source my-app-venv/bin/activate
pip install my-app==1.2.3

# Configure and start systemd service
systemctl enable my-app
systemctl start my-app
echo "VM initialization complete"
```

---

## Instance Templates and Managed Instance Groups

An **Instance Template** is an immutable blueprint for a VM. A **Managed Instance Group (MIG)** uses it to create and manage a fleet of identical, autoscalable VMs.

```bash
# Create an instance template
gcloud compute instance-templates create tmpl-my-app-v123 \
    --project=$PROJECT_ID \
    --machine-type=n2-standard-2 \
    --image-project=ubuntu-os-cloud \
    --image-family=ubuntu-2204-lts \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-balanced \
    --network=vpc-my-app-prod \
    --subnet=snet-app-us-central1 \
    --region=$REGION \
    --no-address \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform \
    --tags=app-server,allow-health-check \
    --metadata-from-file=startup-script=startup.sh \
    --labels=version=v1-2-3

# Create a regional MIG (spans multiple zones for HA)
gcloud compute instance-groups managed create mig-my-app-prod \
    --project=$PROJECT_ID \
    --region=$REGION \
    --template=tmpl-my-app-v123 \
    --size=3 \
    --health-checks=hc-my-app-http \
    --initial-delay=90

# Set autoscaling
gcloud compute instance-groups managed set-autoscaling mig-my-app-prod \
    --project=$PROJECT_ID \
    --region=$REGION \
    --min-num-replicas=3 \
    --max-num-replicas=20 \
    --target-cpu-utilization=0.7 \
    --cool-down-period=90

# Rolling update to a new template (zero-downtime)
gcloud compute instance-groups managed rolling-action start-update mig-my-app-prod \
    --project=$PROJECT_ID \
    --region=$REGION \
    --version=template=tmpl-my-app-v124 \
    --max-surge=3 \
    --max-unavailable=0

# Monitor rollout
gcloud compute instance-groups managed describe mig-my-app-prod \
    --project=$PROJECT_ID \
    --region=$REGION \
    --format="yaml(status)"

# List instances in the group
gcloud compute instance-groups managed list-instances mig-my-app-prod \
    --project=$PROJECT_ID \
    --region=$REGION \
    --format="table(name,zone,status,instanceStatus)"
```

### Health Check

```bash
gcloud compute health-checks create http hc-my-app-http \
    --project=$PROJECT_ID \
    --port=8080 \
    --request-path=/health \
    --check-interval=10 \
    --timeout=5 \
    --healthy-threshold=2 \
    --unhealthy-threshold=3
```

---

## Custom Images

```bash
# Create a custom image from a disk (use stopped VM)
gcloud compute instances stop vm-my-app-prod-001 --zone=$ZONE --project=$PROJECT_ID

gcloud compute images create img-my-app-v123 \
    --project=$PROJECT_ID \
    --source-disk=vm-my-app-prod-001 \
    --source-disk-zone=$ZONE \
    --family=my-app \
    --labels=version=v1-2-3

# Use the custom image in an instance template
gcloud compute instance-templates create tmpl-my-app-v123-custom \
    --project=$PROJECT_ID \
    --machine-type=n2-standard-2 \
    --image=img-my-app-v123 \
    --image-project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --region=$REGION
```

---

## Persistent Disks

```bash
# Create a standalone persistent disk
gcloud compute disks create disk-my-app-data-001 \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --size=500GB \
    --type=pd-ssd \
    --labels=environment=production

# Disk types
# pd-standard  — HDD, backup/cold data, cheapest
# pd-balanced  — SSD, general production
# pd-ssd       — SSD, IOPS-heavy workloads
# pd-extreme   — SSD, highest IOPS (up to 120K read/write IOPS)
# hyperdisk-balanced, hyperdisk-extreme — latest gen, configurable IOPS

# Attach to a running VM
gcloud compute instances attach-disk vm-my-app-prod-001 \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --disk=disk-my-app-data-001 \
    --mode=rw

# Take a snapshot
gcloud compute snapshots create snap-disk-my-app-$(date +%Y%m%d) \
    --project=$PROJECT_ID \
    --source-disk=disk-my-app-data-001 \
    --source-disk-zone=$ZONE \
    --storage-location=$REGION

# Create a scheduled snapshot policy
gcloud compute resource-policies create snapshot-schedule daily-backup \
    --project=$PROJECT_ID \
    --region=$REGION \
    --max-retention-days=7 \
    --start-time=04:00 \
    --daily-schedule

gcloud compute disks add-resource-policies disk-my-app-data-001 \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --resource-policies=daily-backup
```

---

## Spot VMs (Preemptible)

```bash
# Create a Spot VM (up to 91% cheaper, preempted with 30s notice)
gcloud compute instances create vm-spot-worker-001 \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=n2-standard-4 \
    --image-project=ubuntu-os-cloud \
    --image-family=ubuntu-2204-lts \
    --provisioning-model=SPOT \
    --instance-termination-action=DELETE \
    --tags=spot-worker \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform

# For MIG — set provisioningModel in instance template
gcloud compute instance-templates create tmpl-spot-worker \
    --project=$PROJECT_ID \
    --machine-type=n2-standard-4 \
    --image-project=ubuntu-os-cloud \
    --image-family=ubuntu-2204-lts \
    --provisioning-model=SPOT \
    --instance-termination-action=DELETE
```

---

## References

- [Compute Engine documentation](https://cloud.google.com/compute/docs)
- [Machine types](https://cloud.google.com/compute/docs/machine-resource)
- [Managed instance groups](https://cloud.google.com/compute/docs/instance-groups/working-with-managed-instances)
- [Persistent Disk types](https://cloud.google.com/compute/docs/disks)
---

← [Previous: Cloud DNS](../03-networking/cloud-dns.md) | [Home](../../README.md) | [Next: Compute Engine →](./compute-engine.md)
