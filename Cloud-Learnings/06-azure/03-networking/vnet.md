← [Previous: Azure Networking](./README.md) | [Home](../../README.md) | [Next: Network Security Groups →](./network-security-groups.md)

---

# Azure Virtual Networks (VNet)

A Virtual Network (VNet) is a private, isolated network in Azure — the equivalent of AWS VPC. It is the foundation of Azure networking.

---

## Key Properties

| Property | Notes |
|----------|-------|
| **Regional** | A VNet exists in one Azure region; it spans all availability zones in that region |
| **Address space** | One or more CIDR blocks (IPv4 and/or IPv6) |
| **Subnets** | Subdivisions of the VNet address space |
| **No NAT by default** | Outbound internet traffic uses ephemeral public IPs unless restricted |
| **DNS** | Default: Azure DNS (168.63.129.16). Custom: bring your own DNS server |

---

## Creating a VNet

```bash
# Create a VNet with two address ranges
az network vnet create \
    --resource-group rg-my-app-prod-eastus \
    --name vnet-my-app-prod-eastus-001 \
    --location eastus \
    --address-prefixes 10.0.0.0/16 \
    --tags Environment=production Team=platform ManagedBy=Terraform

# List VNets
az network vnet list \
    --query '[*].{Name:name,RG:resourceGroup,AddressSpace:addressSpace.addressPrefixes[0]}' \
    --output table

# Show details
az network vnet show \
    --resource-group rg-my-app-prod-eastus \
    --name vnet-my-app-prod-eastus-001
```

---

## Subnets

```bash
# Create subnets
az network vnet subnet create \
    --resource-group rg-my-app-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-frontend-prod \
    --address-prefix 10.0.1.0/24

az network vnet subnet create \
    --resource-group rg-my-app-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-backend-prod \
    --address-prefix 10.0.2.0/24

az network vnet subnet create \
    --resource-group rg-my-app-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-data-prod \
    --address-prefix 10.0.3.0/24

# AKS requires a dedicated subnet
az network vnet subnet create \
    --resource-group rg-my-app-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-aks-nodes-prod \
    --address-prefix 10.0.4.0/22   # /22 = 1022 usable IPs for nodes

# Gateway subnet (required for VPN/ExpressRoute gateways — must be named exactly "GatewaySubnet")
az network vnet subnet create \
    --resource-group rg-my-app-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name GatewaySubnet \
    --address-prefix 10.0.255.0/27

# Azure Bastion subnet (must be named "AzureBastionSubnet", minimum /26)
az network vnet subnet create \
    --resource-group rg-my-app-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name AzureBastionSubnet \
    --address-prefix 10.0.254.0/26

# List subnets
az network vnet subnet list \
    --resource-group rg-my-app-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --output table
```

### Reserved Addresses in Every Subnet

Azure reserves 5 IP addresses per subnet: `.0` (network), `.1` (gateway), `.2`–`.3` (DNS), `.255` (broadcast). A `/24` has 251 usable IPs.

---

## VNet Subnet Design Patterns

```
vnet: 10.0.0.0/16
├── snet-frontend-prod    10.0.1.0/24   Web tier (App Service, Front Door origin)
├── snet-backend-prod     10.0.2.0/24   API tier (VMs, AKS)
├── snet-data-prod        10.0.3.0/24   Database tier (SQL, PostgreSQL, Cache)
├── snet-aks-nodes-prod   10.0.4.0/22   AKS node pool (needs larger range)
├── snet-private-ep-prod  10.0.8.0/24   Private endpoints for PaaS services
├── snet-mgmt-prod        10.0.9.0/24   Bastion, jump boxes
├── AzureBastionSubnet    10.0.254.0/26 Azure Bastion (fixed name)
└── GatewaySubnet         10.0.255.0/27 VPN / ExpressRoute gateway (fixed name)
```

---

## VNet Peering

VNet peering connects two VNets at the network layer — traffic flows directly without traversing the internet. Can be within the same region (peering) or across regions (global peering).

