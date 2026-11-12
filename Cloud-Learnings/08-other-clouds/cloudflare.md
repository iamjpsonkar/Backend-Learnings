← [Previous: DigitalOcean](./digitalocean.md) | [Home](../README.md) | [Next: Containers →](../09-containers/README.md)

---

# Cloudflare

Cloudflare operates the world's largest edge network — 300+ Points of Presence (PoPs) globally. Unlike traditional cloud providers, Cloudflare focuses on the **edge layer**: DDoS protection, CDN, DNS, Zero Trust access, and edge compute. It complements AWS/Azure/GCP rather than replacing them.

---

## Key Differentiators

| Feature | Detail |
|---------|--------|
| **Global anycast network** | 300+ PoPs, Tier-1 ISP peering — traffic handled at the edge closest to users |
| **Workers** | JavaScript/WASM edge compute running at every PoP — sub-1ms response times possible |
| **R2** | S3-compatible object storage with **zero egress fees** |
| **D1** | Serverless SQLite database running at the edge |
| **Zero Trust** | Access (ZTNA), Gateway (SWG), Tunnel (replaces VPN) — no traditional firewall needed |
| **Magic Transit** | BGP-advertised DDoS protection for on-premises or custom IP prefixes |
| **Free tier** | Generous: unlimited CDN bandwidth, 100K Workers requests/day |

---

## Service Equivalents

| AWS | Cloudflare |
|-----|-----------|
| CloudFront | CDN |
| Lambda@Edge | Workers |
| S3 | R2 |
| Aurora Serverless | D1 (SQLite at edge) |
| API Gateway | Workers (HTTP routing) |
| Route 53 | DNS (authoritative + proxy) |
| WAF | WAF |
| Shield Advanced | DDoS Protection |
| Client VPN | Access (ZTNA) |
| Direct Connect | Magic WAN |
| — | Tunnel (zero-trust private network) |

---

## CLI Setup (Wrangler)

```bash
# Install Wrangler (official Cloudflare CLI)
npm install -g wrangler

# Authenticate
wrangler login
# Opens browser — authorize with your Cloudflare account

# Verify
wrangler whoami

# List accounts
wrangler accounts list

# Set CLOUDFLARE_API_TOKEN for CI/CD
export CLOUDFLARE_API_TOKEN="your-api-token"
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
```

---

## DNS

Cloudflare provides authoritative DNS with optional **proxy mode** (orange cloud) that routes traffic through Cloudflare's network, enabling CDN, WAF, and DDoS protection.

```bash
ZONE_ID="your-zone-id"
API_TOKEN="your-api-token"

# Add an A record with proxy enabled (CDN + DDoS protection)
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    --data '{
        "type": "A",
        "name": "my-app.example.com",
        "content": "1.2.3.4",
        "ttl": 1,
        "proxied": true
    }'

# Add a CNAME pointing to an origin server
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    --data '{
        "type": "CNAME",
        "name": "api",
        "content": "my-app-api.us-east-1.elb.amazonaws.com",
        "proxied": true
    }'

# List DNS records
curl "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records" \
    -H "Authorization: Bearer ${API_TOKEN}" | jq '.result[] | {name: .name, type: .type, content: .content, proxied: .proxied}'
```

---

## CDN and Caching

```bash
# Purge entire cache
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    --data '{"purge_everything": true}'

# Purge specific files
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    --data '{"files": ["https://example.com/index.html", "https://example.com/app.js"]}'
```

### Cache Rules (Page Rules replacement)

Configure in the Cloudflare dashboard or via Terraform:

```hcl
# terraform — cache rule to cache all static assets for 1 year
resource "cloudflare_ruleset" "cache_static" {
  zone_id = var.zone_id
  name    = "Cache static assets"
  kind    = "zone"
  phase   = "http_request_cache_settings"

  rules {
    action = "set_cache_settings"
    action_parameters {
      edge_ttl {
        mode    = "override_origin"
        default = 31536000  # 1 year
      }
      browser_ttl {
        mode    = "override_origin"
        default = 86400  # 1 day
      }
    }
    expression  = "(http.request.uri.path matches \"^/static/\" or http.request.uri.path matches \"^/assets/\")"
    description = "Cache static assets for 1 year at edge"
    enabled     = true
  }
}
```

