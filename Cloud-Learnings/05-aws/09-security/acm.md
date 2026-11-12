← [Previous: Secrets Manager](./secrets-manager.md) | [Home](../../README.md) | [Next: GuardDuty →](./guardduty.md)

---

# AWS Certificate Manager (ACM)

ACM provisions, manages, and auto-renews SSL/TLS certificates for use with AWS services. Public certificates are free; private CA certificates are billed per CA and per certificate issued.

---

## Certificate Types

| Type | Cost | Use |
|------|------|-----|
| **ACM public certificate** | Free | HTTPS on CloudFront, ALB, API Gateway, AppSync, Elastic Beanstalk |
| **ACM private certificate** | $400/month per CA + $0.75/cert | Internal mTLS, private APIs, internal load balancers |
| **Imported certificate** | Free (management only) | Bring your own cert (external CA, legacy) |

**Key constraint:** ACM public certificates cannot be downloaded. They are bound to AWS services only.

---

## Requesting a Public Certificate

```bash
# Request a certificate (DNS validation — recommended)
CERT_ARN=$(aws acm request-certificate \
    --domain-name "example.com" \
    --subject-alternative-names "*.example.com" "api.example.com" \
    --validation-method DNS \
    --idempotency-token my-app-cert-2024 \
    --tags Key=Environment,Value=production Key=Service,Value=my-app \
    --query 'CertificateArn' --output text)

echo "Certificate ARN: $CERT_ARN"

# Describe the certificate to get DNS validation records
aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --query 'Certificate.DomainValidationOptions[*].{Domain:DomainName,Status:ValidationStatus,CNAME:ResourceRecord}' \
    --output table
```

### DNS Validation with Route 53

```bash
# Get the CNAME records needed for DNS validation
VALIDATION_RECORDS=$(aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --query 'Certificate.DomainValidationOptions[*].ResourceRecord')

# If hosted zone is in Route 53, ACM can create the records automatically:
aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --query 'Certificate.DomainValidationOptions[0].ResourceRecord'

# Manually create validation CNAME in Route 53
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
    --dns-name "example.com" \
    --query 'HostedZones[0].Id' --output text | sed 's|/hostedzone/||')

aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch '{
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "_abc123.example.com.",
                "Type": "CNAME",
                "TTL": 300,
                "ResourceRecords": [{"Value": "_xyz789.acm-validations.aws."}]
            }
        }]
    }'

# Wait for the certificate to be issued (DNS propagation takes 1–30 minutes)
aws acm wait certificate-validated --certificate-arn $CERT_ARN
echo "Certificate issued and validated"
```

### Email Validation (Alternative)

```bash
# Request with email validation — sends to WHOIS contacts and common addresses
aws acm request-certificate \
    --domain-name "example.com" \
    --validation-method EMAIL \
    --domain-validation-options DomainName=example.com,ValidationDomain=example.com
# Recipient must click approval link in the email within 72 hours
```

---

## Viewing and Managing Certificates

```bash
# List all certificates
aws acm list-certificates \
    --query 'CertificateSummaryList[*].{Domain:DomainName,ARN:CertificateArn,Status:Status,RenewalStatus:RenewalEligibility}' \
    --output table

# Full certificate details
aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --query 'Certificate.{
        Domain:DomainName,
        SANs:SubjectAlternativeNames,
        Status:Status,
        IssuedAt:IssuedAt,
        NotAfter:NotAfter,
        RenewalStatus:RenewalSummary.RenewalStatus,
        InUseBy:InUseBy
    }'

# List certificates expiring within 30 days
aws acm list-certificates \
    --includes keyTypes=RSA_2048 \
    --query 'CertificateSummaryList[?Status==`ISSUED`].[CertificateArn,DomainName,NotAfter]' \
    --output table

# Delete a certificate (only if not in use by any AWS service)
aws acm delete-certificate --certificate-arn $CERT_ARN
```

---

## Attaching Certificates to Services

### CloudFront

