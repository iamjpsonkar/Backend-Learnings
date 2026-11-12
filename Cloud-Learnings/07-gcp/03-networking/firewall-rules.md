← [Previous: VPC](./vpc.md) | [Home](../../README.md) | [Next: Load Balancing →](./load-balancing.md)

---

# GCP Firewall Rules

GCP firewall rules are stateful, applied at the network level, and target VMs using network tags or service accounts. They differ from AWS security groups (which are applied per instance).

---

## Firewall Rule Concepts

| Concept | GCP | AWS |
|---------|-----|-----|
| Attachment | Network-wide, filtered by tag/SA | Per instance (security group) |
| Statefulness | Stateful (return traffic allowed) | Stateful |
| Default deny | Implied deny all (lowest priority 65535) | Implicit deny |
| Default allow | `default-allow-internal` (if default network) | None |
| Targeting | Network tags or service accounts | SG membership |

---

## Rule Priority

Lower number = higher priority. Rules are evaluated from lowest number to highest.

```
Priority 0          ← Highest
Priority 1000       ← Default for user-created rules
Priority 65534      ← default-allow-internal (allow within VPC)
Priority 65535      ← Implied deny all (cannot modify or delete)
```

---

## Creating Firewall Rules

```bash
PROJECT="my-app-prod-123456"
VPC="vpc-my-app-prod"

# Allow SSH from IAP (Google's Identity-Aware Proxy) — no public IPs needed
gcloud compute firewall-rules create allow-iap-ssh \
    --project=$PROJECT \
    --network=$VPC \
    --direction=INGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:22 \
    --source-ranges=35.235.240.0/20 \  # Google IAP IP range
    --target-tags=allow-iap \
    --description="Allow SSH via IAP to tagged VMs"

# Allow HTTPS from internet to load balancer
gcloud compute firewall-rules create allow-https-inbound \
    --project=$PROJECT \
    --network=$VPC \
    --direction=INGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:443 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=load-balancer \
    --description="Allow HTTPS from internet to LB"

# Allow health checks from Google Load Balancer probes
gcloud compute firewall-rules create allow-health-checks \
    --project=$PROJECT \
    --network=$VPC \
    --direction=INGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:8080 \
    --source-ranges=130.211.0.0/22,35.191.0.0/16 \  # Google LB probe ranges
    --target-tags=backend \
    --description="Allow GCP load balancer health checks"

# Allow internal app-to-data communication
gcloud compute firewall-rules create allow-app-to-db \
    --project=$PROJECT \
    --network=$VPC \
    --direction=INGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:5432 \
    --source-tags=app-server \
    --target-tags=database \
    --description="Allow app tier to reach PostgreSQL"

# Deny all other ingress (explicit — good for auditing)
gcloud compute firewall-rules create deny-all-ingress \
    --project=$PROJECT \
    --network=$VPC \
    --direction=INGRESS \
    --priority=65000 \
    --action=DENY \
    --rules=all \
    --source-ranges=0.0.0.0/0 \
    --description="Deny all other ingress traffic"

# Allow all egress to internet (default)
# GCP's implied rule (priority 65535) allows all egress
# To restrict egress, create a deny-all-egress rule with lower priority
gcloud compute firewall-rules create deny-all-egress \
    --project=$PROJECT \
    --network=$VPC \
    --direction=EGRESS \
    --priority=65000 \
    --action=DENY \
    --rules=all \
    --destination-ranges=0.0.0.0/0

# Then allow specific egress
gcloud compute firewall-rules create allow-egress-google-apis \
    --project=$PROJECT \
    --network=$VPC \
    --direction=EGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:443 \
    --destination-ranges=199.36.153.8/30,199.36.153.4/30 \  # googleapis.com
    --description="Allow HTTPS to Google APIs"
```

---

## Service Account-Based Targeting (More Secure Than Tags)

Tags can be set by any user with instance creation rights — service accounts require `iam.serviceAccounts.actAs` permission.

