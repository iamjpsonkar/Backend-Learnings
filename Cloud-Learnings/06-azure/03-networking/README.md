← [Previous: Managed Identities](../02-entra-id/managed-identities.md) | [Home](../../README.md) | [Next: VNet →](./vnet.md)

---

# Azure Networking

---

## Core Concepts

| Concept | AWS Equivalent | Description |
|---------|----------------|-------------|
| **Virtual Network (VNet)** | VPC | Private network — regional, spans all AZs |
| **Subnet** | Subnet | Subdivision of a VNet |
| **Network Security Group (NSG)** | Security Group | Stateful L4 traffic rules (allow/deny by IP, port, protocol) |
| **Application Security Group (ASG)** | — | Group VMs by role (web, app, db) for NSG rules |
| **Route Table (UDR)** | Route Table | Custom routes — override Azure defaults |
| **VNet Peering** | VPC Peering | Connect VNets within or across regions |
| **Virtual WAN (vWAN)** | Transit Gateway | Hub-and-spoke at global scale |
| **VPN Gateway** | VPN Gateway | Site-to-site and point-to-site VPN |
| **ExpressRoute** | Direct Connect | Dedicated private connection to Azure |
| **Application Gateway** | ALB | L7 load balancer with WAF |
| **Azure Load Balancer** | NLB | L4 load balancer |
| **Azure Front Door** | CloudFront + Global Accelerator | Global L7 CDN + load balancer |
| **Private Endpoint** | VPC Interface Endpoint | Private IP for Azure PaaS services |
| **Private Link Service** | VPC Endpoint Service | Expose your service privately to other VNets |
| **Azure Firewall** | Network Firewall | Managed L4/L7 stateful firewall |
| **Azure Bastion** | EC2 Instance Connect Endpoint | Secure browser-based SSH/RDP — no public IPs |

---

## VNet and Subnet Creation

```bash
RESOURCE_GROUP="rg-my-app-production"
LOCATION="eastus"

# Create a VNet
az network vnet create \
    --resource-group $RESOURCE_GROUP \
    --name vnet-my-app-prod-eastus-001 \
    --address-prefixes 10.0.0.0/16 \
    --location $LOCATION \
    --tags Environment=production ManagedBy=Terraform

# Create subnets
# Public (DMZ) — for Application Gateway, Azure Bastion
az network vnet subnet create \
    --resource-group $RESOURCE_GROUP \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-public \
    --address-prefix 10.0.1.0/24

# Application tier — AKS node pools, VMs
az network vnet subnet create \
    --resource-group $RESOURCE_GROUP \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-app \
    --address-prefix 10.0.10.0/24

# Data tier — databases, cache (delegated to services)
az network vnet subnet create \
    --resource-group $RESOURCE_GROUP \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-data \
    --address-prefix 10.0.20.0/28

# Private endpoints subnet
az network vnet subnet create \
    --resource-group $RESOURCE_GROUP \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-private-endpoints \
    --address-prefix 10.0.30.0/24 \
    --disable-private-endpoint-network-policies true

# Azure Bastion requires a dedicated subnet named AzureBastionSubnet (/26 minimum)
az network vnet subnet create \
    --resource-group $RESOURCE_GROUP \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name AzureBastionSubnet \
    --address-prefix 10.0.100.0/26
```

---

## Network Security Groups (NSGs)

