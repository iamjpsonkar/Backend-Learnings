← [Previous: Workload Identity Federation](../02-iam/workload-identity-federation.md) | [Home](../../README.md) | [Next: VPC →](./vpc.md)

---

# GCP Networking

---

## Service Overview

| Service | AWS Equivalent | Purpose |
|---------|----------------|---------|
| **VPC** | VPC | Global software-defined network |
| **Cloud NAT** | NAT Gateway | Outbound internet for private instances |
| **Cloud Load Balancing** | ALB / NLB / GLB | Global and regional load balancers |
| **Cloud Armor** | WAF + Shield Advanced | DDoS protection + WAF |
| **Cloud CDN** | CloudFront | Content delivery network |
| **Cloud DNS** | Route 53 | Managed DNS |
| **Cloud Interconnect** | Direct Connect | Dedicated private connectivity |
| **Cloud VPN** | Site-to-Site VPN | IPsec VPN to on-premises |
| **VPC Service Controls** | — | API-level perimeter around GCP services |
| **Private Service Connect** | PrivateLink | Private access to Google APIs and services |

### GCP VPC vs AWS VPC

| Feature | GCP VPC | AWS VPC |
|---------|---------|---------|
| Scope | **Global** — one VPC spans all regions | Regional |
| Subnets | Regional — one per region per VPC | Availability-zone level |
| Routing | Automatic between subnets in same VPC | Requires explicit route tables |
| Firewall rules | Stateful, applied at instance level via tags | Security groups + NACLs |
| Load balancer | Single global anycast IP | Per-region ALB |

---

## VPC and Subnets

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"

# Create a custom-mode VPC (recommended over auto-mode)
gcloud compute networks create vpc-my-app-prod \
    --project=$PROJECT_ID \
    --subnet-mode=custom \
    --bgp-routing-mode=global \
    --mtu=1500

# Create subnets in different regions within the same VPC
# Public subnet (for load balancers, NAT, Bastion)
gcloud compute networks subnets create snet-public-us-central1 \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --region=$REGION \
    --range=10.0.1.0/24 \
    --enable-private-ip-google-access

# Private subnet (application tier)
gcloud compute networks subnets create snet-app-us-central1 \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --region=$REGION \
    --range=10.0.11.0/24 \
    --enable-private-ip-google-access

# Data subnet (databases, Memorystore)
gcloud compute networks subnets create snet-data-us-central1 \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --region=$REGION \
    --range=10.0.21.0/24 \
    --enable-private-ip-google-access

# GKE subnet with secondary ranges for pods and services
gcloud compute networks subnets create snet-gke-us-central1 \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --region=$REGION \
    --range=10.0.31.0/24 \
    --secondary-range=pods=10.1.0.0/16,services=10.2.0.0/20 \
    --enable-private-ip-google-access

# List subnets
gcloud compute networks subnets list \
    --project=$PROJECT_ID \
    --filter="network:vpc-my-app-prod" \
    --format="table(name,region,ipCidrRange,secondaryIpRanges)"
```

---

## Firewall Rules

GCP firewall rules are applied at the VPC level and target instances via **network tags** or **service accounts**. All ingress is denied by default; all egress is allowed by default.

```bash
# Allow HTTP/HTTPS from anywhere (for load balancer health checks + internet)
gcloud compute firewall-rules create fw-allow-http-https \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --direction=INGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:80,tcp:443 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=http-server

# Allow GCP health check probes (required for load balancers)
gcloud compute firewall-rules create fw-allow-health-checks \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --direction=INGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:8080 \
    --source-ranges=130.211.0.0/22,35.191.0.0/16 \
    --target-tags=allow-health-check

# Allow app tier to talk to data tier (tag-based)
gcloud compute firewall-rules create fw-app-to-data \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --direction=INGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:5432,tcp:6379 \
    --source-tags=app-server \
    --target-tags=data-server

# Allow IAP SSH (Identity-Aware Proxy — no public IP needed)
gcloud compute firewall-rules create fw-allow-iap-ssh \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --direction=INGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:22 \
    --source-ranges=35.235.240.0/20 \
    --target-tags=iap-access

# Deny all other ingress (explicit — good practice even though it's the default)
gcloud compute firewall-rules create fw-deny-all-ingress \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --direction=INGRESS \
    --priority=65534 \
    --action=DENY \
    --rules=all

# List rules
gcloud compute firewall-rules list \
    --project=$PROJECT_ID \
    --filter="network:vpc-my-app-prod" \
    --format="table(name,direction,priority,sourceRanges,allowed)"
```

---

## Cloud NAT

Cloud NAT provides outbound internet access for instances without public IP addresses. It is regional and fully managed (no NAT instance to maintain).

```bash
# Create a Cloud Router (required by Cloud NAT)
gcloud compute routers create router-us-central1 \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --region=$REGION

# Create Cloud NAT on the router
gcloud compute routers nats create nat-us-central1 \
    --project=$PROJECT_ID \
    --router=router-us-central1 \
    --region=$REGION \
    --nat-all-subnet-ip-ranges \
    --auto-allocate-nat-external-ips \
    --enable-logging