---

## Workers (Edge Compute)

Workers run JavaScript (or WASM) at every Cloudflare PoP. Ideal for: A/B testing, auth at the edge, request transformation, API routing, lightweight APIs.

```bash
# Create a new Worker project
wrangler init my-edge-api --template=hello-world
cd my-edge-api

# Run locally (with live-reload)
wrangler dev

# Deploy to production
wrangler deploy
```

### Worker Examples

```javascript
// src/index.js — Router with caching, auth check, and origin forwarding
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // A/B test: randomly route 10% to new API version
    if (url.pathname.startsWith("/api/") && Math.random() < 0.1) {
      url.hostname = "api-v2.internal.example.com";
      return fetch(url.toString(), request);
    }

    // Block requests without a valid API key header
    const apiKey = request.headers.get("X-Api-Key");
    if (url.pathname.startsWith("/api/internal/") && apiKey !== env.INTERNAL_API_KEY) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Cache GET requests for 60 seconds using the Cache API
    if (request.method === "GET") {
      const cache = caches.default;
      const cached = await cache.match(request);
      if (cached) return cached;

      const response = await fetch(request);
      if (response.ok) {
        const toCache = new Response(response.body, response);
        toCache.headers.set("Cache-Control", "public, max-age=60");
        ctx.waitUntil(cache.put(request, toCache.clone()));
        return toCache;
      }
      return response;
    }

    return fetch(request);
  },
};
```

```toml
# wrangler.toml
name = "my-edge-api"
main = "src/index.js"
compatibility_date = "2024-06-01"

[vars]
APP_ENV = "production"

[[bindings]]
# R2 binding
type = "r2_bucket"
name = "ASSETS"
bucket_name = "my-app-assets"

[[bindings]]
# D1 binding
type = "d1"
name = "DB"
database_name = "my-app-db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

[[bindings]]
# KV binding (key-value store at the edge)
type = "kv_namespace"
name = "SESSIONS"
id = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

---

## R2 (Object Storage — Zero Egress)

R2 is S3-compatible with no egress fees. Use it for assets served through Cloudflare's CDN, large media files, or as a cheaper alternative to S3 for frequently read data.

```bash
# Create a bucket
wrangler r2 bucket create my-app-assets

# Upload an object
wrangler r2 object put my-app-assets/reports/2024/report.pdf \
    --file ./report.pdf \
    --content-type application/pdf

# List objects
wrangler r2 object list my-app-assets

# Download
wrangler r2 object get my-app-assets/reports/2024/report.pdf \
    --file /tmp/report.pdf

# Delete
wrangler r2 object delete my-app-assets/reports/2024/report.pdf
```

```javascript
// Access R2 from a Worker (bound as env.ASSETS)
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const key = url.pathname.slice(1);  // strip leading /

    const object = await env.ASSETS.get(key);
    if (!object) {
      return new Response("Not found", { status: 404 });
    }

    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set("etag", object.httpEtag);

    return new Response(object.body, { headers });
  },
};
```

```python
# Access R2 from a Python service (boto3 with R2 endpoint)
import boto3
import os

r2_client = boto3.client(
    "s3",
    endpoint_url=f"https://{os.environ['CF_ACCOUNT_ID']}.r2.cloudflarestorage.com",
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    region_name="auto",  # R2 uses "auto"
)

r2_client.upload_file(
    "./report.pdf",
    "my-app-assets",
    "reports/2024/report.pdf",
    ExtraArgs={"ContentType": "application/pdf"},
)
```

---

## D1 (SQLite at the Edge)

D1 is a serverless relational database built on SQLite, accessible from Workers.

```bash
# Create a D1 database
wrangler d1 create my-app-db

# Run migrations
wrangler d1 execute my-app-db --file ./schema.sql

# Query from CLI (testing)
wrangler d1 execute my-app-db \
    --command "SELECT * FROM orders WHERE status = 'created' LIMIT 10"
