← [Previous: Azure Account Setup](./README.md) | [Home](../../README.md) | [Next: Billing & Budgets →](./billing-budgets.md)

---

# Azure Account Setup

---

## Azure Account Types

| Account type | Who it's for | Notes |
|-------------|-------------|-------|
| Free account | Individuals learning Azure | $200 credit for 30 days, 12 months of free services |
| Pay-As-You-Go | Small teams, startups | Monthly billing, no commitment |
| Enterprise Agreement (EA) | Large enterprises | Volume discounts, annual commitment |
| Microsoft Customer Agreement (MCA) | Mid-market | Simplified billing, replaces older agreements |
| Azure for Students | Verified students | $100 credit, no credit card required |
| Azure Dev/Test | MSDN subscribers | Reduced rates for non-production workloads |
| CSP (Cloud Solution Provider) | Managed via partner | Billing and support through Microsoft partner |

---

## Azure Hierarchy

```
Azure AD Tenant (Entra ID)
└── Root Management Group
    └── Management Group (e.g., "Production")
        └── Management Group (e.g., "Workloads")
            └── Subscription (e.g., "prod-app-001")
                └── Resource Group (e.g., "rg-my-app-prod-eastus")
                    └── Resources (VMs, Storage, AKS, etc.)
```

| Level | Purpose |
|-------|---------|
| Tenant | Identity root — one Entra ID directory per organization |
| Management Group | Policy and RBAC governance across subscriptions |
| Subscription | Billing boundary, quota boundary, deployment scope |
| Resource Group | Lifecycle unit — deploy, manage, and delete together |
| Resource | Individual service instance |

---

## First Steps After Account Creation

```bash
# 1. Install Azure CLI
brew update && brew install azure-cli   # macOS
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash  # Ubuntu/Debian

# 2. Log in
az login

# 3. Check current subscription
az account show --query '{Name:name,ID:id,Tenant:tenantId}'

# 4. Set default subscription
az account set --subscription "my-subscription-name"

# 5. Verify
az account show --output table
```

---

## Subscription Design

### Single Subscription (small teams)

One subscription for all environments, separated by resource groups:
```
subscription: "my-company"
  rg-my-app-dev
  rg-my-app-staging
  rg-my-app-prod
```

### Multi-Subscription (recommended for enterprise)

Separate subscriptions per environment or business unit:
```
Root Management Group
├── Management Group: Platform
│   └── Subscription: platform-shared-services
├── Management Group: Production
│   ├── Subscription: app-team-prod
│   └── Subscription: data-team-prod
└── Management Group: Non-Production
    ├── Subscription: app-team-dev
    └── Subscription: app-team-staging
```

Benefits: blast-radius isolation, separate billing, independent quota limits, independent policy scope.

---

## Management Groups

```bash
# Create management group hierarchy
az account management-group create \
    --name "production" \
    --display-name "Production Workloads"

az account management-group create \
    --name "nonproduction" \
    --display-name "Non-Production Workloads"

# Move subscription into management group
az account management-group subscription add \
    --name "production" \
    --subscription $SUBSCRIPTION_ID

# List hierarchy
az account management-group list --output table

# View full hierarchy tree
az account management-group show \
    --name "production" \
    --expand \
    --recurse \
    --output json
```

---

## Initial Security Hardening

Run these immediately after creating a new subscription:

```bash
# Enable Microsoft Defender for Cloud (free tier)
az security auto-provisioning-setting update --name mma --auto-provision On

# Enable Defender plans for critical services
az security pricing create --name VirtualMachines --tier Standard
az security pricing create --name StorageAccounts --tier Standard
az security pricing create --name SqlServers --tier Standard
az security pricing create --name AppServices --tier Standard
az security pricing create --name KeyVaults --tier Standard

# Require MFA (configure in Entra ID portal — or via Conditional Access policy)
# See: 02-entra-id/entra-id-basics.md

# Set subscription spending limit / alert
# See: billing-budgets.md

# Restrict resource types with Azure Policy
az policy assignment create \
    --name "allowed-locations" \
    --display-name "Allowed Azure Regions" \
    --policy "e56962a6-4747-49cd-b67b-bf8b01975c4f" \
    --scope /subscriptions/$SUBSCRIPTION_ID \
    --params '{"listOfAllowedLocations": {"value": ["eastus", "eastus2", "westus2"]}}'
```

---

## Cloud Account Safety Checklist

| Task | Command / Action |
|------|-----------------|
| Enable MFA for all users | Entra ID → Conditional Access |
| Remove root/global admin credentials from daily use | Create dedicated admin accounts |
| Set budget alert | See billing-budgets.md |
| Enable Defender for Cloud | `az security pricing create` |
| Enable Activity Log → Log Analytics | `az monitor diagnostic-settings create` |
| Apply Azure Policy for location restrictions | `az policy assignment create` |
| Set resource locks on critical resources | `az lock create --lock-type ReadOnly` |
| Enable soft-delete on Key Vaults | `az keyvault update --enable-soft-delete true` |
| Avoid using client secrets in code — use Managed Identities | See managed-identities.md |

---

## References

- [Azure Free Account](https://azure.microsoft.com/free/)
- [Azure Management Groups](https://docs.microsoft.com/azure/governance/management-groups/)
- [Azure Subscription Design](https://docs.microsoft.com/azure/cloud-adoption-framework/ready/landing-zone/)
- [Azure Security Benchmark](https://docs.microsoft.com/security/benchmark/azure/)

---

← [Previous: Azure Account Setup](./README.md) | [Home](../../README.md) | [Next: Billing & Budgets →](./billing-budgets.md)
