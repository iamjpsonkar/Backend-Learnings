← [Previous: Azure Projects](./README.md) | [Home](../../README.md) | [Next: Microservice on AKS →](./microservice-aks.md)

---

# Project: Static Website with Azure CDN

Deploy a static website using Azure Blob Storage's static website hosting, served globally via Azure CDN with a custom domain and HTTPS.

---

## Architecture

```
User Browser
     │
     ▼
Azure CDN (global edge nodes)
  ├── Custom domain: www.example.com
  ├── HTTPS (cert from Key Vault or CDN-managed)
  └── Origin: stmywebprodeastus.z13.web.core.windows.net
     │
     ▼
Azure Blob Storage (static website hosting)
  └── $web container (index.html, assets/)
```

---

## 1. Storage Account — Static Website Hosting

```bash
RESOURCE_GROUP="rg-my-web-prod-eastus"
LOCATION="eastus"
STORAGE_ACCOUNT="stmywebprodeastus"

# Create resource group
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --tags Environment=production Service=my-web

# Create storage account
az storage account create \
    --resource-group $RESOURCE_GROUP \
    --name $STORAGE_ACCOUNT \
    --location $LOCATION \
    --sku Standard_RAGRS \
    --kind StorageV2 \
    --https-only true \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access true \  # Required for static website
    --tags Environment=production

# Enable static website hosting
az storage blob service-properties update \
    --account-name $STORAGE_ACCOUNT \
    --static-website true \
    --index-document index.html \
    --404-document 404.html \
    --auth-mode login

# Get the static website endpoint
az storage account show \
    --resource-group $RESOURCE_GROUP \
    --name $STORAGE_ACCOUNT \
    --query 'primaryEndpoints.web' -o tsv
# Output: https://stmywebprodeastus.z13.web.core.windows.net/
```

---

## 2. Upload Website Files

```bash
# Build your site first (e.g., npm run build → ./dist/)

# Upload to $web container
az storage blob upload-batch \
    --account-name $STORAGE_ACCOUNT \
    --destination '$web' \
    --source ./dist \
    --overwrite true \
    --content-cache-control "public, max-age=31536000, immutable" \
    --pattern "*.js" \
    --auth-mode login

# HTML files — shorter cache (force revalidation for SPA routing)
az storage blob upload-batch \
    --account-name $STORAGE_ACCOUNT \
    --destination '$web' \
    --source ./dist \
    --overwrite true \
    --content-cache-control "public, max-age=0, must-revalidate" \
    --pattern "*.html" \
    --auth-mode login

# All other assets
az storage blob upload-batch \
    --account-name $STORAGE_ACCOUNT \
    --destination '$web' \
    --source ./dist \
    --overwrite true \
    --auth-mode login
```

---

## 3. Azure CDN Profile and Endpoint

```bash
CDN_PROFILE="cdn-my-web-prod-eastus"
CDN_ENDPOINT="my-web-prod"  # Becomes my-web-prod.azureedge.net
ORIGIN=$(az storage account show \
    --resource-group $RESOURCE_GROUP \
    --name $STORAGE_ACCOUNT \
    --query 'primaryEndpoints.web' -o tsv | sed 's|https://||' | sed 's|/||')
# Origin: stmywebprodeastus.z13.web.core.windows.net

# Create CDN profile (Microsoft CDN tier)
az cdn profile create \
    --resource-group $RESOURCE_GROUP \
    --name $CDN_PROFILE \
    --location Global \
    --sku Standard_Microsoft \
    --tags Environment=production

# Create CDN endpoint
az cdn endpoint create \
    --resource-group $RESOURCE_GROUP \
    --profile-name $CDN_PROFILE \
    --name $CDN_ENDPOINT \
    --origin $ORIGIN \
    --origin-host-header $ORIGIN \
    --https-port 443 \
    --http-port 80 \
    --no-http true \  # Force HTTPS
    --query-string-caching-behavior IgnoreQueryString \
    --tags Environment=production

echo "CDN endpoint: https://$CDN_ENDPOINT.azureedge.net"
```

---

## 4. Custom Domain and HTTPS

```bash
CUSTOM_DOMAIN="www.example.com"

# Create CNAME record in DNS:
# www.example.com → CNAME → my-web-prod.azureedge.net

# Add custom domain to CDN endpoint
az cdn custom-domain create \
    --resource-group $RESOURCE_GROUP \
    --profile-name $CDN_PROFILE \
    --endpoint-name $CDN_ENDPOINT \
    --name "www-example-com" \
    --hostname $CUSTOM_DOMAIN

# Enable HTTPS with CDN-managed certificate (free)
az cdn custom-domain enable-https \
    --resource-group $RESOURCE_GROUP \
    --profile-name $CDN_PROFILE \
    --endpoint-name $CDN_ENDPOINT \
    --name "www-example-com" \
    --min-tls-version 1.2 \
    --certificate-type Dedicated  # DigiCert auto-renewed certificate

echo "HTTPS will be provisioned within 6–8 hours"
```

---

## 5. CDN Rules — SPA Routing Fix

Single-page applications need all 404s rewritten to `index.html`.

```bash
# Add a URL rewrite rule for SPA routing
az cdn endpoint rule add \
    --resource-group $RESOURCE_GROUP \
    --profile-name $CDN_PROFILE \
    --endpoint-name $CDN_ENDPOINT \
    --name "spa-routing" \
    --order 1 \
    --action-name "UrlRewrite" \
    --source-pattern "/" \
    --destination "/index.html" \
    --preserve-unmatched-path false

# Add security headers
az cdn endpoint rule add \
    --resource-group $RESOURCE_GROUP \
    --profile-name $CDN_PROFILE \
    --endpoint-name $CDN_ENDPOINT \
    --name "security-headers" \
    --order 2 \
    --action-name "ModifyResponseHeader" \
    --header-action Append \
    --header-name "Strict-Transport-Security" \
    --header-value "max-age=31536000; includeSubDomains; preload"
```

---

## 6. CI/CD — GitHub Actions Deployment

```yaml
# .github/workflows/deploy-website.yml
name: Deploy Static Website

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install and Build
        run: |
          npm ci
          npm run build

      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Upload to Blob Storage
        uses: azure/cli@v2
        with:
          azcliversion: latest
          inlineScript: |
            # Upload hashed assets with long cache
            az storage blob upload-batch \
              --account-name stmywebprodeastus \
              --destination '$web' \
              --source ./dist \
              --overwrite true \
              --auth-mode login

      - name: Purge CDN Cache
        uses: azure/cli@v2
        with:
          azcliversion: latest
          inlineScript: |
            az cdn endpoint purge \
              --resource-group rg-my-web-prod-eastus \
              --profile-name cdn-my-web-prod-eastus \
              --name my-web-prod \
              --content-paths "/*"
```

---

## Cost Estimate

| Component | Cost |
|-----------|------|
| Blob Storage (Standard RAGRS, 1 GB) | ~$0.05/month |
| CDN (Standard Microsoft, 10 GB egress) | ~$0.87/month |
| CDN HTTPS certificate | Free |
| **Total** | **~$1/month** |

---

← [Previous: Azure Projects](./README.md) | [Home](../../README.md) | [Next: Microservice on AKS →](./microservice-aks.md)