```bash
# Peer VNet A → VNet B (must also peer B → A)
VNET_A_ID=$(az network vnet show \
    --resource-group rg-platform-prod-eastus \
    --name vnet-hub-prod-eastus-001 \
    --query id -o tsv)

VNET_B_ID=$(az network vnet show \
    --resource-group rg-my-app-prod-eastus \
    --name vnet-my-app-prod-eastus-001 \
    --query id -o tsv)

# Peer from hub to spoke
az network vnet peering create \
    --resource-group rg-platform-prod-eastus \
    --name peering-hub-to-my-app \
    --vnet-name vnet-hub-prod-eastus-001 \
    --remote-vnet $VNET_B_ID \
    --allow-vnet-access \
    --allow-forwarded-traffic \
    --allow-gateway-transit     # Hub can share its VPN gateway with spokes

# Peer from spoke to hub
az network vnet peering create \
    --resource-group rg-my-app-prod-eastus \
    --name peering-my-app-to-hub \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --remote-vnet $VNET_A_ID \
    --allow-vnet-access \
    --allow-forwarded-traffic \
    --use-remote-gateways        # Use hub's VPN gateway

# List peerings
az network vnet peering list \
    --resource-group rg-my-app-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --output table
```

---

## DNS Configuration

```bash
# Set custom DNS servers on a VNet
az network vnet update \
    --resource-group rg-my-app-prod-eastus \
    --name vnet-my-app-prod-eastus-001 \
    --dns-servers 10.0.9.4 10.0.9.5   # Custom DNS server IPs

# Revert to Azure DNS
az network vnet update \
    --resource-group rg-my-app-prod-eastus \
    --name vnet-my-app-prod-eastus-001 \
    --dns-servers ""
```

### Private DNS Zones

Private DNS zones provide DNS resolution for private endpoints and custom DNS records within a VNet.

```bash
# Create a private DNS zone
az network private-dns zone create \
    --resource-group rg-my-app-prod-eastus \
    --name "privatelink.blob.core.windows.net"

# Link the DNS zone to a VNet
az network private-dns link vnet create \
    --resource-group rg-my-app-prod-eastus \
    --zone-name "privatelink.blob.core.windows.net" \
    --name link-to-vnet-my-app-prod \
    --virtual-network vnet-my-app-prod-eastus-001 \
    --registration-enabled false    # Auto-register VM DNS names

# Add a DNS record
az network private-dns record-set a add-record \
    --resource-group rg-my-app-prod-eastus \
    --zone-name "contoso.internal" \
    --record-set-name "my-service" \
    --ipv4-address 10.0.2.50
```

---

## User-Defined Routes (UDR)

Override Azure's default routing — e.g., force all internet traffic through an Azure Firewall.

```bash
# Create a route table
az network route-table create \
    --resource-group rg-my-app-prod-eastus \
    --name rt-my-app-prod-eastus \
    --disable-bgp-route-propagation true

# Add a route to send all internet traffic to firewall
az network route-table route create \
    --resource-group rg-my-app-prod-eastus \
    --route-table-name rt-my-app-prod-eastus \
    --name default-to-firewall \
    --address-prefix 0.0.0.0/0 \
    --next-hop-type VirtualAppliance \
    --next-hop-ip-address 10.0.0.4   # Azure Firewall private IP

# Associate route table with a subnet
az network vnet subnet update \
    --resource-group rg-my-app-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-backend-prod \
    --route-table rt-my-app-prod-eastus
```

---

## References

- [Azure Virtual Networks documentation](https://docs.microsoft.com/azure/virtual-network/)
- [VNet peering](https://docs.microsoft.com/azure/virtual-network/virtual-network-peering-overview)
- [Private DNS zones](https://docs.microsoft.com/azure/dns/private-dns-overview)
- [Azure subnet design](https://docs.microsoft.com/azure/virtual-network/virtual-network-vnet-plan-design-arm)

---

← [Previous: Azure Networking](./README.md) | [Home](../../README.md) | [Next: Network Security Groups →](./network-security-groups.md)
