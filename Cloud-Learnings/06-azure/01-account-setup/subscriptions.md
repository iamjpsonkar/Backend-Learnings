← [Previous: CLI Setup](./cli-setup.md) | [Home](../../README.md) | [Next: Resource Groups →](./resource-groups.md)

---

# Azure Subscriptions

---

## What is a Subscription?

A subscription is the primary billing and access boundary in Azure:

- **Billing**: all resources in a subscription appear on the same invoice
- **Access control**: RBAC roles are scoped to a subscription
- **Quotas**: CPU cores, IPs, and other limits apply per subscription
- **Policy**: Azure Policy can be applied at the subscription level

Every subscription belongs to exactly one Entra ID tenant.

---

## Subscription Types

| Type | Notes |
|------|-------|
| Pay-As-You-Go | Default. Billed monthly. No commitment. |
| Free Trial | $200 credit, 30 days. Converts to PAYG. |
| Enterprise Agreement (EA) | Annual commitment. Discounted rates. |
| Microsoft Customer Agreement (MCA) | New EA replacement. Monthly/annual. |
| Azure for Students | $100 credit. Verify with school email. |
| Dev/Test (PAYG) | Reduced rates for non-production. Requires Visual Studio subscription. |
| Azure Sponsorship | Credit granted by Microsoft (events, programs). |
| CSP | Managed by a Microsoft partner. |

---

## Subscription Management

```bash
# List all accessible subscriptions
az account list --output table

# Show details of a specific subscription
az account show --subscription "my-subscription" \
    --query '{Name:name,ID:id,State:state,Tenant:tenantId,User:user.name}'

# Set active subscription
az account set --subscription "my-subscription"
az account set --subscription $SUBSCRIPTION_ID

# Rename a subscription (requires Owner role)
az account subscription rename \
    --subscription-id $SUBSCRIPTION_ID \
    --subscription-name "prod-platform-001"

# Cancel a subscription
az account subscription cancel \
    --subscription-id $SUBSCRIPTION_ID

# View subscription quotas (example: compute)
az vm list-usage --location eastus --output table
```

---

## Management Groups

Management groups let you apply governance (RBAC, Policy) across multiple subscriptions.

```
Root Management Group (auto-created per tenant)
├── Management Group: Platform
│   └── Subscription: platform-shared-services
├── Management Group: Production
│   ├── Subscription: app-team-prod
│   └── Subscription: data-team-prod
└── Management Group: Non-Production
    ├── Subscription: app-team-dev
    └── Subscription: app-team-staging
```

```bash
# Create a management group
az account management-group create \
    --name "mg-production" \
    --display-name "Production Workloads"

# Nest management groups (set parent)
az account management-group create \
    --name "mg-app-prod" \
    --display-name "App Team Production" \
    --parent "mg-production"

# Move a subscription into a management group
az account management-group subscription add \
    --name "mg-production" \
    --subscription $SUBSCRIPTION_ID

# List management groups
az account management-group list --output table

# Show full hierarchy with subscriptions
az account management-group show \
    --name "mg-production" \
    --expand \
    --recurse
```

---

## Subscription Design Patterns

### Pattern 1: Environment-per-subscription

Best for: most organizations. Cleanest cost and policy separation.

```
mg-root
├── mg-platform
│   └── sub-platform-shared (DNS, monitoring, connectivity hub)
├── mg-production
│   ├── sub-app1-prod
│   └── sub-app2-prod
└── mg-nonprod
    ├── sub-app1-dev
    └── sub-app1-staging
```

### Pattern 2: Landing Zone (Azure CAF)

Microsoft's recommended enterprise pattern. Each application team gets their own subscription.

```
mg-root
├── mg-platform (shared services)
│   ├── sub-connectivity (hub VNet, ExpressRoute, Firewall)
│   ├── sub-identity (domain controllers)
│   └── sub-management (log analytics, security center)
└── mg-landing-zones
    ├── mg-corp (internet-restricted)
    │   └── sub-team-a-prod
    └── mg-online (internet-facing)
        └── sub-team-b-prod
```

---

## Azure Policy at Subscription Level

```bash
# List policy definitions
az policy definition list --query '[?policyType==`BuiltIn`].{Name:displayName,ID:name}' \
    --output table | grep -i "location\|tag\|allowed"

# Assign "Allowed locations" policy to a subscription
az policy assignment create \
    --name "allowed-locations" \
    --display-name "Restrict to approved regions" \
    --policy "e56962a6-4747-49cd-b67b-bf8b01975c4f" \
    --scope /subscriptions/$SUBSCRIPTION_ID \
    --params '{"listOfAllowedLocations":{"value":["eastus","eastus2","westus2"]}}'

# Assign "Inherit tags from subscription" policy
az policy assignment create \
    --name "inherit-sub-tags" \
    --display-name "Inherit tags from subscription" \
    --policy "b27a0cbd-a167-4dfa-ae64-4337be671140" \
    --scope /subscriptions/$SUBSCRIPTION_ID

# Check compliance
az policy state summarize --subscription $SUBSCRIPTION_ID

# List non-compliant resources
az policy state list \
    --filter "complianceState eq 'NonCompliant'" \
    --query '[*].{Resource:resourceId,Policy:policyDefinitionName}' \
    --output table
```

---

## Subscription Limits (Key Quotas)

| Resource | Default limit |
|----------|-------------|
| vCPUs per region | 20 (PAYG), higher for EA |
| Resource groups per subscription | 980 |
| Resources per resource group | 800 per resource type |
| Virtual networks | 1,000 |
| Public IP addresses | 60 (dynamic), 20 (static) |
| Azure AD app registrations | 250 |

```bash
# View current quota usage
az vm list-usage --location eastus \
    --query '[*].{Name:name.localizedValue,Current:currentValue,Limit:limit}' \
    --output table

# Request quota increase (submit via portal or support ticket)
az support tickets create \
    --title "Request vCPU quota increase - eastus" \
    --description "Need 100 vCPUs for production AKS cluster" \
    --problem-classification "quota-increase" \
    --severity minimal \
    --contact-first-name "John" \
    --contact-last-name "Smith" \
    --contact-email "ops@example.com" \
    --contact-method email
```

---

## References

- [Azure subscriptions documentation](https://docs.microsoft.com/azure/cloud-adoption-framework/ready/landing-zone/)
- [Management groups overview](https://docs.microsoft.com/azure/governance/management-groups/)
- [Azure subscription limits](https://docs.microsoft.com/azure/azure-resource-manager/management/azure-subscription-service-limits)
- [Azure Policy built-in definitions](https://docs.microsoft.com/azure/governance/policy/samples/built-in-policies)

---

← [Previous: CLI Setup](./cli-setup.md) | [Home](../../README.md) | [Next: Resource Groups →](./resource-groups.md)