```bash
# Create NSG for application tier
az network nsg create \
    --resource-group $RESOURCE_GROUP \
    --name nsg-app \
    --tags Environment=production

# Allow HTTPS from the public internet (for Application Gateway → app tier)
az network nsg rule create \
    --resource-group $RESOURCE_GROUP \
    --nsg-name nsg-app \
    --name Allow-HTTPS-Inbound \
    --priority 100 \
    --protocol Tcp \
    --direction Inbound \
    --source-address-prefixes "*" \
    --source-port-ranges "*" \
    --destination-address-prefixes "*" \
    --destination-port-ranges 443 \
    --access Allow

# Allow internal app traffic (8080) from Application Gateway subnet only
az network nsg rule create \
    --resource-group $RESOURCE_GROUP \
    --nsg-name nsg-app \
    --name Allow-AppGW-To-App \
    --priority 110 \
    --protocol Tcp \
    --direction Inbound \
    --source-address-prefixes 10.0.1.0/24 \
    --destination-port-ranges 8080 \
    --access Allow

# Deny all other inbound
az network nsg rule create \
    --resource-group $RESOURCE_GROUP \
    --nsg-name nsg-app \
    --name Deny-All-Inbound \
    --priority 4096 \
    --protocol "*" \
    --direction Inbound \
    --source-address-prefixes "*" \
    --destination-port-ranges "*" \
    --access Deny

# Attach NSG to subnet
az network vnet subnet update \
    --resource-group $RESOURCE_GROUP \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-app \
    --network-security-group nsg-app

# List NSG rules
az network nsg rule list \
    --resource-group $RESOURCE_GROUP \
    --nsg-name nsg-app \
    --query '[*].{Name:name,Priority:priority,Direction:direction,Access:access,Protocol:protocol,Dest:destinationPortRanges}' \
    --output table
```

---

## VNet Peering

```bash
VNET_A="vnet-hub-prod-eastus-001"
VNET_B="vnet-spoke-app-prod-eastus-001"
RG_A="rg-hub-production"
RG_B="rg-spoke-production"

VNET_A_ID=$(az network vnet show --resource-group $RG_A --name $VNET_A --query id --output tsv)
VNET_B_ID=$(az network vnet show --resource-group $RG_B --name $VNET_B --query id --output tsv)

# Peer A → B
az network vnet peering create \
    --resource-group $RG_A \
    --name peer-hub-to-spoke \
    --vnet-name $VNET_A \
    --remote-vnet $VNET_B_ID \
    --allow-vnet-access \
    --allow-forwarded-traffic \
    --allow-gateway-transit  # Allow spoke to use hub's VPN Gateway

# Peer B → A (peering must be created in both directions)
az network vnet peering create \
    --resource-group $RG_B \
    --name peer-spoke-to-hub \
    --vnet-name $VNET_B \
    --remote-vnet $VNET_A_ID \
    --allow-vnet-access \
    --allow-forwarded-traffic \
    --use-remote-gateways  # Use hub's VPN Gateway

# Verify peering state (must be "Connected" on both sides)
az network vnet peering list --resource-group $RG_A --vnet-name $VNET_A \
    --query '[*].{Name:name,State:peeringState,Remote:remoteVirtualNetwork.id}' --output table
```

---

## Application Gateway (L7 Load Balancer with WAF)

```bash
# Create a public IP for Application Gateway
az network public-ip create \
    --resource-group $RESOURCE_GROUP \
    --name pip-appgw-prod-eastus-001 \
    --sku Standard \
    --allocation-method Static \
    --zone 1 2 3

# Create Application Gateway with WAF_v2 SKU
az network application-gateway create \
    --resource-group $RESOURCE_GROUP \
    --name agw-my-app-prod-eastus-001 \
    --location $LOCATION \
    --sku WAF_v2 \
    --capacity 2 \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-public \
    --public-ip-address pip-appgw-prod-eastus-001 \
    --frontend-port 443 \
    --http-settings-port 8080 \
    --http-settings-protocol Http \
    --routing-rule-type Basic \
    --priority 100 \
    --cert-file /path/to/cert.pfx \
    --cert-password "certpassword"

# Enable OWASP WAF policy
az network application-gateway waf-config set \
    --resource-group $RESOURCE_GROUP \
    --gateway-name agw-my-app-prod-eastus-001 \
    --enabled true \
    --firewall-mode Prevention \
    --rule-set-type OWASP \
    --rule-set-version 3.2
```

---

## Private Endpoints

Private Endpoints give Azure PaaS services (Storage, SQL, Key Vault, etc.) a private IP in your VNet — traffic never leaves the Azure backbone.

