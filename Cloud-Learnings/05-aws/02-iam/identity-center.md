← [Previous: IAM Policies](./policies.md) | [Home](../../README.md) | [Next: Organizations & SCP →](./organizations-scp.md)

---

# AWS IAM Identity Center (SSO)

IAM Identity Center (formerly AWS Single Sign-On) is the recommended way to manage human access to multiple AWS accounts. It provides a central place to manage users, assign permissions, and authenticate — with short-lived temporary credentials instead of long-lived IAM access keys.

---

## Why IAM Identity Center

| IAM Users | IAM Identity Center |
|-----------|---------------------|
| Long-lived access keys | Short-lived temporary credentials (1–12 hours) |
| Per-account user management | Central user management across all accounts |
| Separate IAM user per account | One identity, access to multiple accounts |
| Manual MFA setup per account | MFA enforced centrally |
| No SSO | Browser-based SSO portal |
| Complex key rotation | No keys to rotate |

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Identity source** | Where users and groups come from (built-in directory, Okta, Azure AD, etc.) |
| **Permission set** | A named collection of IAM policies assigned to a user/group in an account |
| **Account assignment** | Granting a user/group a permission set in a specific account |
| **SSO portal** | Web URL where users log in and see their assigned accounts |
| **SCIM** | Protocol for auto-provisioning users/groups from an external IdP |

---

## Setup Overview

1. Enable IAM Identity Center (in the management account)
2. Choose an identity source (built-in directory or external IdP)
3. Create users and groups (or sync from external IdP via SCIM)
4. Create permission sets (map to IAM policies)
5. Assign users/groups → permission sets → accounts
6. Users access via the SSO portal or `aws sso login`

---

## Enable IAM Identity Center

```bash
# Enable via console: IAM Identity Center → Enable
# Or via CLI (requires management account):
aws sso-admin list-instances
# If empty, go to console to enable (initial setup requires console)

# After enabling, get the instance ARN and identity store ID
aws sso-admin list-instances \
    --query 'Instances[0].{InstanceArn:InstanceArn,IdentityStoreId:IdentityStoreId}'
```

---

## Managing Users and Groups

### Built-in Directory

```bash
IDENTITY_STORE_ID="d-1234567890"

# Create a user
aws identitystore create-user \
    --identity-store-id $IDENTITY_STORE_ID \
    --user-name alice \
    --display-name "Alice Smith" \
    --name '{
        "FamilyName": "Smith",
        "GivenName": "Alice"
    }' \
    --emails '[{
        "Value": "alice@example.com",
        "Primary": true
    }]'

# Create a group
aws identitystore create-group \
    --identity-store-id $IDENTITY_STORE_ID \
    --display-name "Developers" \
    --description "Development team"

# Add user to group
GROUP_ID=$(aws identitystore list-groups \
    --identity-store-id $IDENTITY_STORE_ID \
    --filters AttributePath=DisplayName,AttributeValue=Developers \
    --query 'Groups[0].GroupId' --output text)

USER_ID=$(aws identitystore list-users \
    --identity-store-id $IDENTITY_STORE_ID \
    --filters AttributePath=UserName,AttributeValue=alice \
    --query 'Users[0].UserId' --output text)

aws identitystore create-group-membership \
    --identity-store-id $IDENTITY_STORE_ID \
    --group-id $GROUP_ID \
    --member-id UserId=$USER_ID

# List users
aws identitystore list-users \
    --identity-store-id $IDENTITY_STORE_ID \
    --query 'Users[*].{Username:UserName,Name:DisplayName}' \
    --output table
```

### External IdP (Okta, Azure AD, Google Workspace)

1. In IAM Identity Center: Settings → Identity source → Change → External identity provider
2. Download the SP metadata from IAM Identity Center
3. Configure your IdP with the SP metadata (SAML app)
4. Upload the IdP metadata to IAM Identity Center
5. Enable SCIM provisioning for automatic user/group sync

For SCIM:
```
IAM Identity Center → Settings → Identity source → SCIM endpoint + bearer token
# Configure in your IdP's provisioning settings
# Groups created in the IdP appear automatically in IAM Identity Center
```

---

## Permission Sets

A permission set is a template for IAM access. It is instantiated as an IAM role in each account where it is assigned.

```bash
INSTANCE_ARN="arn:aws:sso:::instance/ssoins-1234567890abcdef0"

# Create a permission set
aws sso-admin create-permission-set \
    --instance-arn $INSTANCE_ARN \
    --name "DeveloperAccess" \
    --description "Full access except IAM admin" \
    --session-duration "PT8H"   # ISO 8601 duration: 8 hours

# Attach an AWS managed policy
PERMISSION_SET_ARN=$(aws sso-admin list-permission-sets \
    --instance-arn $INSTANCE_ARN \
    --query 'PermissionSets[0]' --output text)

aws sso-admin attach-managed-policy-to-permission-set \
    --instance-arn $INSTANCE_ARN \
    --permission-set-arn $PERMISSION_SET_ARN \
    --managed-policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# Attach a customer managed policy
aws sso-admin attach-customer-managed-policy-reference-to-permission-set \
    --instance-arn $INSTANCE_ARN \
    --permission-set-arn $PERMISSION_SET_ARN \
    --customer-managed-policy-reference Name=MyCustomPolicy,Path=/

# Add an inline policy to the permission set
aws sso-admin put-inline-policy-to-permission-set \
    --instance-arn $INSTANCE_ARN \
    --permission-set-arn $PERMISSION_SET_ARN \
    --inline-policy '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Deny",
            "Action": "iam:*",
            "Resource": "*"
        }]
    }'

# Set a permission boundary (limit max permissions)
aws sso-admin put-permissions-boundary-to-permission-set \
    --instance-arn $INSTANCE_ARN \
    --permission-set-arn $PERMISSION_SET_ARN \
    --permissions-boundary ManagedPolicyArn=arn:aws:iam::aws:policy/PowerUserAccess
```

