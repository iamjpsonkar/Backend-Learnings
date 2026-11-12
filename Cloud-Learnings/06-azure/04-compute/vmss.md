← [Previous: Virtual Machines](./virtual-machines.md) | [Home](../../README.md) | [Next: Azure Storage →](../05-storage/README.md)

---

# Azure Virtual Machine Scale Sets (VMSS)

VMSS lets you deploy and manage a group of identical, load-balanced VMs with automatic scaling. It is the Azure equivalent of AWS Auto Scaling Groups.

---

## VMSS vs Individual VMs

| Feature | VMSS | Individual VMs |
|---------|------|----------------|
| Horizontal scaling | Automatic or manual | Manual only |
| Load balancing | Built-in (Azure LB or App Gateway) | Must configure separately |
| Rolling upgrades | Yes (rolling, blue-green, manual) | Manual |
| Spot instance support | Yes (mix of spot + regular) | Yes |
| Max instances | 1000 (standard) / 600 (custom image) | Unlimited (deploy individually) |
| Orchestration mode | Flexible or Uniform | N/A |

### Orchestration Modes

| Mode | Use Case |
|------|----------|
| **Flexible** (recommended) | Heterogeneous VMs, AKS-style, zone flexibility |
| **Uniform** | Identical VMs, highest scale (up to 1000 instances) |

---

## Creating a VMSS

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
LOCATION="eastus"

# Create VMSS in Flexible orchestration mode (recommended)
az vmss create \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus-001 \
    --location $LOCATION \
    --orchestration-mode Flexible \
    --image Ubuntu2204 \
    --vm-sku Standard_D2s_v5 \
    --instance-count 2 \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-app \
    --assign-identity [system] \
    --authentication-type ssh \
    --ssh-key-values ~/.ssh/id_rsa.pub \
    --admin-username azureuser \
    --upgrade-policy-mode Rolling \
    --zones 1 2 3 \
    --platform-fault-domain-count 1 \  # For zone-redundant: set 1
    --no-public-ip \
    --tags Environment=production Service=my-app

# Verify VMSS instances
az vmss list-instances \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus-001 \
    --query '[*].{ID:instanceId,State:provisioningState,Zone:zones[0]}' \
    --output table
```

---

## Autoscaling

```bash
# Enable autoscale profile — scale on CPU
az monitor autoscale create \
    --resource-group $RESOURCE_GROUP \
    --name autoscale-vmss-prod \
    --resource vmss-my-app-prod-eastus-001 \
    --resource-type Microsoft.Compute/virtualMachineScaleSets \
    --min-count 2 \
    --max-count 20 \
    --count 2

# Scale out: CPU > 70% for 5 minutes → add 2 instances
az monitor autoscale rule create \
    --resource-group $RESOURCE_GROUP \
    --autoscale-name autoscale-vmss-prod \
    --condition "Percentage CPU > 70 avg 5m" \
    --scale out 2 \
    --cooldown 5

# Scale in: CPU < 30% for 10 minutes → remove 1 instance
az monitor autoscale rule create \
    --resource-group $RESOURCE_GROUP \
    --autoscale-name autoscale-vmss-prod \
    --condition "Percentage CPU < 30 avg 10m" \
    --scale in 1 \
    --cooldown 10

# Scheduled autoscale — scale up during business hours (UTC)
az monitor autoscale profile create \
    --resource-group $RESOURCE_GROUP \
    --autoscale-name autoscale-vmss-prod \
    --name business-hours \
    --min-count 4 \
    --max-count 20 \
    --count 4 \
    --recurrence week mon tue wed thu fri \
    --timezone "UTC" \
    --start 07:00 \
    --end 19:00

# View current autoscale settings
az monitor autoscale show \
    --resource-group $RESOURCE_GROUP \
    --name autoscale-vmss-prod \
    --output json
