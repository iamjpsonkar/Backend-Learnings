← [Previous: Azure Compute](./README.md) | [Home](../../README.md) | [Next: VMSS →](./vmss.md)

---

# Azure Virtual Machines

Azure VMs provide on-demand compute capacity. They are the IaaS foundation for workloads that need full OS control.

---

## VM Size Families

| Series | Purpose | Examples |
|--------|---------|---------|
| **B** | Burstable — low baseline, burst to full CPU | B2s, B4ms (dev/test, small apps) |
| **D** | General purpose — balanced CPU/memory | D4s_v5, D8s_v5 (web apps, databases) |
| **E** | Memory optimized — high memory/CPU ratio | E4s_v5, E16s_v5 (in-memory databases, caches) |
| **F** | Compute optimized — high CPU/memory ratio | F4s_v2, F16s_v2 (batch processing, gaming) |
| **L** | Storage optimized — high local disk throughput | L8s_v3, L16s_v3 (NoSQL, analytics) |
| **M** | Very large memory | M64s, M128s (SAP HANA, large databases) |
| **N** | GPU | NC (AI training), NV (visualization), ND (deep learning) |

```bash
# List available VM sizes in a region
az vm list-sizes \
    --location eastus \
    --query '[*].{Name:name,CPUs:numberOfCores,Memory:memoryInMb,MaxDisk:maxDataDiskCount}' \
    --output table | grep -E "^D|Standard_D"

# Compare prices (requires az extension)
az vm list-skus --location eastus --size Standard_D --output table
```

---

## Creating a VM

```bash
# Create a Linux VM with SSH key authentication (recommended)
az vm create \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --location eastus \
    --image Ubuntu2204 \
    --size Standard_D2s_v5 \
    --admin-username azureuser \
    --ssh-key-values ~/.ssh/id_rsa.pub \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-backend-prod \
    --public-ip-address ""          \     # No public IP — use Bastion
    --nsg ""                              # Attach your own NSG to the subnet
    --zone 1 \                            # Availability Zone 1
    --os-disk-size-gb 64 \
    --storage-sku Premium_LRS \
    --tags Environment=production Team=platform

# Create a Windows VM
az vm create \
    --resource-group rg-my-app-prod-eastus \
    --name vm-app-win-prod-001 \
    --image Win2022Datacenter \
    --size Standard_D4s_v5 \
    --admin-username azureuser \
    --admin-password "$VM_PASSWORD" \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-backend-prod \
    --public-ip-address "" \
    --zone 1

# Show VM details including public/private IP
az vm show \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --show-details \
    --query '{Name:name,Size:hardwareProfile.vmSize,State:powerState,PublicIP:publicIps,PrivateIP:privateIps}'
```

---

## Connecting to VMs

```bash
# SSH (public IP or via Bastion)
ssh azureuser@<public-ip>
ssh -i ~/.ssh/id_rsa azureuser@<public-ip>

# Via Azure Bastion (no public IP needed)
az network bastion ssh \
    --name bastion-my-app-prod-eastus \
    --resource-group rg-my-app-prod-eastus \
    --target-resource-id $(az vm show \
        --resource-group rg-my-app-prod-eastus \
        --name vm-my-app-prod-001 --query id -o tsv) \
    --auth-type ssh-key \
    --username azureuser \
    --ssh-key ~/.ssh/id_rsa

# Serial console access (for locked-out VMs)
az vm boot-diagnostics enable \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --storage $(az storage account show \
        --resource-group rg-my-app-prod-eastus \
        --name stdiagsprodeastus --query primaryEndpoints.blob -o tsv)
```

---

## VM Lifecycle Operations

```bash
# Start / stop / restart
az vm start --resource-group rg-my-app-prod-eastus --name vm-my-app-prod-001
az vm stop --resource-group rg-my-app-prod-eastus --name vm-my-app-prod-001
az vm restart --resource-group rg-my-app-prod-eastus --name vm-my-app-prod-001

# Deallocate (stopped + compute released — no compute billing)
az vm deallocate --resource-group rg-my-app-prod-eastus --name vm-my-app-prod-001

# Get VM status
az vm get-instance-view \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --query "instanceView.statuses[1].displayStatus"

# List all VMs with status
az vm list \
    --show-details \
    --query '[*].{Name:name,RG:resourceGroup,Size:hardwareProfile.vmSize,State:powerState}' \
    --output table

# Resize a VM (requires deallocation first)
az vm deallocate --resource-group rg-my-app-prod-eastus --name vm-my-app-prod-001
az vm resize \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --size Standard_D4s_v5
az vm start --resource-group rg-my-app-prod-eastus --name vm-my-app-prod-001
```

