← [Previous: TCP/IP](./tcp-ip.md) | [Home](../README.md) | [Next: CIDR & Subnetting →](./cidr-subnetting.md)

---

# DNS — Domain Name System

DNS translates human-readable names (`api.example.com`) into IP addresses (`93.184.216.34`). It is a hierarchical, distributed, eventually-consistent database. Understanding DNS is critical for cloud engineers — every service endpoint, load balancer, and CDN relies on it.

---

## How DNS Resolution Works

```
Browser                 Recursive Resolver          Root NS         TLD NS (.com)     Authoritative NS
   │                         │                         │                 │                   │
   │── Query: example.com? ─▶│                         │                 │                   │
   │                         │── Query: example.com? ─▶│                 │                   │
   │                         │◀─ Refer to .com NS ─────│                 │                   │
   │                         │──────── Query: example.com? ─────────────▶│                   │
   │                         │◀──────── Refer to ns1.example.com ─────────│                   │
   │                         │────────────────── Query: example.com? ────────────────────────▶│
   │                         │◀─────────────────── A 93.184.216.34, TTL 3600 ─────────────────│
   │◀── 93.184.216.34 ───────│
   │    (cached for TTL)     │
```

1. **Browser cache**: checks its own DNS cache (and the OS cache).
2. **OS resolver**: checks `/etc/hosts` and `/etc/resolv.conf` (stub resolver).
3. **Recursive resolver**: your ISP, Google (8.8.8.8), or Cloudflare (1.1.1.1). Does the work on your behalf and caches results.
4. **Root nameservers**: 13 logical root servers (operated by ICANN + partners). Know only where the TLD servers are.
5. **TLD nameservers**: know which authoritative servers are responsible for each domain under their TLD (`.com`, `.org`, `.io`).
6. **Authoritative nameserver**: the final authority for a zone. Returns the actual record value.

### Key Terms

| Term | Meaning |
|------|---------|
| **Zone** | A portion of the DNS namespace managed by one entity (e.g., `example.com`) |
| **TTL** | Time To Live — how long a record is cached by resolvers (in seconds) |
| **SOA** | Start of Authority — defines the zone's primary NS, admin email, serial number |
| **Recursive resolver** | Performs the full lookup on behalf of the client, caches results |
| **Stub resolver** | The OS-level resolver that queries a recursive resolver |
| **Negative caching** | Caching of NXDOMAIN (name not found) responses, governed by SOA's minimum TTL |

---

## DNS Record Types

| Type | Purpose | Example |
|------|---------|---------|
| **A** | Maps hostname → IPv4 address | `api.example.com. 300 IN A 93.184.216.34` |
| **AAAA** | Maps hostname → IPv6 address | `api.example.com. 300 IN AAAA 2606:2800::1` |
| **CNAME** | Alias — maps hostname → another hostname | `www.example.com. 300 IN CNAME example.com.` |
| **NS** | Lists authoritative nameservers for the zone | `example.com. 86400 IN NS ns1.example.com.` |
| **MX** | Mail exchange — for email routing, with priority | `example.com. 3600 IN MX 10 mail.example.com.` |
| **TXT** | Arbitrary text — used for SPF, DKIM, domain verification | `example.com. IN TXT "v=spf1 include:_spf.google.com ~all"` |
| **SOA** | Zone authority record — serial, refresh, retry, expire, minimum TTL | (one per zone) |
| **PTR** | Reverse lookup — maps IP → hostname | `34.216.184.93.in-addr.arpa. IN PTR api.example.com.` |
| **SRV** | Service location — protocol, port, priority, weight | `_https._tcp.example.com. IN SRV 10 5 443 server.example.com.` |
| **CAA** | Certificate Authority Authorisation — restricts which CAs can issue certs | `example.com. IN CAA 0 issue "letsencrypt.org"` |
| **ALIAS / ANAME** | Like CNAME but at zone apex (Route 53 Alias record) | Non-standard; vendor extension |

### CNAME Restrictions

- A CNAME **cannot coexist** with any other record at the same name.
- You **cannot CNAME the zone apex** (`example.com`) in standard DNS. Use an ALIAS/ANAME record (Route 53 Alias, Cloudflare CNAME flattening) for this.
- CNAME chains add latency — each link requires another lookup.

---

## TTL Strategy

```
Low TTL (60–300s)    → fast failover, quick changes, but higher DNS query volume
High TTL (3600–86400s) → fewer queries, better caching, but slow to update

Rule of thumb:
  - Static IPs / CDN origins → 3600s (1 hour) or higher
  - Load balancer endpoints  → 60–300s
  - During incident / migration: temporarily drop to 60s BEFORE making changes,
    then increase after traffic has shifted
```

```bash
# Check current TTL for a record
dig +nocmd api.example.com A +noall +answer
# Output: api.example.com.   300   IN   A   93.184.216.34
#                             ^^^
#                             TTL remaining (as seen by resolver)
```

---

## DNS Tools

