← [Previous: Network Security Groups](../03-networking/network-security-groups.md) | [Home](../../README.md) | [Next: Virtual Machines →](./virtual-machines.md)

---

# Azure Compute

---

## Service Selection

| Service | AWS Equivalent | Use case |
|---------|----------------|---------|
| **Azure Virtual Machines** | EC2 | General-purpose IaaS — full OS control |
| **Virtual Machine Scale Sets (VMSS)** | EC2 Auto Scaling Group | Auto-scaling fleet of identical VMs |
| **Azure Kubernetes Service (AKS)** | EKS | Managed Kubernetes — see 07-containers |
| **Azure Container Instances (ACI)** | Fargate (run-task) | Serverless containers — no cluster management |
| **Azure App Service** | Elastic Beanstalk | PaaS for web apps — no VM management |
| **Azure Functions** | Lambda | Serverless functions — see 08-serverless |
| **Azure Batch** | AWS Batch | Large-scale parallel/HPC workloads |

---

## Virtual Machine Series Reference

| Series | vCPUs | Use case |
|--------|-------|---------|
| B (burstable) | 1–20 | Dev/test, low-traffic apps |
| D (general purpose) | 2–96 | Web apps, databases, application servers |
| E (memory optimized) | 2–104 | In-memory databases, SAP, Redis |
| F (compute optimized) | 2–72 | Batch processing, gaming, web servers |
| L (storage optimized) | 8–80 | NoSQL, SQL data warehouses |
| M (memory heavy) | 8–416 | SAP HANA, large in-memory |
| N (GPU) | 6–64 | ML training, GPU rendering |

Naming convention: `{Series}{Version}{Sub-type}_{vCPUs}` (e.g., `Standard_D4s_v5` = D series, v5, 4 vCPUs, premium storage)

---

## Creating a Virtual Machine

```bash
RESOURCE_GROUP="rg-my-app-production"
LOCATION="eastus"

# Create a VM with Ubuntu 22.04, SSH key auth, no public IP
az vm create \
    --resource-group $RESOURCE_GROUP \
    --name vm-my-app-prod-eastus-001 \
    --image Ubuntu2204 \
    --size Standard_D2s_v5 \
    --admin-username azureuser \
    --ssh-key-values ~/.ssh/id_rsa.pub \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-app \
    --nsg nsg-app \
    --public-ip-address "" \
    --os-disk-size-gb 128 \
    --storage-sku Premium_LRS \
    --zone 1 \
    --assign-identity \
    --tags Environment=production Service=my-app

# Query the VM's private IP
az vm show \
    --resource-group $RESOURCE_GROUP \
    --name vm-my-app-prod-eastus-001 \
    --show-details \
    --query '{Name:name,Size:hardwareProfile.vmSize,IP:privateIps,OS:storageProfile.imageReference.offer,Zone:zones[0]}'

# Start / stop / restart
az vm start  --resource-group $RESOURCE_GROUP --name vm-my-app-prod-eastus-001
az vm stop   --resource-group $RESOURCE_GROUP --name vm-my-app-prod-eastus-001
az vm restart --resource-group $RESOURCE_GROUP --name vm-my-app-prod-eastus-001

# Deallocate (stop billing for compute — disk still billed)
az vm deallocate --resource-group $RESOURCE_GROUP --name vm-my-app-prod-eastus-001
```

---

## Custom Script Extension (User Data equivalent)

```bash
# Run a script on VM creation (inline)
az vm create \
    --resource-group $RESOURCE_GROUP \
    --name vm-my-app-prod-eastus-002 \
    --image Ubuntu2204 \
    --size Standard_D2s_v5 \
    --admin-username azureuser \
    --ssh-key-values ~/.ssh/id_rsa.pub \
    --custom-data cloud-init.yml  # cloud-init file

# Run a script on an existing VM via Custom Script Extension
az vm extension set \
    --resource-group $RESOURCE_GROUP \
    --vm-name vm-my-app-prod-eastus-001 \
    --name CustomScript \
    --publisher Microsoft.Azure.Extensions \
    --settings '{"commandToExecute": "apt-get update && apt-get install -y nginx && systemctl enable nginx && systemctl start nginx"}'
```

### cloud-init.yml

```yaml
#cloud-config
package_update: true
packages:
  - nginx
  - curl

runcmd:
  - systemctl enable nginx
  - systemctl start nginx
  - echo "server { listen 80; location /health { return 200 OK; } }" > /etc/nginx/conf.d/health.conf
  - systemctl reload nginx

write_files:
  - path: /etc/app/config.env
    content: |
      APP_ENV=production
      PORT=8080
```

---

## VM Extensions

