← [Previous: VNet](./vnet.md) | [Home](../../README.md) | [Next: Application Gateway →](./application-gateway.md)

---

# Network Security Groups (NSG)

An NSG is a stateful L4 firewall applied to a subnet or NIC (network interface). It filters inbound and outbound traffic using rules based on protocol, port, source, and destination.

---

## How NSGs Work

- NSGs can be associated with a **subnet** (applies to all resources in subnet) or a **NIC** (applies to one specific VM)
- Both subnet-level and NIC-level NSGs are evaluated — most restrictive wins
- Rules are evaluated in **priority order** (lowest number first, 100–4096)
- Each rule is either `Allow` or `Deny`
- Stateful: if inbound traffic is allowed, the response is automatically allowed

### Default Rules (always present, cannot be deleted)

| Priority | Name | Direction | Source | Destination | Port | Action |
|----------|------|-----------|--------|-------------|------|--------|
| 65000 | AllowVnetInBound | Inbound | VirtualNetwork | VirtualNetwork | Any | Allow |
| 65001 | AllowAzureLoadBalancerInBound | Inbound | AzureLoadBalancer | Any | Any | Allow |
| 65500 | DenyAllInBound | Inbound | Any | Any | Any | Deny |
| 65000 | AllowVnetOutBound | Outbound | VirtualNetwork | VirtualNetwork | Any | Allow |
| 65001 | AllowInternetOutBound | Outbound | Any | Internet | Any | Allow |
| 65500 | DenyAllOutBound | Outbound | Any | Any | Any | Deny |

---

## Creating and Managing NSGs

```bash
# Create an NSG
az network nsg create \
    --resource-group rg-my-app-prod-eastus \
    --name nsg-backend-prod-eastus \
    --tags Environment=production Team=platform

# Associate NSG with a subnet
az network vnet subnet update \
    --resource-group rg-my-app-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-backend-prod \
    --network-security-group nsg-backend-prod-eastus

# List NSGs
az network nsg list \
    --resource-group rg-my-app-prod-eastus \
    --output table

# Show all rules for an NSG
az network nsg show \
    --resource-group rg-my-app-prod-eastus \
    --name nsg-backend-prod-eastus \
    --query 'securityRules[*].{Priority:priority,Name:name,Direction:direction,Access:access,Protocol:protocol,SrcPort:sourcePortRange,DstPort:destinationPortRange,Src:sourceAddressPrefix,Dst:destinationAddressPrefix}' \
    --output table
```

---

## NSG Rules

```bash
# Allow inbound HTTPS from the internet
az network nsg rule create \
    --resource-group rg-my-app-prod-eastus \
    --nsg-name nsg-backend-prod-eastus \
    --name allow-https-inbound \
    --priority 100 \
    --direction Inbound \
    --protocol Tcp \
    --source-address-prefixes "*" \
    --source-port-ranges "*" \
    --destination-address-prefixes "*" \
    --destination-port-ranges 443 \
    --access Allow \
    --description "Allow HTTPS from internet"

# Allow inbound from specific IP range (office network)
az network nsg rule create \
    --resource-group rg-my-app-prod-eastus \
    --nsg-name nsg-backend-prod-eastus \
    --name allow-office-ssh \
    --priority 110 \
    --direction Inbound \
    --protocol Tcp \
    --source-address-prefixes 203.0.113.0/24 \
    --source-port-ranges "*" \
    --destination-port-ranges 22 \
    --access Allow

# Deny all inbound traffic explicitly (override default VNet allow)
az network nsg rule create \
    --resource-group rg-my-app-prod-eastus \
    --nsg-name nsg-backend-prod-eastus \
    --name deny-all-inbound \
    --priority 4000 \
    --direction Inbound \
    --protocol "*" \
    --source-address-prefixes "*" \
    --destination-port-ranges "*" \
    --access Deny

# Allow backend to reach database on port 5432
az network nsg rule create \
    --resource-group rg-my-app-prod-eastus \
    --nsg-name nsg-data-prod-eastus \
    --name allow-backend-to-db \
    --priority 100 \
    --direction Inbound \
    --protocol Tcp \
    --source-address-prefixes 10.0.2.0/24 \
    --destination-port-ranges 5432 \
    --access Allow

# Delete a rule
az network nsg rule delete \
    --resource-group rg-my-app-prod-eastus \
    --nsg-name nsg-backend-prod-eastus \
    --name allow-office-ssh
```

---

## Service Tags

Service tags are named groups of IP ranges for Azure services. Use them instead of hard-coding IP ranges.

