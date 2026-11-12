← [Previous: AWS IAM](./README.md) | [Home](../../README.md) | [Next: Users, Groups & Roles →](./users-groups-roles.md)

---

# AWS IAM Overview

IAM (Identity and Access Management) is the AWS service that controls **who** can do **what** on **which** resources. Every single AWS API call passes through IAM for authentication and authorisation.

---

## Core Components

```
         Principal
     (who is calling?)
           │
           │ presents credentials
           ▼
    ┌─────────────┐
    │ Authentication│  Is this credential valid?
    └──────┬──────┘
           │ yes → proceeds to authorisation
           ▼
    ┌─────────────────────────────────┐
    │         Policy Evaluation        │
    │  1. Explicit Deny?  → DENY       │
    │  2. Allow found?    → ALLOW      │
    │  3. No match?       → DENY       │
    └──────────────────┬──────────────┘
                       │
                       ▼
                  API Action
               (create, read, delete...)
                       │
                  on Resource
               (S3 bucket, EC2 instance...)
```

---

## IAM Principals

A **principal** is an entity that can make API requests.

| Principal type | Example | Credentials |
|---------------|---------|-------------|
| **IAM User** | `arn:aws:iam::123456789012:user/alice` | Access key + secret, or console password |
| **IAM Role** | `arn:aws:iam::123456789012:role/AppRole` | Temporary STS credentials |
| **AWS Service** | `ec2.amazonaws.com`, `lambda.amazonaws.com` | Automatic, via service role |
| **Federated user** | SAML/OIDC identity from external IdP | Temporary STS credentials |
| **AWS Account** | `arn:aws:iam::123456789012:root` | Root credentials |

---

## IAM Users

Long-term identities tied to a specific person or application.

```bash
# Create a user
aws iam create-user --user-name alice

# Create console login
aws iam create-login-profile \
    --user-name alice \
    --password 'Initial@Password1' \
    --password-reset-required

# Create access keys (for CLI/API)
aws iam create-access-key --user-name alice

# Attach a policy directly (avoid — use groups instead)
aws iam attach-user-policy \
    --user-name alice \
    --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# List users
aws iam list-users \
    --query 'Users[*].{Name:UserName,Created:CreateDate,LastLogin:PasswordLastUsed}' \
    --output table

# Get last activity (for auditing unused users)
aws iam generate-credential-report
aws iam get-credential-report \
    --query 'Content' --output text | base64 -d | column -t -s,
```

**Best practices for IAM users:**
- Prefer IAM Identity Center (SSO) over IAM users for humans
- For applications on EC2/Lambda: use IAM roles, not users
- If you must use access keys: rotate them every 90 days and never commit them
- Enable MFA for every IAM user with console access

---

## IAM Groups

Groups let you assign policies to a collection of users. A user can belong to multiple groups.

```bash
# Create a group
aws iam create-group --group-name Developers

# Attach managed policy to group
aws iam attach-group-policy \
    --group-name Developers \
    --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# Add user to group
aws iam add-user-to-group \
    --group-name Developers \
    --user-name alice

# List groups a user belongs to
aws iam list-groups-for-user --user-name alice

# List all groups and their policies
aws iam list-groups \
    --query 'Groups[*].GroupName' --output text | tr '\t' '\n' | while read g; do
    echo "=== $g ==="
    aws iam list-attached-group-policies --group-name "$g" \
        --query 'AttachedPolicies[*].PolicyName' --output text
done
```

**Common group structure:**
```
Administrators  — AdministratorAccess
Developers      — PowerUserAccess (all except IAM)
ReadOnly        — ReadOnlyAccess
Billing         — Billing managed policy
SecurityAudit   — SecurityAudit managed policy
```

---

## IAM Roles

Roles are the correct way to grant AWS permissions to:
- **AWS services** (EC2, Lambda, ECS tasks, CodeBuild)
- **External identities** (GitHub Actions, on-premises systems via OIDC/SAML)
- **Cross-account access** (role in account B assumed by user in account A)

Roles have no long-term credentials. They issue **temporary security tokens** (via STS) that expire automatically (15 minutes to 12 hours, configurable).

### Role Components