```

```sql
-- schema.sql
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    total_usd REAL NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
```

```javascript
// Access D1 from a Worker (bound as env.DB)
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/orders" && request.method === "GET") {
      const customerId = url.searchParams.get("customerId");
      const { results } = await env.DB.prepare(
        "SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC LIMIT 20"
      ).bind(customerId).all();

      return Response.json(results);
    }

    if (url.pathname === "/orders" && request.method === "POST") {
      const body = await request.json();
      await env.DB.prepare(
        "INSERT INTO orders (order_id, customer_id, total_usd) VALUES (?, ?, ?)"
      ).bind(body.orderId, body.customerId, body.totalUsd).run();

      return Response.json({ status: "created" }, { status: 201 });
    }

    return new Response("Not found", { status: 404 });
  },
};
```

---

## Zero Trust (Access + Tunnel)

### Cloudflare Tunnel

Tunnel creates a secure outbound-only connection from your origin server to Cloudflare — no inbound firewall rules or public IPs needed.

```bash
# Install cloudflared
# macOS: brew install cloudflared
# Linux: download from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/

# Authenticate
cloudflared tunnel login

# Create a tunnel
cloudflared tunnel create my-app-tunnel

TUNNEL_ID=$(cloudflared tunnel list --output json | jq -r '.[] | select(.name=="my-app-tunnel") | .id')

# Create a config file
cat > ~/.cloudflared/config.yml <<EOF
tunnel: $TUNNEL_ID
credentials-file: /root/.cloudflared/${TUNNEL_ID}.json

ingress:
  - hostname: my-app.example.com
    service: http://localhost:8080
  - hostname: api.example.com
    service: http://localhost:8081
  - service: http_status:404
EOF

# Route a hostname through the tunnel
cloudflared tunnel route dns my-app-tunnel my-app.example.com

# Run the tunnel (as a systemd service in production)
cloudflared tunnel run my-app-tunnel

# Install as a system service
sudo cloudflared service install
sudo systemctl start cloudflared
```

### Cloudflare Access (Zero Trust Application Access)

```bash
# Create an Access application (dashboard or Terraform)
# Users must authenticate via your identity provider (Okta, Google, GitHub, etc.)
# before reaching the origin — enforced at the edge

# Terraform example
resource "cloudflare_access_application" "my_app" {
  zone_id          = var.zone_id
  name             = "My App Internal Dashboard"
  domain           = "dashboard.example.com"
  session_duration = "8h"
  type             = "self_hosted"
}

resource "cloudflare_access_policy" "engineers" {
  application_id = cloudflare_access_application.my_app.id
  zone_id        = var.zone_id
  name           = "Engineers"
  precedence     = 1
  decision       = "allow"

  include {
    email_domain = ["example.com"]
    group        = [cloudflare_access_group.engineers.id]
  }
}
```

---

## WAF (Web Application Firewall)

```bash
# Create a WAF rule via API
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/rulesets" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    --data '{
        "name": "My App WAF Rules",
        "kind": "zone",
        "phase": "http_request_firewall_custom",
        "rules": [
            {
                "action": "block",
                "expression": "(ip.geoip.country in {\"CN\" \"RU\"} and not cf.client.bot)",
                "description": "Block high-risk countries (non-bot)"
            },
            {
                "action": "challenge",
                "expression": "cf.threat_score gt 25",
                "description": "Challenge high threat score IPs"
            }
        ]
    }'
```

---

## Pricing Snapshot

| Service | Free | Paid |
|---------|------|------|
| DNS | Unlimited | Unlimited |
| CDN | Unlimited bandwidth | Unlimited |
| Workers | 100K req/day | $5/mo for 10M req |
| R2 | 10 GB storage, 1M ops | $0.015/GB/mo, no egress |
| D1 | 5 GB, 5M reads, 100K writes/day | $0.001/100K reads |
| KV | 100K reads, 1K writes/day | $0.50/million reads |
| Access | 50 users free | $7/user/mo |
| Tunnel | Free | Free |

---

## References

- [Cloudflare Workers documentation](https://developers.cloudflare.com/workers/)
- [R2 documentation](https://developers.cloudflare.com/r2/)
- [D1 documentation](https://developers.cloudflare.com/d1/)
- [Cloudflare Zero Trust](https://developers.cloudflare.com/cloudflare-one/)
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [Wrangler CLI reference](https://developers.cloudflare.com/workers/wrangler/)
---

← [Previous: DigitalOcean](./digitalocean.md) | [Home](../README.md) | [Next: Containers →](../09-containers/README.md)