```bash
# Basic lookup
dig example.com             # A record by default
dig example.com A           # explicit type
dig example.com MX          # mail records
dig example.com NS          # nameservers
dig example.com TXT         # TXT records
dig example.com ANY         # all records (may be filtered by server)

# Short output
dig +short example.com A

# Query a specific resolver (bypass /etc/resolv.conf)
dig @8.8.8.8 example.com A       # Google
dig @1.1.1.1 example.com A       # Cloudflare
dig @169.254.169.253 example.com  # AWS VPC resolver (from inside EC2)

# Trace the full resolution path
dig +trace example.com

# Reverse DNS lookup
dig -x 93.184.216.34
nslookup 93.184.216.34

# Check TTL as seen from a resolver
dig +nocmd example.com +noall +answer

# nslookup (older, simpler)
nslookup example.com
nslookup example.com 8.8.8.8     # use specific resolver

# Check what /etc/resolv.conf says
cat /etc/resolv.conf
# On cloud instances:
# nameserver 169.254.169.253    ← AWS VPC DNS resolver
# nameserver fd00:ec2::253      ← AWS VPC DNS (IPv6)
```

---

## /etc/hosts — Local Override

```bash
# /etc/hosts format: IP   hostname   [aliases]
127.0.0.1   localhost
10.0.1.50   db.internal db
10.0.1.60   redis.internal

# Hosts file takes precedence over DNS (for that specific name)
# Used for: local dev overrides, container networking, quick testing
# Cloud-init may add entries here automatically (private DNS names)
```

---

## Split-Horizon DNS (Split-View)

The same domain returns different answers depending on where the query originates:

```
Internal clients → db.example.com → 10.0.1.50  (private IP)
External clients → db.example.com → NXDOMAIN or public IP
```

Used to keep internal service addresses from being exposed externally, and to avoid hairpinning traffic through a public IP when both client and server are in the same VPC.

**AWS implementation**: create a **Route 53 Private Hosted Zone** associated with your VPC. DNS queries from within the VPC use the private zone; external queries use the public zone (if it exists).

---

## AWS Route 53

### Route 53 Resolver

- **Default VPC DNS**: `169.254.169.253` (IPv4) or `fd00:ec2::253` (IPv6) — available from any EC2 instance at the VPC base CIDR + 2 address.
- Resolves both public DNS and private hosted zone records.
- Resolves AWS service private endpoints (RDS, ElastiCache, etc.).

### Route 53 Record Types

```bash
# Create an A record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.example.com",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "93.184.216.34"}]
      }
    }]
  }'

# Create an Alias record (points to AWS resource — no TTL needed)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "www.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "my-alb-123456789.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'

# List records in a zone
aws route53 list-resource-record-sets --hosted-zone-id Z1234567890

# Check propagation (test from a different resolver)
dig @8.8.8.8 api.example.com
```

### Route 53 Routing Policies

| Policy | Use case |
|--------|---------|
| **Simple** | Single value; no health checks |
| **Weighted** | A/B testing; gradual traffic shifts |
| **Failover** | Primary/secondary; health-check based |
| **Latency** | Route to lowest-latency region |
| **Geolocation** | Route by user's country/continent |
| **Geoproximity** | Route by physical distance (requires Traffic Flow) |
| **Multivalue Answer** | Up to 8 healthy records; basic load distribution |
| **IP-based** | Route by client IP prefix |

### Resolver Inbound / Outbound Endpoints

For hybrid DNS (on-premises ↔ AWS):

```
On-premises → [Inbound Endpoint] → Route 53 Private Hosted Zone
Route 53   → [Outbound Endpoint] → On-premises DNS server
```

```bash
# List resolver endpoints
aws route53resolver list-resolver-endpoints

# List forwarding rules
aws route53resolver list-resolver-rules
```

---

## Common DNS Issues

| Symptom | Likely cause | Diagnosis |
|---------|-------------|-----------|
| NXDOMAIN for internal service | Missing record in private hosted zone | `dig @169.254.169.253 service.internal` |
| Old IP still resolving | TTL not expired yet | `dig +nocmd host +noall +answer` — check TTL |
| Works from EC2, fails from container | Container using different resolver | Check `/etc/resolv.conf` in container |
| Intermittent failures under load | DNS resolver under load or UDP packet drops | `dig +tcp` (force TCP) |
| CNAME loop | Two CNAMEs pointing at each other | `dig +trace` will show the loop |
| Split-horizon not working | Private hosted zone not associated with VPC | AWS console → PHZ → Associated VPCs |

---

## References

- [RFC 1034 — DNS Concepts](https://www.rfc-editor.org/rfc/rfc1034)
- [RFC 1035 — DNS Implementation](https://www.rfc-editor.org/rfc/rfc1035)
- [AWS Route 53 Developer Guide](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/)
- [Cloudflare: How DNS works](https://www.cloudflare.com/learning/dns/what-is-dns/)
---

← [Previous: TCP/IP](./tcp-ip.md) | [Home](../README.md) | [Next: CIDR & Subnetting →](./cidr-subnetting.md)
