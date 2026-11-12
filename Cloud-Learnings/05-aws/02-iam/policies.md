← [Previous: Users, Groups & Roles](./users-groups-roles.md) | [Home](../../README.md) | [Next: Identity Center →](./identity-center.md)

---

# IAM Policies

An IAM policy is a JSON document that defines what actions are allowed or denied on which resources under what conditions. Policies are the mechanism through which all AWS access is controlled.

---

## Policy Types

| Type | Attached to | Who manages | Use case |
|------|------------|-------------|---------|
| **AWS Managed** | Users, groups, roles | AWS | Common permission sets (ReadOnly, PowerUser) |
| **Customer Managed** | Users, groups, roles | You | Custom, reusable policies |
| **Inline** | One specific entity | You | Unique policy for one identity |
| **Resource-based** | Resources (S3, KMS, SQS…) | You | Cross-account access, resource-level control |
| **Permission boundary** | Users, roles | You | Maximum permissions ceiling |
| **SCP (Service Control Policy)** | OUs, accounts | Org admin | Hard limits across all accounts in an org |
| **Session policy** | STS sessions | You | Reduce permissions at assume-role time |

---

## Policy JSON Structure

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3BucketRead",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `Version` | Yes | Always `"2012-10-17"` (policy language version) |
| `Statement` | Yes | Array of permission statements |
| `Sid` | No | Statement ID — human-readable identifier |
| `Effect` | Yes | `"Allow"` or `"Deny"` |
| `Principal` | Resource-based only | Who the policy applies to |
| `Action` | Yes | List of AWS API actions (e.g., `s3:GetObject`) |
| `Resource` | Yes | ARNs of resources the action applies to |
| `Condition` | No | When the statement applies |

---

## Wildcards in Actions and Resources

```json
"Action": "s3:*"                  // all S3 actions
"Action": "s3:Get*"               // all actions starting with Get
"Action": ["s3:GetObject", "s3:PutObject"]

"Resource": "*"                   // all resources
"Resource": "arn:aws:s3:::my-bucket/*"   // all objects in a bucket
"Resource": "arn:aws:ec2:us-east-1:123456789012:instance/i-*"  // all EC2 instances
```

---

## Policy Evaluation Logic

When an AWS API call is made, IAM evaluates all applicable policies in this order:

```
1. Explicit DENY in any policy?        → DENY (always wins)
2. Allow in SCP?         No →          → DENY
3. Allow in resource-based policy?
   Or Allow in identity policy?  No → → DENY
4. Permission boundary allows it? No → → DENY
5. Session policy allows it?     No → → DENY
6. All checks passed               →   ALLOW
```

**Key rules:**
- **Explicit deny always wins** — no matter what else allows it
- **Default is implicit deny** — nothing is allowed unless explicitly permitted
- Both the identity policy AND the SCP must allow the action (they are ANDed, not ORed)

### Multi-Account Policy Evaluation

```
Account B (resource)   ←── API call ──   Account A (caller)

Both must allow:
  - Account A's identity policy must allow the action
  - Account B's resource-based policy must allow Account A
```

If a resource-based policy in Account B explicitly allows Account A, Account A's own identity policies still need to allow the action.

---

## Common Policy Patterns

### Deny Everything Unless MFA Is Present

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyWithoutMFA",
    "Effect": "Deny",
    "NotAction": [
      "iam:CreateVirtualMFADevice",
      "iam:EnableMFADevice",
      "iam:GetUser",
      "iam:ListMFADevices",
      "iam:ListVirtualMFADevices",
      "iam:ResyncMFADevice",
      "sts:GetSessionToken"
    ],
    "Resource": "*",
    "Condition": {
      "BoolIfExists": {
        "aws:MultiFactorAuthPresent": "false"
      }
    }
  }]
}
```

### Restrict Actions to Specific Regions

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
      "StringNotEquals": {
        "aws:RequestedRegion": ["us-east-1", "us-west-2"]
      }
    }
  }]
}
```

### Allow Access Only From Company IP Range

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
      "NotIpAddress": {
        "aws:SourceIp": ["203.0.113.0/24", "198.51.100.0/24"]
      },
      "Bool": {
        "aws:ViaAWSService": "false"
      }
    }
  }]
}
```

### Tag-Based Access Control (ABAC)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["ec2:StartInstances", "ec2:StopInstances", "ec2:DescribeInstances"],
    "Resource": "*",
    "Condition": {
      "StringEquals": {
        "ec2:ResourceTag/Owner": "${aws:username}"
      }
    }
  }]
}
```

