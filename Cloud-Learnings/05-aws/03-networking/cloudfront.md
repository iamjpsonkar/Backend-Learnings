← [Previous: Route 53](./route53.md) | [Home](../../README.md) | [Next: VPC Peering & Transit Gateway →](./vpc-peering-tgw.md)

---

# Amazon CloudFront

CloudFront is AWS's global Content Delivery Network (CDN). It caches content at 600+ edge locations (Points of Presence) worldwide, reducing latency and offloading traffic from origin servers.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Distribution** | The CloudFront configuration: origins, cache behaviors, SSL cert |
| **Origin** | The source of content: S3, ALB, EC2, API Gateway, or any HTTP server |
| **Edge location** | AWS data center that caches content close to end users |
| **Regional edge cache** | Larger cache tier between edge locations and your origin |
| **Cache behavior** | Rules matching URL patterns that define caching, headers, and origin |
| **Origin Access Control (OAC)** | Restricts S3 origin to CloudFront-only access (replaces OAI) |
| **Cache policy** | Defines what is included in the cache key (headers, cookies, query strings) |
| **Response headers policy** | Security headers added to CloudFront responses |
| **Invalidation** | Force CloudFront to purge cached content before TTL expires |

---

## Creating a Distribution

### S3 Static Website with OAC

```bash
BUCKET_NAME="my-static-site-bucket"
ACCOUNT_ID="123456789012"

# Step 1: Create the S3 bucket (block public access)
aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region us-east-1

aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Step 2: Create CloudFront Origin Access Control
OAC_ID=$(aws cloudfront create-origin-access-control \
    --origin-access-control-config '{
        "Name": "my-site-oac",
        "Description": "OAC for my-static-site-bucket",
        "SigningProtocol": "sigv4",
        "SigningBehavior": "always",
        "OriginAccessControlOriginType": "s3"
    }' \
    --query 'OriginAccessControl.Id' --output text)

echo "OAC ID: $OAC_ID"

# Step 3: Create the CloudFront distribution
DIST_ID=$(aws cloudfront create-distribution \
    --distribution-config '{
        "CallerReference": "my-site-'$(date +%s)'",
        "Comment": "Static site distribution",
        "DefaultRootObject": "index.html",
        "Origins": {
            "Quantity": 1,
            "Items": [{
                "Id": "s3-origin",
                "DomainName": "'$BUCKET_NAME'.s3.us-east-1.amazonaws.com",
                "S3OriginConfig": {"OriginAccessIdentity": ""},
                "OriginAccessControlId": "'$OAC_ID'"
            }]
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "s3-origin",
            "ViewerProtocolPolicy": "redirect-to-https",
            "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
            "Compress": true,
            "AllowedMethods": {
                "Quantity": 2,
                "Items": ["GET", "HEAD"]
            }
        },
        "Enabled": true,
        "HttpVersion": "http2and3",
        "IsIPV6Enabled": true
    }' \
    --query 'Distribution.Id' --output text)

echo "Distribution ID: $DIST_ID"

# Get the CloudFront domain name
DIST_DOMAIN=$(aws cloudfront get-distribution \
    --id $DIST_ID \
    --query 'Distribution.DomainName' --output text)

echo "CloudFront URL: https://$DIST_DOMAIN"

# Step 4: Update S3 bucket policy to allow CloudFront OAC
aws s3api put-bucket-policy \
    --bucket $BUCKET_NAME \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AllowCloudFrontServicePrincipal",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudfront.amazonaws.com"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::'$BUCKET_NAME'/*",
            "Condition": {
                "StringEquals": {
                    "AWS:SourceArn": "arn:aws:cloudfront::'$ACCOUNT_ID':distribution/'$DIST_ID'"
                }
            }
        }]
    }'
```

### ALB or API Gateway Origin

```bash
# Distribution with an ALB as origin (for dynamic content)
aws cloudfront create-distribution \
    --distribution-config '{
        "CallerReference": "alb-site-'$(date +%s)'",
        "Comment": "Dynamic site via ALB",
        "Origins": {
            "Quantity": 1,
            "Items": [{
                "Id": "alb-origin",
                "DomainName": "my-alb-1234.us-east-1.elb.amazonaws.com",
                "CustomOriginConfig": {
                    "HTTPSPort": 443,
                    "OriginProtocolPolicy": "https-only",
                    "OriginSSLProtocols": {
                        "Quantity": 1,
                        "Items": ["TLSv1.2"]
                    }
                }
            }]
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "alb-origin",
            "ViewerProtocolPolicy": "redirect-to-https",
            "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
            "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",
            "AllowedMethods": {
                "Quantity": 7,
                "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"]
            },
            "Compress": true
        },
        "Enabled": true,
        "HttpVersion": "http2and3"
    }'
```

