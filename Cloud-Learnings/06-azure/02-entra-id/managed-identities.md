← [Previous: Service Principals](./service-principals.md) | [Home](../../README.md) | [Next: Azure Networking →](../03-networking/README.md)

---

# Azure Managed Identities

Managed identities let Azure resources authenticate to other Azure services without any credentials in code or configuration. Azure handles the identity lifecycle and token refresh automatically.

---

## Types

| Type | Lifecycle | Best for |
|------|-----------|----------|
| **System-assigned** | Tied to the resource — deleted when resource is deleted | Single resource with unique identity |
| **User-assigned (UAMI)** | Independent resource — reusable across multiple Azure resources | Shared identity, AKS Workload Identity, multiple resources needing same permissions |

---

## System-Assigned Managed Identity

### Enable on Azure Resources

```bash
# Enable on a VM
az vm identity assign \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001

# Enable on an App Service
az webapp identity assign \
    --resource-group rg-my-app-prod-eastus \
    --name app-my-app-prod-eastus

# Enable on Azure Functions
az functionapp identity assign \
    --resource-group rg-my-app-prod-eastus \
    --name func-my-app-prod-eastus

# Enable on AKS (cluster-level identity, used for node operations)
az aks update \
    --resource-group rg-my-app-prod-eastus \
    --name aks-my-app-prod-eastus-001 \
    --enable-managed-identity

# Get the principal ID (object ID) after enabling
PRINCIPAL_ID=$(az vm show \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --query identity.principalId -o tsv)
```

### Grant Permissions to the Identity

```bash
# Grant Storage Blob Data Reader to the VM's identity
az role assignment create \
    --assignee-object-id $PRINCIPAL_ID \
    --assignee-principal-type ServicePrincipal \
    --role "Storage Blob Data Reader" \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus/providers/Microsoft.Storage/storageAccounts/stmyappprod

# Grant Key Vault Secrets User
az keyvault set-policy \
    --name kv-my-app-prod-eastus \
    --object-id $PRINCIPAL_ID \
    --secret-permissions get list

# Grant Key Vault with RBAC model (preferred)
az role assignment create \
    --assignee-object-id $PRINCIPAL_ID \
    --assignee-principal-type ServicePrincipal \
    --role "Key Vault Secrets User" \
    --scope $(az keyvault show --name kv-my-app-prod-eastus --query id -o tsv)
```

---

## User-Assigned Managed Identity (UAMI)

### Create and Assign

```bash
# Create a user-assigned managed identity
IDENTITY_ID=$(az identity create \
    --resource-group rg-my-app-prod-eastus \
    --name id-my-app-production \
    --query id -o tsv)

CLIENT_ID=$(az identity show --ids $IDENTITY_ID --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show --ids $IDENTITY_ID --query principalId -o tsv)

echo "Client ID: $CLIENT_ID"
echo "Principal ID: $PRINCIPAL_ID"

# Assign to a VM
az vm identity assign \
    --resource-group rg-my-app-prod-eastus \
    --name vm-my-app-prod-001 \
    --identities $IDENTITY_ID

# Assign to an App Service
az webapp identity assign \
    --resource-group rg-my-app-prod-eastus \
    --name app-my-app-prod-eastus \
    --identities $IDENTITY_ID

# Grant permissions to the UAMI
az role assignment create \
    --assignee-object-id $PRINCIPAL_ID \
    --assignee-principal-type ServicePrincipal \
    --role "Storage Blob Data Contributor" \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus
```

---

## Using Managed Identity in Code

### Python (azure-identity SDK)

```python
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

# DefaultAzureCredential works locally (via az login) and in Azure (via MI)
credential = DefaultAzureCredential()

# Key Vault — read a secret
kv_client = SecretClient(
    vault_url="https://kv-my-app-prod-eastus.vault.azure.net/",
    credential=credential
)
secret = kv_client.get_secret("db-password")
print(f"Secret value: {secret.value}")

# Blob Storage — upload a file
blob_client = BlobServiceClient(
    account_url="https://stmyappprod.blob.core.windows.net",
    credential=credential
)
container_client = blob_client.get_container_client("my-container")
container_client.upload_blob("hello.txt", b"Hello from managed identity!")

# Use specific managed identity (UAMI)
credential = ManagedIdentityCredential(client_id="<UAMI-client-id>")
```

