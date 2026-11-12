← [Previous: Entra ID Basics](./entra-id-basics.md) | [Home](../../README.md) | [Next: Service Principals →](./service-principals.md)

---

# Azure RBAC

Azure Role-Based Access Control (RBAC) controls who can do what on Azure resources. It operates independently from Entra ID directory roles.

---

## How Azure RBAC Works

An **authorization decision** = Role Assignment + Scope

```
Principal (who)        Role (what)              Scope (where)
─────────────────      ─────────────────────    ──────────────────────────────
User / Group /         Owner / Contributor /    Management Group /
Service Principal /    Reader / custom role      Subscription /
Managed Identity                                 Resource Group /
                                                 Individual Resource
```

Role assignments are **additive** — if a user has Reader on a subscription and Contributor on one resource group, they can contribute in that RG.

---

## Scope Hierarchy

```
Management Group
└── Subscription
    └── Resource Group
        └── Resource
```

Roles assigned at a higher scope are inherited downward. Assigning Contributor at the subscription level grants Contributor on all resource groups and resources within it.

---

## Built-in Roles

### General Purpose

| Role | Permissions |
|------|------------|
| Owner | Full control + manage access (assign roles) |
| Contributor | Create and manage all resources, cannot manage access |
| Reader | View everything, no changes |
| User Access Administrator | Manage role assignments only |

### Common Service-Specific Roles

| Role | Scope |
|------|-------|
| Storage Blob Data Contributor | Read/write/delete blobs |
| Storage Blob Data Reader | Read blobs |
| Key Vault Secrets Officer | Read/write/delete secrets |
| Key Vault Secrets User | Read secrets only |
| AKS Cluster Admin | Full kubectl access |
| AKS RBAC Admin | Admin within namespaces |
| Network Contributor | Manage network resources |
| Virtual Machine Contributor | Manage VMs, no network/storage |
| SQL DB Contributor | Manage SQL databases |
| Monitoring Reader | Read monitoring data |

```bash
# List all built-in roles
az role definition list \
    --query '[?roleType==`BuiltInRole`].{Name:roleName,Type:roleType}' \
    --output table | sort

# Get details of a specific role
az role definition list --name "Contributor" --output json | python3 -m json.tool
```

---

## Assigning Roles

```bash
# Assign a role to a user on a resource group
az role assignment create \
    --assignee alice@contoso.onmicrosoft.com \
    --role "Contributor" \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus

# Assign a role to a group (preferred — easier to manage)
GROUP_ID=$(az ad group show --group "platform-team" --query id -o tsv)
az role assignment create \
    --assignee-object-id $GROUP_ID \
    --assignee-principal-type Group \
    --role "Reader" \
    --scope /subscriptions/$SUBSCRIPTION_ID

# Assign a role to a service principal
SP_OBJ_ID=$(az ad sp show --id $APP_ID --query id -o tsv)
az role assignment create \
    --assignee-object-id $SP_OBJ_ID \
    --assignee-principal-type ServicePrincipal \
    --role "Contributor" \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus

# Assign a role to a managed identity
MI_OBJ_ID=$(az identity show \
    --resource-group rg-my-app-prod-eastus \
    --name id-my-app-production \
    --query principalId -o tsv)
az role assignment create \
    --assignee-object-id $MI_OBJ_ID \
    --assignee-principal-type ServicePrincipal \
    --role "Storage Blob Data Reader" \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus/providers/Microsoft.Storage/storageAccounts/stmyappprod
```

---

## Listing and Removing Assignments

```bash
# List assignments on a scope
az role assignment list \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus \
    --output table

# List all assignments for a specific user
az role assignment list \
    --assignee alice@contoso.onmicrosoft.com \
    --all \
    --output table

# Remove a role assignment
az role assignment delete \
    --assignee alice@contoso.onmicrosoft.com \
    --role "Contributor" \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus
```

---

## Custom Roles

Create custom roles when built-in roles are too permissive.

```bash
# Create a custom role that can only restart VMs
az role definition create --role-definition '{
    "Name": "VM Restart Operator",
    "Description": "Can restart virtual machines but not create or delete them",
    "Actions": [
        "Microsoft.Compute/virtualMachines/read",
        "Microsoft.Compute/virtualMachines/restart/action",
        "Microsoft.Compute/virtualMachines/start/action",
        "Microsoft.Compute/virtualMachines/deallocate/action",
        "Microsoft.Resources/subscriptions/resourceGroups/read"
    ],
    "NotActions": [],
    "DataActions": [],
    "NotDataActions": [],
    "AssignableScopes": [
        "/subscriptions/'"$SUBSCRIPTION_ID"'"
    ]
}'

# List custom roles
az role definition list \
    --query '[?roleType==`CustomRole`].{Name:roleName,Description:description}' \
    --output table

# Update a custom role
az role definition update --role-definition @updated-role.json

# Delete a custom role
az role definition delete --name "VM Restart Operator"
```

---

## Privileged Identity Management (PIM)

PIM provides just-in-time (JIT) access — roles are activated on-demand for a limited time, requiring justification and optional approval. Requires Entra ID P2 license.

```bash
# List eligible role assignments (roles you can activate)
az rest --method GET \
    --url "https://graph.microsoft.com/v1.0/roleManagement/directory/roleEligibilityScheduleInstances?\$filter=principalId eq '$(az ad signed-in-user show --query id -o tsv)'" \
    --query "value[*].{Role:roleDefinitionId,Status:status}"

# Activate an eligible role for 4 hours
az rest --method POST \
    --url "https://graph.microsoft.com/v1.0/roleManagement/directory/roleAssignmentScheduleRequests" \
    --body '{
        "action": "selfActivate",
        "principalId": "'"$(az ad signed-in-user show --query id -o tsv)"'",
        "roleDefinitionId": "b24988ac-6180-42a0-ab88-20f7382dd24c",
        "directoryScopeId": "/",
        "scheduleInfo": {
            "startDateTime": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'",
            "expiration": {"type": "afterDuration", "duration": "PT4H"}
        },
        "justification": "Responding to production incident INC-12345"
    }'
```

---

## RBAC Best Practices

| Practice | Why |
|----------|-----|
| Assign roles to groups, not individual users | Easier to manage, audit, and onboard/offboard |
| Use least-privilege — prefer Reader over Contributor | Limit blast radius |
| Never assign Owner at subscription scope for day-to-day work | Use PIM for on-demand elevation |
| Use resource group scope, not subscription scope when possible | Narrower blast radius |
| Create custom roles for app-specific needs | Avoid over-permissive built-in roles |
| Use PIM for all privileged roles in production | JIT access with justification + audit trail |
| Review role assignments quarterly | Remove orphaned assignments (users who left the team) |

---

## References

- [Azure RBAC documentation](https://docs.microsoft.com/azure/role-based-access-control/)
- [Azure built-in roles](https://docs.microsoft.com/azure/role-based-access-control/built-in-roles)
- [Azure PIM](https://docs.microsoft.com/azure/active-directory/privileged-identity-management/)
- [Custom roles](https://docs.microsoft.com/azure/role-based-access-control/custom-roles)

---

← [Previous: Entra ID Basics](./entra-id-basics.md) | [Home](../../README.md) | [Next: Service Principals →](./service-principals.md)