---

## Cache Policies

Cache policies control what goes into the CloudFront cache key. More cache key components → more cache misses → more origin requests.

### AWS Managed Cache Policies

| Policy | ID | TTL | Use for |
|--------|----|-----|---------|
| CachingOptimized | 658327ea-... | min 1s, max 1yr | S3 static assets (recommended) |
| CachingDisabled | 4135ea2d-... | 0 | Dynamic content, APIs |
| CachingOptimizedForUncompressedObjects | b2884449-... | min 1s | Objects that cannot be compressed |

```bash
# List all managed cache policies
aws cloudfront list-cache-policies \
    --type managed \
    --query 'CachePolicyList.Items[*].{Name:CachePolicy.CachePolicyConfig.Name,ID:CachePolicy.Id}' \
    --output table
```

### Creating a Custom Cache Policy

```bash
CACHE_POLICY_ID=$(aws cloudfront create-cache-policy \
    --cache-policy-config '{
        "Name": "api-cache-policy",
        "Comment": "Cache API responses for 60 seconds, vary by Authorization header",
        "DefaultTTL": 60,
        "MaxTTL": 300,
        "MinTTL": 0,
        "ParametersInCacheKeyAndForwardedToOrigin": {
            "EnableAcceptEncodingGzip": true,
            "EnableAcceptEncodingBrotli": true,
            "HeadersConfig": {
                "HeaderBehavior": "whitelist",
                "Headers": {
                    "Quantity": 1,
                    "Items": ["Authorization"]
                }
            },
            "CookiesConfig": {"CookieBehavior": "none"},
            "QueryStringsConfig": {
                "QueryStringBehavior": "whitelist",
                "QueryStrings": {
                    "Quantity": 2,
                    "Items": ["page", "limit"]
                }
            }
        }
    }' \
    --query 'CachePolicy.Id' --output text)

echo "Cache policy: $CACHE_POLICY_ID"
```

---

## Cache Invalidation

Invalidation removes cached objects before their TTL expires. Use it for urgent updates (hotfix deployments, content corrections).

```bash
DIST_ID="E1234ABCDEFGH"

# Invalidate all objects
aws cloudfront create-invalidation \
    --distribution-id $DIST_ID \
    --paths "/*"

# Invalidate specific paths
aws cloudfront create-invalidation \
    --distribution-id $DIST_ID \
    --paths "/index.html" "/assets/main.js" "/api/*"

# Check invalidation status
aws cloudfront list-invalidations \
    --distribution-id $DIST_ID \
    --query 'InvalidationList.Items[*].{ID:Id,Status:Status,Created:CreateTime}' \
    --output table
```

**Cost:** First 1,000 invalidation paths per month are free; $0.005/path thereafter. Prefer versioned file names (`main.abc123.js`) over frequent invalidations.

---

## Custom Domain and HTTPS (ACM)

```bash
# Step 1: Request an ACM certificate in us-east-1 (required for CloudFront)
CERT_ARN=$(aws acm request-certificate \
    --domain-name "example.com" \
    --subject-alternative-names "www.example.com" \
    --validation-method DNS \
    --region us-east-1 \
    --query 'CertificateArn' --output text)

# Step 2: Get CNAME records for DNS validation
aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --region us-east-1 \
    --query 'Certificate.DomainValidationOptions[*].{Domain:DomainName,CNAMEName:ResourceRecord.Name,CNAMEValue:ResourceRecord.Value}'

# (Add CNAME records to your DNS provider / Route 53)

# Step 3: Wait for validation
aws acm wait certificate-validated \
    --certificate-arn $CERT_ARN \
    --region us-east-1

# Step 4: Update distribution with custom domain + certificate
DIST_ETAG=$(aws cloudfront get-distribution-config \
    --id $DIST_ID \
    --query 'ETag' --output text)

# Get the current config, modify it, then update
aws cloudfront get-distribution-config --id $DIST_ID \
    --query 'DistributionConfig' > /tmp/dist-config.json

# Edit /tmp/dist-config.json: add Aliases and ViewerCertificate, then:
aws cloudfront update-distribution \
    --id $DIST_ID \
    --if-match $DIST_ETAG \
    --distribution-config '{
        "Aliases": {
            "Quantity": 2,
            "Items": ["example.com", "www.example.com"]
        },
        "ViewerCertificate": {
            "ACMCertificateArn": "'$CERT_ARN'",
            "SSLSupportMethod": "sni-only",
            "MinimumProtocolVersion": "TLSv1.2_2021"
        }
    }'

# Step 5: Create Route 53 alias record pointing to CloudFront
HOSTED_ZONE_ID="Z1234567890"
aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch '{
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "example.com",
                "Type": "A",
                "AliasTarget": {
                    "HostedZoneId": "Z2FDTNDATAQYW2",
                    "DNSName": "'$DIST_DOMAIN'",
                    "EvaluateTargetHealth": false
                }
            }
        }]
    }'
```

