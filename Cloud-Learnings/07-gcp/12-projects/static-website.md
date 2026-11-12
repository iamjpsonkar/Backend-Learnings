← [Previous: GCP Projects](./README.md) | [Home](../../README.md) | [Next: GKE Microservice →](./gke-microservice.md)

---

# Project: Static Website with Cloud CDN

Deploy a static website on Cloud Storage with Cloud CDN, a custom domain, HTTPS via a Google-managed certificate, and a GitHub Actions CI/CD pipeline.

---

## Architecture

```
GitHub Actions
    │
    ▼
Cloud Storage bucket (static hosting)
    │
    ▼
Cloud CDN (global edge caching)
    │
    ▼
Global HTTPS Load Balancer
    │
    ▼
Custom domain (api.my-app.com) with Google-managed SSL cert
```

---

## 1. Storage Bucket

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"
DOMAIN="www.my-app.com"
BUCKET="my-app-prod-website"

# Create website bucket
gcloud storage buckets create gs://$BUCKET \
    --project=$PROJECT \
    --location=us \
    --uniform-bucket-level-access \
    --web-main-page-suffix=index.html \
    --web-error-page=404.html

# Allow public read
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
    --member="allUsers" \
    --role="roles/storage.objectViewer"

# Upload site
gcloud storage cp -r ./dist/* gs://$BUCKET/ \
    --project=$PROJECT \
    --cache-control="public, max-age=31536000"  # 1-year cache for immutable assets

# Set shorter cache for HTML (so users get updates quickly)
gcloud storage objects update "gs://$BUCKET/index.html" \
    --cache-control="public, max-age=300"
```

---

## 2. Load Balancer + CDN

```bash
# Reserve a global static IP
gcloud compute addresses create website-ip \
    --project=$PROJECT \
    --global \
    --ip-version=IPV4

STATIC_IP=$(gcloud compute addresses describe website-ip \
    --project=$PROJECT \
    --global \
    --format="value(address)")
echo "Static IP: $STATIC_IP"
# → Point your DNS A record to this IP

# Create backend bucket with Cloud CDN enabled
gcloud compute backend-buckets create backend-website \
    --project=$PROJECT \
    --gcs-bucket-name=$BUCKET \
    --enable-cdn \
    --cache-mode=CACHE_ALL_STATIC \
    --default-ttl=3600 \
    --max-ttl=86400 \
    --client-ttl=300 \
    --negative-caching \
    --description="Website CDN backend"

# URL map (root → backend bucket, /api/* → backend service)
gcloud compute url-maps create urlmap-website \
    --project=$PROJECT \
    --default-backend-bucket=backend-website

# Add path matcher for API traffic (if applicable)
gcloud compute url-maps add-path-matcher urlmap-website \
    --project=$PROJECT \
    --path-matcher-name=api-paths \
    --default-backend-bucket=backend-website \
    --backend-service-path-rules="/api/*=bs-my-app-api"

# Google-managed SSL certificate
gcloud compute ssl-certificates create cert-website \
    --project=$PROJECT \
    --domains=$DOMAIN \
    --global

# HTTPS proxy
gcloud compute target-https-proxies create https-proxy-website \
    --project=$PROJECT \
    --url-map=urlmap-website \
    --ssl-certificates=cert-website

# Forwarding rule (HTTPS)
gcloud compute forwarding-rules create fr-website-https \
    --project=$PROJECT \
    --global \
    --target-https-proxy=https-proxy-website \
    --address=website-ip \
    --ports=443

# HTTP → HTTPS redirect
gcloud compute url-maps import urlmap-http-redirect \
    --project=$PROJECT \
    --global \
    --source=<(cat <<EOF
name: urlmap-http-redirect
defaultUrlRedirect:
  httpsRedirect: true
  redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
EOF
)

gcloud compute target-http-proxies create http-proxy-redirect \
    --project=$PROJECT \
    --url-map=urlmap-http-redirect

gcloud compute forwarding-rules create fr-website-http \
    --project=$PROJECT \
    --global \
    --target-http-proxy=http-proxy-redirect \
    --address=website-ip \
    --ports=80
```

---

## 3. CDN Cache Invalidation

```bash
# Invalidate all cached objects (on deploy)
gcloud compute url-maps invalidate-cdn-cache urlmap-website \
    --project=$PROJECT \
    --path="/*" \
    --async

# Invalidate specific paths
gcloud compute url-maps invalidate-cdn-cache urlmap-website \
    --project=$PROJECT \
    --path="/index.html"
```

---

## 4. GitHub Actions CI/CD

```yaml
# .github/workflows/deploy-website.yml
name: Deploy Website

on:
  push:
    branches: [main]
    paths: ["frontend/**"]

permissions:
  id-token: write
  contents: read

env:
  PROJECT_ID: my-app-prod-123456
  BUCKET: my-app-prod-website

jobs:
  deploy:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build
        env:
          VITE_API_URL: https://api.my-app.com

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.DEPLOY_SA_EMAIL }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Upload to Cloud Storage
        run: |
          # Upload immutable assets with long cache
          gcloud storage cp -r dist/assets gs://${{ env.BUCKET }}/assets/ \
              --cache-control="public, max-age=31536000, immutable"

          # Upload HTML with short cache
          gcloud storage cp dist/index.html gs://${{ env.BUCKET }}/index.html \
              --cache-control="public, max-age=300"

          # Upload other files
          gcloud storage rsync -r -d dist/ gs://${{ env.BUCKET }}/ \
              --exclude="assets/.*"

      - name: Invalidate CDN
        run: |
          gcloud compute url-maps invalidate-cdn-cache urlmap-website \
              --project=${{ env.PROJECT_ID }} \
              --path="/*"

      - name: Notify
        if: always()
        run: echo "Deploy complete — ${{ job.status }}"
```

---

## 5. Terraform (Infrastructure as Code)

```hcl
# infra/website.tf
resource "google_storage_bucket" "website" {
  name                        = "${var.project_id}-website"
  project                     = var.project_id
  location                    = "US"
  force_destroy               = false
  uniform_bucket_level_access = true

  website {
    main_page_suffix = "index.html"
    not_found_page   = "404.html"
  }
}

resource "google_storage_bucket_iam_member" "public_read" {
  bucket = google_storage_bucket.website.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

resource "google_compute_backend_bucket" "website" {
  name        = "backend-website"
  project     = var.project_id
  bucket_name = google_storage_bucket.website.name
  enable_cdn  = true

  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    default_ttl       = 3600
    max_ttl           = 86400
    client_ttl        = 300
    negative_caching  = true
  }
}

resource "google_compute_global_address" "website" {
  name    = "website-ip"
  project = var.project_id
}

resource "google_compute_managed_ssl_certificate" "website" {
  name    = "cert-website"
  project = var.project_id

  managed {
    domains = [var.domain]
  }
}

resource "google_compute_url_map" "website" {
  name            = "urlmap-website"
  project         = var.project_id
  default_service = google_compute_backend_bucket.website.id
}

resource "google_compute_target_https_proxy" "website" {
  name             = "https-proxy-website"
  project          = var.project_id
  url_map          = google_compute_url_map.website.id
  ssl_certificates = [google_compute_managed_ssl_certificate.website.id]
}

resource "google_compute_global_forwarding_rule" "website_https" {
  name       = "fr-website-https"
  project    = var.project_id
  target     = google_compute_target_https_proxy.website.id
  ip_address = google_compute_global_address.website.address
  port_range = "443"
}

output "website_ip" {
  value = google_compute_global_address.website.address
}
```

---

## References

- [Cloud Storage static website](https://cloud.google.com/storage/docs/hosting-static-website)
- [Cloud CDN documentation](https://cloud.google.com/cdn/docs)
- [Google-managed SSL certificates](https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs)

---

← [Previous: GCP Projects](./README.md) | [Home](../../README.md) | [Next: GKE Microservice →](./gke-microservice.md)
