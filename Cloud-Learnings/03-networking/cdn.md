← [Previous: HTTP/HTTPS/TLS](./http-https-tls.md) | [Home](../README.md) | [Next: Zero Trust →](./zero-trust.md)

---

# CDN — Content Delivery Networks

A CDN distributes content across a global network of edge servers, serving requests from the location closest to the user. This reduces latency, offloads origin servers, and improves availability.

---

## How a CDN Works

```
Without CDN:
  User (Tokyo) ──────────────────────── request ──────────────▶ Origin (us-east-1)
                ◀────────────────────── response ─────────────── ~150ms RTT

With CDN:
  User (Tokyo) ─── request ──▶ Edge (Tokyo PoP) ──── cache hit ──▶ User
                               (if miss: fetch from origin, cache, serve)
                               ~5ms RTT for cached content
```

### Cache Hit vs Cache Miss

- **Cache HIT**: edge has the content in cache, serves immediately
- **Cache MISS**: edge fetches from origin, caches the response, serves to user
- **Cache BYPASS**: request goes directly to origin (e.g., authenticated user, dynamic content)

**Cache hit ratio** is the percentage of requests served from cache. Higher is better — aim for >80% for static content.

---

## What to Cache (and What Not To)

### Cache (safe)

- Static assets: JS, CSS, images, fonts (`/static/`, `/assets/`)
- Versioned files: `app.a1b2c3.js` (cache-bust with content hash in filename)
- Public API responses that change infrequently (with appropriate TTL)
- Large binary downloads

### Do NOT cache (or cache very briefly)

- Authenticated responses — each user should get their own data
- Dynamic pages with user-specific content
- Real-time data (stock prices, live scores)
- Session cookies / auth tokens in response bodies
- HTML that changes frequently (use cache-control: no-store or short TTL)

---

## Cache-Control Headers

The `Cache-Control` header tells both CDN edge nodes and browsers how to cache a response.

```
Cache-Control: max-age=3600, public
│                             └── can be cached by CDN + browser
│              └── cache for 3600 seconds (1 hour)
└── directive

Cache-Control: no-store                     # never cache anywhere
Cache-Control: no-cache                     # always revalidate before serving from cache
Cache-Control: private, max-age=0           # browser cache only, not CDN
Cache-Control: public, max-age=86400        # CDN + browser, 1 day
Cache-Control: public, max-age=31536000, immutable  # 1 year, content won't change
Cache-Control: s-maxage=3600, max-age=60    # CDN: 1 hour; browser: 1 minute
```

| Directive | Meaning |
|-----------|---------|
| `public` | Can be cached by CDN and browser |
| `private` | Browser cache only; not CDN |
| `no-store` | Do not cache anywhere |
| `no-cache` | Cache but revalidate on every use |
| `max-age=N` | Cache for N seconds (browser + CDN) |
| `s-maxage=N` | Cache for N seconds on CDN only (overrides max-age for CDN) |
| `immutable` | Tells browser not to revalidate during max-age (for versioned assets) |
| `stale-while-revalidate=N` | Serve stale content while fetching fresh in background |

---

## Cache Validation (Conditional Requests)

When a cached item expires, the CDN can revalidate with the origin instead of downloading the full content again:

### ETag-based

```
Origin response:     ETag: "abc123"
Later browser GET:   If-None-Match: "abc123"
Origin (unchanged):  304 Not Modified (no body)  ← saves bandwidth
Origin (changed):    200 OK + new ETag           ← returns new content
```

### Last-Modified-based

```
Origin response:     Last-Modified: Wed, 21 Oct 2024 07:28:00 GMT
Later GET:           If-Modified-Since: Wed, 21 Oct 2024 07:28:00 GMT
Origin (unchanged):  304 Not Modified
```

---

## Amazon CloudFront

CloudFront is AWS's CDN with 450+ edge locations (Points of Presence) worldwide.

### Key Concepts

| Term | Meaning |
|------|---------|
| **Distribution** | A CloudFront configuration (one or more origins, behaviours, settings) |
| **Origin** | Where CloudFront fetches content from (S3, ALB, EC2, custom HTTP server) |
| **Behaviour** | Rules that map URL paths to origins and cache settings |
| **Edge location** | A PoP that caches content and serves users |
| **Regional Edge Cache** | Larger intermediate cache layer between edges and origin |
| **OAC / OAI** | Origin Access Control/Identity — restricts S3 access to CloudFront only |

### Creating a Distribution

```bash
# Simple distribution: S3 static site with OAC
aws cloudfront create-distribution \
    --distribution-config '{
        "CallerReference": "my-dist-001",
        "Origins": {
            "Quantity": 1,
            "Items": [{
                "Id": "s3-origin",
                "DomainName": "my-bucket.s3.us-east-1.amazonaws.com",
                "S3OriginConfig": {
                    "OriginAccessIdentity": ""
                },
                "OriginAccessControlId": "E1XXXXXXXXXXXXX"
            }]
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "s3-origin",
            "ViewerProtocolPolicy": "redirect-to-https",
            "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
            "Compress": true
        },
        "Enabled": true,
        "Comment": "My static site CDN"
    }'

# List distributions
aws cloudfront list-distributions \
    --query 'DistributionList.Items[*].{ID:Id,Domain:DomainName,Status:Status}'

# Get distribution status
aws cloudfront get-distribution --id E1XXXXXXXXXXXXX \
    --query 'Distribution.Status'
```

### Cache Policies

CloudFront Cache Policies define what goes into the cache key and the TTL:

