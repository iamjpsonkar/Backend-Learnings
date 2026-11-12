← [Previous: Secure VPC](./secure-vpc.md) | [Home](../../README.md) | [Next: Azure →](../../06-azure/README.md)

---

# Project: Static Website with S3 + CloudFront

Host a static website with global CDN, HTTPS, and a custom domain at near-zero cost. Suitable for React/Vue/Angular SPAs, documentation sites, and landing pages.

---

## Architecture

```
Browser
   │
   ▼
Route 53 (alias A record → CloudFront)
   │
   ▼
CloudFront (HTTPS, edge caching, OAC)
   │
   ▼
S3 bucket (private — no public access)
```

**Why use CloudFront in front of S3?**
- HTTPS is not natively available on S3 static website hosting for custom domains
- CloudFront provides edge caching (~400 PoPs worldwide)
- Origin Access Control (OAC) keeps the S3 bucket private
- Free SSL certificate via ACM (must be in `us-east-1`)

---

## Prerequisites

- AWS CLI configured with appropriate permissions
- A registered domain in Route 53 (or external DNS)
- Node.js / npm (for the SPA build — optional if you have static files)

---

## Step 1: Build the Static Site

```bash
# If you have a React/Vite project
npm run build
# Output: dist/ directory

# Or create a minimal test site
mkdir -p dist
cat > dist/index.html <<'EOF'
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>My App</title></head>
<body><h1>Hello from S3 + CloudFront</h1></body>
</html>
EOF
cat > dist/404.html <<'EOF'
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Not Found</title></head>
<body><h1>404 — Page not found</h1></body>
</html>
EOF
```

---

## Step 2: Create the S3 Bucket

```bash
DOMAIN="example.com"
BUCKET_NAME="my-static-site-$(aws sts get-caller-identity --query Account --output text)"
REGION="us-east-1"

# Create the bucket (private — no static website hosting needed when using CloudFront OAC)
aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region $REGION

# Block all public access
aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Enable versioning (allows rollback to previous deployments)
aws s3api put-bucket-versioning \
    --bucket $BUCKET_NAME \
    --versioning-configuration Status=Enabled

# Tag the bucket
aws s3api put-bucket-tagging \
    --bucket $BUCKET_NAME \
    --tagging 'TagSet=[{Key=Purpose,Value=static-website},{Key=Environment,Value=production}]'

echo "Bucket: $BUCKET_NAME"
```

---

## Step 3: Upload the Site

```bash
# Upload with correct content types and cache headers
aws s3 sync dist/ s3://$BUCKET_NAME/ \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "*.html"

# HTML files: short cache so CloudFront invalidation works well
aws s3 sync dist/ s3://$BUCKET_NAME/ \
    --delete \
    --include "*.html" \
    --cache-control "public, max-age=0, must-revalidate"

echo "Files uploaded"
```

---

## Step 4: Request ACM Certificate (us-east-1 required for CloudFront)

```bash
# Request a wildcard cert (covers example.com and *.example.com)
CERT_ARN=$(aws acm request-certificate \
    --domain-name $DOMAIN \
    --subject-alternative-names "*.$DOMAIN" \
    --validation-method DNS \
    --region us-east-1 \
    --query 'CertificateArn' --output text)

echo "Certificate ARN: $CERT_ARN"

# Get the DNS validation CNAME record
aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --region us-east-1 \
    --query 'Certificate.DomainValidationOptions[*].ResourceRecord'

# Add the CNAME to Route 53 and wait for validation (1–30 minutes)
aws acm wait certificate-validated \
    --certificate-arn $CERT_ARN \
    --region us-east-1
echo "Certificate validated"
```

---

## Step 5: Create CloudFront Distribution

