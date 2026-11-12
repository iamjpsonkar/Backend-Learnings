← [Previous: Application Insights](../10-observability/application-insights.md) | [Home](../../README.md) | [Next: Bicep →](./bicep.md)

---

# Azure Infrastructure as Code

---

## Tool Selection

| Tool | AWS Equivalent | Use Case |
|------|----------------|---------|
| **Bicep** | CloudFormation | Azure-native IaC — recommended for Azure-only deployments |
| **ARM Templates** | CloudFormation (raw JSON) | Low-level JSON format Bicep compiles to; use for compatibility |
| **Terraform (Azure provider)** | Terraform (AWS provider) | Multi-cloud or existing Terraform workflows |
| **Azure Developer CLI (azd)** | AWS SAM / CDK | End-to-end developer workflow: provision + deploy + monitor |
| **Pulumi** | CDK | General-purpose IaC with real programming languages |

---

## Bicep

Bicep is a domain-specific language that compiles to ARM JSON. It provides type safety, modularity, and cleaner syntax than raw ARM.

### Install and Setup

```bash
# Install Bicep CLI
az bicep install
az bicep version

# Compile Bicep to ARM (for inspection or deployment without az bicep)
az bicep build --file main.bicep --outfile main.json

# Decompile existing ARM template to Bicep (best-effort)
az bicep decompile --file existing.json
```

### Core Bicep File — main.bicep

```bicep
// main.bicep — deploy a Function App with Storage, App Insights, and Key Vault
targetScope = 'resourceGroup'

@description('Deployment environment (dev, staging, production)')
@allowed(['dev', 'staging', 'production'])
param environment string

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Base name used to build all resource names')
@minLength(3)
@maxLength(10)
param appName string

var prefix = '${appName}-${environment}'
var tags = {
  Environment: environment
  Application: appName
  ManagedBy: 'Bicep'
}

// ─── Storage Account ─────────────────────────────────────────────────────────
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'st${replace(prefix, '-', '')}eastus'
  location: location
  tags: tags
  sku: {
    name: environment == 'production' ? 'Standard_ZRS' : 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

// ─── Log Analytics Workspace ──────────────────────────────────────────────────
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'law-${prefix}-eastus'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: environment == 'production' ? 90 : 30
  }
}

// ─── Application Insights ─────────────────────────────────────────────────────
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${prefix}-eastus'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    IngestionMode: 'LogAnalytics'
  }
}

// ─── App Service Plan (Consumption) ──────────────────────────────────────────
resource hostingPlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: 'asp-${prefix}-eastus'
  location: location
  tags: tags
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  kind: 'functionapp'
  properties: {
    reserved: true  // Linux
  }
}

// ─── Function App ─────────────────────────────────────────────────────────────
resource functionApp 'Microsoft.Web/sites@2022-09-01' = {
  name: 'func-${prefix}-eastus'
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: hostingPlan.id
    siteConfig: {
      pythonVersion: '3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
      ]
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
    httpsOnly: true
  }
}

// ─── Outputs ──────────────────────────────────────────────────────────────────
output functionAppName string = functionApp.name
output functionAppHostname string = functionApp.properties.defaultHostName
output storageAccountName string = storageAccount.name
output appInsightsConnectionString string = appInsights.properties.ConnectionString
```

### Bicep Modules

```bicep
// modules/keyvault.bicep — reusable Key Vault module
@description('Key Vault name')
param vaultName string

@description('Azure region')
param location string

@description('Object ID of the principal to grant Key Vault Administrator')
param adminObjectId string

param tags object = {}

resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: vaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true       // RBAC model (not access policies)
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'Disabled'
  }
}

// Grant admin role
resource adminRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, adminObjectId, 'Key Vault Administrator')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '00482a5a-887f-4fb3-b363-3b7fe8e74483'  // Key Vault Administrator built-in role ID
    )
    principalId: adminObjectId
    principalType: 'User'
  }
}

output keyVaultId string = keyVault.id
output keyVaultUri string = keyVault.properties.vaultUri
```

```bicep
// Reference module from main.bicep
module keyVault 'modules/keyvault.bicep' = {
  name: 'deploy-keyvault'
  params: {
    vaultName: 'kv-${prefix}-eastus'
    location: location
    adminObjectId: '00000000-0000-0000-0000-000000000000'  // set via parameter
    tags: tags
  }
}
```

