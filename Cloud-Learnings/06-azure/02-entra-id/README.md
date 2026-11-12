← [Previous: Resource Groups](../01-account-setup/resource-groups.md) | [Home](../../README.md) | [Next: Entra ID Basics →](./entra-id-basics.md)

---

# Microsoft Entra ID (formerly Azure Active Directory)

Entra ID is Azure's identity and access management platform. It handles authentication (who are you?) and authorization (what can you do?). Every Azure resource is secured through Entra ID.

---

## Core Concepts

| Concept | AWS Equivalent | Meaning |
|---------|----------------|---------|
| **Tenant** | AWS Account (IAM root) | The Entra ID directory — one per organization |
| **User** | IAM User | A human identity |
| **Group** | IAM Group | Collection of users — assign roles to groups |
| **Service Principal** | IAM Role (for applications) | Application identity for code/services |
| **Managed Identity** | IAM Role on EC2/Lambda | Azure-managed identity for Azure resources |
| **App Registration** | OIDC Identity Provider | Register an application in Entra ID |
| **Role** | IAM Policy | A set of permissions (Reader, Contributor, Owner, custom) |
| **Role Assignment** | IAM Policy attachment | Bind a role to a principal on a scope |
| **Scope** | IAM Resource ARN | Where the role applies: management group / subscription / resource group / resource |
| **Conditional Access** | AWS IAM Conditions | Policy-based access control (MFA, location, device) |

---

## RBAC — Role-Based Access Control

Azure RBAC has four built-in roles for general use:

| Role | Permissions |
|------|------------|
| **Owner** | Full control + manage access |
| **Contributor** | Create and manage resources, no access management |
| **Reader** | View resources, no changes |
| **User Access Administrator** | Manage access only |

Plus hundreds of service-specific built-in roles (e.g., `Storage Blob Data Contributor`, `AKS Cluster Admin`).

```bash
# List all built-in roles
az role definition list --query '[?roleType==`BuiltInRole`].{Name:roleName,Description:description}' --output table

# Get role definition details
az role definition list --name "Contributor" --output json

# Assign Contributor role on a resource group
az role assignment create \
    --assignee user@example.com \
    --role Contributor \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-production

# Assign a role to a group
GROUP_ID=$(az ad group show --group "platform-team" --query id --output tsv)
az role assignment create \
    --assignee $GROUP_ID \
    --role "Reader" \
    --scope /subscriptions/$SUBSCRIPTION_ID

# List role assignments on a scope
az role assignment list \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-production \
    --output table

# Remove a role assignment
az role assignment delete \
    --assignee user@example.com \
    --role Contributor \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-production
```

---

## Custom Roles

```bash
# Create a custom role with only the permissions needed
az role definition create --role-definition '{
    "Name": "AKS Node Pool Manager",
    "Description": "Can scale AKS node pools but not delete the cluster",
    "Actions": [
        "Microsoft.ContainerService/managedClusters/read",
        "Microsoft.ContainerService/managedClusters/agentPools/read",
        "Microsoft.ContainerService/managedClusters/agentPools/write"
    ],
    "NotActions": [],
    "DataActions": [],
    "NotDataActions": [],
    "AssignableScopes": [
        "/subscriptions/'"$SUBSCRIPTION_ID"'"
    ]
}'
```

---

## Users and Groups

```bash
# Create a user
az ad user create \
    --display-name "Alice Smith" \
    --user-principal-name alice@example.com \
    --password "TempPass123!" \
    --force-change-password-next-sign-in true

# Get a user
az ad user show --id alice@example.com \
    --query '{Name:displayName,UPN:userPrincipalName,ID:id,AccountEnabled:accountEnabled}'

# Create a group
az ad group create \
    --display-name "platform-team" \
    --mail-nickname "platform-team"

# Add user to group
az ad group member add \
    --group "platform-team" \
    --member-id $(az ad user show --id alice@example.com --query id --output tsv)

# List group members
az ad group member list \
    --group "platform-team" \
    --query '[*].{Name:displayName,UPN:userPrincipalName}' \
    --output table
```

---

## Service Principals

Service principals are application identities used by workloads running outside Azure (CI/CD, on-premises, other clouds).

```bash
# Create a service principal for a CI/CD pipeline
SP=$(az ad sp create-for-rbac \
    --name "sp-github-actions-deployment" \
    --role Contributor \
    --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-production \
    --sdk-auth)

# Output includes appId, password, tenant — store in GitHub Secrets / CI/CD secrets
echo $SP | python3 -m json.tool

# View an existing service principal
az ad sp show --id $APP_ID \
    --query '{Name:displayName,AppID:appId,ServicePrincipalType:servicePrincipalType}'

# Rotate service principal credentials (create new, rotate in CI/CD, delete old)
az ad sp credential reset \
    --id $APP_ID \
    --years 1 \
    --query '{AppID:appId,Password:password,Tenant:tenant}'

# List service principal role assignments
az role assignment list --assignee $APP_ID --output table
```

