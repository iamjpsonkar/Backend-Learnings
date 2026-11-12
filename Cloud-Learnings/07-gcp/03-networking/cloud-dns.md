← [Previous: Load Balancing](./load-balancing.md) | [Home](../../README.md) | [Next: GCP Compute →](../04-compute/README.md)

---

# Cloud DNS

Cloud DNS is a scalable, highly available managed DNS service. It supports public zones (for internet DNS), private zones (for VPC-internal resolution), and DNS peering.

---

## Zone Types

| Zone Type | Visibility | Use Case |
|-----------|-----------|----------|
| **Public** | Internet-resolvable | External domains (example.com) |
| **Private** | VPC-internal only | Internal services, SQL, private endpoints |
| **Forwarding** | Delegates to another resolver | On-premises DNS servers |
| **Peering** | Shares a private zone with another VPC | Shared VPC, VPC peering |

---

## Public Zones

```bash
PROJECT="my-app-prod-123456"

# Create a public managed zone
gcloud dns managed-zones create zone-example-com \
    --project=$PROJECT \
    --dns-name="example.com." \
    --description="Public zone for example.com" \
    --visibility=public \
    --dnssec-state=on  # Enable DNSSEC (recommended)

# Get the name servers (update at your domain registrar)
gcloud dns managed-zones describe zone-example-com \
    --project=$PROJECT \
    --format="value(nameServers)"
# Output: ns-cloud-a1.googledomains.com., ns-cloud-a2.googledomains.com., ...

# Start a record-set transaction
gcloud dns record-sets transaction start \
    --zone=zone-example-com \
    --project=$PROJECT

# Add an A record (point domain to LB IP)
gcloud dns record-sets transaction add \
    --zone=zone-example-com \
    --project=$PROJECT \
    --name="example.com." \
    --type=A \
    --ttl=300 \
    "34.120.100.200"

# Add www subdomain
gcloud dns record-sets transaction add \
    --zone=zone-example-com \
    --project=$PROJECT \
    --name="www.example.com." \
    --type=CNAME \
    --ttl=300 \
    "example.com."

# Add MX records (email)
gcloud dns record-sets transaction add \
    --zone=zone-example-com \
    --project=$PROJECT \
    --name="example.com." \
    --type=MX \
    --ttl=3600 \
    "10 aspmx.l.google.com." \
    "20 alt1.aspmx.l.google.com."

# Commit the transaction
gcloud dns record-sets transaction execute \
    --zone=zone-example-com \
    --project=$PROJECT

# Abort without changes
gcloud dns record-sets transaction abort \
    --zone=zone-example-com \
    --project=$PROJECT
```

---

## Direct Record Operations (Without Transaction)

```bash
# Create a record directly (simpler for single changes)
gcloud dns record-sets create api.example.com. \
    --zone=zone-example-com \
    --project=$PROJECT \
    --type=A \
    --ttl=60 \
    --rrdatas="34.120.100.200"

# Update a record
gcloud dns record-sets update api.example.com. \
    --zone=zone-example-com \
    --project=$PROJECT \
    --type=A \
    --ttl=300 \
    --rrdatas="34.120.100.201"

# Delete a record
gcloud dns record-sets delete api.example.com. \
    --zone=zone-example-com \
    --project=$PROJECT \
    --type=A

# List all records
gcloud dns record-sets list \
    --zone=zone-example-com \
    --project=$PROJECT \
    --format="table(name,type,ttl,rrdatas)"
```

---

## Private Zones (Internal DNS)