```bash
# CloudFront requires the certificate to be in us-east-1 (N. Virginia)
# Request or import cert in us-east-1, then reference in distribution config

DISTRIBUTION_ID="E1234ABCDEFGH"

# Get current distribution config
aws cloudfront get-distribution-config \
    --id $DISTRIBUTION_ID \
    --query 'DistributionConfig' > /tmp/dist-config.json

# Update ViewerCertificate section in /tmp/dist-config.json:
# "ViewerCertificate": {
#     "ACMCertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/xxx",
#     "SSLSupportMethod": "sni-only",
#     "MinimumProtocolVersion": "TLSv1.2_2021"
# }
```

### Application Load Balancer

```bash
ALB_ARN="arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/abc123"

# Create HTTPS listener (443) with the certificate
LISTENER_ARN=$(aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTPS \
    --port 443 \
    --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
    --certificates CertificateArn=$CERT_ARN \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN \
    --query 'Listeners[0].ListenerArn' --output text)

# Add an additional certificate (SNI — multiple domains on one ALB)
aws elbv2 add-listener-certificates \
    --listener-arn $LISTENER_ARN \
    --certificates CertificateArn=arn:aws:acm:us-east-1:123456789012:certificate/yyy

# List certificates on a listener
aws elbv2 describe-listener-certificates \
    --listener-arn $LISTENER_ARN \
    --query 'Certificates[*].{ARN:CertificateArn,IsDefault:IsDefault}' \
    --output table
```

### API Gateway (Custom Domain)

```bash
# Create a custom domain name backed by ACM cert (Regional endpoint)
aws apigateway create-domain-name \
    --domain-name "api.example.com" \
    --regional-certificate-arn $CERT_ARN \
    --endpoint-configuration types=REGIONAL \
    --security-policy TLS_1_2

# Get the regional domain name to create a Route 53 alias record
aws apigateway get-domain-name \
    --domain-name "api.example.com" \
    --query '{RegionalDomain:regionalDomainName,RegionalZone:regionalHostedZoneId}'
```

---

## Importing External Certificates

```bash
# Import a certificate issued by an external CA (e.g., Let's Encrypt, DigiCert)
aws acm import-certificate \
    --certificate fileb:///path/to/cert.pem \
    --private-key fileb:///path/to/private.key \
    --certificate-chain fileb:///path/to/chain.pem \
    --tags Key=Source,Value=letsencrypt

# Reimport (update) an existing imported certificate before expiry
IMPORTED_ARN="arn:aws:acm:us-east-1:123456789012:certificate/xxx"
aws acm import-certificate \
    --certificate-arn $IMPORTED_ARN \
    --certificate fileb:///path/to/new-cert.pem \
    --private-key fileb:///path/to/private.key \
    --certificate-chain fileb:///path/to/chain.pem
```

**Note:** Imported certificates do not auto-renew. You must track expiry and reimport manually.

---

## Auto-Renewal

ACM certificates (DNS-validated) renew automatically 60 days before expiry, provided:
- The CNAME validation record still exists in DNS
- The certificate is in use by at least one AWS service

```bash
# Check renewal status
aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --query 'Certificate.RenewalSummary.{Status:RenewalStatus,Reason:RenewalStatusReason,UpdatedAt:UpdatedAt}'

# Possible RenewalStatus values:
# PENDING_AUTO_RENEWAL   - within renewal window, waiting
# PENDING_VALIDATION     - DNS/email validation needed (validation record missing)
# SUCCESS                - renewed
# FAILED                 - renewal failed

# CloudWatch alarm for certificate expiry (ACM emits DaysToExpiry metric)
aws cloudwatch put-metric-alarm \
    --alarm-name "acm-cert-expiry-30days" \
    --alarm-description "ACM certificate expiring within 30 days" \
    --namespace "AWS/CertificateManager" \
    --metric-name "DaysToExpiry" \
    --dimensions Name=CertificateArn,Value=$CERT_ARN \
    --statistic Minimum \
    --period 86400 \
    --threshold 30 \
    --comparison-operator LessThanOrEqualToThreshold \
    --evaluation-periods 1 \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts
```

---

## ACM Private CA