### Deploy Bicep

```bash
RESOURCE_GROUP="rg-my-app-production"

# Validate without deploying
az deployment group validate \
    --resource-group $RESOURCE_GROUP \
    --template-file main.bicep \
    --parameters environment=production appName=myapp

# What-if (preview changes before applying)
az deployment group what-if \
    --resource-group $RESOURCE_GROUP \
    --template-file main.bicep \
    --parameters environment=production appName=myapp

# Deploy
az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --name "deploy-$(date +%Y%m%d-%H%M%S)" \
    --template-file main.bicep \
    --parameters environment=production appName=myapp \
    --output table

# Deploy with a parameters file
az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file main.bicep \
    --parameters @parameters.production.json

# Check deployment status
az deployment group show \
    --resource-group $RESOURCE_GROUP \
    --name deploy-20240601-120000 \
    --query '{Status:properties.provisioningState,Duration:properties.duration}'
```

### parameters.production.json

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environment": {
      "value": "production"
    },
    "appName": {
      "value": "myapp"
    },
    "location": {
      "value": "eastus"
    }
  }
}
```

---

## Terraform on Azure

### Remote State Setup

```bash
# Create backend storage (run once)
BACKEND_RG="rg-terraform-state"
BACKEND_SA="sttfstatemyorg"
BACKEND_CONTAINER="tfstate"

az group create --name $BACKEND_RG --location eastus

az storage account create \
    --resource-group $BACKEND_RG \
    --name $BACKEND_SA \
    --sku Standard_ZRS \
    --kind StorageV2 \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false \
    --https-only true

az storage container create \
    --account-name $BACKEND_SA \
    --name $BACKEND_CONTAINER \
    --auth-mode login

# Enable versioning (protects against accidental state deletion)
az storage account blob-service-properties update \
    --account-name $BACKEND_SA \
    --resource-group $BACKEND_RG \
    --enable-versioning true
```

### versions.tf

```hcl
terraform {
  required_version = ">= 1.7"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "sttfstatemyorg"
    container_name       = "tfstate"
    key                  = "my-app/production.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }

  # Authentication: uses environment variables or managed identity
  # ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_TENANT_ID, ARM_SUBSCRIPTION_ID
  # Or: use_oidc = true for GitHub Actions OIDC (no client secret)
}
```

### variables.tf

```hcl
variable "environment" {
  description = "Deployment environment"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be one of: dev, staging, production"
  }
}

variable "location" {
  description = "Azure region for primary deployment"
  type        = string
  default     = "eastus"
}

variable "app_name" {
  description = "Short application name (3-10 chars, lowercase, alphanumeric)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,10}$", var.app_name))
    error_message = "app_name must be 3-10 lowercase alphanumeric characters"
  }
}

variable "address_space" {
  description = "VNet address space CIDR"
  type        = string
  default     = "10.0.0.0/16"
}
```

### main.tf

```hcl
locals {
  prefix = "${var.app_name}-${var.environment}"
  common_tags = {
    Environment = var.environment
    Application = var.app_name
    ManagedBy   = "Terraform"
    UpdatedAt   = timestamp()
  }
}

data "azurerm_client_config" "current" {}

# ─── Resource Group ────────────────────────────────────────────────────────────
resource "azurerm_resource_group" "main" {
  name     = "rg-${local.prefix}-${var.location}"
  location = var.location
  tags     = local.common_tags
}

# ─── Virtual Network ───────────────────────────────────────────────────────────
resource "azurerm_virtual_network" "main" {
  name                = "vnet-${local.prefix}-${var.location}-001"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  address_space       = [var.address_space]
  tags                = local.common_tags
}

resource "azurerm_subnet" "subnets" {
  for_each = {
    public           = { cidr = cidrsubnet(var.address_space, 8, 1) }
    app              = { cidr = cidrsubnet(var.address_space, 8, 11) }
    data             = { cidr = cidrsubnet(var.address_space, 8, 21) }
    private-endpoints = { cidr = cidrsubnet(var.address_space, 8, 31) }
  }

  name                 = "snet-${each.key}"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [each.value.cidr]
}

# ─── Log Analytics Workspace ───────────────────────────────────────────────────
resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${local.prefix}-${var.location}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "production" ? 90 : 30
  tags                = local.common_tags
}

