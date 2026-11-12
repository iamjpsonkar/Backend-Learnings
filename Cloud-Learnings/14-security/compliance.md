← [Previous: Threat Modeling](./threat-modeling.md) | [Home](../README.md) | [Next: Incident Response →](./incident-response.md)

---

# Compliance

Compliance frameworks define security baselines for specific industries and data types. Cloud providers share responsibility — they provide compliant infrastructure, but you are responsible for your configuration, code, and data handling.

---

## Framework Overview

| Framework | Who it applies to | Key focus |
|-----------|------------------|-----------|
| **SOC 2 Type II** | SaaS/cloud service providers | Security, availability, integrity, confidentiality, privacy |
| **PCI-DSS** | Payment card data processors | Cardholder data protection |
| **HIPAA** | US healthcare data (PHI) | Protected health information |
| **ISO 27001** | Any organization | Information security management system (ISMS) |
| **GDPR** | Companies handling EU personal data | Data privacy and individual rights |
| **CIS Benchmarks** | Any | Technical security configuration baselines |
| **FedRAMP** | US government cloud services | NIST 800-53 controls |
| **NIST CSF** | Any | Cybersecurity risk management |

---

## SOC 2

SOC 2 evaluates controls across five Trust Services Criteria (TSC):

| TSC | Key controls to implement |
|-----|--------------------------|
| Security (CC) | Logical access, encryption, monitoring, incident response |
| Availability (A) | Uptime SLAs, disaster recovery, capacity planning |
| Processing Integrity (PI) | Input validation, error handling, reconciliation |
| Confidentiality (C) | Data classification, encryption at rest, NDA processes |
| Privacy (P) | Data collection notice, consent, retention, deletion |

### Evidence Collection Automation

```bash
# AWS: Enable CloudTrail for audit logs (required for SOC 2)
aws cloudtrail create-trail \
    --name prod-audit-trail \
    --s3-bucket-name my-app-audit-logs \
    --include-global-service-events \
    --is-multi-region-trail \
    --enable-log-file-validation   # Tamper-evident log integrity

aws cloudtrail start-logging --name prod-audit-trail

# Enable Config for resource configuration history
aws configservice put-configuration-recorder \
    --configuration-recorder name=default,roleARN=arn:aws:iam::123456789012:role/ConfigRole \
    --recording-group allSupported=true,includeGlobalResourceTypes=true

aws configservice put-delivery-channel \
    --delivery-channel name=default,s3BucketName=my-app-config-logs

aws configservice start-configuration-recorder --configuration-recorder-name default

# Check Config compliance
aws configservice describe-compliance-by-config-rule \
    --compliance-types NON_COMPLIANT \
    --query 'ComplianceByConfigRules[*].{Rule:ConfigRuleName,Compliance:Compliance.ComplianceType}'
```

### SOC 2 Config Rules

```bash
# Deploy CIS AWS Foundations Benchmark rules via Config
aws configservice put-config-rule --config-rule '{
    "ConfigRuleName": "mfa-enabled-for-iam-console-access",
    "Source": {
        "Owner": "AWS",
        "SourceIdentifier": "MFA_ENABLED_FOR_IAM_CONSOLE_ACCESS"
    }
}'

aws configservice put-config-rule --config-rule '{
    "ConfigRuleName": "root-account-mfa-enabled",
    "Source": {
        "Owner": "AWS",
        "SourceIdentifier": "ROOT_ACCOUNT_MFA_ENABLED"
    }
}'

aws configservice put-config-rule --config-rule '{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "Source": {
        "Owner": "AWS",
        "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED"
    }
}'

# Conformance pack: CIS Level 1
aws configservice put-conformance-pack \
    --conformance-pack-name CIS-AWS-Foundations-Benchmark \
    --template-s3-uri s3://aws-config-rules-packages-us-east-1/CIS-AWS-Foundations-Level1-Conformance-Pack.yaml \
    --delivery-s3-bucket my-app-config-logs
```

---

## PCI-DSS

PCI-DSS v4.0 (12 requirements) applies whenever you store, process, or transmit cardholder data.

