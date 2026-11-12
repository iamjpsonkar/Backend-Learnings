← [Previous: Azure IaC](./README.md) | [Home](../../README.md) | [Next: Terraform on Azure →](./terraform-azure.md)

---

# Azure Bicep

Bicep is Azure's domain-specific language for Infrastructure as Code. It compiles to ARM JSON, supports modular design, and has first-class Azure tooling (VS Code extension, `what-if` deployments, schema validation).

---

## Bicep vs Terraform vs ARM

| Feature | Bicep | Terraform | ARM JSON |
|---------|-------|-----------|----------|
| Language | DSL (Azure-only) | HCL (multi-cloud) | JSON |
| State management | Azure Resource Manager | State file (local/remote) | ARM |
| Multi-cloud | No | Yes | No |
| Modules | Yes | Yes | Linked templates |
| Preview changes | `--what-if` | `plan` | `--what-if` |
| Drift detection | Limited | Yes (`plan`) | Limited |
| Tooling | Azure CLI, VS Code | Terraform CLI | Azure CLI |

---

## Bicep Syntax Basics

```bicep
// Parameters
@description('The environment name.')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('The Azure region.')
param location string = resourceGroup().location

@minLength(3)
@maxLength(24)
param storageAccountName string

@secure()
param adminPassword string

// Variables
var storageSkuMap = {
  dev: 'Standard_LRS'
  staging: 'Standard_GRS'
  prod: 'Standard_RAGRS'
}
var storageSku = storageSkuMap[environment]
var tags = {
  Environment: environment
  ManagedBy: 'Bicep'
  DeployedAt: utcNow()
}
```

---

## Full Example — Web App + Storage

```bicep
// main.bicep
@description('Environment: dev, staging, prod')
param environment string = 'prod'

@description('Azure region')
param location string = resourceGroup().location

@description('Application name')
param appName string = 'my-app'

var prefix = '${appName}-${environment}'
var tags = {
  Environment: environment
  Service: appName
  ManagedBy: 'Bicep'
}

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'st${replace(prefix, '-', '')}eastus'
  location: location
  tags: tags
  sku: {
    name: environment == 'prod' ? 'Standard_RAGRS' : 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: 'plan-${prefix}'
  location: location
  tags: tags
  sku: {
    name: environment == 'prod' ? 'P2v3' : 'B1'
    tier: environment == 'prod' ? 'PremiumV3' : 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true  // Required for Linux
  }
}

// App Service
resource webApp 'Microsoft.Web/sites@2022-09-01' = {
  name: 'app-${prefix}'
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'STORAGE_ACCOUNT_URL'
          value: storageAccount.properties.primaryEndpoints.blob
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
      ]
    }
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${prefix}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    SamplingPercentage: environment == 'prod' ? 10 : 100
  }
}

// Log Analytics Workspace reference (existing)
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = {
  name: 'log-platform-prod-eastus'
  scope: resourceGroup('rg-platform-monitoring-eastus')
}

// Grant App Service storage access (RBAC)
resource storageBlobContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, webApp.id, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')  // Storage Blob Data Contributor
    principalId: webApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output webAppUrl string = 'https://${webApp.properties.defaultHostName}'
output storageAccountName string = storageAccount.name
output appInsightsConnectionString string = appInsights.properties.ConnectionString
```

---

## Modules

```bicep
// modules/vnet.bicep
@description('VNet name')
param vnetName string

@description('Address prefix')
param addressPrefix string = '10.0.0.0/16'

param location string = resourceGroup().location
param tags object = {}

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [addressPrefix]
    }
    subnets: [
      {
        name: 'snet-app'
        properties: { addressPrefix: '10.0.10.0/24' }
      }
      {
        name: 'snet-data'
        properties: { addressPrefix: '10.0.20.0/28' }
      }
    ]
  }
}

output vnetId string = vnet.id
output appSubnetId string = vnet.properties.subnets[0].id
```

```bicep
// main.bicep — consume the module
module network './modules/vnet.bicep' = {
  name: 'vnet-deployment'
  params: {
    vnetName: 'vnet-${prefix}'
    addressPrefix: '10.0.0.0/16'
    tags: tags
  }
}

// Use module output
resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  // ...
  properties: {
    virtualNetworkSubnetId: network.outputs.appSubnetId
  }
}
```

---

## Deploying Bicep

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"

# Preview changes (what-if)
az deployment group what-if \
    --resource-group $RESOURCE_GROUP \
    --template-file main.bicep \
    --parameters environment=prod appName=my-app

# Deploy
az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --name "deploy-$(date +%Y%m%d-%H%M%S)" \
    --template-file main.bicep \
    --parameters environment=prod appName=my-app \
    --confirm-with-what-if

# Deploy using a parameters file
# main.bicepparam:
# using 'main.bicep'
# param environment = 'prod'
# param appName = 'my-app'

az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file main.bicep \
    --parameters main.bicepparam

# View deployment history
az deployment group list \
    --resource-group $RESOURCE_GROUP \
    --output table

# Check deployment outputs
az deployment group show \
    --resource-group $RESOURCE_GROUP \
    --name "deploy-20240615-120000" \
    --query properties.outputs
```

---

## Bicep Registry (Shared Modules)

```bash
# Publish a module to an ACR-backed Bicep registry
az bicep publish \
    --file modules/vnet.bicep \
    --target "br:acrmyappprodeastus.azurecr.io/bicep/modules/vnet:1.0.0"

# Consume from registry in main.bicep:
# module network 'br:acrmyappprodeastus.azurecr.io/bicep/modules/vnet:1.0.0' = { ... }
```

---

## References

- [Bicep documentation](https://docs.microsoft.com/azure/azure-resource-manager/bicep/)
- [Bicep playground](https://aka.ms/bicepdemo)
- [Bicep registry](https://docs.microsoft.com/azure/azure-resource-manager/bicep/private-module-registry)
- [ARM template reference](https://docs.microsoft.com/azure/templates/)

---

← [Previous: Azure IaC](./README.md) | [Home](../../README.md) | [Next: Terraform on Azure →](./terraform-azure.md)
