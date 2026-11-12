← [Previous: Azure RBAC](./rbac.md) | [Home](../../README.md) | [Next: Managed Identities →](./managed-identities.md)

---

# Azure Service Principals

A service principal is an application identity in Entra ID — the identity used by non-human workloads (CI/CD pipelines, external applications, scripts) to access Azure resources.

---

## Service Principal vs Managed Identity

| | Service Principal | Managed Identity |
|-|-------------------|-----------------|
| Credentials | Client secret or certificate — YOU manage them | Azure manages automatically — no secrets |
| Use case | Workloads outside Azure (GitHub Actions, Jenkins, on-prem) | Workloads running inside Azure (VMs, AKS pods, Functions) |
| Rotation | Manual or scripted | Automatic |
| Recommendation | Only when managed identity is not possible | Preferred for all Azure-hosted workloads |

---

## Creating a Service Principal

```bash
# Create a service principal with a client secret
# --sdk-auth outputs a JSON blob for GitHub Actions / Terraform
SP=$(az ad sp create-for-rbac \
    --name "sp-github-actions-my-app" \
    --role "Contributor" \
    --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus \
    --sdk-auth)

echo $SP | python3 -m json.tool
# Output:
# {
#   "clientId": "...",
#   "clientSecret": "...",
#   "subscriptionId": "...",
#   "tenantId": "...",
#   "activeDirectoryEndpointUrl": "...",
#   ...
# }

# Create without role assignment (assign role separately)
az ad sp create-for-rbac \
    --name "sp-terraform-plan" \
    --skip-assignment

# Get the service principal object ID
SP_OBJECT_ID=$(az ad sp show --id $CLIENT_ID --query id -o tsv)
```

---

## Managing Credentials

### Client Secrets

```bash
# List credential details (not the secret value itself)
az ad sp credential list \
    --id $CLIENT_ID \
    --query '[*].{KeyID:keyId,DisplayName:displayName,EndDate:endDate}' \
    --output table

# Add a new client secret
az ad sp credential reset \
    --id $CLIENT_ID \
    --years 1 \
    --append \
    --query '{ClientID:appId,Secret:password,Tenant:tenant}'

# Delete a specific credential
az ad sp credential delete \
    --id $CLIENT_ID \
    --key-id <key-id>

# Reset (replace) all credentials — generates new secret
az ad sp credential reset \
    --id $CLIENT_ID \
    --years 1
```

### Certificate Authentication (more secure)

```bash
# Generate a self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
    -days 365 -nodes -subj "/CN=sp-my-app"

# Create SP with certificate
az ad sp create-for-rbac \
    --name "sp-terraform-prod" \
    --cert @cert.pem \
    --years 1

# Login using certificate
az login \
    --service-principal \
    --tenant $TENANT_ID \
    --username $CLIENT_ID \
    --password @key.pem
```

---

## Federated Identity Credentials (OIDC — no secrets)

Federated credentials let external identity providers (GitHub Actions, Kubernetes service accounts) exchange their OIDC tokens for Azure access tokens — **no client secrets needed**.

### GitHub Actions → Azure (recommended for CI/CD)

```bash
# 1. Create the App Registration
APP_ID=$(az ad app create \
    --display-name "sp-github-actions-my-repo" \
    --query appId -o tsv)

# 2. Create the service principal
az ad sp create --id $APP_ID

SP_OBJECT_ID=$(az ad sp show --id $APP_ID --query id -o tsv)

# 3. Assign role
az role assignment create \
    --assignee-object-id $SP_OBJECT_ID \
    --assignee-principal-type ServicePrincipal \
    --role "Contributor" \
    --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus

# 4. Add federated credential for main branch
az ad app federated-credential create \
    --id $APP_ID \
    --parameters '{
        "name": "github-main-branch",
        "issuer": "https://token.actions.githubusercontent.com",
        "subject": "repo:my-org/my-repo:ref:refs/heads/main",
        "audiences": ["api://AzureADTokenExchange"],
        "description": "GitHub Actions main branch"
    }'

# 5. Add federated credential for pull requests
az ad app federated-credential create \
    --id $APP_ID \
    --parameters '{
        "name": "github-pull-requests",
        "issuer": "https://token.actions.githubusercontent.com",
        "subject": "repo:my-org/my-repo:pull_request",
        "audiences": ["api://AzureADTokenExchange"]
    }'

# 6. Store in GitHub Secrets: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID
```

#### GitHub Actions Workflow (OIDC)

```yaml
name: Deploy to Azure
on:
  push:
    branches: [main]
permissions:
  id-token: write    # Required for OIDC
  contents: read
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: azure/login@v1
      with:
        client-id: ${{ secrets.AZURE_CLIENT_ID }}
        tenant-id: ${{ secrets.AZURE_TENANT_ID }}
        subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
    - run: az group list --output table
```

---

## Viewing and Managing Service Principals

```bash
# List service principals
az ad sp list \
    --query '[*].{Name:displayName,AppID:appId,Type:servicePrincipalType}' \
    --output table

# Get details of a service principal
az ad sp show --id $APP_ID \
    --query '{Name:displayName,AppID:appId,ObjID:id,Enabled:accountEnabled}'

# List role assignments for a service principal
az role assignment list \
    --assignee $APP_ID \
    --all \
    --output table

# Disable a service principal
az ad sp update --id $APP_ID --account-enabled false

# Delete a service principal
az ad sp delete --id $APP_ID
# Note: also delete the app registration
az ad app delete --id $APP_ID
```

---

## Service Principal Rotation Checklist

Client secrets expire. Set up rotation reminders:

```bash
# Find service principals with expiring credentials (next 30 days)
az ad app list --query '[*].{AppID:appId,Name:displayName}' -o tsv | \
while read APP_ID APP_NAME; do
    az ad app credential list --id $APP_ID \
        --query "[?endDateTime<'$(date -u -d "+30 days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v+30d +%Y-%m-%dT%H:%M:%SZ)'].{App:'$APP_NAME',KeyID:keyId,ExpiresOn:endDateTime}" \
        --output table 2>/dev/null
done
```

---

## References

- [Service principals documentation](https://docs.microsoft.com/azure/active-directory/develop/app-objects-and-service-principals)
- [Federated identity credentials](https://docs.microsoft.com/azure/active-directory/develop/workload-identity-federation)
- [GitHub Actions OIDC with Azure](https://docs.microsoft.com/azure/developer/github/connect-from-azure)

---

← [Previous: Azure RBAC](./rbac.md) | [Home](../../README.md) | [Next: Managed Identities →](./managed-identities.md)