---

## Security Headers Policy

```bash
# Add security headers to all CloudFront responses
HEADERS_POLICY_ID=$(aws cloudfront create-response-headers-policy \
    --response-headers-policy-config '{
        "Name": "security-headers",
        "Comment": "HSTS, CSP, and other security headers",
        "SecurityHeadersConfig": {
            "XSSProtection": {
                "Override": true,
                "Protection": true,
                "ModeBlock": true
            },
            "FrameOptions": {
                "Override": true,
                "FrameOption": "DENY"
            },
            "ReferrerPolicy": {
                "Override": true,
                "ReferrerPolicy": "strict-origin-when-cross-origin"
            },
            "ContentTypeOptions": {
                "Override": true
            },
            "StrictTransportSecurity": {
                "Override": true,
                "AccessControlMaxAgeSec": 31536000,
                "IncludeSubdomains": true,
                "Preload": true
            }
        }
    }' \
    --query 'ResponseHeadersPolicy.Id' --output text)

echo "Response headers policy: $HEADERS_POLICY_ID"
```

---

## CloudFront Functions vs Lambda@Edge

| | CloudFront Functions | Lambda@Edge |
|--|---------------------|-------------|
| Runtime | JavaScript (ES5.1) | Node.js, Python |
| Triggers | Viewer request, Viewer response | Viewer request/response + Origin request/response |
| Execution location | Edge locations (600+) | Regional edge caches (~13) |
| Max execution time | 1ms | 5s (viewer), 30s (origin) |
| Memory | 2MB | 128MB–10GB |
| Cost | $0.1/1M requests | $0.6/1M requests + duration |
| Use for | URL rewrites, header manipulation, simple auth | A/B testing, complex auth, server-side rendering |

### CloudFront Function Example: URL Rewrite

```javascript
// Rewrite /blog → /blog/index.html for S3 origin
function handler(event) {
    var request = event.request;
    var uri = request.uri;

    // Append index.html if path ends with /
    if (uri.endsWith('/')) {
        request.uri += 'index.html';
    }
    // Append index.html if no file extension
    else if (!uri.includes('.')) {
        request.uri += '/index.html';
    }

    return request;
}
```

```bash
# Deploy a CloudFront Function
FUNCTION_ARN=$(aws cloudfront create-function \
    --name url-rewrite \
    --function-config '{"Comment": "Rewrite URLs for S3 SPA", "Runtime": "cloudfront-js-1.0"}' \
    --function-code fileb://url-rewrite.js \
    --query 'FunctionSummary.FunctionMetadata.FunctionARN' --output text)

aws cloudfront publish-function \
    --name url-rewrite \
    --if-match $(aws cloudfront describe-function --name url-rewrite --query 'ETag' --output text)
```

---

## Monitoring and Logging

```bash
DIST_ID="E1234ABCDEFGH"

# Enable access logging to S3
aws cloudfront update-distribution \
    --id $DIST_ID \
    --if-match $DIST_ETAG \
    --distribution-config '{
        "Logging": {
            "Enabled": true,
            "IncludeCookies": false,
            "Bucket": "my-cloudfront-logs.s3.amazonaws.com",
            "Prefix": "cloudfront/"
        }
    }'

# CloudFront metrics are in us-east-1, namespace AWS/CloudFront
aws cloudwatch get-metric-statistics \
    --region us-east-1 \
    --namespace AWS/CloudFront \
    --metric-name Requests \
    --dimensions Name=DistributionId,Value=$DIST_ID Name=Region,Value=Global \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum \
    --output table

# Key CloudFront metrics
# Requests           — total viewer requests
# BytesDownloaded    — bytes transferred to viewers
# BytesUploaded      — bytes received from viewers (POST/PUT)
# 4xxErrorRate       — client error rate
# 5xxErrorRate       — origin error rate
# CacheHitRate       — percentage of requests served from cache (higher = better)
# OriginLatency      — time for origin to respond (when cache miss occurs)
```

---

## References

- [CloudFront documentation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/)
- [Origin Access Control](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- [Cache policies](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-the-cache-key.html)
- [CloudFront Functions](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-functions.html)
- [Lambda@Edge](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html)
---

← [Previous: Route 53](./route53.md) | [Home](../../README.md) | [Next: VPC Peering & Transit Gateway →](./vpc-peering-tgw.md)
