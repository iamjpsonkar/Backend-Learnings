← [Previous: Subscriptions](./subscriptions.md) | [Home](../../README.md) | [Next: Azure Entra ID →](../02-entra-id/README.md)

---

# Azure Resource Groups

---

## What is a Resource Group?

A resource group is a logical container that holds related Azure resources. It is the fundamental unit of lifecycle management in Azure.

Key properties:
- **Location**: where the resource group metadata is stored (resources inside can be in different regions)
- **Lifecycle**: deleting a resource group deletes all resources inside it
- **Billing**: resources inside share the same subscription's billing
- **RBAC**: you can assign roles at the resource group level
- **Tags**: tags on the resource group do not automatically propagate to resources (use Azure Policy for that)

---

## Creating and Managing Resource Groups

```bash
# Create a resource group
az group create \
    --name rg-my-app-prod-eastus \
    --location eastus \
    --tags Environment=production Team=platform CostCenter=CC-1234 ManagedBy=Terraform

# List resource groups
az group list --output table
az group list --query '[*].{Name:name,Location:location,State:properties.provisioningState}' \
    --output table

# Show details of a resource group
az group show --name rg-my-app-prod-eastus

# Check if a resource group exists
az group exists --name rg-my-app-prod-eastus

# List all resources in a resource group
az resource list \
    --resource-group rg-my-app-prod-eastus \
    --output table

az resource list \
    --resource-group rg-my-app-prod-eastus \
    --query '[*].{Name:name,Type:type,Location:location}' \
    --output table

# Delete a resource group (deletes ALL resources inside — irreversible)
az group delete --name rg-my-app-old --yes --no-wait
```

---

## Naming Conventions

Consistent naming makes governance and cost analysis practical. Follow the Azure Cloud Adoption Framework (CAF) pattern:

```
{resource-type}-{workload}-{environment}-{region}-{instance}

Examples:
  rg-my-app-prod-eastus           Resource Group
  rg-my-app-dev-eastus            Resource Group (dev)
  rg-platform-shared-eastus       Resource Group (shared services)
  rg-network-hub-eastus           Resource Group (hub VNet)
```

### Azure Resource Type Abbreviations (CAF)

| Resource | Abbreviation | Example |
|----------|-------------|---------|
| Resource Group | rg | rg-my-app-prod-eastus |
| Virtual Network | vnet | vnet-my-app-prod-eastus |
| Subnet | snet | snet-app-prod-eastus |
| Network Security Group | nsg | nsg-app-prod-eastus |
| Virtual Machine | vm | vm-my-app-prod-001 |
| Storage Account | st | stmyappprodeastus (no hyphens, max 24 chars) |
| Key Vault | kv | kv-my-app-prod-eastus |
| AKS Cluster | aks | aks-my-app-prod-eastus-001 |
| App Service | app | app-my-app-prod-eastus |
| SQL Server | sql | sql-my-app-prod-eastus |
| Log Analytics Workspace | log | log-platform-prod-eastus |

---

## Tags

Tags are key-value pairs attached to resources for cost allocation, governance, and automation.

```bash
# Tag an existing resource group
az tag update \
    --resource-id $(az group show --name rg-my-app-prod-eastus --query id -o tsv) \
    --operation Merge \
    --tags Environment=production Team=platform CostCenter=CC-1234

# Tag a specific resource
az resource update \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --resource-type Microsoft.Compute/virtualMachines \
    --set tags.Owner=alice@example.com

# List all tags on a resource group
az group show --name rg-my-app-prod-eastus --query tags

# Find resources with missing tags (via Azure Resource Graph)
az graph query -q "
    Resources
    | where resourceGroup == 'rg-my-app-prod-eastus'
    | where isnull(tags.Environment) or isnull(tags.Team)
    | project name, type, tags
" --output table

# Enforce tags with Azure Policy (inherit tag from resource group)
az policy assignment create \
    --name "inherit-rg-environment-tag" \
    --display-name "Inherit Environment tag from resource group" \
    --policy "9be0cae6-0423-4b41-99b4-64d86a44e431" \
    --scope /subscriptions/$SUBSCRIPTION_ID
```

---

## Resource Locks

Locks prevent accidental deletion or modification.

| Lock type | Effect |
|-----------|--------|
| ReadOnly | No creates, updates, or deletes on any resource in the group |
| CanNotDelete | No deletions, but reads and updates are allowed |

```bash
# Apply a delete lock to a production resource group
az lock create \
    --name "no-delete-prod" \
    --resource-group rg-my-app-prod-eastus \
    --lock-type CanNotDelete \
    --notes "Production resources — contact platform team before deleting"

# Apply a read-only lock (stricter — prevents any changes)
az lock create \
    --name "readonly-lock" \
    --resource-group rg-my-app-prod-eastus \
    --lock-type ReadOnly

# List locks on a resource group
az lock list --resource-group rg-my-app-prod-eastus --output table

# Delete a lock before deleting the resource group
az lock delete \
    --name "no-delete-prod" \
    --resource-group rg-my-app-prod-eastus
```

---

## Resource Group Design Patterns

### By environment (simplest)

```
rg-my-app-dev-eastus
rg-my-app-staging-eastus
rg-my-app-prod-eastus
```

### By lifecycle (deploy and delete together)

```
rg-network-hub-eastus          # VNet, firewall, VPN — long-lived
rg-platform-monitoring-eastus  # Log Analytics, monitoring — long-lived
rg-my-app-prod-eastus          # App resources — update with app releases
rg-my-app-data-prod-eastus     # Databases — separate lifecycle from app
```

### By team ownership

```
rg-platform-infra-prod-eastus
rg-backend-api-prod-eastus
rg-data-pipelines-prod-eastus
rg-frontend-prod-eastus
```

**Rule of thumb**: put resources that are deployed, updated, and deleted together in the same resource group.

---

## Move Resources Between Groups

```bash
# Validate that resources can be moved (dry-run)
az resource invoke-action \
    --action validateMoveResources \
    --ids /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-source \
    --request-body '{
        "resources": ["/subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-source/providers/Microsoft.Compute/virtualMachines/my-vm"],
        "targetResourceGroup": "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-destination"
    }'

# Move resources to another resource group
az resource move \
    --destination-group rg-my-app-prod-v2-eastus \
    --ids \
        /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus/providers/Microsoft.Compute/virtualMachines/vm-001 \
        /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus/providers/Microsoft.Network/networkInterfaces/nic-001
```

> Not all resource types support moves. Check [Azure resource move support](https://docs.microsoft.com/azure/azure-resource-manager/management/move-support-resources) before attempting.

---

## References

- [Azure resource groups](https://docs.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal)
- [Azure naming conventions (CAF)](https://docs.microsoft.com/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming)
- [Azure resource locks](https://docs.microsoft.com/azure/azure-resource-manager/management/lock-resources)
- [Move resources between groups](https://docs.microsoft.com/azure/azure-resource-manager/management/move-resource-group-and-subscription)

---

← [Previous: Subscriptions](./subscriptions.md) | [Home](../../README.md) | [Next: Azure Entra ID →](../02-entra-id/README.md)
