← [Previous: Projects Overview](./README.md) | [Home](../README.md) | [Next: Serverless API →](./serverless-api.md)

---

# Project: Static Website CDN

Deploy a globally distributed static website with HTTPS, custom domain, and automatic cache invalidation on deployment. No servers, no maintenance — pay only for storage and CDN requests.

**Estimated cost:** ~$1–3/month (S3 + CloudFront + Route 53)
**Time to complete:** 45–60 minutes

---

## Architecture

```
Browser
  │  HTTPS (ACM cert)
  ▼
Route 53 (myapp.com → CloudFront)
  │
  ▼
CloudFront Distribution
  ├── Cache (edge locations worldwide)
  └── Origin: S3 bucket (private — OAC)
        │
        └── index.html, style.css, app.js, images/...
```

---

## Step 1: Create the S3 Bucket

```bash
export DOMAIN="myapp.com"
export BUCKET="${DOMAIN}-website"
export REGION="us-east-1"

# Create bucket (must be in us-east-1 for CloudFront OAC with S3 website)
aws s3api create-bucket \
    --bucket $BUCKET \
    --region $REGION

# Block all public access — CloudFront will use OAC
aws s3api put-public-access-block \
    --bucket $BUCKET \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,\
BlockPublicPolicy=true,RestrictPublicBuckets=true

# Enable versioning (so you can roll back deployments)
aws s3api put-bucket-versioning \
    --bucket $BUCKET \
    --versioning-configuration Status=Enabled

echo "Bucket created: s3://$BUCKET"
```

---

## Step 2: Request TLS Certificate

```bash
# Certificate must be in us-east-1 for CloudFront
CERT_ARN=$(aws acm request-certificate \
    --domain-name $DOMAIN \
    --subject-alternative-names "www.$DOMAIN" \
    --validation-method DNS \
    --region us-east-1 \
    --query 'CertificateArn' --output text)

echo "Certificate ARN: $CERT_ARN"

# Get DNS validation record to add to Route 53
aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --region us-east-1 \
    --query 'Certificate.DomainValidationOptions[*].{Domain:DomainName,Name:ResourceRecord.Name,Value:ResourceRecord.Value}'

# Add the CNAME record to Route 53 (replace NAME and VALUE from above)
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
    --dns-name $DOMAIN \
    --query 'HostedZones[0].Id' --output text | sed 's|/hostedzone/||')

aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch '{
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "_abc123.myapp.com",
                "Type": "CNAME",
                "TTL": 300,
                "ResourceRecords": [{"Value": "_xyz.acm-validations.aws."}]
            }
        }]
    }'

# Wait for certificate to be issued (2-5 minutes after DNS propagation)
aws acm wait certificate-validated \
    --certificate-arn $CERT_ARN \
    --region us-east-1
echo "Certificate issued"
```

---

## Step 3: Create CloudFront Distribution with OAC

```bash
# Create Origin Access Control (OAC) — modern replacement for OAI
OAC_ID=$(aws cloudfront create-origin-access-control \
    --origin-access-control-config '{
        "Name": "'"$BUCKET"'-oac",
        "Description": "OAC for '"$BUCKET"'",
        "OriginAccessControlOriginType": "s3",
        "SigningBehavior": "always",
        "SigningProtocol": "sigv4"
    }' \
    --query 'OriginAccessControl.Id' --output text)

echo "OAC ID: $OAC_ID"

# Create the distribution
DIST_ID=$(aws cloudfront create-distribution \
    --distribution-config '{
        "CallerReference": "'"$(uuidgen)"'",
        "Aliases": {"Quantity": 2, "Items": ["'"$DOMAIN"'", "www.'"$DOMAIN"'"]},
        "DefaultRootObject": "index.html",
        "Origins": {
            "Quantity": 1,
            "Items": [{
                "Id": "s3-origin",
                "DomainName": "'"$BUCKET"'.s3.'"$REGION"'.amazonaws.com",
                "S3OriginConfig": {"OriginAccessIdentity": ""},
                "OriginAccessControlId": "'"$OAC_ID"'"
            }]
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "s3-origin",
            "ViewerProtocolPolicy": "redirect-to-https",
            "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
            "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"], "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}},
            "Compress": true
        },
        "CustomErrorResponses": {
            "Quantity": 1,
            "Items": [{"ErrorCode": 403, "ResponsePagePath": "/index.html", "ResponseCode": "200", "ErrorCachingMinTTL": 0}]
        },
        "PriceClass": "PriceClass_100",
        "ViewerCertificate": {
            "ACMCertificateArn": "'"$CERT_ARN"'",
            "SSLSupportMethod": "sni-only",
            "MinimumProtocolVersion": "TLSv1.2_2021"
        },
        "Enabled": true,
        "HttpVersion": "http2and3",
        "IsIPV6Enabled": true,
        "Comment": "'"$DOMAIN"' static website"
    }' \
    --query 'Distribution.Id' --output text)

DIST_DOMAIN=$(aws cloudfront get-distribution \
    --id $DIST_ID \
    --query 'Distribution.DomainName' --output text)

echo "Distribution ID: $DIST_ID"
echo "Distribution domain: $DIST_DOMAIN"
```