---

## Managed Identities

Managed identities are the preferred way to authenticate Azure resources to other Azure services — no credentials to manage.

| Type | Lifecycle | Use case |
|------|-----------|---------|
| **System-assigned** | Tied to the resource — deleted with resource | Single resource, simple auth |
| **User-assigned** | Independent lifecycle — reuse across resources | Shared identity across multiple resources |

```bash
# Enable system-assigned managed identity on a VM
az vm identity assign \
    --resource-group rg-my-app-production \
    --name vm-my-app-prod-eastus-001

# Get the principal ID of the system-assigned identity
PRINCIPAL_ID=$(az vm show \
    --resource-group rg-my-app-production \
    --name vm-my-app-prod-eastus-001 \
    --query identity.principalId --output tsv)

# Grant the VM read access to a Key Vault
az keyvault set-policy \
    --name kv-my-app-prod-eastus \
    --object-id $PRINCIPAL_ID \
    --secret-permissions get list

# Create a user-assigned managed identity (reusable)
IDENTITY_ID=$(az identity create \
    --resource-group rg-my-app-production \
    --name id-my-app-production \
    --query id --output tsv)

# Assign to an AKS cluster (for pod workload identity)
az aks update \
    --resource-group rg-my-app-production \
    --name aks-my-app-prod-eastus-001 \
    --assign-identity $IDENTITY_ID

# Grant permissions to the user-assigned identity
CLIENT_ID=$(az identity show --ids $IDENTITY_ID --query clientId --output tsv)
az role assignment create \
    --assignee $CLIENT_ID \
    --role "Storage Blob Data Reader" \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-production
```

---

## App Registrations (OAuth2 / OIDC)

```bash
# Register an application (for OAuth2 authorization code flow)
APP_ID=$(az ad app create \
    --display-name "my-app-production" \
    --sign-in-audience AzureADMyOrg \
    --web-redirect-uris "https://my-app.example.com/auth/callback" \
    --query appId --output tsv)

# Add API permissions (Microsoft Graph — User.Read)
az ad app permission add \
    --id $APP_ID \
    --api 00000003-0000-0000-c000-000000000000 \
    --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope

# Grant admin consent
az ad app permission admin-consent --id $APP_ID

# Configure as federated identity (GitHub Actions OIDC — no secrets needed)
az ad app federated-credential create \
    --id $APP_ID \
    --parameters '{
        "name": "github-actions-main",
        "issuer": "https://token.actions.githubusercontent.com",
        "subject": "repo:my-org/my-repo:ref:refs/heads/main",
        "audiences": ["api://AzureADTokenExchange"]
    }'
```

---

## Multi-Factor Authentication and Conditional Access

```bash
# View Conditional Access policies (requires P1 or P2 license)
az rest --method GET \
    --url "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" \
    --query "value[*].{Name:displayName,State:state}" --output table

# Create a Conditional Access policy via Microsoft Graph (require MFA for all users)
az rest --method POST \
    --url "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" \
    --body '{
        "displayName": "Require MFA for All Users",
        "state": "enabled",
        "conditions": {
            "users": {"includeUsers": ["All"]},
            "applications": {"includeApplications": ["All"]},
            "locations": {"includeLocations": ["All"]}
        },
        "grantControls": {
            "operator": "OR",
            "builtInControls": ["mfa"]
        }
    }'
```

---

## Privileged Identity Management (PIM)

PIM provides just-in-time privileged access — roles are activated on-demand, not always-on.

```bash
# Activate an eligible role assignment (requires PIM P2 license)
az rest --method POST \
    --url "https://graph.microsoft.com/v1.0/roleManagement/directory/roleAssignmentScheduleRequests" \
    --body '{
        "action": "selfActivate",
        "principalId": "'"$USER_OBJECT_ID"'",
        "roleDefinitionId": "b24988ac-6180-42a0-ab88-20f7382dd24c",
        "directoryScopeId": "/",
        "scheduleInfo": {
            "startDateTime": "2024-01-01T00:00:00Z",
            "expiration": {"type": "afterDuration", "duration": "PT4H"}
        },
        "justification": "Investigating production incident"
    }'
```

---

## References

- [Entra ID documentation](https://docs.microsoft.com/azure/active-directory/)
- [Azure RBAC built-in roles](https://docs.microsoft.com/azure/role-based-access-control/built-in-roles)
- [Managed identities](https://docs.microsoft.com/azure/active-directory/managed-identities-azure-resources/)
- [Conditional Access](https://docs.microsoft.com/azure/active-directory/conditional-access/)
- [Microsoft Graph API](https://docs.microsoft.com/graph/)
---

← [Previous: Resource Groups](../01-account-setup/resource-groups.md) | [Home](../../README.md) | [Next: Entra ID Basics →](./entra-id-basics.md)
