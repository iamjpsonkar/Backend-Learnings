← [Previous: Security Overview](./README.md) | [Home](../README.md) | [Next: Network Security →](./network-security.md)

---

# IAM and Least Privilege

The principle of least privilege grants only the minimum permissions needed to perform a task. Over-permissioned identities are one of the most common cloud security vulnerabilities.

---

## Core Principles

1. **Start with zero access** — deny by default, add only what is needed
2. **Prefer roles over users** — services use IAM roles, not access keys
3. **No shared credentials** — one identity per service/team member
4. **Time-bound access** — use temporary credentials via STS/Workload Identity
5. **Audit continuously** — review and revoke unused permissions regularly

---

## AWS IAM Best Practices

```bash
# ─── Audit unused permissions ───────────────────────────────────
# IAM Access Analyzer — finds unused permissions in roles
aws accessanalyzer create-analyzer \
    --analyzer-name my-analyzer \
    --type ACCOUNT

# Generate access report for a role
aws iam generate-service-last-accessed-details \
    --arn arn:aws:iam::123456789012:role/MyAppRole

JOB_ID=$(aws iam generate-service-last-accessed-details \
    --arn arn:aws:iam::123456789012:role/MyAppRole \
    --query 'JobId' --output text)

aws iam get-service-last-accessed-details \
    --job-id $JOB_ID \
    --query 'ServicesLastAccessed[?TotalAuthenticatedEntities>`0`].[ServiceName,LastAuthenticated]' \
    --output table

# Find roles with overly broad policies (Admin or *)
aws iam list-roles --query 'Roles[*].RoleName' --output text | tr '\t' '\n' | while read role; do
    POLICIES=$(aws iam list-attached-role-policies --role-name "$role" --query 'AttachedPolicies[*].PolicyName' --output text)
    echo "$role: $POLICIES"
done
```

### Permission Boundaries

A permission boundary is the maximum permissions an IAM entity can have, regardless of what policies are attached.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowOnlySpecificServices",
            "Effect": "Allow",
            "Action": [
                "s3:*",
                "dynamodb:*",
                "sqs:*",
                "cloudwatch:PutMetricData",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        },
        {
            "Sid": "DenyEscalation",
            "Effect": "Deny",
            "Action": [
                "iam:*",
                "sts:AssumeRole",
                "organizations:*"
            ],
            "Resource": "*"
        }
    ]
}
```

```bash
# Attach permission boundary to a role
aws iam put-role-permissions-boundary \
    --role-name MyAppRole \
    --permissions-boundary arn:aws:iam::123456789012:policy/AppPermissionBoundary
```

### Service Control Policies (SCPs) — AWS Organizations

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DenyLeaveOrg",
            "Effect": "Deny",
            "Action": "organizations:LeaveOrganization",
            "Resource": "*"
        },
        {
            "Sid": "RequireRegion",
            "Effect": "Deny",
            "Action": "*",
            "Resource": "*",
            "Condition": {
                "StringNotEquals": {
                    "aws:RequestedRegion": ["us-east-1", "us-west-2"]
                }
            }
        },
        {
            "Sid": "DenyDisableCloudTrail",
            "Effect": "Deny",
            "Action": [
                "cloudtrail:DeleteTrail",
                "cloudtrail:StopLogging",
                "cloudtrail:UpdateTrail"
            ],
            "Resource": "*"
        },
        {
            "Sid": "RequireIMDSv2",
            "Effect": "Deny",
            "Action": "ec2:RunInstances",
            "Resource": "arn:aws:ec2:*:*:instance/*",
            "Condition": {
                "StringNotEquals": {
                    "ec2:MetadataHttpTokens": "required"
                }
            }
        }
    ]
}
```