### Minimize Scope — Tokenization

The best PCI control is to not touch card data at all. Use tokenization:

```python
# Use Stripe/Braintree/Adyen — they handle PCI scope
# Your code only ever sees a token, never the card number

import stripe
import logging

logger = logging.getLogger(__name__)
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]  # From secrets manager


def charge_customer(customer_id: str, amount_cents: int, currency: str = "usd") -> str:
    """
    Charge an existing Stripe customer.
    customer_id is a Stripe token — we never see the card number.
    Returns payment_intent_id for audit logging.
    """
    logger.info("Creating payment intent", extra={
        "customer_id": customer_id,
        "amount_cents": amount_cents,
        "currency": currency,
    })
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        customer=customer_id,
        confirm=True,
    )
    logger.info("Payment intent created", extra={
        "payment_intent_id": intent.id,
        "status": intent.status,
    })
    return intent.id
```

### PCI Network Segmentation

```bash
# Cardholder Data Environment (CDE) must be isolated
# Create dedicated VPC for CDE with no route to non-CDE systems
aws ec2 create-vpc --cidr-block 172.16.0.0/16 --tag-specifications \
    'ResourceType=vpc,Tags=[{Key=Name,Value=vpc-cde-prod},{Key=pci-scope,Value=true}]'

# Security group: CDE DB only accepts from CDE app tier
aws ec2 authorize-security-group-ingress \
    --group-id $CDE_DB_SG \
    --protocol tcp --port 5432 \
    --source-group $CDE_APP_SG

# Log all CDE access to CloudWatch with retention
aws logs put-retention-policy \
    --log-group-name /cde/access-logs \
    --retention-in-days 365  # PCI requires 12 months
```

---

## HIPAA

HIPAA applies to Protected Health Information (PHI) in the US healthcare sector.

### Technical Safeguards

```bash
# Required: Audit logs for all PHI access
# AWS CloudTrail + S3 access logs + RDS audit logs

# RDS PostgreSQL audit logging
aws rds modify-db-parameter-group \
    --db-parameter-group-name phi-postgres-params \
    --parameters "ParameterName=pgaudit.log,ParameterValue='read,write,ddl',ApplyMethod=immediate"

# S3: Enable access logging for PHI buckets
aws s3api put-bucket-logging \
    --bucket my-phi-data \
    --bucket-logging-status '{
        "LoggingEnabled": {
            "TargetBucket": "my-phi-access-logs",
            "TargetPrefix": "phi/"
        }
    }'

# Required: Encryption at rest and in transit
# AWS: KMS CMK for all PHI data stores (see encryption.md)

# Required: Automatic logoff / session timeout
# Application-level: token TTL ≤ 15 minutes for PHI access

# BAA (Business Associate Agreement) with AWS
# Must be signed before using AWS for PHI
# Available in AWS Artifact: https://console.aws.amazon.com/artifact/
```

---

## GDPR (Key Technical Requirements)

```python
# Right to erasure — delete all user data
import logging
from typing import List

logger = logging.getLogger(__name__)


def erase_user_data(user_id: str) -> dict:
    """
    GDPR Article 17 — Right to erasure.
    Returns a report of what was deleted.
    """
    logger.info("Processing erasure request", extra={"user_id": user_id})
    deleted = {}

    # 1. Delete from primary database
    with db.transaction():
        rows = db.execute("DELETE FROM users WHERE id = %s RETURNING email", (user_id,))
        deleted["user_record"] = rows.rowcount
        logger.info("Deleted user record", extra={"user_id": user_id, "rows": rows.rowcount})

    # 2. Delete from analytics (BigQuery/Redshift)
    analytics_client.delete_user_events(user_id)
    deleted["analytics_events"] = True
    logger.info("Deleted analytics events", extra={"user_id": user_id})

    # 3. Remove from S3 (profile pictures, uploads)
    s3_keys = list_user_s3_objects(user_id)
    for key in s3_keys:
        s3.delete_object(Bucket=USER_DATA_BUCKET, Key=key)
    deleted["s3_objects"] = len(s3_keys)
    logger.info("Deleted S3 objects", extra={"user_id": user_id, "count": len(s3_keys)})

    # 4. Submit data deletion to third parties
    for vendor in ["stripe", "intercom", "sendgrid"]:
        submit_third_party_deletion(vendor, user_id)
    deleted["third_party_deletions"] = ["stripe", "intercom", "sendgrid"]

    # 5. Audit log the erasure (keep for legal compliance — this is NOT erasable)
    audit_log.record("gdpr_erasure", user_id=user_id, deleted=deleted)

    logger.info("Erasure complete", extra={"user_id": user_id, "summary": deleted})
    return deleted
```

