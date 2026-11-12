← [Previous: Network Security Groups](./network-security-groups.md) | [Home](../../README.md) | [Next: Private Endpoints →](./private-endpoints.md)

---

# Azure Application Gateway

Application Gateway is a regional L7 (HTTP/HTTPS) load balancer with built-in Web Application Firewall (WAF), SSL termination, URL-based routing, and session affinity.

---

## Application Gateway vs Azure Load Balancer

| Feature | Application Gateway | Azure Load Balancer |
|---------|---------------------|---------------------|
| Layer | 7 (HTTP/HTTPS) | 4 (TCP/UDP) |
| SSL termination | Yes | No |
| WAF | Yes (WAF_v2 SKU) | No |
| URL-based routing | Yes | No |
| Host-based routing | Yes | No |
| Session affinity | Cookie-based | IP hash |
| WebSocket / HTTP/2 | Yes | No |
| Scope | Regional | Regional |
| Backend types | VMs, VMSS, AKS, App Service, IPs | VMs, VMSS |

---

## SKUs

| SKU | Notes |
|-----|-------|
| Standard_v2 | L7 LB, autoscaling, zone redundancy |
| WAF_v2 | Standard_v2 + Web Application Firewall (recommended for internet-facing) |

---

## Creating an Application Gateway

```bash
# Create public IP for the Application Gateway
az network public-ip create \
    --resource-group rg-my-app-prod-eastus \
    --name pip-agw-my-app-prod-eastus \
    --sku Standard \
    --allocation-method Static \
    --zone 1 2 3

# Create the Application Gateway (WAF_v2)
az network application-gateway create \
    --resource-group rg-my-app-prod-eastus \
    --name agw-my-app-prod-eastus-001 \
    --location eastus \
    --sku WAF_v2 \
    --capacity 2 \                      # Min instances (0 for autoscale)
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-agw-prod \            # Dedicated subnet (/24 min recommended)
    --public-ip-address pip-agw-my-app-prod-eastus \
    --frontend-port 443 \
    --http-settings-port 80 \
    --http-settings-protocol Http \
    --routing-rule-type Basic \
    --priority 100 \
    --servers 10.0.2.4 10.0.2.5 \      # Backend VM IPs
    --cert-file cert.pfx \              # SSL certificate
    --cert-password "$CERT_PASSWORD" \
    --waf-policy /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus/providers/Microsoft.Network/ApplicationGatewayWebApplicationFirewallPolicies/waf-policy-prod
```

---

## URL-Based and Host-Based Routing

```bash
# Add a path-based rule to route /api/* to an API backend pool
az network application-gateway url-path-map create \
    --resource-group rg-my-app-prod-eastus \
    --gateway-name agw-my-app-prod-eastus-001 \
    --name url-path-map \
    --paths "/api/*" \
    --address-pool api-backend-pool \
    --http-settings api-http-settings \
    --rule-name api-rule \
    --default-address-pool frontend-backend-pool \
    --default-http-settings frontend-http-settings

# Add a listener for a different hostname
az network application-gateway http-listener create \
    --resource-group rg-my-app-prod-eastus \
    --gateway-name agw-my-app-prod-eastus-001 \
    --name listener-admin \
    --frontend-port 443 \
    --frontend-ip appGatewayFrontendIP \
    --host-name admin.example.com \
    --ssl-cert my-ssl-cert

# Add backend pool for admin
az network application-gateway address-pool create \
    --resource-group rg-my-app-prod-eastus \
    --gateway-name agw-my-app-prod-eastus-001 \
    --name admin-backend-pool \
    --servers 10.0.2.10

# Add routing rule for admin
az network application-gateway rule create \
    --resource-group rg-my-app-prod-eastus \
    --gateway-name agw-my-app-prod-eastus-001 \
    --name rule-admin \
    --http-listener listener-admin \
    --address-pool admin-backend-pool \
    --http-settings admin-http-settings \
    --rule-type Basic \
    --priority 200
```

