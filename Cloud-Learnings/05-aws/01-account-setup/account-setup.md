← [Previous: AWS Account Setup](./README.md) | [Home](../../README.md) | [Next: Billing & Budgets →](./billing-budgets.md)

---

# AWS Account Setup and Hardening

Securing an AWS account on day one prevents the most common and most expensive cloud security incidents — exposed access keys, public S3 buckets, and undetected cryptocurrency mining.

---

## Root Account Security

The **root account** has unrestricted access to everything in the account. It cannot be restricted by IAM policies. Treat it like a break-glass emergency credential.

```
Root account security rules:
  1. Enable MFA immediately after account creation
  2. Delete all root access keys
  3. Store the root password in a password manager (not in your head)
  4. Only use root for tasks that explicitly require it:
     - Change account name, email, or payment method
     - Restore IAM access when all admin IAM users are locked out
     - Enable/disable certain services for the first time
     - Close the account
```

### Enable Root MFA

1. Sign in to the AWS console as root
2. Account menu (top right) → Security credentials
3. Multi-factor authentication → Assign MFA device
4. Choose: Authenticator app (TOTP) or Hardware security key (FIDO2 — preferred)
5. Follow the setup wizard

```bash
# Verify root MFA is enabled (requires admin IAM user or role)
aws iam get-account-summary \
    --query 'SummaryMap.AccountMFAEnabled'
# Returns 1 if enabled, 0 if not

# List virtual MFA devices
aws iam list-virtual-mfa-devices \
    --assignment-status Assigned
```

### Delete Root Access Keys

```bash
# Check if root access keys exist
aws iam get-account-summary \
    --query 'SummaryMap.AccountAccessKeysPresent'
# Returns 1 if root access keys exist — delete them immediately

# Must be done via the console: Account → Security credentials → Access keys → Delete
```

---

## First IAM Admin User

Do not continue using root for daily work. Create an admin identity immediately.

**Option A — IAM Identity Center (recommended for teams):**
See [identity-center.md](identity-center.md). Provides SSO, temporary credentials, and central management.

**Option B — IAM admin user (simpler for solo developers):**

```bash
# Create an admin group
aws iam create-group --group-name Administrators

# Attach the AdministratorAccess policy to the group
aws iam attach-group-policy \
    --group-name Administrators \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Create an admin user
aws iam create-user --user-name alice

# Add to the group
aws iam add-user-to-group \
    --user-name alice \
    --group-name Administrators

# Create a login profile (console password)
aws iam create-login-profile \
    --user-name alice \
    --password 'TemporaryP@ssw0rd1!' \
    --password-reset-required

# Create access keys for CLI usage (can also use SSO instead)
aws iam create-access-key --user-name alice
# Save the AccessKeyId and SecretAccessKey — shown only once

# Enforce MFA for console access via an IAM policy (see policies.md for the deny-without-MFA pattern)
```

---

## CloudTrail — Audit Logging

CloudTrail records every API call made in your AWS account. It is the primary audit trail for security investigations, compliance, and debugging.

```bash
# Create a CloudTrail trail (all regions, management + data events)
aws cloudtrail create-trail \
    --name org-audit-trail \
    --s3-bucket-name my-cloudtrail-logs-123456789012 \
    --include-global-service-events \
    --is-multi-region-trail \
    --enable-log-file-validation    # detects log tampering via SHA-256 hash

# Start logging
aws cloudtrail start-logging --name org-audit-trail

# Verify trail is active
aws cloudtrail get-trail-status --name org-audit-trail \
    --query '{Logging:IsLogging,LatestDelivery:LatestDeliveryTime}'

# List active trails across all regions
aws cloudtrail describe-trails --include-shadow-trails false
```

### S3 Bucket for CloudTrail

The bucket must have a specific bucket policy that only allows CloudTrail to write to it.

```bash
# Create the bucket
aws s3api create-bucket \
    --bucket my-cloudtrail-logs-123456789012 \
    --region us-east-1

# Block all public access
aws s3api put-public-access-block \
    --bucket my-cloudtrail-logs-123456789012 \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Enable versioning (for compliance)
aws s3api put-bucket-versioning \
    --bucket my-cloudtrail-logs-123456789012 \
    --versioning-configuration Status=Enabled

# Apply the required bucket policy (CloudTrail needs GetBucketAcl + PutObject)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3api put-bucket-policy \
    --bucket my-cloudtrail-logs-123456789012 \
    --policy "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [
            {
                \"Sid\": \"AWSCloudTrailAclCheck\",
                \"Effect\": \"Allow\",
                \"Principal\": {\"Service\": \"cloudtrail.amazonaws.com\"},
                \"Action\": \"s3:GetBucketAcl\",
                \"Resource\": \"arn:aws:s3:::my-cloudtrail-logs-123456789012\"
            },
            {
                \"Sid\": \"AWSCloudTrailWrite\",
                \"Effect\": \"Allow\",
                \"Principal\": {\"Service\": \"cloudtrail.amazonaws.com\"},
                \"Action\": \"s3:PutObject\",
                \"Resource\": \"arn:aws:s3:::my-cloudtrail-logs-123456789012/AWSLogs/${ACCOUNT_ID}/*\",
                \"Condition\": {
                    \"StringEquals\": {\"s3:x-amz-acl\": \"bucket-owner-full-control\"}
                }
            }
        ]
    }"
```

### Querying CloudTrail with Athena

For large-scale log analysis:

```sql
-- Athena query: find all console logins in the last 7 days
SELECT eventtime, useridentity.username, sourceipaddress, useragent
FROM cloudtrail_logs
WHERE eventsource = 'signin.amazonaws.com'
  AND eventname = 'ConsoleLogin'
  AND eventtime > to_iso8601(current_timestamp - interval '7' day)
ORDER BY eventtime DESC;

-- Find API calls that returned AccessDenied
SELECT eventtime, useridentity.arn, eventsource, eventname, errorcode, errormessage
FROM cloudtrail_logs
WHERE errorcode = 'AccessDenied'
  AND eventtime > to_iso8601(current_timestamp - interval '1' day)
ORDER BY eventtime DESC
LIMIT 100;
```

---

## GuardDuty — Threat Detection

GuardDuty continuously analyses CloudTrail, VPC Flow Logs, and DNS logs to detect threats without requiring any configuration.

```bash
# Enable GuardDuty (do this in every region you use)
aws guardduty create-detector \
    --enable \
    --features '[
        {"Name": "S3_DATA_EVENTS", "Status": "ENABLED"},
        {"Name": "EKS_AUDIT_LOGS", "Status": "ENABLED"},
        {"Name": "LAMBDA_NETWORK_LOGS", "Status": "ENABLED"}
    ]'

# Get detector ID (needed for other commands)
DETECTOR_ID=$(aws guardduty list-detectors --query 'DetectorIds[0]' --output text)

# List current findings
aws guardduty list-findings \
    --detector-id $DETECTOR_ID \
    --finding-criteria '{"Criterion": {"service.archived": {"Eq": ["false"]}}}'

# Get finding details
aws guardduty get-findings \
    --detector-id $DETECTOR_ID \
    --finding-ids finding-id-here

# Create a CloudWatch Events rule to alert on new findings
aws events put-rule \
    --name guardduty-findings \
    --event-pattern '{
        "source": ["aws.guardduty"],
        "detail-type": ["GuardDuty Finding"]
    }' \
    --state ENABLED
```

**Common GuardDuty finding types:**

| Finding | What it means |
|---------|--------------|
| `UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B` | Console login from unusual location |
| `CryptoCurrency:EC2/BitcoinTool.B!DNS` | Instance mining cryptocurrency |
| `Trojan:EC2/DNSDataExfiltration` | Data exfiltration via DNS tunnelling |
| `UnauthorizedAccess:EC2/SSHBruteForce` | SSH brute force attack |
| `CredentialAccess:IAMUser/AnomalousBehavior` | Unusual API calls for this user |

---

## S3 Block Public Access (Account Level)

Prevents any bucket or object in the account from becoming public, regardless of individual bucket settings.

```bash
# Block all public S3 access at account level
aws s3control put-public-access-block \
    --account-id $(aws sts get-caller-identity --query Account --output text) \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Verify
aws s3control get-public-access-block \
    --account-id $(aws sts get-caller-identity --query Account --output text)
```

---

## EBS Default Encryption

All new EBS volumes will be encrypted automatically.

```bash
# Enable EBS default encryption (per region — run in each region you use)
aws ec2 enable-ebs-encryption-by-default

# Verify
aws ec2 get-ebs-encryption-by-default

# Use a custom KMS key (optional; uses AWS-managed key by default)
aws ec2 modify-ebs-default-kms-key-id \
    --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abc-123
```

---

## Account-Level Password Policy

```bash
aws iam update-account-password-policy \
    --minimum-password-length 16 \
    --require-symbols \
    --require-numbers \
    --require-uppercase-characters \
    --require-lowercase-characters \
    --allow-users-to-change-password \
    --max-password-age 90 \
    --password-reuse-prevention 12 \
    --hard-expiry
```

---

## IAM Access Analyzer

Identifies resources exposed to the internet or to external AWS accounts.

```bash
# Create an analyzer for the account
aws accessanalyzer create-analyzer \
    --analyzer-name account-analyzer \
    --type ACCOUNT

# List findings (externally accessible resources)
aws accessanalyzer list-findings \
    --analyzer-arn arn:aws:access-analyzer:us-east-1:123456789012:analyzer/account-analyzer \
    --query 'findings[?status==`ACTIVE`].[resource,resourceType,condition]' \
    --output table
```

---

## Security Hub

Security Hub aggregates findings from GuardDuty, IAM Access Analyzer, Inspector, Macie, and third-party tools in one place. It also runs automated checks against security standards (AWS Foundational Security Best Practices, CIS AWS Foundations).

```bash
# Enable Security Hub
aws securityhub enable-security-hub \
    --enable-default-standards

# Get overall security score
aws securityhub describe-hub \
    --query 'HubArn'

# List failed controls
aws securityhub get-findings \
    --filters '{"ComplianceStatus": [{"Value": "FAILED", "Comparison": "EQUALS"}]}' \
    --query 'Findings[*].{Title:Title,Severity:Severity.Label,Resource:Resources[0].Id}' \
    --output table
```

---

## References

- [AWS account root user best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html)
- [CloudTrail documentation](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/)
- [GuardDuty documentation](https://docs.aws.amazon.com/guardduty/latest/ug/)
- [Security Hub documentation](https://docs.aws.amazon.com/securityhub/latest/userguide/)
---

← [Previous: AWS Account Setup](./README.md) | [Home](../../README.md) | [Next: Billing & Budgets →](./billing-budgets.md)