```bash
# Create Origin Access Control
OAC_ID=$(aws cloudfront create-origin-access-control \
    --origin-access-control-config '{
        "Name": "my-site-oac",
        "Description": "OAC for my static site",
        "SigningProtocol": "sigv4",
        "SigningBehavior": "always",
        "OriginAccessControlOriginType": "s3"
    }' \
    --query 'OriginAccessControl.Id' --output text)

# Create the distribution
DISTRIBUTION_JSON=$(aws cloudfront create-distribution --distribution-config '{
    "CallerReference": "static-site-2024",
    "Comment": "My static website",
    "DefaultRootObject": "index.html",
    "Aliases": {
        "Quantity": 2,
        "Items": ["'"$DOMAIN"'", "www.'"$DOMAIN"'"]
    },
    "Origins": {
        "Quantity": 1,
        "Items": [{
            "Id": "S3Origin",
            "DomainName": "'"$BUCKET_NAME"'.s3.us-east-1.amazonaws.com",
            "S3OriginConfig": {"OriginAccessIdentity": ""},
            "OriginAccessControlId": "'"$OAC_ID"'"
        }]
    },
    "DefaultCacheBehavior": {
        "TargetOriginId": "S3Origin",
        "ViewerProtocolPolicy": "redirect-to-https",
        "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
        "Compress": true,
        "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
        "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}
    },
    "CustomErrorResponses": {
        "Quantity": 2,
        "Items": [
            {
                "ErrorCode": 403,
                "ResponsePagePath": "/index.html",
                "ResponseCode": "200",
                "ErrorCachingMinTTL": 10
            },
            {
                "ErrorCode": 404,
                "ResponsePagePath": "/404.html",
                "ResponseCode": "404",
                "ErrorCachingMinTTL": 10
            }
        ]
    },
    "ViewerCertificate": {
        "ACMCertificateArn": "'"$CERT_ARN"'",
        "SSLSupportMethod": "sni-only",
        "MinimumProtocolVersion": "TLSv1.2_2021"
    },
    "HttpVersion": "http2and3",
    "IsIPV6Enabled": true,
    "Enabled": true,
    "PriceClass": "PriceClass_100"
}')

DISTRIBUTION_ID=$(echo $DISTRIBUTION_JSON | python3 -c "import sys,json; print(json.load(sys.stdin)['Distribution']['Id'])")
DISTRIBUTION_DOMAIN=$(echo $DISTRIBUTION_JSON | python3 -c "import sys,json; print(json.load(sys.stdin)['Distribution']['DomainName'])")

echo "Distribution ID: $DISTRIBUTION_ID"
echo "Distribution domain: $DISTRIBUTION_DOMAIN"
```

---

## Step 6: Attach S3 Bucket Policy (Allow CloudFront OAC)

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws s3api put-bucket-policy \
    --bucket $BUCKET_NAME \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AllowCloudFrontOAC",
            "Effect": "Allow",
            "Principal": {"Service": "cloudfront.amazonaws.com"},
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::'"$BUCKET_NAME"'/*",
            "Condition": {
                "StringEquals": {
                    "AWS:SourceArn": "arn:aws:cloudfront::'"$ACCOUNT_ID"':distribution/'"$DISTRIBUTION_ID"'"
                }
            }
        }]
    }'
```

---

## Step 7: Configure Route 53

```bash
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
    --dns-name "$DOMAIN" \
    --query 'HostedZones[0].Id' --output text | sed 's|/hostedzone/||')

# Create alias records for both apex and www
aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch '{
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "'"$DOMAIN"'",
                    "Type": "A",
                    "AliasTarget": {
                        "HostedZoneId": "Z2FDTNDATAQYW2",
                        "DNSName": "'"$DISTRIBUTION_DOMAIN"'",
                        "EvaluateTargetHealth": false
                    }
                }
            },
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "www.'"$DOMAIN"'",
                    "Type": "A",
                    "AliasTarget": {
                        "HostedZoneId": "Z2FDTNDATAQYW2",
                        "DNSName": "'"$DISTRIBUTION_DOMAIN"'",
                        "EvaluateTargetHealth": false
                    }
                }
            }
        ]
    }'
# Z2FDTNDATAQYW2 is the CloudFront hosted zone ID — always the same
```

---

## Step 8: Deployment Script

```bash
#!/usr/bin/env bash
# deploy.sh — upload new build and invalidate CloudFront cache
set -euo pipefail

BUCKET_NAME="my-static-site-123456789012"
DISTRIBUTION_ID="E1234ABCDEFGH"

echo "Building..."
npm run build

echo "Uploading assets (long cache)..."
aws s3 sync dist/ s3://$BUCKET_NAME/ \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "*.html"

echo "Uploading HTML (no cache)..."
aws s3 sync dist/ s3://$BUCKET_NAME/ \
    --include "*.html" \
    --cache-control "public, max-age=0, must-revalidate"

echo "Invalidating CloudFront cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id $DISTRIBUTION_ID \
    --paths "/*" \
    --query 'Invalidation.Id' --output text)

echo "Waiting for invalidation $INVALIDATION_ID to complete..."
aws cloudfront wait invalidation-completed \
    --distribution-id $DISTRIBUTION_ID \
    --id $INVALIDATION_ID

echo "Deployment complete: https://$DOMAIN"
```

---

## Cost Estimate

| Service | Usage | Monthly Cost |
|---------|-------|-------------|
| S3 storage | 1 GB | ~$0.02 |
| S3 PUT requests | 10,000 per deploy | ~$0.05 per deploy |
| CloudFront | 10 GB transfer + 1M requests | ~$1.00 |
| Route 53 hosted zone | 1 zone | $0.50 |
| ACM certificate | 1 cert | Free |
| **Total** | | **~$2/month** |

---

## References

- [S3 static website hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)
- [CloudFront + S3 with OAC](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- [Route 53 alias records](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-choosing-alias-non-alias.html)
---

← [Previous: Secure VPC](./secure-vpc.md) | [Home](../../README.md) | [Next: Azure →](../../06-azure/README.md)