### IAM Conditions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::my-app-data/*",
            "Condition": {
                "StringEquals": {
                    "s3:prefix": ["${aws:PrincipalTag/team}/"]
                },
                "Bool": {
                    "aws:MultiFactorAuthPresent": "true"
                },
                "IpAddress": {
                    "aws:SourceIp": ["10.0.0.0/8", "203.0.113.0/24"]
                },
                "DateGreaterThan": {
                    "aws:CurrentTime": "2024-01-01T00:00:00Z"
                }
            }
        }
    ]
}
```

---

## GCP IAM Best Practices

```bash
PROJECT="my-app-prod-123456"

# ─── Audit IAM bindings ────────────────────────────────────────
# Find all project-level bindings
gcloud projects get-iam-policy $PROJECT \
    --format="table(bindings.role,bindings.members)"

# Find service accounts with project-owner or editor roles
gcloud projects get-iam-policy $PROJECT \
    --flatten="bindings[].members" \
    --format="table(bindings.role,bindings.members)" \
    --filter="bindings.role:roles/owner OR bindings.role:roles/editor"

# Disable unused service accounts
gcloud iam service-accounts disable \
    legacy-sa@$PROJECT.iam.gserviceaccount.com \
    --project=$PROJECT

# Recommend least-privilege roles for a service account
gcloud recommender recommendations list \
    --recommender=google.iam.policy.Recommender \
    --location=global \
    --project=$PROJECT \
    --format="table(name,description,priority)"

# ─── Org policy constraints ───────────────────────────────────
# Restrict resource locations
gcloud org-policies set-policy org-policy.yaml
```

```yaml
# org-policy.yaml — restrict GCP resource locations
name: projects/my-app-prod-123456/policies/gcp.resourceLocations
spec:
  rules:
    - values:
        allowedValues:
          - in:us-locations
          - in:eu-locations
---
# Disable service account key creation (force Workload Identity)
name: projects/my-app-prod-123456/policies/iam.disableServiceAccountKeyCreation
spec:
  rules:
    - enforce: true
---
# Require OS Login on Compute Engine VMs
name: projects/my-app-prod-123456/policies/compute.requireOsLogin
spec:
  rules:
    - enforce: true
```

---

## Azure IAM Best Practices

```bash
SUBSCRIPTION_ID="your-subscription-id"

# ─── Audit role assignments ────────────────────────────────────
# List all role assignments at subscription scope
az role assignment list \
    --subscription $SUBSCRIPTION_ID \
    --all \
    --query "[?principalType=='ServicePrincipal'].{Principal:principalName,Role:roleDefinitionName,Scope:scope}" \
    --output table

# Find over-privileged assignments (Owner/Contributor at subscription)
az role assignment list \
    --subscription $SUBSCRIPTION_ID \
    --query "[?roleDefinitionName=='Owner' || roleDefinitionName=='Contributor']" \
    --output table

# Enable PIM (Privileged Identity Management) — just-in-time access
az rest --method post \
    --uri "https://management.azure.com/providers/Microsoft.Authorization/roleEligibilityScheduleRequests?api-version=2022-04-01-preview"
```

---

## Rotate and Revoke

```bash
# AWS: Find and delete old access keys
aws iam list-users --query 'Users[*].UserName' --output text | tr '\t' '\n' | while read user; do
    aws iam list-access-keys --user-name "$user" \
        --query "AccessKeyMetadata[?Status=='Active' && CreateDate<='$(date -d '90 days ago' +%Y-%m-%d)'].{User:'$user',KeyId:AccessKeyId,Created:CreateDate}" \
        --output table
done

# GCP: Delete all service account keys (enforce Workload Identity)
SA="sa-my-app@my-project.iam.gserviceaccount.com"
gcloud iam service-accounts keys list --iam-account=$SA --managed-by=user \
    --format="value(name)" | while read key; do
    gcloud iam service-accounts keys delete $key --iam-account=$SA --quiet
done
```

---

## References

- [AWS IAM best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS IAM Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html)
- [GCP IAM recommender](https://cloud.google.com/iam/docs/recommender-overview)
- [Azure PIM](https://learn.microsoft.com/en-us/azure/active-directory/privileged-identity-management/)

---

← [Previous: Security Overview](./README.md) | [Home](../README.md) | [Next: Network Security →](./network-security.md)
