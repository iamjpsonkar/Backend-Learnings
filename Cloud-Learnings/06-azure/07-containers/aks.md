← [Previous: ACR](./acr.md) | [Home](../../README.md) | [Next: ACI →](./aci.md)

---

# Azure Kubernetes Service (AKS)

AKS is a managed Kubernetes service. Azure manages the control plane; you manage node pools and workloads. AKS integrates with ACR, Entra ID, Azure Monitor, Key Vault, and Azure networking.

---

## AKS Architecture

```
Azure-managed control plane (free tier)
  ├── kube-apiserver
  ├── etcd
  ├── kube-scheduler
  └── kube-controller-manager

Your node pools (you pay for node VMs)
  ├── System node pool  (kube-system, CoreDNS, etc.)
  └── User node pool(s) (your workloads)

Integrations:
  ├── ACR (image pull via AcrPull role)
  ├── Azure CNI / Cilium (networking)
  ├── Entra Workload Identity (pods → Azure services)
  ├── Azure Monitor + Container Insights
  └── Key Vault Secrets Store CSI Driver
```

---

## Creating an AKS Cluster

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
LOCATION="eastus"
CLUSTER_NAME="aks-my-app-prod-eastus-001"
ACR_NAME="acrmyappprodeastus"

# Create cluster — private, zone-redundant, Workload Identity enabled
az aks create \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --location $LOCATION \
    --kubernetes-version 1.29 \
    --node-count 3 \
    --node-vm-size Standard_D4s_v5 \
    --node-osdisk-size 128 \
    --node-osdisk-type Ephemeral \
    --zones 1 2 3 \
    --vnet-subnet-id $(az network vnet subnet show \
        --resource-group $RESOURCE_GROUP \
        --vnet-name vnet-my-app-prod-eastus-001 \
        --name snet-app --query id -o tsv) \
    --network-plugin azure \
    --network-plugin-mode overlay \
    --network-policy cilium \
    --enable-private-cluster \
    --private-dns-zone system \
    --enable-workload-identity \
    --enable-oidc-issuer \
    --enable-managed-identity \
    --attach-acr $ACR_NAME \
    --enable-cluster-autoscaler \
    --min-count 3 \
    --max-count 15 \
    --enable-addons monitoring \
    --workspace-resource-id $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus --query id -o tsv) \
    --auto-upgrade-channel patch \
    --tags Environment=production Service=my-app

# Get credentials
az aks get-credentials \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME

# Verify
kubectl get nodes -o wide
```

---

## Node Pools

```bash
# Add a user node pool (GPU, high-memory, or spot)
az aks nodepool add \
    --resource-group $RESOURCE_GROUP \
    --cluster-name $CLUSTER_NAME \
    --name workload \
    --node-count 3 \
    --node-vm-size Standard_D8s_v5 \
    --zones 1 2 3 \
    --mode User \
    --enable-cluster-autoscaler \
    --min-count 3 \
    --max-count 30 \
    --node-taints workload=true:NoSchedule \
    --labels tier=workload \
    --node-osdisk-type Ephemeral

# Add a spot node pool for cost savings
az aks nodepool add \
    --resource-group $RESOURCE_GROUP \
    --cluster-name $CLUSTER_NAME \
    --name spot \
    --node-count 0 \
    --node-vm-size Standard_D4s_v5 \
    --spot-max-price -1 \
    --priority Spot \
    --eviction-policy Delete \
    --enable-cluster-autoscaler \
    --min-count 0 \
    --max-count 20 \
    --node-taints "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"

# Scale a node pool manually
az aks nodepool scale \
    --resource-group $RESOURCE_GROUP \
    --cluster-name $CLUSTER_NAME \
    --name workload \
    --node-count 6

# Upgrade node pool OS image
az aks nodepool upgrade \
    --resource-group $RESOURCE_GROUP \
    --cluster-name $CLUSTER_NAME \
    --name workload \
    --node-image-only