# View NAT logs (in Cloud Logging)
# resource.type="nat_gateway" logName="projects/PROJECT_ID/logs/compute.googleapis.com%2Fnat_flows"
```

---

## VPC Peering

```bash
# Peer two VPCs in the same project (or across projects)
gcloud compute networks peerings create peer-prod-to-shared \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --peer-project=my-shared-services \
    --peer-network=vpc-shared-services \
    --export-custom-routes \
    --import-custom-routes

# Peering must be created on both sides
gcloud compute networks peerings create peer-shared-to-prod \
    --project=my-shared-services \
    --network=vpc-shared-services \
    --peer-project=$PROJECT_ID \
    --peer-network=vpc-my-app-prod \
    --export-custom-routes \
    --import-custom-routes

# List peerings
gcloud compute networks peerings list \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod
```

> **Note:** VPC peering does not support transitive routing. Use Shared VPC or a hub-and-spoke via Network Connectivity Center for transitive connectivity.

---

## Cloud Load Balancing

GCP offers several load balancer types:

| Type | Layer | Scope | Use Case |
|------|-------|-------|---------|
| **Global External ALB** | L7 | Global | HTTPS apps with global users, Cloud CDN, Cloud Armor |
| **Regional External ALB** | L7 | Regional | Regional HTTPS apps |
| **External Network LB (pass-through)** | L4 | Regional | High-performance TCP/UDP |
| **Internal ALB** | L7 | Regional | Internal microservices |
| **Internal Passthrough NLB** | L4 | Regional | Internal high-throughput TCP/UDP |

```bash
# Global HTTPS load balancer for Cloud Run / GCE backends

# 1. Reserve a global static IP
gcloud compute addresses create ip-my-app-global \
    --project=$PROJECT_ID \
    --global

# 2. Create a managed SSL certificate (auto-provisioned and renewed)
gcloud compute ssl-certificates create cert-my-app \
    --project=$PROJECT_ID \
    --domains=my-app.example.com \
    --global

# 3. Create a backend service pointing at a serverless NEG (Cloud Run)
gcloud compute network-endpoint-groups create neg-my-app-run \
    --project=$PROJECT_ID \
    --region=$REGION \
    --network-endpoint-type=SERVERLESS \
    --cloud-run-service=my-app-api

gcloud compute backend-services create bs-my-app \
    --project=$PROJECT_ID \
    --global \
    --load-balancing-scheme=EXTERNAL_MANAGED

gcloud compute backend-services add-backend bs-my-app \
    --project=$PROJECT_ID \
    --global \
    --network-endpoint-group=neg-my-app-run \
    --network-endpoint-group-region=$REGION

# 4. URL map
gcloud compute url-maps create urlmap-my-app \
    --project=$PROJECT_ID \
    --global \
    --default-service=bs-my-app

# 5. HTTPS proxy
gcloud compute target-https-proxies create proxy-my-app \
    --project=$PROJECT_ID \
    --url-map=urlmap-my-app \
    --ssl-certificates=cert-my-app \
    --global

# 6. Forwarding rule (binds IP → proxy)
gcloud compute forwarding-rules create fr-my-app-https \
    --project=$PROJECT_ID \
    --global \
    --ip-address=ip-my-app-global \
    --target-https-proxy=proxy-my-app \
    --ports=443

# HTTP → HTTPS redirect
gcloud compute url-maps import urlmap-http-redirect \
    --project=$PROJECT_ID \
    --global <<'EOF'
name: urlmap-http-redirect
defaultUrlRedirect:
  redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
  httpsRedirect: true
EOF

gcloud compute target-http-proxies create proxy-my-app-http \
    --project=$PROJECT_ID \
    --url-map=urlmap-http-redirect \
    --global

gcloud compute forwarding-rules create fr-my-app-http \
    --project=$PROJECT_ID \
    --global \
    --ip-address=ip-my-app-global \
    --target-http-proxy=proxy-my-app-http \
    --ports=80
```

---

## Cloud DNS

```bash
# Create a public DNS zone
gcloud dns managed-zones create zone-example-com \
    --project=$PROJECT_ID \
    --dns-name=example.com. \
    --description="Public zone for example.com" \
    --visibility=public

# Add an A record
gcloud dns record-sets create my-app.example.com. \
    --project=$PROJECT_ID \
    --zone=zone-example-com \
    --type=A \
    --ttl=300 \
    --rrdatas=$(gcloud compute addresses describe ip-my-app-global \
        --global --format="value(address)")

# Add a CNAME record
gcloud dns record-sets create www.example.com. \
    --project=$PROJECT_ID \
    --zone=zone-example-com \
    --type=CNAME \
    --ttl=300 \
    --rrdatas=my-app.example.com.

# Create a private DNS zone (internal service discovery)
gcloud dns managed-zones create zone-internal \
    --project=$PROJECT_ID \
    --dns-name=internal.example.com. \
    --visibility=private \
    --networks=vpc-my-app-prod \
    --description="Private zone for internal services"
```

---

## References

- [GCP VPC documentation](https://cloud.google.com/vpc/docs)
- [Cloud Load Balancing](https://cloud.google.com/load-balancing/docs)
- [Cloud NAT](https://cloud.google.com/nat/docs)
- [Cloud DNS](https://cloud.google.com/dns/docs)
- [VPC firewall rules](https://cloud.google.com/vpc/docs/firewalls)
---

← [Previous: Workload Identity Federation](../02-iam/workload-identity-federation.md) | [Home](../../README.md) | [Next: VPC →](./vpc.md)