```bash
STORAGE_ID=$(az storage account show \
    --resource-group $RESOURCE_GROUP \
    --name stmyappprodeastus \
    --query id --output tsv)

# Create private endpoint for blob storage
az network private-endpoint create \
    --resource-group $RESOURCE_GROUP \
    --name pe-storage-blob \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-private-endpoints \
    --private-connection-resource-id $STORAGE_ID \
    --group-id blob \
    --connection-name pe-conn-storage-blob

# Create private DNS zone for blob (so DNS resolves to private IP)
az network private-dns zone create \
    --resource-group $RESOURCE_GROUP \
    --name "privatelink.blob.core.windows.net"

az network private-dns link vnet create \
    --resource-group $RESOURCE_GROUP \
    --zone-name "privatelink.blob.core.windows.net" \
    --name dns-link-prod-vnet \
    --virtual-network vnet-my-app-prod-eastus-001 \
    --registration-enabled false

# Create DNS record from private endpoint
az network private-endpoint dns-zone-group create \
    --resource-group $RESOURCE_GROUP \
    --endpoint-name pe-storage-blob \
    --name blob-zone-group \
    --private-dns-zone "privatelink.blob.core.windows.net" \
    --zone-name blob
```

---

## Azure Bastion (Secure VM Access)

```bash
# Create Bastion (requires AzureBastionSubnet)
BASTION_PIP=$(az network public-ip create \
    --resource-group $RESOURCE_GROUP \
    --name pip-bastion-prod-eastus \
    --sku Standard \
    --allocation-method Static \
    --query id --output tsv)

az network bastion create \
    --resource-group $RESOURCE_GROUP \
    --name bastion-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --public-ip-address $BASTION_PIP \
    --sku Standard \
    --enable-tunneling  # Enables native SSH/RDP tunneling via az CLI

# Connect to a VM via Bastion tunnel (no public IP on VM required)
az network bastion ssh \
    --resource-group $RESOURCE_GROUP \
    --name bastion-prod-eastus \
    --target-resource-id $(az vm show --resource-group $RESOURCE_GROUP --name vm-app-001 --query id --output tsv) \
    --auth-type "ssh-key" \
    --username azureuser \
    --ssh-key ~/.ssh/id_rsa
```

---

## VPN Gateway (Site-to-Site)

```bash
# Create VPN Gateway (takes 30–45 minutes to provision)
az network vnet subnet create \
    --resource-group $RESOURCE_GROUP \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name GatewaySubnet \
    --address-prefix 10.0.255.0/27

VPN_PIP=$(az network public-ip create \
    --resource-group $RESOURCE_GROUP \
    --name pip-vpngw-prod-eastus \
    --sku Standard --allocation-method Static \
    --query id --output tsv)

az network vnet-gateway create \
    --resource-group $RESOURCE_GROUP \
    --name vpngw-prod-eastus \
    --vnet vnet-my-app-prod-eastus-001 \
    --gateway-type Vpn \
    --vpn-type RouteBased \
    --sku VpnGw2AZ \
    --public-ip-address $VPN_PIP \
    --no-wait

# Create local network gateway (represents your on-premises network)
az network local-gateway create \
    --resource-group $RESOURCE_GROUP \
    --name lgw-onprem \
    --gateway-ip-address 203.0.113.10 \
    --local-address-prefixes 192.168.0.0/16

# Create VPN connection
az network vpn-connection create \
    --resource-group $RESOURCE_GROUP \
    --name vpn-conn-onprem \
    --vnet-gateway1 vpngw-prod-eastus \
    --local-gateway2 lgw-onprem \
    --shared-key "SecurePreSharedKey123!" \
    --connection-type IPSec
```

---

## References

- [Azure Virtual Network documentation](https://docs.microsoft.com/azure/virtual-network/)
- [Network Security Groups](https://docs.microsoft.com/azure/virtual-network/network-security-groups-overview)
- [Application Gateway](https://docs.microsoft.com/azure/application-gateway/)
- [Private Link and Private Endpoint](https://docs.microsoft.com/azure/private-link/)
- [Azure Bastion](https://docs.microsoft.com/azure/bastion/)
---

← [Previous: Managed Identities](../02-entra-id/managed-identities.md) | [Home](../../README.md) | [Next: VNet →](./vnet.md)