```json
{
  "Role": {
    "RoleName": "AppRole",
    "Arn": "arn:aws:iam::123456789012:role/AppRole",

    "AssumeRolePolicyDocument": {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    },

    "AttachedPolicies": ["arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"]
  }
}
```

The **trust policy** (`AssumeRolePolicyDocument`) defines **who can assume this role**.
Permission **policies** define **what the role can do**.

```bash
# Create a role for EC2 instances (to access S3)
aws iam create-role \
    --role-name EC2-S3-ReadOnly \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' \
    --description "Allows EC2 instances to read from S3"

# Attach a permissions policy
aws iam attach-role-policy \
    --role-name EC2-S3-ReadOnly \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Create an instance profile (required to associate role with EC2)
aws iam create-instance-profile \
    --instance-profile-name EC2-S3-ReadOnly-Profile

aws iam add-role-to-instance-profile \
    --instance-profile-name EC2-S3-ReadOnly-Profile \
    --role-name EC2-S3-ReadOnly

# Associate with a running instance
aws ec2 associate-iam-instance-profile \
    --instance-id i-0abc1234 \
    --iam-instance-profile Name=EC2-S3-ReadOnly-Profile

# View role details
aws iam get-role --role-name EC2-S3-ReadOnly
aws iam list-attached-role-policies --role-name EC2-S3-ReadOnly
```

### Cross-Account Role Assumption

```bash
# In account B: create a role that allows account A to assume it
aws iam create-role \
    --role-name CrossAccountReadOnly \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::ACCOUNT_A_ID:root"},
            "Action": "sts:AssumeRole"
        }]
    }'

# In account A: assume the role
aws sts assume-role \
    --role-arn arn:aws:iam::ACCOUNT_B_ID:role/CrossAccountReadOnly \
    --role-session-name audit-session
```

---

## IAM Conditions

Conditions make policies context-aware — restrict by IP, time, MFA status, resource tags:

```json
{
  "Effect": "Allow",
  "Action": "ec2:TerminateInstances",
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:RequestedRegion": "us-east-1",
      "ec2:ResourceTag/Environment": "development"
    },
    "Bool": {
      "aws:MultiFactorAuthPresent": "true"
    },
    "IpAddress": {
      "aws:SourceIp": "203.0.113.0/24"
    }
  }
}
```

**Common condition keys:**

| Key | Type | Use case |
|-----|------|---------|
| `aws:MultiFactorAuthPresent` | Bool | Require MFA |
| `aws:SourceIp` | IpAddress | Restrict to office/VPN IP |
| `aws:RequestedRegion` | String | Limit to specific regions |
| `aws:PrincipalTag/key` | String | Policy based on principal's tags |
| `aws:ResourceTag/key` | String | Policy based on resource tags |
| `aws:CalledVia` | String | Allow only when called by a service |
| `sts:ExternalId` | String | Extra secret for cross-account roles (confused deputy) |

---

## Access Advisor and Credential Report

```bash
# Credential report: login dates, key rotation, MFA status for all users
aws iam generate-credential-report
sleep 5
aws iam get-credential-report \
    --query 'Content' --output text | base64 -d

# Access advisor: what services has a user/role actually used?
# Step 1: generate report
JOB=$(aws iam generate-service-last-accessed-details \
    --arn arn:aws:iam::123456789012:user/alice \
    --query 'JobId' --output text)

# Step 2: wait and retrieve
aws iam get-service-last-accessed-details \
    --job-id $JOB \
    --query 'ServicesLastAccessed[?TotalAuthenticatedEntities>`0`].[ServiceName,LastAuthenticated]' \
    --output table
```

---

## IAM Limits

| Resource | Default limit |
|----------|--------------|
| Users per account | 5,000 |
| Groups per account | 300 |
| Roles per account | 1,000 |
| Policies per account | 1,500 |
| Managed policies attached to a user/role | 10 |
| Inline policy document size | 2,048 characters |
| Managed policy document size | 6,144 characters |
| Policy versions | 5 (one active, four non-active) |

---

## References

- [IAM documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/)
- [IAM best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [IAM condition keys reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)
- [AWS policy simulator](https://policysim.aws.amazon.com/)
---

← [Previous: AWS IAM](./README.md) | [Home](../../README.md) | [Next: Users, Groups & Roles →](./users-groups-roles.md)
