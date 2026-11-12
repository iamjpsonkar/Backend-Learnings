← [Previous: Identity Center](./identity-center.md) | [Home](../../README.md) | [Next: AWS Networking →](../03-networking/README.md)

---

# AWS Organizations and Service Control Policies

AWS Organizations lets you manage multiple AWS accounts under a single structure. Service Control Policies (SCPs) enforce guardrails that no IAM policy or root user can override.

---

## Why Use AWS Organizations

| Without Organizations | With Organizations |
|----------------------|-------------------|
| One account for everything | Separate accounts per environment/team |
| No hard guardrails between teams | SCPs prevent dangerous actions org-wide |
| Single blast radius | Failure in one account can't affect others |
| One bill, no chargeback | Consolidated billing with per-account breakdown |
| Manual security baseline per account | AWS Control Tower automates baseline |

**Recommended account structure:**

```
Management (root) account
├── Security OU
│   ├── Log Archive account     (CloudTrail, Config logs centralized here)
│   └── Security Tooling account (GuardDuty delegated admin, Security Hub)
├── Infrastructure OU
│   ├── Network account         (shared Transit Gateway, Direct Connect)
│   └── Shared Services account (ECR, shared AMIs, Artifactory)
├── Workloads OU
│   ├── Production OU
│   │   ├── prod-api account
│   │   └── prod-data account
│   └── Non-Production OU
│       ├── staging account
│       └── development account
└── Sandbox OU
    └── developer-sandbox accounts (each dev gets their own)
```

---

## Organization Structure Concepts

| Concept | Meaning |
|---------|---------|
| **Management account** | The root account that created the organization. Has billing access and can create OUs and accounts. |
| **Member account** | Any account in the organization that is not the management account |
| **OU (Organizational Unit)** | A container for accounts and other OUs — forms the hierarchy |
| **Root** | The top of the OU hierarchy (there is exactly one) |
| **SCP** | A policy attached to Root, OU, or Account that limits what IAM in that scope can allow |

---

## Setting Up an Organization

```bash
# Create an organization (run from the management account)
aws organizations create-organization --feature-set ALL

# List the organization structure
aws organizations list-roots
aws organizations list-organizational-units-for-parent \
    --parent-id r-xxxx    # root ID from list-roots

# Create OUs
aws organizations create-organizational-unit \
    --parent-id r-xxxx \
    --name Security

aws organizations create-organizational-unit \
    --parent-id r-xxxx \
    --name Workloads

aws organizations create-organizational-unit \
    --parent-id ou-xxxx-xxxxxxxx \   # Workloads OU ID
    --name Production

# Create a new member account
aws organizations create-account \
    --account-name "Production API" \
    --email prod-api@mycompany.com   # must be unique and reachable

# Check account creation status
aws organizations describe-create-account-status \
    --create-account-request-id car-12345

# Move an account to an OU
aws organizations move-account \
    --account-id 111122223333 \
    --source-parent-id r-xxxx \
    --destination-parent-id ou-xxxx-xxxxxxxx

# List accounts in an OU
aws organizations list-accounts-for-parent \
    --parent-id ou-xxxx-xxxxxxxx \
    --query 'Accounts[*].{Name:Name,ID:Id,Status:Status}' \
    --output table
```

---

## Service Control Policies (SCPs)

SCPs define the **maximum permissions** for any IAM principal in an account or OU. They are applied in addition to — not instead of — IAM policies. Both must allow an action for it to succeed.

### How SCPs Work

```
Management account SCP → applied to all member accounts
  └── OU SCP           → applied to all accounts in this OU
        └── Account SCP → applied to this specific account

For any action to succeed:
  ALL applicable SCPs must allow it
  AND the IAM identity policy must allow it
```

**SCPs do NOT apply to:**
- The management account (root account of the org)
- AWS service-linked roles

**SCPs DO apply to:**
- All IAM users and roles in member accounts
- The root user of member accounts

### SCP Strategies

**Deny-list (default):** Start with `FullAWSAccess` (allow all), then add specific denies. Simpler to manage; recommended for most organizations.

**Allow-list:** Remove `FullAWSAccess` and explicitly allow only what you need. More restrictive; use for highly locked-down environments.

---

## Common SCP Examples

