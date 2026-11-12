← [Previous: Key Vault](./key-vault.md) | [Home](../../README.md) | [Next: Azure Observability →](../10-observability/README.md)

---

# Microsoft Defender for Cloud

Defender for Cloud is Azure's cloud security posture management (CSPM) and cloud workload protection platform (CWPP). It provides security recommendations, threat detection, vulnerability assessment, and compliance reporting.

---

## Two Pillars

| Pillar | What it does |
|--------|-------------|
| **CSPM** — Cloud Security Posture Management | Continuously assess resources against security benchmarks, provide hardening recommendations, secure score |
| **CWPP** — Cloud Workload Protection | Real-time threat detection for VMs, containers, databases, storage, Key Vault, App Service |

---

## Defender Plans

Each plan protects a specific resource type (granular billing):

| Plan | Resource Type | Key Capabilities |
|------|--------------|-----------------|
| Defender for Servers | VMs, Arc servers | JIT VM access, vulnerability scanning, file integrity monitoring |
| Defender for Containers | AKS, ACR, Arc K8s | Image scanning, runtime threat detection, K8s audit log analysis |
| Defender for Storage | Storage accounts | Malware scanning, anomalous access detection |
| Defender for SQL | Azure SQL, SQL on VM | SQL injection detection, anomalous activity |
| Defender for Key Vault | Key Vault | Suspicious access, unusual geo, high-rate queries |
| Defender for App Service | App Service, Functions | Web attack detection, lateral movement |
| Defender for Resource Manager | ARM operations | Suspicious ARM operations, privilege escalation |
| Defender CSPM (Enhanced) | Subscription-wide | Attack paths, governance rules, data security posture |

---

## Enabling Defender Plans

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Enable individual plans
az security pricing create \
    --name VirtualMachines \
    --tier Standard \
    --subscription $SUBSCRIPTION_ID

az security pricing create \
    --name Containers \
    --tier Standard

az security pricing create \
    --name StorageAccounts \
    --tier Standard

az security pricing create \
    --name KeyVaults \
    --tier Standard

az security pricing create \
    --name SqlServers \
    --tier Standard

az security pricing create \
    --name AppServices \
    --tier Standard

az security pricing create \
    --name Arm \
    --tier Standard

# Enable auto-provisioning of monitoring agents
az security auto-provisioning-setting update \
    --name mma \
    --auto-provision On

# View all pricing tiers
az security pricing list \
    --query '[*].{Plan:name,Tier:pricingTier}' \
    --output table
```

---

## Secure Score

The Secure Score (0–100) measures your overall security posture. Each recommendation has a score impact.

```bash
# Get current secure score
az security secure-scores list \
    --query '[*].{Score:score.current,Max:score.max,Percentage:score.percentage}' \
    --output table

# Get recommendations sorted by score impact
az security task list \
    --query '[*].{Task:name,State:state,Severity:properties.resourceDetails.Source}' \
    --output table

# Get security assessments
az security assessment list \
    --query '[?properties.status.code==`Unhealthy`].{Name:displayName,Severity:properties.metadata.severity}' \
    --output table
```

---

## Just-In-Time (JIT) VM Access

JIT closes RDP (3389) and SSH (22) by default and opens them for a limited time on request.

```bash
# Enable JIT for a VM
az security jit-policy create \
    --resource-group rg-my-app-prod-eastus \
    --name default \
    --location eastus \
    --virtual-machines '[{
        "id": "/subscriptions/'$SUBSCRIPTION_ID'/resourceGroups/rg-my-app-prod-eastus/providers/Microsoft.Compute/virtualMachines/vm-my-app-prod-001",
        "ports": [
            {
                "number": 22,
                "protocol": "TCP",
                "allowedSourceAddressPrefix": "My IP",
                "maxRequestAccessDuration": "PT3H"
            }
        ]
    }]'

# Request JIT access (get temporary SSH access)
az security jit-policy initiate \
    --resource-group rg-my-app-prod-eastus \
    --name default \
    --virtual-machines '[{
        "id": "/subscriptions/'$SUBSCRIPTION_ID'/resourceGroups/rg-my-app-prod-eastus/providers/Microsoft.Compute/virtualMachines/vm-my-app-prod-001",
        "ports": [{"number": 22, "duration": "PT2H", "allowedSourceAddressPrefix": "203.0.113.10/32"}]
    }]'
```

---

## Security Alerts

```bash
# List active security alerts
az security alert list \
    --location eastus \
    --query '[?properties.status==`Active`].{Title:properties.alertDisplayName,Severity:properties.severity,Time:properties.timeGeneratedUtc,Resource:properties.compromisedEntity}' \
    --output table

# Dismiss an alert
az security alert update \
    --location eastus \
    --name "alert-id-here" \
    --status Dismissed

# Export alerts to Log Analytics (via Defender continuous export)
az security export-settings create \
    --name LogAnalytics \
    --setting-type DataExportSettings \
    --is-enabled true \
    --workspace-id $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus --query id -o tsv)
```

---

## Regulatory Compliance

Defender for Cloud maps your resources to compliance frameworks (PCI-DSS, ISO 27001, SOC 2, CIS).

```bash
# List compliance standards assigned to a subscription
az security regulatory-compliance-standards list \
    --query '[*].{Standard:name,State:state,Passed:passedControls,Failed:failedControls}' \
    --output table

# Get controls for a standard
az security regulatory-compliance-controls list \
    --standard-name "CIS-Azure-Foundations-Benchmark" \
    --query '[?state==`Failed`].{Control:name,Description:description}' \
    --output table
```

---

## Defender for Containers — AKS

```bash
# View container-specific recommendations
az security assessment list \
    --query '[?properties.resourceDetails.resourceType==`Microsoft.ContainerService/managedClusters`]
             .{Name:displayName,Status:properties.status.code,Severity:properties.metadata.severity}' \
    --output table

# Enable Defender for Containers profile on AKS (installs Defender DaemonSet)
az aks update \
    --resource-group rg-my-app-prod-eastus \
    --name aks-my-app-prod-eastus-001 \
    --enable-defender
```

---

## Microsoft Sentinel Integration

Defender for Cloud alerts can be forwarded to Microsoft Sentinel for SIEM correlation.

```bash
# Create Log Analytics workspace for Sentinel
az monitor log-analytics workspace create \
    --resource-group rg-platform-monitoring-eastus \
    --workspace-name log-sentinel-prod-eastus \
    --location eastus \
    --sku PerGB2018

# Enable Sentinel on the workspace
az sentinel onboarding-state create \
    --resource-group rg-platform-monitoring-eastus \
    --workspace-name log-sentinel-prod-eastus \
    --name default

# Connect Defender alerts to Sentinel via data connector
# (Done in Azure Portal: Sentinel → Data connectors → Microsoft Defender for Cloud)
```

---

## References

- [Defender for Cloud documentation](https://docs.microsoft.com/azure/defender-for-cloud/)
- [Just-in-time VM access](https://docs.microsoft.com/azure/defender-for-cloud/just-in-time-access-overview)
- [Secure score](https://docs.microsoft.com/azure/defender-for-cloud/secure-score-access-and-track)
- [Defender for Containers](https://docs.microsoft.com/azure/defender-for-cloud/defender-for-containers-introduction)

---

← [Previous: Key Vault](./key-vault.md) | [Home](../../README.md) | [Next: Azure Observability →](../10-observability/README.md)