```bash
# Create a private zone for internal service discovery
gcloud dns managed-zones create zone-internal \
    --project=$PROJECT \
    --dns-name="internal.example.com." \
    --description="Private zone for internal services" \
    --visibility=private \
    --networks=vpc-my-app-prod  # Attach to VPC

# Add a record for a Cloud SQL instance (private IP)
gcloud dns record-sets create db.internal.example.com. \
    --zone=zone-internal \
    --project=$PROJECT \
    --type=A \
    --ttl=300 \
    --rrdatas="10.0.20.4"

# Add a record for an internal load balancer
gcloud dns record-sets create api.internal.example.com. \
    --zone=zone-internal \
    --project=$PROJECT \
    --type=A \
    --ttl=60 \
    --rrdatas="10.0.10.100"

# VMs in vpc-my-app-prod can now resolve:
# db.internal.example.com → 10.0.20.4
# api.internal.example.com → 10.0.10.100

# Attach private zone to additional VPCs
gcloud dns managed-zones update zone-internal \
    --project=$PROJECT \
    --add-private-visibility-config \
    network=vpc-shared-services,project=$PROJECT
```

---

## Forwarding Zones (On-Premises DNS)

```bash
# Forward on-premises domain queries to on-prem DNS servers
gcloud dns managed-zones create zone-onprem-forwarding \
    --project=$PROJECT \
    --dns-name="corp.example.com." \
    --description="Forward corporate DNS to on-premises" \
    --visibility=private \
    --networks=vpc-my-app-prod \
    --forwarding-targets=192.168.1.10,192.168.1.11  # On-prem DNS IPs

# Use private forwarding (traffic stays on private RFC 1918 paths via VPN)
gcloud dns managed-zones create zone-onprem-private \
    --project=$PROJECT \
    --dns-name="corp.example.com." \
    --visibility=private \
    --networks=vpc-my-app-prod \
    --private-forwarding-targets=192.168.1.10,192.168.1.11
```

---

## DNS Policies

DNS policies configure DNS behavior for VMs in a VPC.

```bash
# Create a DNS policy to enable inbound DNS forwarding
# (allows on-prem systems to query Cloud DNS private zones via VPN)
gcloud dns policies create dns-policy-my-app \
    --project=$PROJECT \
    --networks=vpc-my-app-prod \
    --enable-inbound-forwarding \
    --description="DNS policy for vpc-my-app-prod"

# Get inbound DNS forwarding IP (configure as DNS server on-premises)
gcloud dns policies describe dns-policy-my-app \
    --project=$PROJECT \
    --format="json(networks[].inboundForwardingConfig)"
```

---

## Cloud DNS with Terraform

```hcl
resource "google_dns_managed_zone" "public" {
  project     = var.project
  name        = "zone-example-com"
  dns_name    = "example.com."
  description = "Public DNS zone"
  visibility  = "public"

  dnssec_config {
    state = "on"
  }
}

resource "google_dns_record_set" "a_root" {
  project      = var.project
  managed_zone = google_dns_managed_zone.public.name
  name         = "example.com."
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_global_address.lb_ip.address]
}

resource "google_dns_managed_zone" "private" {
  project     = var.project
  name        = "zone-internal"
  dns_name    = "internal.example.com."
  visibility  = "private"

  private_visibility_config {
    networks {
      network_url = google_compute_network.vpc.id
    }
  }
}
```

---

## Verification

```bash
# Verify DNS resolution (use dig or nslookup)
dig my-app.example.com A +short
dig @8.8.8.8 my-app.example.com A +short  # Force Google DNS

# Check DNSSEC
dig my-app.example.com +dnssec +short

# Check TTL
dig my-app.example.com A | grep "IN.*A"

# From a VM inside the VPC — check private zone resolution
# gcloud compute ssh my-vm --zone=us-central1-a
# dig db.internal.example.com A +short
# Expected: 10.0.20.4
```

---

## References

- [Cloud DNS documentation](https://cloud.google.com/dns/docs)
- [Private zones](https://cloud.google.com/dns/docs/zones/zones-overview#private_zones)
- [DNS forwarding](https://cloud.google.com/dns/docs/zones/forwarding-zones)
- [DNSSEC](https://cloud.google.com/dns/docs/dnssec)

---

← [Previous: Load Balancing](./load-balancing.md) | [Home](../../README.md) | [Next: GCP Compute →](../04-compute/README.md)