# List node pools
az aks nodepool list \
    --resource-group $RESOURCE_GROUP \
    --cluster-name $CLUSTER_NAME \
    --output table
```

---

## Workload Identity

Workload Identity lets pods authenticate to Azure services using managed identities — no credentials in pods.

```bash
# 1. Get OIDC issuer URL
OIDC_ISSUER=$(az aks show \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --query "oidcIssuerProfile.issuerUrl" -o tsv)

# 2. Create user-assigned managed identity for the workload
az identity create \
    --resource-group $RESOURCE_GROUP \
    --name id-my-app-workload

CLIENT_ID=$(az identity show \
    --resource-group $RESOURCE_GROUP \
    --name id-my-app-workload --query clientId -o tsv)

PRINCIPAL_ID=$(az identity show \
    --resource-group $RESOURCE_GROUP \
    --name id-my-app-workload --query principalId -o tsv)

# 3. Grant the identity permissions (e.g., read Key Vault secrets)
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Key Vault Secrets User" \
    --scope $(az keyvault show \
        --resource-group $RESOURCE_GROUP \
        --name kv-my-app-prod-eastus --query id -o tsv)

# 4. Create Kubernetes ServiceAccount
kubectl create serviceaccount my-app-sa -n my-app

kubectl annotate serviceaccount my-app-sa \
    --namespace my-app \
    "azure.workload.identity/client-id=$CLIENT_ID"

# 5. Create federated identity credential
az identity federated-credential create \
    --resource-group $RESOURCE_GROUP \
    --identity-name id-my-app-workload \
    --name aks-my-app-federated \
    --issuer $OIDC_ISSUER \
    --subject "system:serviceaccount:my-app:my-app-sa" \
    --audiences "api://AzureADTokenExchange"

# 6. Label the pod to use Workload Identity
# In Deployment spec, add:
# spec.template.metadata.labels: azure.workload.identity/use: "true"
# spec.template.spec.serviceAccountName: my-app-sa
```

---

## Cluster Upgrades

```bash
# List available upgrade versions
az aks get-upgrades \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --output table

# Upgrade control plane first
az aks upgrade \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --kubernetes-version 1.30 \
    --control-plane-only

# Then upgrade node pools
az aks nodepool upgrade \
    --resource-group $RESOURCE_GROUP \
    --cluster-name $CLUSTER_NAME \
    --name workload \
    --kubernetes-version 1.30

# Enable patch auto-upgrade
az aks update \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --auto-upgrade-channel patch \
    --node-os-upgrade-channel NodeImage
```

---

## Key Vault Secrets Store CSI Driver

```bash
# Enable the add-on
az aks enable-addons \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --addons azure-keyvault-secrets-provider

# SecretProviderClass — mount Key Vault secret as a volume or env var
cat <<EOF | kubectl apply -f -
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: my-app-secrets
  namespace: my-app
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    clientID: "$CLIENT_ID"
    keyvaultName: "kv-my-app-prod-eastus"
    tenantId: "$(az account show --query tenantId -o tsv)"
    objects: |
      array:
        - |
          objectName: db-password
          objectType: secret
          objectVersion: ""
EOF
```

---

## Monitoring

```bash
# Enable Container Insights (if not done at creation)
az aks enable-addons \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --addons monitoring \
    --workspace-resource-id $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus --query id -o tsv)

# View live logs from a pod
kubectl logs -n my-app -l app=my-app -f --tail=100

# Run a diagnostic check
az aks kollect \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --storage-account stmyappprodeastus \
    --sas-token "$SAS_TOKEN"
```

---

## References

- [AKS documentation](https://docs.microsoft.com/azure/aks/)
- [Workload Identity](https://docs.microsoft.com/azure/aks/workload-identity-overview)
- [AKS cluster upgrades](https://docs.microsoft.com/azure/aks/upgrade-cluster)
- [Key Vault CSI driver](https://docs.microsoft.com/azure/aks/csi-secrets-store-driver)

---

← [Previous: ACR](./acr.md) | [Home](../../README.md) | [Next: ACI →](./aci.md)
