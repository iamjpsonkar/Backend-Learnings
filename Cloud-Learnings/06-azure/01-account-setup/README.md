← [Previous: Azure](../README.md) | [Home](../../README.md) | [Next: Account Setup →](./account-setup.md)

---

# Azure Account Setup

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Tenant** | An Entra ID (Azure AD) directory — one per organization |
| **Subscription** | A billing and resource container — linked to one tenant |
| **Management Group** | Container for subscriptions — hierarchy for policy and RBAC |
| **Resource Group** | Logical container for resources within a subscription — unit of lifecycle |
| **Resource** | A deployable service instance (VM, storage account, etc.) |
| **Azure Portal** | Web console at portal.azure.com |
| **Azure CLI** | `az` command-line tool |
| **Azure PowerShell** | `Az` PowerShell module |
| **Cloud Shell** | Browser-based shell (Bash or PowerShell) in the portal |

---

## Azure CLI Setup

```bash
# Install on macOS
brew update && brew install azure-cli

# Install on Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Verify
az version

# Log in (opens browser)
az login

# Log in with service principal (for CI/CD)
az login --service-principal \
    --tenant $TENANT_ID \
    --username $APP_ID \
    --password $CLIENT_SECRET

# List tenants you have access to
az account tenant list --output table

# List subscriptions
az account list --output table

# Set active subscription
az account set --subscription "my-production-subscription"

# Verify current context
az account show --query '{Subscription:name,ID:id,Tenant:tenantId,User:user.name}'
```

---

## Subscription and Resource Group Management

```bash
# Create a resource group
az group create \
    --name rg-my-app-production \
    --location eastus \
    --tags Environment=production Service=my-app ManagedBy=Terraform

# List resource groups
az group list --output table

# List resources in a group
az resource list \
    --resource-group rg-my-app-production \
    --output table

# Get resource group location list
az account list-locations \
    --query '[*].{Name:name,DisplayName:displayName,RegionType:metadata.regionType}' \
    --output table | grep -i Recommended

# Move resources to another resource group
az resource move \
    --destination-group rg-my-app-v2 \
    --ids $(az resource list --resource-group rg-my-app-old --query '[*].id' --output tsv)

# Delete a resource group and all resources inside (irreversible)
az group delete --name rg-my-app-old --yes --no-wait
```

---

## Management Groups

```bash
# Create management group hierarchy
az account management-group create \
    --name "production" \
    --display-name "Production" \
    --parent-id "root-management-group-id"

az account management-group create \
    --name "development" \
    --display-name "Development"

# Move subscription into a management group
az account management-group subscription add \
    --name "production" \
    --subscription $SUBSCRIPTION_ID

# List management group hierarchy
az account management-group list --output table
```

---

## Cost Management and Budgets

```bash
# View cost for the current month (requires Cost Management Reader role)
az consumption usage list \
    --billing-period-name $(date +%Y%m) \
    --query '[*].{Service:instanceName,Cost:pretaxCost,Currency:currency}' \
    --output table

# Create a budget (alert at 80% and 100% of $500/month)
az consumption budget create \
    --budget-name production-monthly \
    --amount 500 \
    --time-grain Monthly \
    --start-date $(date +%Y-%m-01) \
    --end-date 2026-12-31 \
    --notifications '{
        "Actual_GreaterThan_80_Percent": {
            "enabled": true,
            "operator": "GreaterThan",
            "threshold": 80,
            "contactEmails": ["ops@example.com"],
            "contactRoles": ["Owner"]
        },
        "Actual_GreaterThan_100_Percent": {
            "enabled": true,
            "operator": "GreaterThan",
            "threshold": 100,
            "contactEmails": ["ops@example.com", "finance@example.com"],
            "contactRoles": ["Owner", "Contributor"]
        }
    }'
```

---

## Naming Conventions

Azure does not enforce naming conventions, but the Cloud Adoption Framework recommends:

```
{resource-type}-{workload}-{environment}-{region}-{instance}

Examples:
  rg-my-app-prod-eastus          # Resource Group
  vnet-my-app-prod-eastus-001    # Virtual Network
  vm-my-app-prod-eastus-001      # Virtual Machine
  st{myappprodeastus}            # Storage Account (no hyphens, max 24 chars)
  kv-my-app-prod-eastus          # Key Vault
  aks-my-app-prod-eastus-001     # AKS cluster
```

Resource type abbreviations: [Azure abbreviations reference](https://docs.microsoft.com/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations)

---

## Tagging Strategy

```bash
# Apply tags to a resource group (propagates to all future resources when using policies)
az tag update \
    --resource-id $(az group show --name rg-my-app-production --query id --output tsv) \
    --operation Merge \
    --tags Environment=production CostCenter=CC-1234 Team=platform ManagedBy=Terraform

# List resources missing mandatory tags using Azure Resource Graph
az graph query -q "
    Resources
    | where isnull(tags.Environment) or isnull(tags.CostCenter)
    | project name, type, resourceGroup, location
    | order by type asc
" --output table
```

---

## Security Baseline for New Subscriptions

```bash
# Enable Microsoft Defender for Cloud (free tier — includes security recommendations)
az security auto-provisioning-setting update \
    --name mma \
    --auto-provision On

# Enable Defender plans for key services
az security pricing create --name VirtualMachines --tier Standard
az security pricing create --name StorageAccounts --tier Standard
az security pricing create --name SqlServers --tier Standard

# Enable Azure Activity Log → Log Analytics
az monitor diagnostic-settings create \
    --name activity-log-to-workspace \
    --resource /subscriptions/$SUBSCRIPTION_ID \
    --workspace $LOG_ANALYTICS_WORKSPACE_ID \
    --logs '[{"category": "Administrative", "enabled": true},
             {"category": "Security", "enabled": true},
             {"category": "Alert", "enabled": true},
             {"category": "Policy", "enabled": true}]'
```

---

## References

- [Azure subscriptions documentation](https://docs.microsoft.com/azure/cloud-adoption-framework/ready/landing-zone/)
- [Azure CLI documentation](https://docs.microsoft.com/cli/azure/)
- [Azure naming conventions](https://docs.microsoft.com/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming)
- [Azure Cost Management](https://docs.microsoft.com/azure/cost-management-billing/)
---

← [Previous: Azure](../README.md) | [Home](../../README.md) | [Next: Account Setup →](./account-setup.md)
