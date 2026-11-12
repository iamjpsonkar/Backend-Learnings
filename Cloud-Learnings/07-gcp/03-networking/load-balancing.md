← [Previous: Firewall Rules](./firewall-rules.md) | [Home](../../README.md) | [Next: Cloud DNS →](./cloud-dns.md)

---

# GCP Load Balancing

GCP offers several managed load balancer types. The Global External HTTPS Load Balancer is the most powerful — it operates at the edge of Google's network (Anycast), supporting HTTP/2, WebSocket, Cloud CDN, Cloud Armor, and serverless NEGs.

---

## Load Balancer Types

| Type | Scope | Layer | Backend Types | Use Case |
|------|-------|-------|---------------|----------|
| **Global External HTTPS** | Global | 7 | MIG, NEG, Serverless NEG, Cloud Storage | Public APIs, web apps |
| **Regional External HTTPS** | Regional | 7 | MIG, NEG | Regional web apps |
| **External TCP/UDP (Network)** | Global/Regional | 4 | MIG | TCP/UDP services |
| **Internal HTTP(S)** | Regional | 7 | MIG, NEG | Internal APIs |
| **Internal TCP/UDP** | Regional | 4 | MIG, Instances | Internal TCP services |
| **Global External TCP Proxy** | Global | 4 | MIG, NEG | TCP (non-HTTP) |

---

## Global HTTPS Load Balancer — Component Chain

```
Client
  │
  ▼
Global External IP (Anycast)
  │
  ▼
Forwarding Rule (port 443 → target HTTPS proxy)
  │
  ▼
Target HTTPS Proxy (SSL certificate attached)
  │
  ▼
URL Map (host/path routing → backend services)
  │
  ├── /api/* → Backend Service: api-backend (NEG with Cloud Run)
  └── /* → Backend Service: web-backend (MIG with GCE instances)
            │
            ▼
        Backend Service (health check, session affinity, CDN config)
            │
            ▼
        Instance Group (MIG) or NEG
```

---

## Creating a Global HTTPS Load Balancer

```bash
PROJECT="my-app-prod-123456"
BACKEND_REGION="us-central1"

# 1. Reserve a global static IP
gcloud compute addresses create lb-ip-my-app \
    --project=$PROJECT \
    --global \
    --ip-version=IPV4

LB_IP=$(gcloud compute addresses describe lb-ip-my-app \
    --global --project=$PROJECT --format="value(address)")
echo "LB IP: $LB_IP"  # Configure DNS A record to this IP

# 2. Create health check
gcloud compute health-checks create http hc-my-app \
    --project=$PROJECT \
    --port=8080 \
    --request-path=/healthz \
    --check-interval=10 \
    --timeout=5 \
    --healthy-threshold=2 \
    --unhealthy-threshold=3

# 3. Create backend service
gcloud compute backend-services create bs-my-app \
    --project=$PROJECT \
    --global \
    --protocol=HTTP \
    --port-name=http \
    --health-checks=hc-my-app \
    --enable-cdn \
    --connection-draining-timeout=30 \
    --session-affinity=NONE

# 4. Add backend (MIG or NEG) to backend service
# For a Managed Instance Group:
gcloud compute backend-services add-backend bs-my-app \
    --project=$PROJECT \
    --global \
    --instance-group=mig-my-app-us-central1 \
    --instance-group-region=$BACKEND_REGION \
    --balancing-mode=UTILIZATION \
    --max-utilization=0.8 \
    --capacity-scaler=1.0

# For a Serverless NEG (Cloud Run):
gcloud compute network-endpoint-groups create neg-cloud-run-my-app \
    --project=$PROJECT \
    --region=$BACKEND_REGION \
    --network-endpoint-type=SERVERLESS \
    --cloud-run-service=my-app

gcloud compute backend-services add-backend bs-my-app \
    --project=$PROJECT \
    --global \
    --network-endpoint-group=neg-cloud-run-my-app \
    --network-endpoint-group-region=$BACKEND_REGION

# 5. Create URL map
gcloud compute url-maps create url-map-my-app \
    --project=$PROJECT \
    --default-service=bs-my-app

# Add path-based routing
gcloud compute url-maps import url-map-my-app \
    --project=$PROJECT \
    --global \
    --source=- <<EOF
defaultService: projects/$PROJECT/global/backendServices/bs-my-app
hostRules:
  - hosts: ["my-app.example.com"]
    pathMatcher: main
  - hosts: ["api.example.com"]
    pathMatcher: api
pathMatchers:
  - name: main
    defaultService: projects/$PROJECT/global/backendServices/bs-my-app
  - name: api
    defaultService: projects/$PROJECT/global/backendServices/bs-api
    pathRules:
      - paths: ["/v1/*"]
        service: projects/$PROJECT/global/backendServices/bs-api-v1
      - paths: ["/v2/*"]
        service: projects/$PROJECT/global/backendServices/bs-api-v2
EOF

# 6. Create SSL certificate (Google-managed — auto-renewed)
gcloud compute ssl-certificates create cert-my-app \
    --project=$PROJECT \
    --domains=my-app.example.com,www.my-app.example.com \
    --global

# 7. Create HTTPS target proxy
gcloud compute target-https-proxies create proxy-my-app \
    --project=$PROJECT \
    --url-map=url-map-my-app \
    --ssl-certificates=cert-my-app \
    --global

# 8. Create forwarding rule (ties everything together)
gcloud compute forwarding-rules create fr-my-app-https \
    --project=$PROJECT \
    --global \
    --ip-address=lb-ip-my-app \
    --ip-protocol=TCP \
    --ports=443 \
    --target-https-proxy=proxy-my-app

# HTTP → HTTPS redirect
gcloud compute url-maps import url-map-http-redirect \
    --project=$PROJECT --global --source=- <<EOF
defaultUrlRedirect:
  httpsRedirect: true
  redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
EOF

gcloud compute target-http-proxies create proxy-my-app-http \
    --project=$PROJECT \
    --url-map=url-map-http-redirect

gcloud compute forwarding-rules create fr-my-app-http \
    --project=$PROJECT \
    --global \
    --ip-address=lb-ip-my-app \
    --ip-protocol=TCP \
    --ports=80 \
    --target-http-proxy=proxy-my-app-http
```

