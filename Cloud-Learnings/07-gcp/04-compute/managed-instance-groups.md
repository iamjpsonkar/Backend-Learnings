← [Previous: Compute Engine](./compute-engine.md) | [Home](../../README.md) | [Next: GCP Storage →](../05-storage/README.md)

---

# Managed Instance Groups (MIGs)

MIGs are groups of identical VMs managed as a single entity. They provide autoscaling, rolling updates, health checking, and regional (multi-zone) distribution.

---

## MIG Types

| Type | Scope | Zones | Use Case |
|------|-------|-------|----------|
| **Regional MIG** | Multi-zone | All zones in a region | Production — redundancy across zones |
| **Zonal MIG** | Single zone | One zone | Dev/test, stateful workloads |

---

## Creating an Instance Template

An instance template defines the VM configuration. MIGs use templates to create instances.

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"
SA_EMAIL="sa-my-app@$PROJECT.iam.gserviceaccount.com"

# Create instance template
gcloud compute instance-templates create tmpl-my-app-v1 \
    --project=$PROJECT \
    --machine-type=n2-standard-4 \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --boot-disk-size=50GB \
    --boot-disk-type=pd-ssd \
    --no-address \
    --subnet=subnet-app-us-central1 \
    --region=$REGION \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform \
    --shielded-secure-boot \
    --shielded-vtpm \
    --tags=backend,allow-iap \
    --labels=environment=production,service=my-app \
    --metadata=startup-script='#!/bin/bash
# Download app from GCS
gsutil cp gs://my-app-prod-artifacts/my-app-latest.tar.gz /tmp/
tar -xzf /tmp/my-app-latest.tar.gz -C /opt/
systemctl enable my-app
systemctl start my-app'

# List templates
gcloud compute instance-templates list \
    --project=$PROJECT \
    --format="table(name,machine_type,creationTimestamp)"
```

---

## Creating a Regional MIG

```bash
# Create a regional MIG (spans all zones in the region)
gcloud compute instance-groups managed create mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --template=tmpl-my-app-v1 \
    --size=3 \
    --base-instance-name=my-app \
    --description="My App production MIG"

# Set named ports (required for load balancer backend)
gcloud compute instance-groups managed set-named-ports mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --named-ports=http:8080

# List instances in the MIG
gcloud compute instance-groups managed list-instances mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --format="table(name,zone,status,instanceStatus,currentAction)"
```

---

## Autoscaling

```bash
# Configure autoscaling — scale on CPU utilization
gcloud compute instance-groups managed set-autoscaling mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --min-num-replicas=3 \
    --max-num-replicas=30 \
    --cool-down-period=90 \
    --target-cpu-utilization=0.7

# Scale on custom metric (from Cloud Monitoring)
gcloud compute instance-groups managed set-autoscaling mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --min-num-replicas=2 \
    --max-num-replicas=20 \
    --update-stackdriver-metric=custom.googleapis.com/my_app/queue_depth \
    --stackdriver-metric-single-instance-assignment=100 \
    --stackdriver-metric-utilization-target=0.8 \
    --stackdriver-metric-utilization-target-type=GAUGE

# Scale-to-zero (for dev — min=0 means MIG can scale to 0 when idle)
gcloud compute instance-groups managed set-autoscaling mig-my-app-dev \
    --project=$PROJECT \
    --region=$REGION \
    --min-num-replicas=0 \
    --max-num-replicas=5 \
    --target-cpu-utilization=0.7

# View current autoscaling status
gcloud compute instance-groups managed describe mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --format="json(autoscaler)"
```

---

## Rolling Updates

```bash
# Create a new template version (after building and testing new app)
gcloud compute instance-templates create tmpl-my-app-v2 \
    --project=$PROJECT \
    --machine-type=n2-standard-4 \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --boot-disk-size=50GB \
    --boot-disk-type=pd-ssd \
    --no-address \
    --subnet=subnet-app-us-central1 \
    --region=$REGION \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform \
    --tags=backend,allow-iap \
    --labels=environment=production,service=my-app,version=v2 \
    --metadata=startup-script='#!/bin/bash
gsutil cp gs://my-app-prod-artifacts/my-app-v2.tar.gz /tmp/
tar -xzf /tmp/my-app-v2.tar.gz -C /opt/
systemctl enable my-app
systemctl start my-app'

# Start a rolling update (replace instances with new template)
gcloud compute instance-groups managed rolling-action start-update mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --version=template=tmpl-my-app-v2 \
    --max-surge=3 \           # Max extra instances during update
    --max-unavailable=0 \     # Never go below desired capacity
    --replacement-method=substitute

# Canary update — update 20% of instances with new template
gcloud compute instance-groups managed rolling-action start-update mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --version=template=tmpl-my-app-v1 \
    --canary-version=template=tmpl-my-app-v2,target-size=20% \
    --max-surge=3 \
    --max-unavailable=0

# Wait for update to complete
gcloud compute instance-groups managed wait-until mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --version-target-reached

# Monitor update progress
gcloud compute instance-groups managed describe mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --format="table(status.isStable,status.versionTarget.isReached,status.stateful)"

# Rollback (revert to previous template)
gcloud compute instance-groups managed rolling-action start-update mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --version=template=tmpl-my-app-v1 \
    --max-surge=3 \
    --max-unavailable=0
```

---

## Health Checks

```bash
# Create an HTTP health check for the MIG
gcloud compute health-checks create http hc-my-app-mig \
    --project=$PROJECT \
    --port=8080 \
    --request-path=/healthz \
    --check-interval=10 \
    --timeout=5 \
    --healthy-threshold=2 \
    --unhealthy-threshold=3

# Attach health check to MIG (enables autohealing — replaces unhealthy VMs)
gcloud compute instance-groups managed update mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --health-check=hc-my-app-mig \
    --initial-delay=300  # Seconds before autohealing starts (allow app to init)

# Check instance health
gcloud compute instance-groups managed list-instances mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --format="table(name,zone,instanceStatus,healthState)"

# Recreate unhealthy instances immediately
gcloud compute instance-groups managed recreate-instances mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --instances=my-app-abcd  # Specific instance name
```

---

## Manual Scale Operations

```bash
# Scale MIG to a specific size
gcloud compute instance-groups managed resize mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --size=6

# Get current size
gcloud compute instance-groups managed describe mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --format="value(targetSize)"

# Abandon an instance (remove from MIG without deleting)
gcloud compute instance-groups managed abandon-instances mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --instances=my-app-abcd

# Delete the MIG (and all instances)
gcloud compute instance-groups managed delete mig-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --quiet
```

---

## References

- [MIG documentation](https://cloud.google.com/compute/docs/instance-groups)
- [Autoscaling](https://cloud.google.com/compute/docs/autoscaler)
- [Rolling updates](https://cloud.google.com/compute/docs/instance-groups/rolling-out-updates-to-managed-instance-groups)
- [Autohealing](https://cloud.google.com/compute/docs/instance-groups/autohealing-instances-in-migs)

---

← [Previous: Compute Engine](./compute-engine.md) | [Home](../../README.md) | [Next: GCP Storage →](../05-storage/README.md)
