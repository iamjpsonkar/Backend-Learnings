← [Previous: Azure Observability](./README.md) | [Home](../../README.md) | [Next: Application Insights →](./application-insights.md)

---

# Azure Monitor

Azure Monitor is the unified observability platform for all Azure services. It collects metrics, logs, and traces, enables alerting, and integrates with Log Analytics for deep analysis.

---

## Architecture Overview

```
Azure Resources (VMs, AKS, App Service, Storage, ...)
      │
      ▼
┌─────────────────────────────────────────────────┐
│              Azure Monitor                      │
│  ┌─────────────┐   ┌──────────────────────────┐ │
│  │  Metrics    │   │  Log Analytics Workspace │ │
│  │ (time-series│   │  (Kusto Query Language)  │ │
│  │  data)      │   └──────────────────────────┘ │
│  └─────────────┘                                │
│  ┌─────────────────────────────────────────────┐│
│  │         Alerts & Action Groups              ││
│  └─────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
      │               │
      ▼               ▼
  Dashboards    Application Insights
                (distributed tracing)
```

---

## Metrics

Azure Monitor Metrics are time-series values emitted by Azure resources every minute by default. No configuration needed — they are collected automatically.

```bash
# List available metrics for a resource
az monitor metrics list-definitions \
    --resource $(az vm show --resource-group rg-my-app-prod-eastus --name vm-my-app-prod-001 --query id -o tsv) \
    --query '[*].{Name:name.value,Unit:unit,Description:displayDescription}' \
    --output table

# Query CPU usage for a VM (last hour)
az monitor metrics list \
    --resource $(az vm show --resource-group rg-my-app-prod-eastus --name vm-my-app-prod-001 --query id -o tsv) \
    --metric "Percentage CPU" \
    --interval PT5M \
    --start-time $(date -u -d "-1 hour" +%Y-%m-%dT%H:%MZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%MZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%MZ) \
    --aggregation Average \
    --query 'value[0].timeseries[0].data[*].{Time:timeStamp,CPU:average}' \
    --output table

# Query storage account transactions
az monitor metrics list \
    --resource $(az storage account show --name stmyappprodeastus --query id -o tsv) \
    --metric "Transactions" \
    --interval PT1H \
    --aggregation Total \
    --output table
```

---

## Log Analytics Workspace

Log Analytics stores structured logs from Azure resources, VMs, and applications. Queries use KQL (Kusto Query Language).

```bash
# Create a Log Analytics workspace
az monitor log-analytics workspace create \
    --resource-group rg-platform-monitoring-eastus \
    --workspace-name log-platform-prod-eastus \
    --location eastus \
    --sku PerGB2018 \
    --retention-time 90 \
    --tags Environment=production Team=platform

# Get workspace ID and key (for agent configuration)
WS_ID=$(az monitor log-analytics workspace show \
    --resource-group rg-platform-monitoring-eastus \
    --workspace-name log-platform-prod-eastus \
    --query customerId -o tsv)

WS_KEY=$(az monitor log-analytics workspace get-shared-keys \
    --resource-group rg-platform-monitoring-eastus \
    --workspace-name log-platform-prod-eastus \
    --query primarySharedKey -o tsv)

echo "Workspace ID: $WS_ID"
```

### Diagnostic Settings — Send Resource Logs to Log Analytics

```bash
# Send VM boot diagnostics and activity logs
az monitor diagnostic-settings create \
    --name "vm-diag-to-workspace" \
    --resource $(az vm show --resource-group rg-my-app-prod-eastus --name vm-my-app-prod-001 --query id -o tsv) \
    --workspace $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus \
        --query id -o tsv) \
    --metrics '[{"category":"AllMetrics","enabled":true,"retentionPolicy":{"enabled":false,"days":0}}]'

# Send subscription Activity Log to workspace
az monitor diagnostic-settings create \
    --name "activity-log-to-workspace" \
    --resource /subscriptions/$SUBSCRIPTION_ID \
    --workspace $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus \
        --query id -o tsv) \
    --logs '[
        {"category":"Administrative","enabled":true},
        {"category":"Security","enabled":true},
        {"category":"Alert","enabled":true},
        {"category":"Policy","enabled":true},
        {"category":"ResourceHealth","enabled":true}
    ]'

# Send AKS diagnostics
az monitor diagnostic-settings create \
    --name "aks-diag-to-workspace" \
    --resource $(az aks show --resource-group rg-my-app-prod-eastus --name aks-my-app-prod-eastus-001 --query id -o tsv) \
    --workspace $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus --query id -o tsv) \
    --logs '[
        {"category":"kube-apiserver","enabled":true},
        {"category":"kube-controller-manager","enabled":true},
        {"category":"kube-scheduler","enabled":true},
        {"category":"kube-audit","enabled":true},
        {"category":"cluster-autoscaler","enabled":true}
    ]' \
    --metrics '[{"category":"AllMetrics","enabled":true}]'
```

---

## KQL — Kusto Query Language Basics

KQL is used to query Log Analytics data.