---

## CIS Benchmarks

The CIS provides hardened baselines for common systems. The AWS Foundations Benchmark is free and widely used.

```bash
# CIS AWS Foundations Benchmark v2.0 — key checks

# 1.1 Ensure MFA is enabled for the root account
aws iam get-account-summary | jq '.AccountSummaryMap.AccountMFAEnabled'

# 1.4 Ensure no root access keys exist
aws iam list-access-keys --query 'AccessKeyMetadata[?UserName==`root`]'

# 2.1 Ensure CloudTrail is enabled in all regions
aws cloudtrail describe-trails --query 'trailList[?IsMultiRegionTrail==`true`]'

# 2.6 Ensure S3 bucket access logging is enabled on CloudTrail S3 buckets
aws s3api get-bucket-logging --bucket $CLOUDTRAIL_BUCKET

# 3.1 Ensure a log metric filter and alarm exist for unauthorized API calls
aws logs describe-metric-filters \
    --log-group-name $CLOUDTRAIL_LOG_GROUP \
    --filter-name-prefix "UnauthorizedAPICalls"

# 4.1 Ensure no security groups allow ingress from 0.0.0.0/0 to port 22
aws ec2 describe-security-groups \
    --query "SecurityGroups[?IpPermissions[?FromPort==\`22\` && IpRanges[?CidrIp=='0.0.0.0/0']]].GroupId"

# 5.1 Ensure no network ACLs allow ingress from 0.0.0.0/0 to port 22
aws ec2 describe-network-acls \
    --query "NetworkAcls[?Entries[?RuleAction=='allow' && CidrBlock=='0.0.0.0/0' && PortRange.From<=\`22\` && PortRange.To>=\`22\`]]"

# Run automated CIS benchmark assessment
aws securityhub enable-standards \
    --standards-subscription-requests StandardsArn=arn:aws:securityhub:us-east-1::standards/cis-aws-foundations-benchmark/v/1.4.0
```

---

## Compliance as Code (Terraform + Policy)

```hcl
# OPA policy: enforce encryption at rest for all S3 buckets
# policies/s3_encryption.rego
package terraform.s3

deny[msg] {
    resource := input.planned_values.root_module.resources[_]
    resource.type == "aws_s3_bucket"
    not has_encryption(resource)
    msg := sprintf("S3 bucket '%s' must have server-side encryption enabled", [resource.name])
}

has_encryption(resource) {
    resource.values.server_side_encryption_configuration[_].rule[_].apply_server_side_encryption_by_default[_]
}
```

```bash
# Run OPA against Terraform plan
terraform plan -out=plan.tfplan
terraform show -json plan.tfplan > plan.json
opa eval --input plan.json --data policies/ "data.terraform.s3.deny" --fail

# Checkov: runs 1000+ policy checks against Terraform/K8s/CloudFormation
pip install checkov
checkov -d . --compact --framework terraform
checkov -d . --check CKV_AWS_53  # Specific check: S3 bucket logging

# tfsec: fast Terraform security scanner
brew install tfsec
tfsec . --minimum-severity HIGH
```

---

## References

- [SOC 2 — AICPA](https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services)
- [PCI DSS v4.0](https://www.pcisecuritystandards.org/)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [GDPR Text](https://gdpr-info.eu/)
- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- [AWS Compliance Programs](https://aws.amazon.com/compliance/programs/)

---

← [Previous: Threat Modeling](./threat-modeling.md) | [Home](../README.md) | [Next: Incident Response →](./incident-response.md)