```bash
SA_APP="sa-app@$PROJECT.iam.gserviceaccount.com"
SA_DB="sa-db@$PROJECT.iam.gserviceaccount.com"

# Allow app service account to reach database service account
gcloud compute firewall-rules create allow-app-sa-to-db-sa \
    --project=$PROJECT \
    --network=$VPC \
    --direction=INGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:5432 \
    --source-service-accounts=$SA_APP \
    --target-service-accounts=$SA_DB

# Allow GKE pods (via their node SA) to reach internal services
gcloud compute firewall-rules create allow-gke-nodes \
    --project=$PROJECT \
    --network=$VPC \
    --direction=INGRESS \
    --priority=1000 \
    --action=ALLOW \
    --rules=tcp:8080 \
    --source-service-accounts="sa-gke-nodes@$PROJECT.iam.gserviceaccount.com" \
    --target-tags=backend
```

---

## Listing and Managing Rules

```bash
# List all firewall rules in a network
gcloud compute firewall-rules list \
    --filter="network=vpc-my-app-prod" \
    --project=$PROJECT \
    --format="table(name,direction,priority,allowed[].map().firewall_rule().list():label=ALLOW,denied[].map().firewall_rule().list():label=DENY,sourceTags,targetTags)"

# Describe a rule
gcloud compute firewall-rules describe allow-iap-ssh --project=$PROJECT

# Update a rule (change source ranges)
gcloud compute firewall-rules update allow-https-inbound \
    --project=$PROJECT \
    --source-ranges=0.0.0.0/0,::/0

# Disable a rule without deleting
gcloud compute firewall-rules update allow-ssh-debug \
    --project=$PROJECT \
    --disabled

# Delete a rule
gcloud compute firewall-rules delete allow-ssh-debug \
    --project=$PROJECT --quiet
```

---

## Hierarchical Firewall Policies

Organization-level firewall policies apply across all VPCs in an org or folder.

```bash
ORG_ID="1234567890"

# Create a hierarchical policy
gcloud compute firewall-policies create \
    --short-name=org-security-policy \
    --description="Organization-wide security baseline" \
    --organization=$ORG_ID

# Add a rule (deny known malicious ranges)
gcloud compute firewall-policies rules create 100 \
    --firewall-policy=POLICY_ID \
    --action=deny \
    --direction=INGRESS \
    --src-ip-ranges=198.51.100.0/24 \
    --layer4-configs=all \
    --organization=$ORG_ID

# Associate the policy with the organization (applies to all VPCs)
gcloud compute firewall-policies associations create \
    --firewall-policy=POLICY_ID \
    --organization=$ORG_ID
```

---

## Firewall Insights (Recommended)

```bash
# Enable firewall insights (Cloud Recommender)
gcloud recommender recommendations list \
    --recommender=google.compute.firewall.Recommender \
    --location=global \
    --project=$PROJECT \
    --format="table(name,recommenderSubtype,stateInfo.state,primaryImpact.securityProjection.details)"

# View shadowed rules (rules that are always overridden by higher-priority rules)
gcloud compute firewall-rules list \
    --project=$PROJECT \
    --filter="disabled=false" \
    --format="table(name,priority,direction,action)" \
    --sort-by=priority
```

---

## VPC Flow Logs

```bash
# Enable flow logs on a subnet (for network traffic analysis)
gcloud compute networks subnets update subnet-app-us-central1 \
    --region=us-central1 \
    --project=$PROJECT \
    --enable-flow-logs \
    --logging-aggregation-interval=INTERVAL_5_SEC \
    --logging-flow-sampling=0.5 \
    --logging-metadata=INCLUDE_ALL_METADATA

# Query flow logs in Cloud Logging
gcloud logging read \
    'logName="projects/'$PROJECT'/logs/compute.googleapis.com%2Fvpc_flows" AND
     jsonPayload.connection.dest_port=443' \
    --project=$PROJECT \
    --limit=20
```

---

## References

- [Firewall rules overview](https://cloud.google.com/vpc/docs/firewalls)
- [Service account-based firewall targeting](https://cloud.google.com/vpc/docs/firewalls#service-accounts-vs-tags)
- [Hierarchical firewall policies](https://cloud.google.com/vpc/docs/firewall-policies)
- [VPC Flow Logs](https://cloud.google.com/vpc/docs/flow-logs)

---

← [Previous: VPC](./vpc.md) | [Home](../../README.md) | [Next: Load Balancing →](./load-balancing.md)