```kql
// Basic table query
AzureActivity
| limit 100

// Filter by time and operation
AzureActivity
| where TimeGenerated > ago(24h)
| where OperationNameValue contains "write" or OperationNameValue contains "delete"
| project TimeGenerated, Caller, OperationNameValue, ResourceGroup, ActivityStatusValue
| order by TimeGenerated desc

// Top 10 error-producing resources
AzureActivity
| where ActivityStatusValue == "Failure"
| where TimeGenerated > ago(7d)
| summarize ErrorCount=count() by ResourceGroup, OperationNameValue
| top 10 by ErrorCount

// VM CPU usage from AzureMetrics
AzureMetrics
| where MetricName == "Percentage CPU"
| where TimeGenerated > ago(1h)
| where Resource == "VM-MY-APP-PROD-001"
| summarize AvgCPU=avg(Average), MaxCPU=max(Maximum) by bin(TimeGenerated, 5m)
| render timechart

// Kubernetes pod restarts
ContainerLog
| where LogEntrySource == "stderr"
| where TimeGenerated > ago(1h)
| where LogEntry contains "OOMKilled" or LogEntry contains "CrashLoop"
| project TimeGenerated, ContainerName, LogEntry
| order by TimeGenerated desc

// Count of failed sign-ins by user (Entra ID SigninLogs)
SigninLogs
| where TimeGenerated > ago(24h)
| where ResultType != 0  // Non-zero = failure
| summarize FailedSignIns=count() by UserPrincipalName, AppDisplayName, ResultDescription
| top 20 by FailedSignIns
```

```bash
# Run a KQL query from CLI
az monitor log-analytics query \
    --workspace $WS_ID \
    --analytics-query "AzureActivity | where TimeGenerated > ago(1h) | summarize count() by ActivityStatusValue" \
    --output table
```

---

## Alerts

### Metric Alert

```bash
# Alert when VM CPU exceeds 80% for 5 minutes
az monitor metrics alert create \
    --resource-group rg-platform-monitoring-eastus \
    --name "vm-cpu-high-alert" \
    --description "Alert when CPU > 80% for 5 min" \
    --scopes $(az vm show --resource-group rg-my-app-prod-eastus --name vm-my-app-prod-001 --query id -o tsv) \
    --condition "avg Percentage CPU > 80" \
    --window-size PT5M \
    --evaluation-frequency PT1M \
    --severity 2 \
    --action $(az monitor action-group show \
        --resource-group rg-platform-monitoring-eastus \
        --name ag-platform-alerts --query id -o tsv)
```

### Log Alert (KQL-based)

```bash
# Alert on any failed Azure Activity Log events
az monitor scheduled-query create \
    --resource-group rg-platform-monitoring-eastus \
    --name "activity-log-failure-alert" \
    --scopes $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus --query id -o tsv) \
    --condition-query "AzureActivity | where ActivityStatusValue == 'Failure' | where TimeGenerated > ago(5m)" \
    --condition "count > 0" \
    --evaluation-frequency PT5M \
    --window-duration PT5M \
    --severity 2 \
    --action-groups $(az monitor action-group show \
        --resource-group rg-platform-monitoring-eastus \
        --name ag-platform-alerts --query id -o tsv)
```

---

## Action Groups

Action groups define who gets notified (email, SMS, webhook, PagerDuty, Logic App) when an alert fires.

```bash
# Create an action group
az monitor action-group create \
    --resource-group rg-platform-monitoring-eastus \
    --name ag-platform-alerts \
    --short-name "platform" \
    --email-receiver name=ops email=ops@example.com \
    --email-receiver name=oncall email=oncall@example.com \
    --webhook-receiver name=pagerduty \
        service-uri="https://events.pagerduty.com/integration/xxxxx/enqueue" \
        use-common-alert-schema true

# List action groups
az monitor action-group list \
    --resource-group rg-platform-monitoring-eastus \
    --output table
```

---

## Azure Monitor Agent (AMA)

The modern replacement for the legacy MMA/OMS agent. Collects logs and metrics from VMs.

```bash
# Install AMA on a Linux VM
az vm extension set \
    --resource-group rg-my-app-prod-eastus \
    --vm-name vm-my-app-prod-001 \
    --name AzureMonitorLinuxAgent \
    --publisher Microsoft.Azure.Monitor \
    --version 1.0 \
    --enable-auto-upgrade true

# Create a Data Collection Rule to send VM logs to Log Analytics
az monitor data-collection rule create \
    --name dcr-vms-to-workspace \
    --resource-group rg-platform-monitoring-eastus \
    --location eastus \
    --rule-file dcr-definition.json  # JSON definition with data sources and destinations
```

---

## References

- [Azure Monitor documentation](https://docs.microsoft.com/azure/azure-monitor/)
- [KQL quick reference](https://docs.microsoft.com/azure/data-explorer/kql-quick-reference)
- [Log Analytics query examples](https://docs.microsoft.com/azure/azure-monitor/logs/queries)
- [Azure Monitor alerts](https://docs.microsoft.com/azure/azure-monitor/alerts/alerts-overview)
- [Application Insights](https://docs.microsoft.com/azure/azure-monitor/app/app-insights-overview)

---

← [Previous: Azure Observability](./README.md) | [Home](../../README.md) | [Next: Application Insights →](./application-insights.md)