This allows a user to start/stop only EC2 instances tagged with their own username as `Owner`.

### S3 Bucket Policy — Allow Specific Roles Only

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::123456789012:role/AppRole",
          "arn:aws:iam::123456789012:role/CIRole"
        ]
      },
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::my-bucket/*"
    },
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"],
      "Condition": {
        "Bool": {"aws:SecureTransport": "false"}
      }
    }
  ]
}
```

### EC2 — Allow Terminate Only for dev Environment

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ec2:TerminateInstances",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ec2:ResourceTag/Environment": "development"
        }
      }
    },
    {
      "Effect": "Deny",
      "Action": "ec2:TerminateInstances",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "ec2:ResourceTag/Environment": "development"
        }
      }
    }
  ]
}
```

---

## Permission Boundaries

A permission boundary is an IAM managed policy that sets the **maximum** permissions an IAM entity (user or role) can have. Even if you attach `AdministratorAccess`, if the boundary allows only S3, only S3 actions work.

**Use case**: Delegate IAM administration to teams without letting them create users/roles with more permissions than their own.

```bash
# Create a permission boundary policy
aws iam create-policy \
    --policy-name DeveloperBoundary \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["s3:*", "ec2:*", "cloudwatch:*", "logs:*"],
            "Resource": "*"
        }]
    }'

# Attach boundary to a role at creation time
aws iam create-role \
    --role-name DeveloperRole \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:root"},"Action":"sts:AssumeRole"}]}' \
    --permissions-boundary arn:aws:iam::123456789012:policy/DeveloperBoundary

# Attach boundary to an existing user
aws iam put-user-permissions-boundary \
    --user-name alice \
    --permissions-boundary arn:aws:iam::123456789012:policy/DeveloperBoundary
```

---

## Managing Policies via CLI

```bash
# Create a customer-managed policy
aws iam create-policy \
    --policy-name S3BucketReadPolicy \
    --description "Read access to the data-lake bucket" \
    --policy-document file://s3-read-policy.json

# Create a new version of a policy
aws iam create-policy-version \
    --policy-arn arn:aws:iam::123456789012:policy/S3BucketReadPolicy \
    --policy-document file://s3-read-policy-v2.json \
    --set-as-default

# List policy versions
aws iam list-policy-versions \
    --policy-arn arn:aws:iam::123456789012:policy/S3BucketReadPolicy

# Get policy document
aws iam get-policy-version \
    --policy-arn arn:aws:iam::123456789012:policy/S3BucketReadPolicy \
    --version-id v2 \
    --query 'PolicyVersion.Document'

# Attach managed policy to a role
aws iam attach-role-policy \
    --role-name MyRole \
    --policy-arn arn:aws:iam::123456789012:policy/S3BucketReadPolicy

# List policies attached to a role
aws iam list-attached-role-policies --role-name MyRole

# Put an inline policy on a role
aws iam put-role-policy \
    --role-name MyRole \
    --policy-name InlineS3Policy \
    --policy-document file://inline-policy.json

# Simulate a policy (policy simulator via CLI)
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::123456789012:role/MyRole \
    --action-names s3:GetObject s3:PutObject ec2:DescribeInstances \
    --resource-arns arn:aws:s3:::my-bucket/*
```

---

## AWS Managed Policy Reference

| Policy | Grants |
|--------|--------|
| `AdministratorAccess` | Full access to everything including IAM |
| `PowerUserAccess` | Full access except IAM user/group/role management |
| `ReadOnlyAccess` | Read-only across all services |
| `SecurityAudit` | Read security configuration across services |
| `Billing` | View and manage billing information |
| `AmazonS3ReadOnlyAccess` | Read-only access to S3 |
| `AmazonEC2FullAccess` | Full EC2 access |
| `AmazonRDSReadOnlyAccess` | Read-only RDS access |
| `AWSLambdaBasicExecutionRole` | Write CloudWatch Logs (standard Lambda role) |
| `AmazonSSMManagedInstanceCore` | Required for SSM Session Manager on EC2 |

---

## References

- [IAM policy reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies.html)
- [IAM policy examples](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_examples.html)
- [IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
- [AWS policy simulator](https://policysim.aws.amazon.com/)
---

← [Previous: Users, Groups & Roles](./users-groups-roles.md) | [Home](../../README.md) | [Next: Identity Center →](./identity-center.md)