### Deny All Actions Outside Approved Regions

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyOutsideApprovedRegions",
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
      "StringNotEquals": {
        "aws:RequestedRegion": [
          "us-east-1",
          "us-west-2",
          "eu-west-1"
        ]
      },
      "ArnNotLike": {
        "aws:PrincipalARN": [
          "arn:aws:iam::*:role/OrganizationAccountAccessRole"
        ]
      }
    }
  }]
}
```

### Prevent Leaving the Organization

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyLeavingOrg",
    "Effect": "Deny",
    "Action": "organizations:LeaveOrganization",
    "Resource": "*"
  }]
}
```

### Protect Security Services from Being Disabled

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ProtectSecurityServices",
    "Effect": "Deny",
    "Action": [
      "cloudtrail:DeleteTrail",
      "cloudtrail:StopLogging",
      "cloudtrail:UpdateTrail",
      "guardduty:DeleteDetector",
      "guardduty:DisassociateFromMasterAccount",
      "securityhub:DisableSecurityHub",
      "config:DeleteConfigurationRecorder",
      "config:StopConfigurationRecorder"
    ],
    "Resource": "*",
    "Condition": {
      "ArnNotLike": {
        "aws:PrincipalARN": [
          "arn:aws:iam::*:role/SecurityBreakGlassRole"
        ]
      }
    }
  }]
}
```

### Require S3 Encryption

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyUnencryptedS3PutObject",
    "Effect": "Deny",
    "Action": "s3:PutObject",
    "Resource": "*",
    "Condition": {
      "Null": {
        "s3:x-amz-server-side-encryption": "true"
      }
    }
  }]
}
```

### Deny Root Account Actions

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyRootAccount",
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
      "StringLike": {
        "aws:PrincipalArn": "arn:aws:iam::*:root"
      }
    }
  }]
}
```

---

## Attaching and Managing SCPs

```bash
# Enable SCPs (if not already enabled)
aws organizations enable-policy-type \
    --root-id r-xxxx \
    --policy-type SERVICE_CONTROL_POLICY

# Create an SCP
aws organizations create-policy \
    --type SERVICE_CONTROL_POLICY \
    --name DenyUnapprovedRegions \
    --description "Deny API calls outside approved regions" \
    --content file://deny-regions-scp.json

# List all SCPs
aws organizations list-policies \
    --filter SERVICE_CONTROL_POLICY \
    --query 'Policies[*].{Name:Name,ID:Id,Description:Description}' \
    --output table

# Attach SCP to an OU
aws organizations attach-policy \
    --policy-id p-xxxxxxxxxxxx \
    --target-id ou-xxxx-xxxxxxxx

# Attach SCP to a specific account
aws organizations attach-policy \
    --policy-id p-xxxxxxxxxxxx \
    --target-id 111122223333

# View policies attached to an OU/account
aws organizations list-policies-for-target \
    --filter SERVICE_CONTROL_POLICY \
    --target-id ou-xxxx-xxxxxxxx

# View effective SCPs on an account (all inherited + directly attached)
aws organizations list-policies-for-target \
    --filter SERVICE_CONTROL_POLICY \
    --target-id 111122223333

# Delete an SCP (must detach from all targets first)
aws organizations detach-policy \
    --policy-id p-xxxxxxxxxxxx \
    --target-id ou-xxxx-xxxxxxxx

aws organizations delete-policy --policy-id p-xxxxxxxxxxxx
```

---

## Consolidated Billing

All member accounts' charges roll up to the management account's invoice.

```bash
# View costs per linked account
aws ce get-cost-and-usage \
    --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=LINKED_ACCOUNT \
    --query 'ResultsByTime[0].Groups[*].{Account:Keys[0],Cost:Metrics.BlendedCost.Amount}' \
    --output table | sort -k3 -rn
```

**Benefits:**
- Single invoice for all accounts
- Volume discounts and Reserved Instance/Savings Plans sharing across accounts
- Free Tier applies per account (can be useful for sandbox accounts)

---

## AWS Control Tower

Control Tower automates the multi-account setup, deploying:
- Landing zone (account structure, log archive, security account)
- Guardrails (preventive via SCPs, detective via Config rules)
- Account vending machine (create new accounts via Service Catalog)

For new organizations, start with Control Tower rather than setting up Organizations manually.

---

## References

- [AWS Organizations documentation](https://docs.aws.amazon.com/organizations/latest/userguide/)
- [SCP syntax reference](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_syntax.html)
- [AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/)
- [SCP examples](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_examples.html)
---

← [Previous: Identity Center](./identity-center.md) | [Home](../../README.md) | [Next: AWS Networking →](../03-networking/README.md)
