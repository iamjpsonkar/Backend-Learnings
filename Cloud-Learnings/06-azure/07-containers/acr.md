← [Previous: Azure Containers](./README.md) | [Home](../../README.md) | [Next: AKS →](./aks.md)

---

# Azure Container Registry (ACR)

ACR is a private OCI-compliant container registry. It supports Docker images, Helm charts, and any OCI artifact. It integrates natively with AKS, Azure Container Apps, and CI/CD pipelines.

---

## SKU Comparison

| SKU | Storage | Throughput | Geo-replication | Private link | Use Case |
|-----|---------|-----------|-----------------|--------------|----------|
| **Basic** | 10 GB | Low | No | No | Dev/test |
| **Standard** | 100 GB | Medium | No | No | Most workloads |
| **Premium** | 500 GB | High | Yes | Yes | Production, enterprise |

---

## Creating a Registry

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
LOCATION="eastus"
ACR_NAME="acrmyappprodeastus"  # Globally unique, alphanumeric, 5–50 chars

# Create Premium ACR with zone redundancy
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --location $LOCATION \
    --sku Premium \
    --zone-redundancy Enabled \
    --admin-enabled false \  # Use managed identity, not admin credentials
    --tags Environment=production Service=my-app

# Get registry login server
az acr show \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --query loginServer --output tsv
# Output: acrmyappprodeastus.azurecr.io

# Grant AKS kubelet identity pull access
AKS_IDENTITY=$(az aks show \
    --resource-group $RESOURCE_GROUP \
    --name aks-my-app-prod-eastus-001 \
    --query identityProfile.kubeletidentity.objectId -o tsv)

az role assignment create \
    --assignee $AKS_IDENTITY \
    --role AcrPull \
    --scope $(az acr show --resource-group $RESOURCE_GROUP \
        --name $ACR_NAME --query id -o tsv)
```

---

## Building and Pushing Images

```bash
# Method 1: ACR Tasks — cloud build (no local Docker required)
az acr build \
    --registry $ACR_NAME \
    --image my-app:$(git rev-parse --short HEAD) \
    --image my-app:latest \
    --file Dockerfile \
    .

# Method 2: Local docker build + push
az acr login --name $ACR_NAME
docker build -t $ACR_NAME.azurecr.io/my-app:v1.2.3 .
docker push $ACR_NAME.azurecr.io/my-app:v1.2.3

# Tag with multiple tags
docker tag $ACR_NAME.azurecr.io/my-app:v1.2.3 $ACR_NAME.azurecr.io/my-app:latest
docker push $ACR_NAME.azurecr.io/my-app:latest
```

---

## ACR Tasks (Automated Builds)

ACR Tasks can build images triggered by git commits, base image updates, or on a schedule.

```bash
# Create a task triggered on git push to main
az acr task create \
    --registry $ACR_NAME \
    --name build-my-app \
    --image "my-app:{{.Run.ID}}" \
    --image "my-app:latest" \
    --context https://github.com/my-org/my-app.git#refs/heads/main \
    --file Dockerfile \
    --git-access-token $GITHUB_PAT \
    --assign-identity [system]

# Create a multi-step task with YAML
# acr-task.yaml:
# version: v1.1.0
# steps:
#   - build: -t $Registry/my-app:$ID -t $Registry/my-app:latest .
#   - push: ["$Registry/my-app:$ID", "$Registry/my-app:latest"]
#   - cmd: $Registry/my-app:$ID /app/tests/smoke.sh  # Run smoke test

az acr task create \
    --registry $ACR_NAME \
    --name build-and-test \
    --context https://github.com/my-org/my-app.git \
    --file acr-task.yaml \
    --git-access-token $GITHUB_PAT

# Run a task manually
az acr task run \
    --registry $ACR_NAME \
    --name build-my-app

# View task run history
az acr task list-runs \
    --registry $ACR_NAME \
    --output table
```

---

## Image Lifecycle — Retention and Cleanup

```bash
# Enable soft-delete (recover deleted images within 14 days)
az acr config soft-delete update \
    --registry $ACR_NAME \
    --status Enabled \
    --days 14

# Create a retention policy — delete untagged manifests after 7 days
az acr config retention update \
    --registry $ACR_NAME \
    --status Enabled \
    --days 7 \
    --type UntaggedManifests

# Purge old images (keep latest 5 tags, delete older than 30 days)
az acr run \
    --registry $ACR_NAME \
    --cmd "acr purge --filter 'my-app:.*' --ago 30d --keep 5 --untagged" \
    /dev/null

# Schedule weekly cleanup
az acr task create \
    --registry $ACR_NAME \
    --name weekly-purge \
    --cmd "acr purge --filter '.*:.*' --ago 30d --keep 10 --untagged" \
    --schedule "0 2 * * 0" \
    --context /dev/null
```

---

## Geo-Replication (Premium)

```bash
# Replicate to West Europe for lower-latency pulls from Europe
az acr replication create \
    --registry $ACR_NAME \
    --location westeurope \
    --zone-redundancy Enabled

# List replications
az acr replication list \
    --registry $ACR_NAME \
    --output table

# Remove a replication
az acr replication delete \
    --registry $ACR_NAME \
    --name westeurope
```

---

## Private Endpoint for ACR

```bash
# Create private endpoint so AKS nodes pull images without leaving the VNet
az network private-endpoint create \
    --resource-group $RESOURCE_GROUP \
    --name pe-acr \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-private-endpoints \
    --private-connection-resource-id $(az acr show \
        --resource-group $RESOURCE_GROUP \
        --name $ACR_NAME --query id -o tsv) \
    --group-id registry \
    --connection-name pe-conn-acr

# Disable public access after private endpoint is created
az acr update \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --public-network-enabled false

# Create private DNS zone for ACR
az network private-dns zone create \
    --resource-group $RESOURCE_GROUP \
    --name "privatelink.azurecr.io"

az network private-dns link vnet create \
    --resource-group $RESOURCE_GROUP \
    --zone-name "privatelink.azurecr.io" \
    --name dns-link-acr \
    --virtual-network vnet-my-app-prod-eastus-001 \
    --registration-enabled false

az network private-endpoint dns-zone-group create \
    --resource-group $RESOURCE_GROUP \
    --endpoint-name pe-acr \
    --name acr-zone-group \
    --private-dns-zone "privatelink.azurecr.io" \
    --zone-name registry
```

---

## Useful Commands

```bash
# List repositories
az acr repository list --name $ACR_NAME --output table

# List tags for a repository
az acr repository show-tags \
    --name $ACR_NAME \
    --repository my-app \
    --orderby time_desc \
    --output table

# Show manifest details
az acr repository show \
    --name $ACR_NAME \
    --image my-app:latest

# Delete a specific tag
az acr repository delete \
    --name $ACR_NAME \
    --image my-app:v1.0.0 \
    --yes

# Import image from Docker Hub
az acr import \
    --name $ACR_NAME \
    --source docker.io/library/nginx:1.25 \
    --image nginx:1.25
```

---

## References

- [Azure Container Registry documentation](https://docs.microsoft.com/azure/container-registry/)
- [ACR Tasks](https://docs.microsoft.com/azure/container-registry/container-registry-tasks-overview)
- [Geo-replication](https://docs.microsoft.com/azure/container-registry/container-registry-geo-replication)

---

← [Previous: Azure Containers](./README.md) | [Home](../../README.md) | [Next: AKS →](./aks.md)