```bash
# Create a cache policy
aws cloudfront create-cache-policy \
    --cache-policy-config '{
        "Name": "api-cache-policy",
        "DefaultTTL": 300,
        "MaxTTL": 3600,
        "MinTTL": 0,
        "ParametersInCacheKeyAndForwardedToOrigin": {
            "EnableAcceptEncodingGzip": true,
            "EnableAcceptEncodingBrotli": true,
            "HeadersConfig": {
                "HeaderBehavior": "none"
            },
            "QueryStringsConfig": {
                "QueryStringBehavior": "whitelist",
                "QueryStrings": {
                    "Quantity": 1,
                    "Items": ["version"]
                }
            },
            "CookiesConfig": {
                "CookieBehavior": "none"
            }
        }
    }'
```

**Managed cache policies** (built-in):
- `CachingOptimized` — maximises cache hits; for S3 static content
- `CachingDisabled` — forward all requests to origin; for dynamic content
- `CachingOptimizedForUncompressedObjects` — no compression negotiation

### Cache Invalidation

When you update content at the origin, cached copies at edge nodes remain until TTL expires. Force immediate expiry with an invalidation:

```bash
# Invalidate specific paths
aws cloudfront create-invalidation \
    --distribution-id E1XXXXXXXXXXXXX \
    --paths "/index.html" "/static/app.js"

# Invalidate all files (wildcard)
aws cloudfront create-invalidation \
    --distribution-id E1XXXXXXXXXXXXX \
    --paths "/*"

# Check invalidation status
aws cloudfront list-invalidations \
    --distribution-id E1XXXXXXXXXXXXX
```

> **Cost**: First 1,000 invalidation paths per month are free; after that, $0.005 per path. Use **versioned filenames** (`app.a1b2c3.js`) instead of invalidations for static assets — no cost, instantaneous, and old versions remain cached for existing users.

### Custom Domain and HTTPS

```bash
# 1. Request ACM certificate (must be in us-east-1 for CloudFront)
aws acm request-certificate \
    --region us-east-1 \
    --domain-name cdn.example.com \
    --validation-method DNS

# 2. Add CNAME to your distribution with the certificate
aws cloudfront update-distribution \
    --id E1XXXXXXXXXXXXX \
    --distribution-config '{
        ...
        "Aliases": {
            "Quantity": 1,
            "Items": ["cdn.example.com"]
        },
        "ViewerCertificate": {
            "ACMCertificateArn": "arn:aws:acm:us-east-1:...:certificate/...",
            "SSLSupportMethod": "sni-only",
            "MinimumProtocolVersion": "TLSv1.2_2021"
        }
    }'

# 3. Create Route 53 Alias record
# cdn.example.com → ALIAS → xxxxxxxxxxxx.cloudfront.net
```

### Origin Access Control (OAC) for S3

Restricts S3 bucket access so only CloudFront can read it — prevents bypassing the CDN.

```bash
# Create OAC
aws cloudfront create-origin-access-control \
    --origin-access-control-config '{
        "Name": "my-oac",
        "SigningBehavior": "always",
        "SigningProtocol": "sigv4",
        "OriginAccessControlOriginType": "s3"
    }'

# S3 bucket policy (allow CloudFront service principal)
# {
#   "Effect": "Allow",
#   "Principal": {"Service": "cloudfront.amazonaws.com"},
#   "Action": "s3:GetObject",
#   "Resource": "arn:aws:s3:::my-bucket/*",
#   "Condition": {
#     "StringEquals": {
#       "AWS:SourceArn": "arn:aws:cloudfront::123456789012:distribution/E1XXXXX"
#     }
#   }
# }
```

### CloudFront Functions and Lambda@Edge

Run code at edge locations for request/response manipulation:

| | CloudFront Functions | Lambda@Edge |
|--|---------------------|-------------|
| Trigger | Viewer request/response only | Viewer + origin request/response |
| Runtime | JavaScript (ES5.1) | Node.js, Python |
| Max execution time | 1ms | 5s (viewer), 30s (origin) |
| Memory | 2MB | 128MB–10GB |
| Use cases | URL rewriting, header manipulation, redirects, auth tokens | Complex auth (JWT validation), A/B testing, image resizing |

```javascript
// CloudFront Function: redirect /home → /
function handler(event) {
    var request = event.request;
    if (request.uri === '/home') {
        return {
            statusCode: 301,
            statusDescription: 'Moved Permanently',
            headers: {location: {value: '/'}}
        };
    }
    return request;
}
```

---

## CloudFront Monitoring

```bash
# View cache statistics (CloudWatch metrics)
aws cloudwatch get-metric-statistics \
    --namespace AWS/CloudFront \
    --metric-name CacheHitRate \
    --dimensions Name=DistributionId,Value=E1XXXXXXXXXXXXX \
    --start-time 2024-01-15T00:00:00Z \
    --end-time 2024-01-15T23:59:59Z \
    --period 3600 \
    --statistics Average

# Enable real-time logs for debugging (high-cost, use temporarily)
aws cloudfront create-realtime-log-config \
    --end-points '{...}' \
    --fields "timestamp" "c-ip" "cs-method" "cs-uri-stem" "sc-status" "x-edge-result-type"
```

---

## References

- [AWS CloudFront documentation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/)
- [AWS managed cache policies](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html)
- [CloudFront Functions documentation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-functions.html)
- [MDN: HTTP caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)
---

← [Previous: HTTP/HTTPS/TLS](./http-https-tls.md) | [Home](../README.md) | [Next: Zero Trust →](./zero-trust.md)