---

## Managed Disks

```bash
# List OS disk for a VM
az vm show \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --query storageProfile.osDisk

# Add a data disk
az vm disk attach \
    --resource-group rg-my-app-prod-eastus \
    --vm-name vm-my-app-prod-001 \
    --name disk-data-prod-001 \
    --size-gb 512 \
    --sku Premium_LRS \
    --new

# Create and attach an existing disk
az disk create \
    --resource-group rg-my-app-prod-eastus \
    --name disk-data-prod-002 \
    --size-gb 1024 \
    --sku Premium_LRS \
    --zone 1

az vm disk attach \
    --resource-group rg-my-app-prod-eastus \
    --vm-name vm-my-app-prod-001 \
    --disk $(az disk show --resource-group rg-my-app-prod-eastus --name disk-data-prod-002 --query id -o tsv)

# Resize a data disk (must be detached or VM deallocated)
az disk update \
    --resource-group rg-my-app-prod-eastus \
    --name disk-data-prod-001 \
    --size-gb 1024
```

### Disk SKUs

| SKU | Use case | IOPS |
|-----|---------|------|
| Premium_LRS | Production VMs, databases | 120–20,000 |
| Premium_ZRS | Zone-redundant production | 120–20,000 |
| StandardSSD_LRS | Web servers, lightly loaded apps | 500–6,000 |
| Standard_LRS | Dev/test, infrequently accessed | 500–2,000 |
| UltraSSD_LRS | Latency-sensitive, high-perf databases | Configurable up to 160,000 |

---

## Availability Options

### Availability Zones

Deploy VMs across physically separate datacenters within a region.

```bash
# Create VMs in different zones
az vm create ... --zone 1   # AZ 1
az vm create ... --zone 2   # AZ 2
az vm create ... --zone 3   # AZ 3
```

### Availability Sets (legacy — prefer zones)

Groups VMs across separate fault domains (different racks) and update domains.

```bash
az availability-set create \
    --resource-group rg-my-app-prod-eastus \
    --name avail-set-my-app-prod \
    --platform-fault-domain-count 3 \
    --platform-update-domain-count 5 \
    --sku Aligned   # Required for managed disks

az vm create ... --availability-set avail-set-my-app-prod
```

---

## VM Extensions

Run scripts and install software on VMs after provisioning.

```bash
# Run a shell script (Linux)
az vm extension set \
    --resource-group rg-my-app-prod-eastus \
    --vm-name vm-my-app-prod-001 \
    --name CustomScript \
    --publisher Microsoft.Azure.Extensions \
    --settings '{"commandToExecute":"apt-get update && apt-get install -y nginx"}'

# Enable Azure Monitor Agent
az vm extension set \
    --resource-group rg-my-app-prod-eastus \
    --vm-name vm-my-app-prod-001 \
    --name AzureMonitorLinuxAgent \
    --publisher Microsoft.Azure.Monitor \
    --version 1.0 \
    --enable-auto-upgrade true

# Enable Microsoft Defender for Endpoint (MDE)
az vm extension set \
    --resource-group rg-my-app-prod-eastus \
    --vm-name vm-my-app-prod-001 \
    --name MDE.Linux \
    --publisher Microsoft.Azure.AzureDefenderForServers
```

---

## Spot VMs

Up to 90% cheaper than regular VMs — but can be evicted when Azure needs capacity.

```bash
az vm create \
    --resource-group rg-my-app-dev-eastus \
    --name vm-batch-spot-001 \
    --image Ubuntu2204 \
    --size Standard_D4s_v5 \
    --priority Spot \
    --eviction-policy Deallocate \   # Deallocate | Delete
    --max-price -1 \                 # -1 = pay up to the pay-as-you-go price
    --admin-username azureuser \
    --ssh-key-values ~/.ssh/id_rsa.pub
```

---

## References

- [Azure VM documentation](https://docs.microsoft.com/azure/virtual-machines/)
- [VM sizes](https://docs.microsoft.com/azure/virtual-machines/sizes)
- [Managed disks](https://docs.microsoft.com/azure/virtual-machines/managed-disks-overview)
- [Azure Bastion](https://docs.microsoft.com/azure/bastion/)

---

← [Previous: Azure Compute](./README.md) | [Home](../../README.md) | [Next: VMSS →](./vmss.md)
