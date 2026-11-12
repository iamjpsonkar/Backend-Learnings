← [Previous: GCP Networking](./README.md) | [Home](../../README.md) | [Next: Firewall Rules →](./firewall-rules.md)

---

# GCP VPC Networks

GCP VPCs are global resources — a single VPC spans all regions. Subnets are regional. This differs from AWS where VPCs are regional.

---

## GCP vs AWS Networking

| Concept | GCP | AWS |
|---------|-----|-----|
| Network scope | Global | Regional |
| Subnet scope | Regional | Availability Zone |
| Default routes | Auto-created | Route table |
| Internet gateway | Automatic (for external IPs) | IGW resource |
| NAT gateway | Cloud NAT (regional) | NAT Gateway (per-AZ) |
| Firewall | Network-level, tag-based | Security Groups (instance-level) |
| Shared networking | Shared VPC (host/service projects) | AWS RAM + VPC sharing |

---

## VPC Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Auto mode** | Auto-creates subnets in every region (10.128.0.0/9 range) | Dev, exploration |
| **Custom mode** | You define all subnets | Production — use this |

---

## Creating a VPC and Subnets

```bash
PROJECT="my-app-prod-123456"

# Create a custom mode VPC
gcloud compute networks create vpc-my-app-prod \
    --project=$PROJECT \
    --subnet-mode=custom \
    --bgp-routing-mode=global \
    --description="Production VPC for my-app"

# Create regional subnets
# Application tier — us-central1
gcloud compute networks subnets create subnet-app-us-central1 \
    --project=$PROJECT \
    --network=vpc-my-app-prod \
    --region=us-central1 \
    --range=10.0.10.0/24 \
    --enable-private-ip-google-access \
    --enable-flow-logs \
    --logging-aggregation-interval=INTERVAL_5_SEC \
    --logging-flow-sampling=0.5

# Data tier
gcloud compute networks subnets create subnet-data-us-central1 \
    --project=$PROJECT \
    --network=vpc-my-app-prod \
    --region=us-central1 \
    --range=10.0.20.0/28 \
    --enable-private-ip-google-access

# GKE pods — secondary ranges allow pods to get IPs from a different range
gcloud compute networks subnets create subnet-gke-us-central1 \
    --project=$PROJECT \
    --network=vpc-my-app-prod \
    --region=us-central1 \
    --range=10.0.100.0/24 \
    --secondary-range=pods=10.1.0.0/16,services=10.2.0.0/20 \
    --enable-private-ip-google-access

# List subnets
gcloud compute networks subnets list \
    --network=vpc-my-app-prod \
    --project=$PROJECT \
    --format="table(name,region,ipCidrRange,secondaryIpRanges[].rangeName,privateIpGoogleAccess)"
```

---

## Private Google Access

Private Google Access lets VMs without external IPs reach Google APIs (Cloud Storage, BigQuery, etc.) over private Google peering.

```bash
# Enable on a subnet (done with --enable-private-ip-google-access above)
gcloud compute networks subnets update subnet-app-us-central1 \
    --region=us-central1 \
    --project=$PROJECT \
    --enable-private-ip-google-access

# Configure Private Service Connect for googleapis.com
# This routes Google API traffic through your VPC (no internet required)
gcloud compute addresses create private-google-access-ip \
    --project=$PROJECT \
    --global \
    --purpose=PRIVATE_SERVICE_CONNECT \
    --addresses=10.0.0.2 \
    --network=vpc-my-app-prod

gcloud compute forwarding-rules create private-google-access \
    --project=$PROJECT \
    --global \
    --network=vpc-my-app-prod \
    --address=private-google-access-ip \
    --target-google-apis-bundle=all-apis
```

---

## VPC Peering

VPC peering connects two VPCs so resources can communicate using internal IPs. VPC peering is non-transitive.

```bash
VPC_A="vpc-my-app-prod"
VPC_B="vpc-shared-services"
PROJECT_A="my-app-prod-123456"
PROJECT_B="shared-services-789012"

# Peer A → B
gcloud compute networks peerings create peer-app-to-shared \
    --project=$PROJECT_A \
    --network=$VPC_A \
    --peer-project=$PROJECT_B \
    --peer-network=$VPC_B \
    --import-custom-routes \
    --export-custom-routes

# Peer B → A (must create in both directions)
gcloud compute networks peerings create peer-shared-to-app \
    --project=$PROJECT_B \
    --network=$VPC_B \
    --peer-project=$PROJECT_A \
    --peer-network=$VPC_A \
    --import-custom-routes \
    --export-custom-routes

# Verify peering state (must be ACTIVE on both sides)
gcloud compute networks peerings list \
    --network=$VPC_A \
    --project=$PROJECT_A \
    --format="table(name,state,peerNetwork)"
```

---

## Shared VPC

Shared VPC allows multiple service projects to use subnets from a central host project. Network resources are managed centrally; compute resources are in separate projects.

```bash
HOST_PROJECT="shared-networking-prod"
SERVICE_PROJECT="my-app-prod-123456"

# Enable Shared VPC on the host project
gcloud compute shared-vpc enable $HOST_PROJECT

# Associate a service project
gcloud compute shared-vpc associated-projects add $SERVICE_PROJECT \
    --host-project=$HOST_PROJECT

# Grant service project SA permission to use host subnets
gcloud projects add-iam-policy-binding $HOST_PROJECT \
    --member="serviceAccount:SERVICE_ACCOUNT@$SERVICE_PROJECT.iam.gserviceaccount.com" \
    --role="roles/compute.networkUser"

# Grant GKE SA permission to use host subnets (for GKE in service project)
gcloud projects add-iam-policy-binding $HOST_PROJECT \
    --member="serviceAccount:service-PROJECT_NUMBER@container-engine-robot.iam.gserviceaccount.com" \
    --role="roles/container.hostServiceAgentUser"

# List service projects associated with a host project
gcloud compute shared-vpc list-associated-resources $HOST_PROJECT
```

---

## Routes

```bash
# View routes (auto-created for subnets, default internet route)
gcloud compute routes list \
    --project=$PROJECT \
    --filter="network=vpc-my-app-prod" \
    --format="table(name,destRange,nextHopGateway,nextHopIlb,priority)"

# Create a custom route — route specific traffic through a VPN/interconnect
gcloud compute routes create route-to-onprem \
    --project=$PROJECT \
    --network=vpc-my-app-prod \
    --destination-range=192.168.0.0/16 \
    --next-hop-vpn-tunnel=vpn-tunnel-to-onprem \
    --next-hop-vpn-tunnel-region=us-central1 \
    --priority=1000

# Delete the default internet route (for fully private VPCs)
gcloud compute routes delete default-route-HASH \
    --project=$PROJECT \
    --quiet
```

---

## Deleting a VPC

```bash
# Must delete all subnets, firewalls, and VMs first
gcloud compute networks subnets delete subnet-app-us-central1 \
    --region=us-central1 --project=$PROJECT --quiet

gcloud compute networks delete vpc-my-app-prod \
    --project=$PROJECT --quiet
```

---

## References

- [VPC overview](https://cloud.google.com/vpc/docs/vpc)
- [Subnets](https://cloud.google.com/vpc/docs/subnets)
- [VPC peering](https://cloud.google.com/vpc/docs/vpc-peering)
- [Shared VPC](https://cloud.google.com/vpc/docs/shared-vpc)

---

← [Previous: GCP Networking](./README.md) | [Home](../../README.md) | [Next: Firewall Rules →](./firewall-rules.md)