```

---

## Upgrade Policies

VMSS supports three upgrade policy modes for rolling out OS/image changes:

| Mode | Behavior |
|------|----------|
| **Automatic** | Azure upgrades instances automatically in batches |
| **Rolling** | You control batch size, max unhealthy % |
| **Manual** | You manually trigger upgrades per instance |

```bash
# Configure rolling upgrade policy
az vmss update \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus-001 \
    --set upgradePolicy.mode=Rolling \
    --set upgradePolicy.rollingUpgradePolicy.maxBatchInstancePercent=20 \
    --set upgradePolicy.rollingUpgradePolicy.maxUnhealthyInstancePercent=20 \
    --set upgradePolicy.rollingUpgradePolicy.maxUnhealthyUpgradedInstancePercent=20 \
    --set upgradePolicy.rollingUpgradePolicy.pauseTimeBetweenBatches=PT30S

# Manually upgrade specific instances
az vmss update-instances \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus-001 \
    --instance-ids 0 1 2

# Upgrade all instances at once (for manual mode)
az vmss update-instances \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus-001 \
    --instance-ids "*"
```

---

## Custom Script Extension (Bootstrap)

```bash
# Run a custom script on all new VMSS instances at provisioning
az vmss extension set \
    --resource-group $RESOURCE_GROUP \
    --vmss-name vmss-my-app-prod-eastus-001 \
    --name customScript \
    --publisher Microsoft.Azure.Extensions \
    --version 2.1 \
    --settings '{
        "commandToExecute": "apt-get update && apt-get install -y nginx && systemctl enable nginx && systemctl start nginx"
    }'

# Cloud-init via --custom-data at creation (preferred over CSE for init)
# Use: --custom-data /path/to/cloud-init.yaml
```

---

## Manual Scale Operations

```bash
# Scale out to 10 instances immediately
az vmss scale \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus-001 \
    --new-capacity 10

# Deallocate a specific instance (stop billing for compute)
az vmss deallocate \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus-001 \
    --instance-ids 5

# Delete a specific instance
az vmss delete-instances \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus-001 \
    --instance-ids 5

# List instances with details
az vmss list-instances \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus-001 \
    --output table
```

---

## Load Balancer Integration

```bash
# Create internal load balancer for VMSS backend
az network lb create \
    --resource-group $RESOURCE_GROUP \
    --name lb-vmss-prod \
    --sku Standard \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-app \
    --frontend-ip-name fe-config \
    --backend-pool-name be-pool

az network lb probe create \
    --resource-group $RESOURCE_GROUP \
    --lb-name lb-vmss-prod \
    --name health-probe \
    --protocol Http \
    --port 80 \
    --path /health

az network lb rule create \
    --resource-group $RESOURCE_GROUP \
    --lb-name lb-vmss-prod \
    --name http-rule \
    --protocol Tcp \
    --frontend-port 80 \
    --backend-port 80 \
    --frontend-ip-name fe-config \
    --backend-pool-name be-pool \
    --probe-name health-probe

# Associate VMSS with the backend pool
az vmss update \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus-001 \
    --add virtualMachineProfile.networkProfile.networkInterfaceConfigurations[0].ipConfigurations[0].loadBalancerBackendAddressPools \
        id=$(az network lb address-pool show \
            --resource-group $RESOURCE_GROUP \
            --lb-name lb-vmss-prod \
            --name be-pool \
            --query id -o tsv)
```

---

## References

- [Virtual Machine Scale Sets documentation](https://docs.microsoft.com/azure/virtual-machine-scale-sets/)
- [Autoscale with VMSS](https://docs.microsoft.com/azure/virtual-machine-scale-sets/virtual-machine-scale-sets-autoscale-overview)
- [Upgrade policies](https://docs.microsoft.com/azure/virtual-machine-scale-sets/virtual-machine-scale-sets-upgrade-scale-set)

---

← [Previous: Virtual Machines](./virtual-machines.md) | [Home](../../README.md) | [Next: Azure Storage →](../05-storage/README.md)