### Using the IMDS Token Endpoint Directly (any language)

```bash
# From inside an Azure VM or container — get an access token
TOKEN=$(curl -s -H "Metadata:true" \
    "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2019-08-01&resource=https://management.azure.com/" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Use the token to call Azure APIs
curl -s -H "Authorization: Bearer $TOKEN" \
    "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups?api-version=2021-04-01" \
    | python3 -m json.tool
```

---

## AKS Workload Identity

AKS Workload Identity lets Kubernetes Pods authenticate as a UAMI using Kubernetes service account tokens — no secrets needed inside pods.

```bash
# 1. Enable OIDC issuer and Workload Identity on AKS cluster
az aks update \
    --resource-group rg-my-app-prod-eastus \
    --name aks-my-app-prod-eastus-001 \
    --enable-oidc-issuer \
    --enable-workload-identity

# 2. Get the OIDC issuer URL
OIDC_URL=$(az aks show \
    --resource-group rg-my-app-prod-eastus \
    --name aks-my-app-prod-eastus-001 \
    --query "oidcIssuerProfile.issuerUrl" -o tsv)

# 3. Create a UAMI
IDENTITY_ID=$(az identity create \
    --resource-group rg-my-app-prod-eastus \
    --name id-my-app-prod \
    --query id -o tsv)

CLIENT_ID=$(az identity show --ids $IDENTITY_ID --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show --ids $IDENTITY_ID --query principalId -o tsv)

# 4. Grant permissions to UAMI (e.g., Key Vault Secrets User)
az role assignment create \
    --assignee-object-id $PRINCIPAL_ID \
    --assignee-principal-type ServicePrincipal \
    --role "Key Vault Secrets User" \
    --scope $(az keyvault show --name kv-my-app-prod-eastus --query id -o tsv)

# 5. Create Kubernetes service account with workload identity annotation
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: production
  annotations:
    azure.workload.identity/client-id: "$CLIENT_ID"
  labels:
    azure.workload.identity/use: "true"
EOF

# 6. Create federated credential linking k8s SA to UAMI
az identity federated-credential create \
    --name my-app-federated-credential \
    --identity-name id-my-app-prod \
    --resource-group rg-my-app-prod-eastus \
    --issuer "$OIDC_URL" \
    --subject "system:serviceaccount:production:my-app-sa" \
    --audience "api://AzureADTokenExchange"

# 7. Deploy Pod using the service account
# Pods with serviceAccountName: my-app-sa + label azure.workload.identity/use: "true"
# will automatically get a projected token for the UAMI
```

---

## Listing and Auditing Managed Identities

```bash
# List all user-assigned managed identities
az identity list \
    --query '[*].{Name:name,RG:resourceGroup,ClientID:clientId}' \
    --output table

# Find all resources using a specific UAMI
az resource list \
    --query "[?identity.userAssignedIdentities.\"$IDENTITY_ID\" != null].{Name:name,Type:type}" \
    --output table

# View role assignments for a managed identity
az role assignment list \
    --assignee $CLIENT_ID \
    --all \
    --output table
```

---

## References

- [Managed identities documentation](https://docs.microsoft.com/azure/active-directory/managed-identities-azure-resources/)
- [AKS Workload Identity](https://docs.microsoft.com/azure/aks/workload-identity-overview)
- [azure-identity Python SDK](https://docs.microsoft.com/python/api/overview/azure/identity-readme)
- [DefaultAzureCredential](https://docs.microsoft.com/azure/developer/python/sdk/authentication-overview)

---

← [Previous: Service Principals](./service-principals.md) | [Home](../../README.md) | [Next: Azure Networking →](../03-networking/README.md)