```bash
# Create a Private CA (subordinate CA is recommended; root CA costs the same)
CA_ARN=$(aws acm-pca create-certificate-authority \
    --certificate-authority-type SUBORDINATE \
    --certificate-authority-configuration '{
        "KeyAlgorithm": "RSA_2048",
        "SigningAlgorithm": "SHA256WITHRSA",
        "Subject": {
            "Country": "US",
            "Organization": "My Company",
            "OrganizationalUnit": "Engineering",
            "CommonName": "My Company Internal CA"
        }
    }' \
    --revocation-configuration '{
        "CrlConfiguration": {
            "Enabled": true,
            "ExpirationInDays": 7,
            "S3BucketName": "my-crl-bucket"
        }
    }' \
    --tags Key=Environment,Value=production \
    --query 'CertificateAuthorityArn' --output text)

# Get the CSR to sign with your root CA
aws acm-pca get-certificate-authority-csr \
    --certificate-authority-arn $CA_ARN \
    --query 'Csr' --output text > /tmp/subordinate-ca.csr

# After signing externally, import the signed certificate
aws acm-pca import-certificate-authority-certificate \
    --certificate-authority-arn $CA_ARN \
    --certificate fileb:///tmp/subordinate-ca.crt \
    --certificate-chain fileb:///tmp/root-ca.crt

# Issue a private certificate (valid for 365 days)
PRIVATE_CERT_ARN=$(aws acm-pca issue-certificate \
    --certificate-authority-arn $CA_ARN \
    --csr fileb:///tmp/server.csr \
    --signing-algorithm SHA256WITHRSA \
    --validity Value=365,Type=DAYS \
    --query 'CertificateArn' --output text)

# Get the issued certificate
aws acm-pca get-certificate \
    --certificate-authority-arn $CA_ARN \
    --certificate-arn $PRIVATE_CERT_ARN \
    --query 'Certificate' --output text
```

---

## TLS Policy Selection

| Policy | TLS Versions | Ciphers | Use case |
|--------|-------------|---------|----------|
| `ELBSecurityPolicy-TLS13-1-2-2021-06` | TLS 1.2, 1.3 | Strong only | Recommended default |
| `ELBSecurityPolicy-TLS13-1-3-2021-06` | TLS 1.3 only | TLS 1.3 only | Highest security; breaks older clients |
| `ELBSecurityPolicy-2016-08` | TLS 1.0–1.2 | Broad | Legacy client compatibility only |
| `TLSv1.2_2021` (CloudFront) | TLS 1.2, 1.3 | Strong | Recommended for CloudFront |

**Recommendation:** Use `ELBSecurityPolicy-TLS13-1-2-2021-06` for ALB and `TLSv1.2_2021` for CloudFront.

---

## Certificate Monitoring

```bash
# EventBridge rule for ACM certificate expiry events
aws events put-rule \
    --name "acm-cert-expiry-warning" \
    --event-pattern '{
        "source": ["aws.acm"],
        "detail-type": ["ACM Certificate Approaching Expiration"]
    }' \
    --state ENABLED

aws events put-targets \
    --rule "acm-cert-expiry-warning" \
    --targets Id=ops-sns,Arn=arn:aws:sns:us-east-1:123456789012:ops-alerts

# ACM also sends events at: 45 days, 30 days, 15 days, 7 days, 3 days, 1 day before expiry
# These events fire for BOTH ACM-issued AND imported certificates
```

---

## Common Patterns

| Scenario | Approach |
|----------|----------|
| Single domain on ALB | Request ACM cert with DNS validation in same region as ALB |
| Wildcard for subdomains | Request `*.example.com` — covers one level deep only |
| Multi-region CloudFront | Request cert in `us-east-1` (CloudFront requirement) |
| Internal mTLS | ACM Private CA — issue client + server certs |
| Imported cert expiry tracking | EventBridge `ACM Certificate Approaching Expiration` event + CloudWatch `DaysToExpiry` alarm |
| Multiple domains on one ALB | Use SNI — add multiple ACM certs to the HTTPS listener |

---

## References

- [ACM documentation](https://docs.aws.amazon.com/acm/latest/userguide/)
- [ACM Private CA](https://docs.aws.amazon.com/privateca/latest/userguide/)
- [ALB TLS policies](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listener.html#describe-ssl-policies)
- [ACM pricing](https://aws.amazon.com/certificate-manager/pricing/)
---

← [Previous: Secrets Manager](./secrets-manager.md) | [Home](../../README.md) | [Next: GuardDuty →](./guardduty.md)