---

## WAF Policy

```bash
# Create a WAF policy
az network application-gateway waf-policy create \
    --resource-group rg-my-app-prod-eastus \
    --name waf-policy-prod \
    --location eastus

# Set WAF mode to Prevention (blocks malicious requests)
az network application-gateway waf-policy policy-setting update \
    --resource-group rg-my-app-prod-eastus \
    --policy-name waf-policy-prod \
    --mode Prevention \
    --state Enabled \
    --request-body-check true \
    --max-request-body-size 128 \
    --file-upload-limit 100

# Enable OWASP rule set
az network application-gateway waf-policy managed-rule rule-set add \
    --resource-group rg-my-app-prod-eastus \
    --policy-name waf-policy-prod \
    --type OWASP \
    --version 3.2

# Add a custom rule (rate limit by IP)
az network application-gateway waf-policy custom-rule create \
    --resource-group rg-my-app-prod-eastus \
    --policy-name waf-policy-prod \
    --name block-specific-ip \
    --priority 10 \
    --action Block \
    --rule-type MatchRule \
    --match-condition '[{"matchVariables":[{"variableName":"RemoteAddr"}],"operator":"IPMatch","values":["198.51.100.0/24"]}]'
```

---

## Health Probes

```bash
# Create a custom health probe
az network application-gateway probe create \
    --resource-group rg-my-app-prod-eastus \
    --gateway-name agw-my-app-prod-eastus-001 \
    --name health-probe-api \
    --protocol Http \
    --host-name-from-http-settings true \
    --path "/healthz" \
    --interval 30 \
    --timeout 30 \
    --threshold 3

# Update HTTP settings to use the probe
az network application-gateway http-settings update \
    --resource-group rg-my-app-prod-eastus \
    --gateway-name agw-my-app-prod-eastus-001 \
    --name api-http-settings \
    --probe health-probe-api \
    --timeout 30 \
    --cookie-based-affinity Disabled \
    --connection-draining-timeout 30
```

---

## Autoscaling

```bash
# Configure autoscaling (min 0 for cost savings when idle)
az network application-gateway update \
    --resource-group rg-my-app-prod-eastus \
    --name agw-my-app-prod-eastus-001 \
    --min-capacity 1 \
    --max-capacity 10

# Check current instance count
az network application-gateway show \
    --resource-group rg-my-app-prod-eastus \
    --name agw-my-app-prod-eastus-001 \
    --query 'sku.capacity'
```

---

## Useful Commands

```bash
# List application gateways
az network application-gateway list \
    --resource-group rg-my-app-prod-eastus \
    --output table

# Show backend health (check which backends are healthy)
az network application-gateway show-backend-health \
    --resource-group rg-my-app-prod-eastus \
    --name agw-my-app-prod-eastus-001\
    --query 'backendAddressPools[*].backendHttpSettingsCollection[*].servers[*].{Address:address,Status:health}'

# Enable diagnostic logging to Log Analytics
az monitor diagnostic-settings create \
    --name agw-diag \
    --resource $(az network application-gateway show \
        --resource-group rg-my-app-prod-eastus \
        --name agw-my-app-prod-eastus-001 --query id -o tsv) \
    --workspace $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus --query id -o tsv) \
    --logs '[{"category":"ApplicationGatewayAccessLog","enabled":true},{"category":"ApplicationGatewayFirewallLog","enabled":true}]' \
    --metrics '[{"category":"AllMetrics","enabled":true}]'
```

---

## References

- [Application Gateway documentation](https://docs.microsoft.com/azure/application-gateway/)
- [WAF on Application Gateway](https://docs.microsoft.com/azure/web-application-firewall/ag/ag-overview)
- [URL-based routing](https://docs.microsoft.com/azure/application-gateway/url-route-overview)

---

← [Previous: Network Security Groups](./network-security-groups.md) | [Home](../../README.md) | [Next: Private Endpoints →](./private-endpoints.md)