```bash
# Install Azure Monitor Agent (replaces Log Analytics Agent)
az vm extension set \
    --resource-group $RESOURCE_GROUP \
    --vm-name vm-my-app-prod-eastus-001 \
    --name AzureMonitorLinuxAgent \
    --publisher Microsoft.Azure.Monitor \
    --enable-auto-upgrade true

# List installed extensions
az vm extension list \
    --resource-group $RESOURCE_GROUP \
    --vm-name vm-my-app-prod-eastus-001 \
    --output table

# Run command remotely (no SSH needed — via Azure agent)
az vm run-command invoke \
    --resource-group $RESOURCE_GROUP \
    --name vm-my-app-prod-eastus-001 \
    --command-id RunShellScript \
    --scripts "systemctl status nginx" \
    --query 'value[0].message' --output tsv
```

---

## VM Scale Sets (VMSS)

```bash
# Create a VMSS with auto scaling (2–10 VMs based on CPU)
az vmss create \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus \
    --image Ubuntu2204 \
    --vm-sku Standard_D2s_v5 \
    --instance-count 2 \
    --admin-username azureuser \
    --ssh-key-values ~/.ssh/id_rsa.pub \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-app \
    --load-balancer "" \
    --upgrade-policy-mode Rolling \
    --zones 1 2 3 \
    --assign-identity \
    --custom-data cloud-init.yml

# Configure auto scaling
az monitor autoscale create \
    --resource-group $RESOURCE_GROUP \
    --resource vmss-my-app-prod-eastus \
    --resource-type Microsoft.Compute/virtualMachineScaleSets \
    --name autoscale-vmss-my-app \
    --min-count 2 \
    --max-count 10 \
    --count 2

# Scale out when CPU > 70% for 5 minutes
az monitor autoscale rule create \
    --resource-group $RESOURCE_GROUP \
    --autoscale-name autoscale-vmss-my-app \
    --condition "Percentage CPU > 70 avg 5m" \
    --scale out 2 \
    --cooldown 5

# Scale in when CPU < 30% for 10 minutes
az monitor autoscale rule create \
    --resource-group $RESOURCE_GROUP \
    --autoscale-name autoscale-vmss-my-app \
    --condition "Percentage CPU < 30 avg 10m" \
    --scale in 1 \
    --cooldown 10

# Rolling upgrade — update all instances to a new image
az vmss update \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus \
    --set virtualMachineProfile.storageProfile.imageReference.version=latest

az vmss rolling-upgrade start \
    --resource-group $RESOURCE_GROUP \
    --name vmss-my-app-prod-eastus
```

---

## Disks and Snapshots

```bash
# Add a data disk to a running VM
az vm disk attach \
    --resource-group $RESOURCE_GROUP \
    --vm-name vm-my-app-prod-eastus-001 \
    --name disk-my-app-data-001 \
    --size-gb 256 \
    --sku Premium_LRS \
    --new

# Create a snapshot of an OS disk
DISK_ID=$(az vm show \
    --resource-group $RESOURCE_GROUP \
    --name vm-my-app-prod-eastus-001 \
    --query storageProfile.osDisk.managedDisk.id --output tsv)

az snapshot create \
    --resource-group $RESOURCE_GROUP \
    --name snap-my-app-$(date +%Y%m%d) \
    --source $DISK_ID \
    --incremental

# List snapshots
az snapshot list --resource-group $RESOURCE_GROUP --output table
```

---

## Cost Optimization

| Strategy | Savings | Notes |
|----------|---------|-------|
| Reserved Instances (1yr) | Up to 40% | Commit to a VM family and region |
| Reserved Instances (3yr) | Up to 60% | Best for stable, long-running workloads |
| Spot VMs | Up to 90% | Can be evicted with 30s notice — batch, stateless only |
| Azure Hybrid Benefit | Up to 49% | Use Windows Server or SQL Server licenses you own |
| B-series burstable | — | Cost-effective for dev/test with variable CPU |
| Auto-shutdown | — | Stop dev VMs at night via `az vm auto-shutdown` |

```bash
# Enable auto-shutdown at 7 PM UTC
az vm auto-shutdown \
    --resource-group $RESOURCE_GROUP \
    --name vm-my-app-dev-001 \
    --time 1900 \
    --email ops@example.com
```

---

## References

- [Azure Virtual Machines documentation](https://docs.microsoft.com/azure/virtual-machines/)
- [VM sizes](https://docs.microsoft.com/azure/virtual-machines/sizes)
- [VMSS documentation](https://docs.microsoft.com/azure/virtual-machine-scale-sets/)
- [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/)
---

← [Previous: Network Security Groups](../03-networking/network-security-groups.md) | [Home](../../README.md) | [Next: Virtual Machines →](./virtual-machines.md)
