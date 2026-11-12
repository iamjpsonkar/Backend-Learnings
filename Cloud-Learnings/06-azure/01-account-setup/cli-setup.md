← [Previous: Billing & Budgets](./billing-budgets.md) | [Home](../../README.md) | [Next: Subscriptions →](./subscriptions.md)

---

# Azure CLI Setup

---

## Installation

```bash
# macOS
brew update && brew install azure-cli

# Ubuntu / Debian
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# RHEL / CentOS / Fedora
sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
sudo dnf install azure-cli

# Windows (PowerShell)
winget install Microsoft.AzureCLI

# Docker (no local install)
docker run -it mcr.microsoft.com/azure-cli

# Verify
az version
az --version
```

---

## Authentication

```bash
# Interactive login (browser)
az login

# Login to a specific tenant
az login --tenant my-org.onmicrosoft.com

# Login with service principal + client secret
az login \
    --service-principal \
    --tenant $TENANT_ID \
    --username $APP_ID \
    --password $CLIENT_SECRET

# Login with service principal + certificate
az login \
    --service-principal \
    --tenant $TENANT_ID \
    --username $APP_ID \
    --password @path/to/cert.pem

# Login with managed identity (inside Azure VM or container)
az login --identity
az login --identity --username $USER_ASSIGNED_CLIENT_ID  # Specific UAMI

# Device code login (no browser — headless servers)
az login --use-device-code

# Check who you are logged in as
az account show
az ad signed-in-user show --query '{Name:displayName,UPN:userPrincipalName}'
```

---

## Subscription Management

```bash
# List all subscriptions you have access to
az account list --output table
az account list --query '[*].{Name:name,ID:id,State:state,Default:isDefault}' --output table

# Set default subscription
az account set --subscription "my-production"
az account set --subscription $SUBSCRIPTION_ID

# Verify active subscription
az account show --query '{Name:name,ID:id,Tenant:tenantId}'

# Show available regions
az account list-locations \
    --query '[?metadata.regionType==`Physical`].{Name:name,DisplayName:displayName}' \
    --output table | sort
```

---

## CLI Configuration

```bash
# View current config
az configure --list-defaults

# Set defaults (avoids repeating --resource-group and --location)
az configure --defaults location=eastus
az configure --defaults group=rg-my-app-prod-eastus

# Set default output format (table | json | yaml | tsv | none)
az configure --defaults output=table

# Config stored at: ~/.azure/config

# Use a named configuration profile (for multiple accounts)
az account set --subscription prod-account
az configure --defaults group=rg-prod location=eastus
```

### Config File (`~/.azure/config`)

```ini
[defaults]
location = eastus
group = rg-my-app-prod-eastus
output = table

[logging]
enable_log_file = yes
log_dir = /home/user/.azure/logs
```

---

## Useful CLI Patterns

```bash
# Query with JMESPath
az vm list --query '[*].{Name:name,RG:resourceGroup,Size:hardwareProfile.vmSize,State:powerState}' \
    --output table

# Tab-delimited output (for scripting)
az account list --query '[*].id' --output tsv

# Wait for a resource to finish deploying
az deployment group wait \
    --name my-deployment \
    --resource-group rg-my-app-prod-eastus \
    --created

# Use --no-wait for fire-and-forget
az vm deallocate \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --no-wait

# Debug mode — shows HTTP requests
az vm list --debug 2>&1 | head -50

# Verbose mode
az group create --name rg-test --location eastus --verbose
```

---

## Azure Cloud Shell

Cloud Shell is a browser-based shell (Bash or PowerShell) available at shell.azure.com or from the Azure Portal toolbar. It comes pre-installed with:

- Azure CLI (`az`)
- Azure PowerShell (`Az`)
- Terraform
- kubectl, helm
- git, jq, vim

```bash
# Cloud Shell automatically authenticates to your Azure subscription
# No login needed — it uses your portal session

# Cloud Shell storage: ~/clouddrive is persisted to an Azure Files share
ls ~/clouddrive

# Upload/download files via the toolbar
# Or mount from Azure Files:
clouddrive mount --subscription $SUBSCRIPTION_ID \
    --resource-group rg-cloudshell \
    --storage-account stcloudshell \
    --file-share cloudshell
```

---

## Azure PowerShell

Alternative to the CLI for Windows administrators and automation.

```powershell
# Install
Install-Module -Name Az -AllowClobber -Force

# Login
Connect-AzAccount
Connect-AzAccount -TenantId $TenantId

# Set subscription
Set-AzContext -SubscriptionId $SubscriptionId

# Common commands
Get-AzResourceGroup | Format-Table
Get-AzVM | Select-Object Name,ResourceGroupName,Location
New-AzResourceGroup -Name "rg-test" -Location "eastus"
```

---

## CLI Extension Management

```bash
# List installed extensions
az extension list --output table

# Add useful extensions
az extension add --name account         # Subscription management
az extension add --name aks-preview     # AKS preview features
az extension add --name application-insights
az extension add --name containerapp
az extension add --name resource-graph  # az graph commands

# Update extensions
az extension update --name aks-preview

# Remove extension
az extension remove --name aks-preview
```

---

## Environment Variables

These variables are picked up by Azure CLI and SDKs automatically:

```bash
# Service principal authentication
export AZURE_TENANT_ID="..."
export AZURE_CLIENT_ID="..."
export AZURE_CLIENT_SECRET="..."    # Or AZURE_CLIENT_CERTIFICATE_PATH

# Subscription context
export AZURE_SUBSCRIPTION_ID="..."

# Azure environment (for sovereign clouds)
export AZURE_CLOUD_NAME="AzureCloud"  # AzureCloud | AzureChinaCloud | AzureUSGovernment
```

---

## References

- [Azure CLI documentation](https://docs.microsoft.com/cli/azure/)
- [Azure CLI query (JMESPath)](https://docs.microsoft.com/cli/azure/query-azure-cli)
- [Azure Cloud Shell](https://docs.microsoft.com/azure/cloud-shell/overview)
- [Azure PowerShell](https://docs.microsoft.com/powershell/azure/)

---

← [Previous: Billing & Budgets](./billing-budgets.md) | [Home](../../README.md) | [Next: Subscriptions →](./subscriptions.md)
