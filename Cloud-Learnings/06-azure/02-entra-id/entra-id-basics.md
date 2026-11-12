← [Previous: Azure Entra ID](./README.md) | [Home](../../README.md) | [Next: Azure RBAC →](./rbac.md)

---

# Microsoft Entra ID Basics

Microsoft Entra ID (formerly Azure Active Directory) is Microsoft's cloud-based identity and access management service. It is the authentication and authorization foundation for all of Azure.

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Tenant** | An Entra ID directory — one per organization. Identified by a GUID (tenant ID) and a domain (contoso.onmicrosoft.com) |
| **User** | A human identity. Can be a member (internal) or guest (B2B) |
| **Group** | Collection of users. Use groups for role assignments — never assign roles directly to individual users in production |
| **Service Principal** | Application identity for non-human workloads (CI/CD, third-party apps) |
| **Managed Identity** | Azure-managed service principal for Azure resources — no credential management needed |
| **App Registration** | Represents an application in Entra ID — used for OAuth2 / OIDC flows |
| **Directory Role** | Entra ID-level administrative roles (Global Admin, User Admin) — separate from Azure RBAC |
| **Tenant Domain** | Primary domain: `contoso.onmicrosoft.com`. Custom domains can be added |

---

## Tenant Setup

```bash
# Get tenant ID
az account show --query tenantId --output tsv

# List all tenants you have access to
az account tenant list --output table

# View tenant details via Microsoft Graph
az rest --method GET \
    --url "https://graph.microsoft.com/v1.0/organization" \
    --query "value[0].{Name:displayName,ID:id,Domain:verifiedDomains[0].name}"

# Add a custom domain (requires DNS TXT record for verification)
az ad domain show --domain "contoso.com" 2>/dev/null || \
    az ad domain create --domain "contoso.com"
```

---

## Users

```bash
# Create a user
az ad user create \
    --display-name "Alice Smith" \
    --user-principal-name alice@contoso.onmicrosoft.com \
    --password "TempPass@2024!" \
    --force-change-password-next-sign-in true \
    --mail-nickname alice

# List users
az ad user list \
    --query '[*].{Name:displayName,UPN:userPrincipalName,Enabled:accountEnabled}' \
    --output table

# Get a specific user
az ad user show --id alice@contoso.onmicrosoft.com \
    --query '{Name:displayName,UPN:userPrincipalName,ID:id,Enabled:accountEnabled}'

# Disable a user (e.g., offboarding)
az ad user update \
    --id alice@contoso.onmicrosoft.com \
    --account-enabled false

# Reset password
az ad user update \
    --id alice@contoso.onmicrosoft.com \
    --password "NewTempPass@2024!" \
    --force-change-password-next-sign-in true

# Delete a user
az ad user delete --id alice@contoso.onmicrosoft.com
```

---

## Groups

```bash
# Create a security group
az ad group create \
    --display-name "platform-team" \
    --mail-nickname "platform-team" \
    --description "Platform engineering team"

# Add a user to a group
az ad group member add \
    --group "platform-team" \
    --member-id $(az ad user show --id alice@contoso.onmicrosoft.com --query id -o tsv)

# Add a service principal to a group
az ad group member add \
    --group "platform-team" \
    --member-id $(az ad sp show --id $APP_ID --query id -o tsv)

# List group members
az ad group member list \
    --group "platform-team" \
    --query '[*].{Name:displayName,Type:odataType}' \
    --output table

# Check if a user is in a group
az ad group member check \
    --group "platform-team" \
    --member-id $(az ad user show --id alice@contoso.onmicrosoft.com --query id -o tsv)

# List groups a user belongs to
az ad user get-member-groups --id alice@contoso.onmicrosoft.com --output table
```

---

## Multi-Factor Authentication (MFA)

MFA is the single most important security control for identity. Enable it for all users, especially administrators.

### Per-User MFA (legacy — use Conditional Access instead)

```bash
# Enable MFA via Microsoft Graph
az rest --method PATCH \
    --url "https://graph.microsoft.com/beta/users/$(az ad user show --id alice@contoso.onmicrosoft.com --query id -o tsv)" \
    --body '{"strongAuthenticationRequirements": [{"rememberDevicesNotIssuedBefore": null, "state": "Enabled"}]}'
```

### Conditional Access (recommended)

Conditional Access policies enforce MFA based on conditions (user, location, device, risk level). Requires Entra ID P1 license.

```bash
# Require MFA for all users accessing all apps (via Microsoft Graph)
az rest --method POST \
    --url "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" \
    --body '{
        "displayName": "Require MFA — All Users",
        "state": "enabled",
        "conditions": {
            "users": {
                "includeUsers": ["All"],
                "excludeUsers": ["breakglass-account-object-id"]
            },
            "applications": {"includeApplications": ["All"]},
            "locations": {"includeLocations": ["All"]}
        },
        "grantControls": {
            "operator": "OR",
            "builtInControls": ["mfa"]
        }
    }'

# List Conditional Access policies
az rest --method GET \
    --url "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" \
    --query "value[*].{Name:displayName,State:state}" --output table
```

---

## Break-Glass Accounts

Every tenant should have at least two emergency admin accounts that are excluded from Conditional Access policies:

- No MFA requirement (in case MFA system fails)
- Stored credentials in a physical safe
- Monitored via alerts — any sign-in triggers an immediate notification

```bash
# Create break-glass account
az ad user create \
    --display-name "BreakGlass-001" \
    --user-principal-name breakglass001@contoso.onmicrosoft.com \
    --password "$(openssl rand -base64 32)" \
    --force-change-password-next-sign-in false

# Assign Global Administrator role
az role assignment create \
    --assignee breakglass001@contoso.onmicrosoft.com \
    --role "62e90394-69f5-4237-9190-012177145e10" \
    --scope /
```

---

## Entra ID Directory Roles

These are tenant-level administrative roles, separate from Azure RBAC.

| Role | What it controls |
|------|-----------------|
| Global Administrator | Full tenant control — treat like root |
| User Administrator | Create/delete users and groups |
| Application Administrator | Manage app registrations |
| Security Administrator | Security policies and alerts |
| Billing Administrator | Billing and subscriptions |
| Privileged Role Administrator | Manage role assignments |

```bash
# List directory role definitions
az rest --method GET \
    --url "https://graph.microsoft.com/v1.0/directoryRoles" \
    --query "value[*].{Name:displayName,ID:id}" --output table

# Assign Global Administrator to a user
az rest --method POST \
    --url "https://graph.microsoft.com/v1.0/directoryRoles/62e90394-69f5-4237-9190-012177145e10/members/\$ref" \
    --body "{\"@odata.id\": \"https://graph.microsoft.com/v1.0/directoryObjects/$(az ad user show --id alice@contoso.onmicrosoft.com --query id -o tsv)\"}"
```

---

## References

- [Entra ID documentation](https://docs.microsoft.com/azure/active-directory/)
- [Entra ID licenses](https://www.microsoft.com/security/business/microsoft-entra-pricing)
- [Conditional Access documentation](https://docs.microsoft.com/azure/active-directory/conditional-access/)
- [Break-glass accounts guidance](https://docs.microsoft.com/azure/active-directory/roles/security-emergency-access)

---

← [Previous: Azure Entra ID](./README.md) | [Home](../../README.md) | [Next: Azure RBAC →](./rbac.md)