---

## Step 4: Attach Bucket Policy for OAC

```bash
aws s3api put-bucket-policy \
    --bucket $BUCKET \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AllowCloudFrontOAC",
            "Effect": "Allow",
            "Principal": {"Service": "cloudfront.amazonaws.com"},
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::'"$BUCKET"'/*",
            "Condition": {
                "StringEquals": {
                    "AWS:SourceArn": "arn:aws:cloudfront::'"$(aws sts get-caller-identity --query Account --output text)"':distribution/'"$DIST_ID"'"
                }
            }
        }]
    }'

echo "Bucket policy attached"
```

---

## Step 5: Configure DNS

```bash
# Point domain to CloudFront
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
                        "DNSName": "'"$DIST_DOMAIN"'",
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
                        "DNSName": "'"$DIST_DOMAIN"'",
                        "EvaluateTargetHealth": false
                    }
                }
            }
        ]
    }'

echo "DNS records updated"
```

---

## Step 6: Deploy Website Files

```bash
# Sample project structure
mkdir -p my-website
cat > my-website/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My App</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <h1>Hello from AWS!</h1>
    <p>Served by CloudFront + S3</p>
    <script src="/app.js"></script>
</body>
</html>
EOF

# Upload with correct cache headers
# Long-lived cache for versioned assets (js/css with hash in filename)
aws s3 sync my-website/ s3://$BUCKET/ \
    --delete \
    --exclude "*.html" \
    --cache-control "max-age=31536000,immutable"

# Short cache for HTML (allows quick updates)
aws s3 sync my-website/ s3://$BUCKET/ \
    --exclude "*" \
    --include "*.html" \
    --cache-control "no-cache,no-store,must-revalidate"

# Invalidate CloudFront cache after deployment
aws cloudfront create-invalidation \
    --distribution-id $DIST_ID \
    --paths "/*.html"

echo "Deployment complete: https://$DOMAIN"
```

---

## Step 7: CI/CD Deployment Script

```yaml
# .github/workflows/deploy.yml
name: Deploy Website

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-deploy-role
          aws-region: us-east-1

      - name: Sync versioned assets (long cache)
        run: |
          aws s3 sync dist/ s3://${{ vars.S3_BUCKET }}/ \
            --delete \
            --exclude "*.html" \
            --cache-control "max-age=31536000,immutable"

      - name: Sync HTML (no cache)
        run: |
          aws s3 sync dist/ s3://${{ vars.S3_BUCKET }}/ \
            --exclude "*" --include "*.html" \
            --cache-control "no-cache,no-store,must-revalidate"

      - name: Invalidate CloudFront
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ vars.CLOUDFRONT_DIST_ID }} \
            --paths "/*"
```

---

## Verification

```bash
# Wait for distribution to deploy (10-15 min for new distributions)
aws cloudfront wait distribution-deployed --id $DIST_ID

# Test HTTPS
curl -I https://$DOMAIN
# Expect: HTTP/2 200, x-cache: Hit from cloudfront

# Test cache headers
curl -sI https://$DOMAIN/style.css | grep cache-control
# Expect: max-age=31536000,immutable

# Check distribution status
aws cloudfront get-distribution --id $DIST_ID \
    --query 'Distribution.{Status:Status,Domain:DomainName}'
```

---

## Teardown

```bash
# 1. Disable distribution first (required before deletion)
ETAG=$(aws cloudfront get-distribution-config --id $DIST_ID --query 'ETag' --output text)
aws cloudfront get-distribution-config --id $DIST_ID \
    --query 'DistributionConfig' > dist-config.json
# Edit: set "Enabled": false in dist-config.json
aws cloudfront update-distribution --id $DIST_ID \
    --if-match $ETAG --distribution-config file://dist-config.json
aws cloudfront wait distribution-deployed --id $DIST_ID

# 2. Delete distribution
ETAG=$(aws cloudfront get-distribution-config --id $DIST_ID --query 'ETag' --output text)
aws cloudfront delete-distribution --id $DIST_ID --if-match $ETAG

# 3. Empty and delete bucket
aws s3 rm s3://$BUCKET --recursive
aws s3api delete-bucket --bucket $BUCKET

# 4. Delete certificate (only if not used elsewhere)
aws acm delete-certificate --certificate-arn $CERT_ARN --region us-east-1
```

---

← [Previous: Projects Overview](./README.md) | [Home](../README.md) | [Next: Serverless API →](./serverless-api.md)