| Tag | Covers |
|-----|--------|
| `Internet` | Any IP outside the VNet |
| `VirtualNetwork` | The VNet address space + peered VNets |
| `AzureLoadBalancer` | Azure health probe IPs |
| `AzureCloud` | All Azure datacenter IPs |
| `Storage` | Azure Storage service IPs |
| `Sql` | Azure SQL Database IPs |
| `AppService` | App Service outbound IPs |
| `AzureMonitor` | Log Analytics and Azure Monitor IPs |
| `AzureBastion` | Azure Bastion service IPs |

```bash
# Allow Azure Monitor outbound (for Log Analytics agent)
az network nsg rule create \
    --resource-group rg-my-app-prod-eastus \
    --nsg-name nsg-backend-prod-eastus \
    --name allow-azure-monitor-outbound \
    --priority 200 \
    --direction Outbound \
    --destination-address-prefixes AzureMonitor \
    --destination-port-ranges 443 \
    --access Allow

# Allow Azure Storage outbound
az network nsg rule create \
    --resource-group rg-my-app-prod-eastus \
    --nsg-name nsg-backend-prod-eastus \
    --name allow-storage-outbound \
    --priority 210 \
    --direction Outbound \
    --destination-address-prefixes Storage \
    --destination-port-ranges 443 \
    --access Allow
```

---

## Application Security Groups (ASG)

ASGs let you group VMs by role (e.g., "web-servers", "db-servers") and write NSG rules that reference the group instead of IP addresses. As VMs are added to ASGs, rules apply automatically.

```bash
# Create ASGs for web and database tiers
az network asg create \
    --resource-group rg-my-app-prod-eastus \
    --name asg-web-servers-prod

az network asg create \
    --resource-group rg-my-app-prod-eastus \
    --name asg-db-servers-prod

# Assign a VM's NIC to an ASG
az network nic update \
    --resource-group rg-my-app-prod-eastus \
    --name nic-vm-web-001 \
    --application-security-groups \
        $(az network asg show --resource-group rg-my-app-prod-eastus --name asg-web-servers-prod --query id -o tsv)

# Write NSG rule using ASGs instead of IP ranges
az network nsg rule create \
    --resource-group rg-my-app-prod-eastus \
    --nsg-name nsg-backend-prod-eastus \
    --name allow-web-to-db \
    --priority 100 \
    --direction Inbound \
    --protocol Tcp \
    --source-asgs \
        $(az network asg show --resource-group rg-my-app-prod-eastus --name asg-web-servers-prod --query id -o tsv) \
    --destination-asgs \
        $(az network asg show --resource-group rg-my-app-prod-eastus --name asg-db-servers-prod --query id -o tsv) \
    --destination-port-ranges 5432 \
    --access Allow
```

---

## NSG Flow Logs

Capture all accepted and rejected flows for security analysis and troubleshooting.

```bash
# Create a storage account for flow logs
az storage account create \
    --resource-group rg-platform-monitoring-eastus \
    --name stflowlogsprodeastus \
    --sku Standard_LRS \
    --location eastus

# Enable NSG flow logs (v2 — includes traffic analytics)
az network watcher flow-log create \
    --resource-group rg-my-app-prod-eastus \
    --name fl-nsg-backend-prod \
    --nsg nsg-backend-prod-eastus \
    --storage-account stflowlogsprodeastus \
    --enabled true \
    --format JSON \
    --log-version 2 \
    --retention 30 \
    --traffic-analytics true \
    --workspace $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus \
        --query id -o tsv)

# List flow logs
az network watcher flow-log list \
    --location eastus \
    --output table
```

---

## Effective Security Rules

See what rules actually apply to a VM's NIC (combines subnet NSG + NIC NSG + default rules):

```bash
NIC_ID=$(az vm show \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --query 'networkProfile.networkInterfaces[0].id' -o tsv)

az network nic show-effective-nsg \
    --ids $NIC_ID \
    --query 'effectiveNetworkSecurityGroups[*].effectiveSecurityRules[*].{Name:name,Direction:direction,Access:access,Priority:priority,DstPort:destinationPortRange}' \
    --output table
```

---

## References

- [NSG documentation](https://docs.microsoft.com/azure/virtual-network/network-security-groups-overview)
- [Service tags](https://docs.microsoft.com/azure/virtual-network/service-tags-overview)
- [Application security groups](https://docs.microsoft.com/azure/virtual-network/application-security-groups)
- [NSG flow logs](https://docs.microsoft.com/azure/network-watcher/network-watcher-nsg-flow-logging-overview)

---

← [Previous: VNet](./vnet.md) | [Home](../../README.md) | [Next: Application Gateway →](./application-gateway.md)