---

## Cloud CDN

```bash
# Enable Cloud CDN on a backend service (already done with --enable-cdn above)
# Configure CDN policy
gcloud compute backend-services update bs-my-app \
    --project=$PROJECT \
    --global \
    --cache-mode=CACHE_ALL_STATIC \
    --default-ttl=3600 \
    --max-ttl=86400 \
    --client-ttl=600 \
    --negative-caching

# Invalidate CDN cache
gcloud compute url-maps invalidate-cdn-cache url-map-my-app \
    --project=$PROJECT \
    --global \
    --path="/*"

gcloud compute url-maps invalidate-cdn-cache url-map-my-app \
    --project=$PROJECT \
    --global \
    --path="/static/app.js"
```

---

## Internal Load Balancer

```bash
# Internal HTTPS load balancer (for microservices within VPC)
gcloud compute addresses create lb-internal-ip \
    --project=$PROJECT \
    --region=$BACKEND_REGION \
    --subnet=subnet-app-us-central1 \
    --addresses=10.0.10.100 \
    --purpose=SHARED_LOADBALANCER_VIP

gcloud compute backend-services create bs-internal-api \
    --project=$PROJECT \
    --load-balancing-scheme=INTERNAL_MANAGED \
    --protocol=HTTP \
    --region=$BACKEND_REGION \
    --health-checks=hc-my-app \
    --health-checks-region=$BACKEND_REGION

gcloud compute url-maps create url-map-internal \
    --project=$PROJECT \
    --default-service=bs-internal-api \
    --region=$BACKEND_REGION

gcloud compute target-http-proxies create proxy-internal \
    --project=$PROJECT \
    --url-map=url-map-internal \
    --region=$BACKEND_REGION

gcloud compute forwarding-rules create fr-internal \
    --project=$PROJECT \
    --region=$BACKEND_REGION \
    --load-balancing-scheme=INTERNAL_MANAGED \
    --network=vpc-my-app-prod \
    --subnet=subnet-app-us-central1 \
    --ip-address=lb-internal-ip \
    --ports=80 \
    --target-http-proxy=proxy-internal \
    --target-http-proxy-region=$BACKEND_REGION
```

---

## Viewing LB Status

```bash
# List forwarding rules
gcloud compute forwarding-rules list --project=$PROJECT --format="table(name,IPAddress,IPProtocol,ports,target)"

# Check SSL certificate provisioning status
gcloud compute ssl-certificates describe cert-my-app \
    --project=$PROJECT --global \
    --format="table(name,managed.status,managed.domainStatus)"
# Status will be PROVISIONING initially, then ACTIVE once DNS is pointing to LB_IP

# View backend health
gcloud compute backend-services get-health bs-my-app \
    --project=$PROJECT --global \
    --format="json"
```

---

## References

- [Cloud Load Balancing overview](https://cloud.google.com/load-balancing/docs/load-balancing-overview)
- [External HTTPS load balancer](https://cloud.google.com/load-balancing/docs/https)
- [Google-managed SSL certificates](https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs)
- [Cloud CDN](https://cloud.google.com/cdn/docs)

---

← [Previous: Firewall Rules](./firewall-rules.md) | [Home](../../README.md) | [Next: Cloud DNS →](./cloud-dns.md)