### Common Permission Set Structure

| Name | Policies | Session | For |
|------|----------|---------|-----|
| `AdministratorAccess` | AdministratorAccess | 4h | Account admins |
| `DeveloperAccess` | PowerUserAccess + deny IAM | 8h | Developers |
| `ReadOnlyAccess` | ReadOnlyAccess | 8h | Auditors, stakeholders |
| `BillingAccess` | Billing | 8h | Finance team |
| `SecurityAudit` | SecurityAudit + ViewOnlyAccess | 8h | Security team |
| `NetworkAdmin` | AmazonVPCFullAccess + related | 4h | Network team |

---

## Account Assignments

Account assignments grant a principal (user or group) a permission set in a specific account.

```bash
ACCOUNT_ID="111122223333"

# Assign a group to an account with a permission set
aws sso-admin create-account-assignment \
    --instance-arn $INSTANCE_ARN \
    --target-id $ACCOUNT_ID \
    --target-type AWS_ACCOUNT \
    --permission-set-arn $PERMISSION_SET_ARN \
    --principal-type GROUP \
    --principal-id $GROUP_ID

# Assign an individual user
aws sso-admin create-account-assignment \
    --instance-arn $INSTANCE_ARN \
    --target-id $ACCOUNT_ID \
    --target-type AWS_ACCOUNT \
    --permission-set-arn $PERMISSION_SET_ARN \
    --principal-type USER \
    --principal-id $USER_ID

# List all assignments for an account
aws sso-admin list-account-assignments \
    --instance-arn $INSTANCE_ARN \
    --account-id $ACCOUNT_ID \
    --permission-set-arn $PERMISSION_SET_ARN \
    --query 'AccountAssignments[*].{Principal:PrincipalId,Type:PrincipalType}' \
    --output table
```

---

## CLI Authentication via SSO

```bash
# Configure SSO profile (one-time)
aws configure sso
# Enter: SSO start URL, SSO region, account, role, CLI region

# Or configure ~/.aws/config manually:
# [sso-session myorg]
# sso_start_url = https://myorg.awsapps.com/start
# sso_region = us-east-1
# sso_registration_scopes = sso:account:access
#
# [profile dev]
# sso_session = myorg
# sso_account_id = 111122223333
# sso_role_name = DeveloperAccess
# region = us-east-1

# Log in (opens browser)
aws sso login --profile dev

# Use the profile
aws s3 ls --profile dev
export AWS_PROFILE=dev

# Log out
aws sso logout

# List all available accounts and roles (after login)
aws sso list-accounts --access-token $(cat ~/.aws/sso/cache/*.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('accessToken',''))")
```

---

## SCIM Auto-Provisioning Pattern

When using an external IdP with SCIM:

```
Okta / Azure AD / Google Workspace
    │
    │ SCIM (automatic sync every ~40 min)
    ▼
IAM Identity Center (users + groups mirror IdP)
    │
    │ Account assignments (configured once)
    ▼
AWS Accounts (roles created automatically per permission set)
```

**Lifecycle automation:**
- New employee added to Okta group "Developers" → automatically gets access to dev/staging AWS accounts
- Employee leaves → disable in Okta → access revoked in IAM Identity Center within 40 minutes (or immediately via force sync)
- No manual AWS IAM user creation/deletion required

---

## MFA Configuration

```bash
# Enforce MFA for all users in the directory
# IAM Identity Center → Settings → Authentication → MFA → Require MFA

# Options:
#   Required (all users must enroll before first sign-in)
#   Required only for users with no corporate credentials (IdP without MFA)
#   Not required (not recommended)

# Supported MFA types:
#   TOTP (authenticator apps: Okta Verify, Google Authenticator, Authy)
#   WebAuthn / FIDO2 (hardware security keys: YubiKey)
```

---

## References

- [IAM Identity Center documentation](https://docs.aws.amazon.com/singlesignon/latest/userguide/)
- [IAM Identity Center CLI commands](https://docs.aws.amazon.com/cli/latest/reference/sso-admin/)
- [SCIM provisioning](https://docs.aws.amazon.com/singlesignon/latest/userguide/provision-automatically.html)
- [Okta + AWS IAM Identity Center integration](https://help.okta.com/en-us/content/topics/deploymentguides/aws/aws-deployment.htm)
---

← [Previous: IAM Policies](./policies.md) | [Home](../../README.md) | [Next: Organizations & SCP →](./organizations-scp.md)
