← [Previous: Bicep](./bicep.md) | [Home](../../README.md) | [Next: Azure Projects →](../12-projects/README.md)

---

# Terraform on Azure

Terraform uses the AzureRM and AzureAD providers to manage Azure resources. State is stored in Azure Blob Storage. Authentication uses a service principal or OIDC (recommended for CI/CD).

---

## Provider and Backend Configuration

```hcl
# versions.tf
terraform {
  required_version = ">= 1.6"

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
    resource_group_name  = "rg-terraform-state-prod"
    storage_account_name = "stterraformstateprod"
    container_name       = "tfstate"
    key                  = "my-app/prod/terraform.tfstate"
    use_oidc             = true  # GitHub Actions OIDC — no static credentials
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
  use_oidc = true
}

provider "azuread" {
  use_oidc = true
}
```

---

## State Backend Setup

```bash
# Create storage account for Terraform state (one-time setup)
STATE_RG="rg-terraform-state-prod"
STATE_SA="stterraformstateprod"

az group create --name $STATE_RG --location eastus

az storage account create \
    --resource-group $STATE_RG \
    --name $STATE_SA \
    --sku Standard_RAGRS \
    --kind StorageV2 \
    --https-only true \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false

# Enable versioning (protect against accidental state deletion)
az storage account blob-service-properties update \
    --resource-group $STATE_RG \
    --account-name $STATE_SA \
    --enable-versioning true \
    --enable-soft-delete true \
    --soft-delete-days 30

az storage container create \
    --account-name $STATE_SA \
    --name tfstate \
    --auth-mode login

echo "State backend ready: $STATE_SA/tfstate"
```

---

## variables.tf

```hcl
# variables.tf
variable "environment" {
  type        = string
  description = "Deployment environment"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "location" {
  type        = string
  description = "Azure region"
  default     = "eastus"
}

variable "app_name" {
  type        = string
  description = "Application name (lowercase, no hyphens)"
  validation {
    condition     = can(regex("^[a-z0-9]+$", var.app_name))
    error_message = "app_name must be lowercase alphanumeric."
  }
}

variable "admin_object_id" {
  type        = string
  description = "Object ID of the Entra ID user/group to grant admin access"
  sensitive   = false
}
```

---

## main.tf — Core Infrastructure

```hcl
# main.tf
locals {
  prefix = "${var.app_name}-${var.environment}"
  tags = {
    Environment = var.environment
    Service     = var.app_name
    ManagedBy   = "Terraform"
    Repository  = "https://github.com/my-org/my-app"
  }
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "rg-${local.prefix}-${var.location}"
  location = var.location
  tags     = local.tags
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "vnet-${local.prefix}-${var.location}-001"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  address_space       = ["10.0.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.10.0/24"]
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "snet-private-endpoints"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.30.0/24"]
}

# Network Security Group
resource "azurerm_network_security_group" "app" {
  name                = "nsg-app-${var.location}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tags                = local.tags

  security_rule {
    name                       = "Allow-HTTPS-Inbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "app" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.app.id
}

# Key Vault
resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.prefix}-${var.location}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = var.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "premium"
  enable_rbac_authorization  = true
  soft_delete_retention_days = 90
  purge_protection_enabled   = true
  tags                       = local.tags

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
  }
}

data "azurerm_client_config" "current" {}

# Key Vault RBAC — admin access
resource "azurerm_role_assignment" "kv_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.admin_object_id
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "main" {
  name                = "aks-${local.prefix}-${var.location}-001"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  dns_prefix          = "${var.app_name}-${var.environment}"
  kubernetes_version  = "1.29"
  tags                = local.tags

  default_node_pool {
    name                   = "system"
    node_count             = 3
    vm_size                = "Standard_D4s_v5"
    zones                  = ["1", "2", "3"]
    vnet_subnet_id         = azurerm_subnet.app.id
    enable_auto_scaling    = true
    min_count              = 3
    max_count              = 10
    os_disk_type           = "Ephemeral"
    only_critical_addons_enabled = true
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "cilium"
    load_balancer_sku = "standard"
  }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  monitor_metrics {}

  lifecycle {
    ignore_changes = [
      default_node_pool[0].node_count,
      kubernetes_version,
    ]
  }
}

# ACR — grant AKS pull access
resource "azurerm_container_registry" "main" {
  name                = "acr${replace(local.prefix, "-", "")}${var.location}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  sku                 = "Premium"
  admin_enabled       = false
  zone_redundancy_enabled = var.environment == "prod" ? true : false
  tags                = local.tags
}

resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}
```

---

## outputs.tf

```hcl
# outputs.tf
output "resource_group_name" {
  value       = azurerm_resource_group.main.name
  description = "Resource group name"
}

output "aks_cluster_name" {
  value       = azurerm_kubernetes_cluster.main.name
  description = "AKS cluster name"
}

output "acr_login_server" {
  value       = azurerm_container_registry.main.login_server
  description = "ACR login server"
}

output "key_vault_uri" {
  value       = azurerm_key_vault.main.vault_uri
  description = "Key Vault URI"
}

output "oidc_issuer_url" {
  value       = azurerm_kubernetes_cluster.main.oidc_issuer_url
  description = "AKS OIDC issuer URL for Workload Identity"
}
```

---

## GitHub Actions — OIDC Deployment

```yaml
# .github/workflows/terraform.yml
name: Terraform Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  id-token: write   # Required for OIDC
  contents: read

env:
  ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
  ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
  ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
  ARM_USE_OIDC: "true"

jobs:
  terraform:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./infra

    steps:
      - uses: actions/checkout@v4

      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.8.0

      - name: Terraform Init
        run: terraform init

      - name: Terraform Validate
        run: terraform validate

      - name: Terraform Plan
        run: terraform plan -var="environment=prod" -var="app_name=myapp" -out=tfplan

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: terraform apply tfplan
```

---

## References

- [AzureRM provider documentation](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Terraform backend for Azure](https://developer.hashicorp.com/terraform/language/settings/backends/azurerm)
- [GitHub Actions OIDC for Azure](https://docs.microsoft.com/azure/developer/github/connect-from-azure)

---

← [Previous: Bicep](./bicep.md) | [Home](../../README.md) | [Next: Azure Projects →](../12-projects/README.md)
