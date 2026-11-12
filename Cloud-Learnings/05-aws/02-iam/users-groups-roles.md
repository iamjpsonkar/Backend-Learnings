← [Previous: IAM Overview](./iam-overview.md) | [Home](../../README.md) | [Next: IAM Policies →](./policies.md)

---

# IAM Users, Groups, and Roles

This file covers the practical details of creating and managing IAM users, groups, and roles — including instance profiles, trust policies, and role chaining patterns used in cloud architectures.

---

## IAM Users — When to Use

| Situation | Recommendation |
|-----------|---------------|
| Human accessing AWS console + CLI | Prefer IAM Identity Center (SSO); IAM user if SSO not available |
| Application running on EC2 | IAM Role via instance profile — never an IAM user |
| Application running on Lambda | Lambda execution role — never an IAM user |
| CI/CD pipeline on GitHub Actions | OIDC role assumption — never a static key |
| CI/CD pipeline on Jenkins (self-hosted) | IAM role on the Jenkins EC2 instance |
| Third-party SaaS integration | IAM role with ExternalId (cross-account) |

**Avoid long-lived access keys.** They don't expire automatically, don't require MFA, and cause the most IAM-related security incidents when committed to code or exposed in logs.

---

## Creating and Managing Users

```bash
# Create a user
aws iam create-user \
    --user-name alice \
    --tags Key=Team,Value=backend Key=Environment,Value=production

# Create console password
aws iam create-login-profile \
    --user-name alice \
    --password 'Initial@Pass1' \
    --password-reset-required

# Create access keys
aws iam create-access-key --user-name alice
# Returns: AccessKeyId, SecretAccessKey, Status, CreateDate
# SecretAccessKey shown ONLY at creation time — save it immediately

# List a user's access keys (shows key IDs but not secret)
aws iam list-access-keys --user-name alice

# Rotate access keys
# Step 1: Create new key
aws iam create-access-key --user-name alice
# Step 2: Update application to use new key
# Step 3: Deactivate old key
aws iam update-access-key \
    --user-name alice \
    --access-key-id AKIAIOSFODNN7OLD \
    --status Inactive
# Step 4: Verify app works, then delete old key
aws iam delete-access-key \
    --user-name alice \
    --access-key-id AKIAIOSFODNN7OLD

# Enable MFA for a user
aws iam create-virtual-mfa-device \
    --virtual-mfa-device-name alice-mfa \
    --outfile /tmp/alice-mfa-qr.png \
    --bootstrap-method QRCodePNG
# User scans QR code and provides two consecutive TOTP codes:
aws iam enable-mfa-device \
    --user-name alice \
    --serial-number arn:aws:iam::123456789012:mfa/alice-mfa \
    --authentication-code1 123456 \
    --authentication-code2 789012

# Lock a user (disable console access + deactivate keys)
aws iam update-login-profile --user-name alice --password-reset-required
aws iam list-access-keys --user-name alice --query 'AccessKeyMetadata[*].AccessKeyId' \
    --output text | tr '\t' '\n' | while read key; do
    aws iam update-access-key --user-name alice --access-key-id "$key" --status Inactive
done

# Delete a user (must remove all attachments first)
aws iam detach-user-policy --user-name alice --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
aws iam remove-user-from-group --user-name alice --group-name Developers
aws iam delete-login-profile --user-name alice
aws iam delete-user --user-name alice
```

---

## Creating and Managing Groups

```bash
# Create groups
aws iam create-group --group-name Administrators
aws iam create-group --group-name Developers
aws iam create-group --group-name ReadOnly
aws iam create-group --group-name Billing

# Attach managed policies
aws iam attach-group-policy \
    --group-name Administrators \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

aws iam attach-group-policy \
    --group-name Developers \
    --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

aws iam attach-group-policy \
    --group-name ReadOnly \
    --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

aws iam attach-group-policy \
    --group-name Billing \
    --policy-arn arn:aws:iam::aws:policy/job-function/Billing

# Add users to groups
aws iam add-user-to-group --group-name Developers --user-name alice
aws iam add-user-to-group --group-name Developers --user-name bob

# List group members
aws iam get-group --group-name Developers \
    --query 'Users[*].UserName' --output table

# List a user's groups
aws iam list-groups-for-user --user-name alice \
    --query 'Groups[*].GroupName' --output text
```

---

## Creating and Managing Roles

### Service Roles (EC2, Lambda, ECS, etc.)

```bash
# Lambda execution role
aws iam create-role \
    --role-name LambdaBasicRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' \
    --description "Basic Lambda execution role"

aws iam attach-role-policy \
    --role-name LambdaBasicRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# ECS task role
aws iam create-role \
    --role-name ECSTaskRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

# ECS task execution role (pulls images from ECR, writes logs)
aws iam create-role \
    --role-name ECSTaskExecutionRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

aws iam attach-role-policy \
    --role-name ECSTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

### OIDC Roles (GitHub Actions, Kubernetes IRSA)

```bash
# GitHub Actions OIDC role (no long-lived keys needed)
aws iam create-role \
    --role-name GitHubActionsDeployRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:ref:refs/heads/main"
                }
            }
        }]
    }'