# ─── Application Insights ──────────────────────────────────────────────────────
resource "azurerm_application_insights" "main" {
  name                = "appi-${local.prefix}-${var.location}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = local.common_tags
}

# ─── Key Vault ─────────────────────────────────────────────────────────────────
resource "random_id" "kv_suffix" {
  byte_length = 3
}

resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.prefix}-${random_id.kv_suffix.hex}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  soft_delete_retention_days = 90
  purge_protection_enabled   = true
  tags                       = local.common_tags
}
```

### outputs.tf

```hcl
output "resource_group_name" {
  description = "Name of the primary resource group"
  value       = azurerm_resource_group.main.name
}

output "vnet_id" {
  description = "Virtual network resource ID"
  value       = azurerm_virtual_network.main.id
}

output "app_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

output "key_vault_uri" {
  description = "Key Vault URI for secret retrieval"
  value       = azurerm_key_vault.main.vault_uri
}
```

### Terraform Workflow

```bash
# Authenticate (CI/CD — GitHub Actions OIDC)
export ARM_CLIENT_ID="$AZURE_CLIENT_ID"
export ARM_TENANT_ID="$AZURE_TENANT_ID"
export ARM_SUBSCRIPTION_ID="$AZURE_SUBSCRIPTION_ID"
export ARM_USE_OIDC=true

# Init (downloads provider, configures backend)
terraform init

# Validate configuration
terraform validate

# Format check
terraform fmt -check -recursive

# Plan — save to file for reproducible apply
terraform plan \
    -var="environment=production" \
    -var="app_name=myapp" \
    -out=tfplan

# Review plan output, then apply
terraform apply tfplan

# Workspaces — isolate environments with same config
terraform workspace new staging
terraform workspace select production
terraform workspace list

# Destroy (use with care — prompts for confirmation)
terraform destroy \
    -var="environment=production" \
    -var="app_name=myapp"
```

### Terraform Module Pattern

```
modules/
└── azure-function-app/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    └── README.md
```

```hcl
# Calling a module from root main.tf
module "function_app" {
  source = "./modules/azure-function-app"

  resource_group_name     = azurerm_resource_group.main.name
  location                = var.location
  prefix                  = local.prefix
  storage_account_name    = "st${replace(local.prefix, "-", "")}${var.location}"
  app_insights_connection = azurerm_application_insights.main.connection_string
  tags                    = local.common_tags
}
```

---

## GitHub Actions CI/CD — Bicep Deploy

```yaml
# .github/workflows/deploy-bicep.yml
name: Deploy Infrastructure

on:
  push:
    branches: [main]
    paths: ["infra/**"]
  workflow_dispatch:
    inputs:
      environment:
        description: Target environment
        required: true
        default: staging
        type: choice
        options: [dev, staging, production]

permissions:
  id-token: write   # Required for OIDC authentication
  contents: read

jobs:
  deploy:
    name: Deploy (${{ github.event.inputs.environment || 'staging' }})
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment || 'staging' }}

    steps:
      - uses: actions/checkout@v4

      - name: Azure Login (OIDC — no stored secrets)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Bicep What-If
        uses: azure/arm-deploy@v2
        with:
          resourceGroupName: rg-myapp-${{ github.event.inputs.environment || 'staging' }}-eastus
          template: infra/main.bicep
          parameters: infra/parameters.${{ github.event.inputs.environment || 'staging' }}.json
          deploymentMode: Validate
          additionalArguments: --what-if

      - name: Deploy Bicep
        uses: azure/arm-deploy@v2
        with:
          resourceGroupName: rg-myapp-${{ github.event.inputs.environment || 'staging' }}-eastus
          template: infra/main.bicep
          parameters: infra/parameters.${{ github.event.inputs.environment || 'staging' }}.json
          deploymentName: deploy-${{ github.run_number }}
          failOnStdErr: true
```

---

## References

- [Bicep documentation](https://docs.microsoft.com/azure/azure-resource-manager/bicep/)
- [Bicep modules](https://docs.microsoft.com/azure/azure-resource-manager/bicep/modules)
- [Terraform Azure provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Azure Developer CLI (azd)](https://docs.microsoft.com/azure/developer/azure-developer-cli/)
---

← [Previous: Application Insights](../10-observability/application-insights.md) | [Home](../../README.md) | [Next: Bicep →](./bicep.md)
