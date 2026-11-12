← [Previous: Account Setup](./account-setup.md) | [Home](../../README.md) | [Next: CLI Setup →](./cli-setup.md)

---

# Azure Billing & Budgets

---

## Billing Structure

```
Enrollment Account / MCA Billing Account
└── Billing Profile (invoice recipient)
    └── Invoice Section (department / team)
        └── Subscription
            └── Resource Group (tags for cost allocation)
                └── Resources
```

In practice, most teams work at the **Subscription** level for cost visibility.

---

## Cost Management + Billing

Azure Cost Management is the built-in tool for tracking and optimizing cloud spend.

```bash
# View current month cost breakdown by service
az consumption usage list \
    --start-date $(date +%Y-%m-01) \
    --end-date $(date +%Y-%m-%d) \
    --query '[*].{Service:product,Cost:pretaxCost,Currency:currency}' \
    --output table

# View cost by resource group
az consumption usage list \
    --query '[?resourceGroup!=null] | [*].{RG:resourceGroup,Cost:pretaxCost}' \
    --output table | sort -k2 -rn | head -20

# Get top 10 most expensive resources last 30 days
az consumption usage list \
    --query 'sort_by([*],&pretaxCost)[-10:].{Resource:instanceName,Cost:pretaxCost,Service:product}' \
    --output table
```

---

## Budgets

Budgets trigger alerts (email, action group) when actual or forecasted spend reaches thresholds.

```bash
# Create a monthly budget with 80% and 100% alerts
az consumption budget create \
    --budget-name "prod-monthly-budget" \
    --amount 1000 \
    --time-grain Monthly \
    --start-date $(date +%Y-%m-01) \
    --end-date 2026-12-31 \
    --resource-group-filter "rg-my-app-prod-eastus" \
    --notifications '{
        "Actual_GreaterThan_80_Percent": {
            "enabled": true,
            "operator": "GreaterThan",
            "threshold": 80,
            "thresholdType": "Actual",
            "contactEmails": ["ops@example.com"],
            "contactRoles": ["Owner"]
        },
        "Forecast_GreaterThan_100_Percent": {
            "enabled": true,
            "operator": "GreaterThan",
            "threshold": 100,
            "thresholdType": "Forecasted",
            "contactEmails": ["ops@example.com", "finance@example.com"]
        }
    }'

# List budgets
az consumption budget list --output table

# Delete a budget
az consumption budget delete --budget-name "prod-monthly-budget"
```

---

## Tagging for Cost Allocation

Tags are the primary mechanism for breaking down costs by team, project, or environment.

```bash
# Tag a resource group
az tag update \
    --resource-id $(az group show --name rg-my-app-prod-eastus --query id -o tsv) \
    --operation Merge \
    --tags Environment=production CostCenter=CC-1234 Team=platform Project=my-app

# Enforce mandatory tags via Azure Policy
az policy assignment create \
    --name "require-cost-tags" \
    --display-name "Require CostCenter and Team tags" \
    --policy "96670d01-0a4d-4649-9c89-2d3abc0a5025" \
    --scope /subscriptions/$SUBSCRIPTION_ID

# Find untagged resource groups
az graph query -q "
    ResourceContainers
    | where type == 'microsoft.resources/subscriptions/resourcegroups'
    | where isnull(tags.CostCenter) or isnull(tags.Team)
    | project name, location, tags
" --output table
```

### Recommended Tags

| Tag | Values | Purpose |
|-----|--------|---------|
| `Environment` | production, staging, dev, sandbox | Filter by env |
| `CostCenter` | CC-1234, CC-5678 | Finance chargeback |
| `Team` | platform, backend, data | Team accountability |
| `Project` | my-app, data-pipeline | Project grouping |
| `ManagedBy` | Terraform, Bicep, Manual | IaC tracking |
| `Owner` | alice@example.com | Contact for alerts |

---

## Cost Optimization Levers

| Option | Savings | Notes |
|--------|---------|-------|
| Reserved Instances (1-yr) | ~35–40% | Commit to 1 or 3 years |
| Reserved Instances (3-yr) | ~55–60% | Best for stable workloads |
| Azure Savings Plans | ~15–65% | Flexible hourly spend commitment |
| Spot VMs | up to 90% | Interruptible — use for batch/dev |
| Azure Hybrid Benefit | ~40% on VMs | Bring your own Windows Server / SQL licenses |
| Dev/Test pricing | ~50–70% | For non-production subscriptions |
| Auto-shutdown (dev VMs) | Variable | Schedule VMs to stop at night |
| Right-sizing | Variable | Match VM size to actual usage |
| Delete idle resources | Variable | Unattached disks, orphaned IPs, empty LBs |

```bash
# Enable Azure Hybrid Benefit on a VM
az vm update \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --license-type Windows_Server

# Schedule VM auto-shutdown (DevTest Labs or via Azure Policy)
az vm auto-shutdown \
    --resource-group rg-my-app-dev-eastus \
    --name vm-my-app-dev-001 \
    --time 1900 \
    --timezone "UTC"
```

---

## Cost Alerts via Azure Monitor

```bash
# Create action group for billing alerts
az monitor action-group create \
    --resource-group rg-platform-monitoring \
    --name ag-billing-alerts \
    --short-name "billing" \
    --email-receiver name=ops email=ops@example.com

# View all active budget alerts
az consumption budget list \
    --query '[*].{Name:name,Amount:amount,CurrentSpend:currentSpend.amount,Unit:currentSpend.unit}' \
    --output table
```

---

## Useful Cost Management Queries (Azure Resource Graph)

```bash
# Total cost by resource type this month
az graph query -q "
    Resources
    | join kind=leftouter (
        resourcecontainers
        | where type == 'microsoft.resources/subscriptions'
        | project subscriptionId, subscriptionName=name
    ) on subscriptionId
    | project name, type, resourceGroup, location, subscriptionName
    | summarize count() by type
    | order by count_ desc
" --output table

# Find unused disks (not attached to a VM)
az graph query -q "
    Resources
    | where type == 'microsoft.compute/disks'
    | where properties.diskState == 'Unattached'
    | project name, resourceGroup, properties.diskSizeGB, location
" --output table
```

---

## References

- [Azure Cost Management documentation](https://docs.microsoft.com/azure/cost-management-billing/)
- [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)
- [Azure Reserved Instances](https://docs.microsoft.com/azure/virtual-machines/prepay-reserved-vm-instances)
- [Azure Advisor Cost Recommendations](https://docs.microsoft.com/azure/advisor/advisor-cost-recommendations)

---

← [Previous: Account Setup](./account-setup.md) | [Home](../../README.md) | [Next: CLI Setup →](./cli-setup.md)