# EKS IRSA (IAM Roles for Service Accounts)
OIDC_PROVIDER=$(aws eks describe-cluster \
    --name my-cluster \
    --query "cluster.identity.oidc.issuer" \
    --output text | sed 's|https://||')

aws iam create-role \
    --role-name MyAppIRSARole \
    --assume-role-policy-document "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [{
            \"Effect\": \"Allow\",
            \"Principal\": {
                \"Federated\": \"arn:aws:iam::123456789012:oidc-provider/${OIDC_PROVIDER}\"
            },
            \"Action\": \"sts:AssumeRoleWithWebIdentity\",
            \"Condition\": {
                \"StringEquals\": {
                    \"${OIDC_PROVIDER}:aud\": \"sts.amazonaws.com\",
                    \"${OIDC_PROVIDER}:sub\": \"system:serviceaccount:production:my-app\"
                }
            }
        }]
    }"
```

### Cross-Account Role (with ExternalId)

ExternalId prevents the confused deputy problem — a third party can't trick your account into assuming their role.

```bash
# In the target account: role that partner account can assume
aws iam create-role \
    --role-name PartnerAuditRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::PARTNER_ACCOUNT_ID:root"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": "unique-secret-per-customer-abc123"
                }
            }
        }]
    }'

# Partner assumes the role with ExternalId
aws sts assume-role \
    --role-arn arn:aws:iam::YOUR_ACCOUNT:role/PartnerAuditRole \
    --role-session-name partner-audit \
    --external-id unique-secret-per-customer-abc123
```

---

## Instance Profiles

Instance profiles are containers for IAM roles that can be attached to EC2 instances. An EC2 instance can have exactly one instance profile (which contains one role).

```bash
# Create instance profile and add role
aws iam create-instance-profile \
    --instance-profile-name MyApp-InstanceProfile

aws iam add-role-to-instance-profile \
    --instance-profile-name MyApp-InstanceProfile \
    --role-name MyApp-EC2Role

# Attach to an instance at launch
aws ec2 run-instances \
    --image-id ami-0abcdef1234567890 \
    --instance-type t3.micro \
    --iam-instance-profile Name=MyApp-InstanceProfile \
    ...

# Attach/replace on a running instance
aws ec2 associate-iam-instance-profile \
    --instance-id i-0abc1234 \
    --iam-instance-profile Name=MyApp-InstanceProfile

# Replace existing instance profile
ASSOCIATION_ID=$(aws ec2 describe-iam-instance-profile-associations \
    --filters Name=instance-id,Values=i-0abc1234 \
    --query 'IamInstanceProfileAssociations[0].AssociationId' \
    --output text)

aws ec2 replace-iam-instance-profile-association \
    --association-id $ASSOCIATION_ID \
    --iam-instance-profile Name=NewProfile

# From inside EC2: verify current role
curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/
# Returns the role name; then:
curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/MyApp-EC2Role
# Returns temporary credentials (AccessKeyId, SecretAccessKey, Token, Expiration)
```

---

## Trust Policy Principals Reference

| Principal | Trust policy value | Used for |
|-----------|-------------------|---------|
| EC2 service | `{"Service": "ec2.amazonaws.com"}` | EC2 instance profiles |
| Lambda | `{"Service": "lambda.amazonaws.com"}` | Lambda execution roles |
| ECS task | `{"Service": "ecs-tasks.amazonaws.com"}` | ECS task roles |
| CodeBuild | `{"Service": "codebuild.amazonaws.com"}` | CodeBuild project role |
| CloudFormation | `{"Service": "cloudformation.amazonaws.com"}` | CloudFormation stack role |
| Another account | `{"AWS": "arn:aws:iam::ACCOUNT_ID:root"}` | Cross-account |
| Specific role | `{"AWS": "arn:aws:iam::ACCOUNT_ID:role/RoleName"}` | Scoped cross-account |
| IAM user | `{"AWS": "arn:aws:iam::ACCOUNT_ID:user/alice"}` | User-specific assumption |
| GitHub OIDC | `{"Federated": "...token.actions.githubusercontent.com"}` | GitHub Actions |
| Kubernetes OIDC | `{"Federated": "arn:aws:iam::ID:oidc-provider/..."}` | EKS IRSA |

---

## References

- [IAM users](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users.html)
- [IAM roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)
- [Instance profiles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html)
- [OIDC federation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_oidc.html)
---

← [Previous: IAM Overview](./iam-overview.md) | [Home](../../README.md) | [Next: IAM Policies →](./policies.md)
