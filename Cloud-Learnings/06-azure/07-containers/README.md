← [Previous: Redis](../06-databases/redis.md) | [Home](../../README.md) | [Next: ACR →](./acr.md)

---

# Azure Containers

---

## Service Selection

| Service | AWS Equivalent | Use case |
|---------|----------------|---------|
| **Azure Container Registry (ACR)** | ECR | Private container image registry |
| **Azure Kubernetes Service (AKS)** | EKS | Managed Kubernetes — production containers |
| **Azure Container Instances (ACI)** | Fargate run-task / ECS one-off | Serverless containers — no cluster needed |
| **Azure Container Apps** | ECS Fargate service | Serverless microservices with built-in KEDA scaling |

---

## Azure Container Registry (ACR)

```bash
RESOURCE_GROUP="rg-my-app-production"
LOCATION="eastus"
ACR_NAME="acrmyappprodeastus"

# Create an ACR (Premium SKU for geo-replication and private link)
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Premium \
    --location $LOCATION \
    --admin-enabled false \
    --tags Environment=production

# Authenticate Docker to ACR
az acr login --name $ACR_NAME

# Build and push using ACR Tasks (builds in the cloud — no local Docker needed)
az acr build \
    --registry $ACR_NAME \
    --image my-app/backend:v1.2.3 \
    --file Dockerfile \
    .

# Tag and push locally
docker tag my-app/backend:v1.2.3 ${ACR_NAME}.azurecr.io/my-app/backend:v1.2.3
docker push ${ACR_NAME}.azurecr.io/my-app/backend:v1.2.3

# List repositories and tags
az acr repository list --name $ACR_NAME --output table
az acr repository show-tags --name $ACR_NAME --repository my-app/backend --output table

# Enable vulnerability scanning (Defender for Containers)
az security pricing create --name ContainerRegistry --tier Standard

# Purge old images (keep last 5 tags with prefix v)
az acr run \
    --registry $ACR_NAME \
    --cmd 'acr purge --filter "my-app/backend:v.*" --keep 5 --untagged' \
    /dev/null

# Grant AKS pull access (preferred over admin credentials)
AKS_KUBELET_IDENTITY=$(az aks show \
    --resource-group $RESOURCE_GROUP \
    --name aks-my-app-prod-eastus-001 \
    --query identityProfile.kubeletidentity.clientId --output tsv)

az role assignment create \
    --assignee $AKS_KUBELET_IDENTITY \
    --role AcrPull \
    --scope $(az acr show --name $ACR_NAME --query id --output tsv)
```

---

## Azure Kubernetes Service (AKS)

```bash
# Create AKS cluster with managed identity, Azure CNI, and system node pool
az aks create \
    --resource-group $RESOURCE_GROUP \
    --name aks-my-app-prod-eastus-001 \
    --location $LOCATION \
    --kubernetes-version 1.29 \
    --node-count 3 \
    --node-vm-size Standard_D4s_v5 \
    --nodepool-name system \
    --zones 1 2 3 \
    --network-plugin azure \
    --vnet-subnet-id $(az network vnet subnet show \
        --resource-group $RESOURCE_GROUP \
        --vnet-name vnet-my-app-prod-eastus-001 \
        --name snet-app --query id --output tsv) \
    --enable-managed-identity \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --enable-cluster-autoscaler \
    --min-count 3 \
    --max-count 10 \
    --uptime-sla \
    --enable-azure-monitor-metrics \
    --attach-acr $ACR_NAME \
    --tags Environment=production

# Get credentials
az aks get-credentials \
    --resource-group $RESOURCE_GROUP \
    --name aks-my-app-prod-eastus-001 \
    --overwrite-existing

kubectl get nodes -o wide

# Add a user node pool for application workloads
az aks nodepool add \
    --resource-group $RESOURCE_GROUP \
    --cluster-name aks-my-app-prod-eastus-001 \
    --name user \
    --node-count 2 \
    --node-vm-size Standard_D4s_v5 \
    --zones 1 2 3 \
    --mode User \
    --enable-cluster-autoscaler \
    --min-count 2 \
    --max-count 20 \
    --node-taints workload=application:NoSchedule \
    --labels role=application

# Add a spot node pool
az aks nodepool add \
    --resource-group $RESOURCE_GROUP \
    --cluster-name aks-my-app-prod-eastus-001 \
    --name spot \
    --node-count 0 \
    --node-vm-size Standard_D4s_v5 \
    --priority Spot \
    --eviction-policy Delete \
    --spot-max-price -1 \
    --enable-cluster-autoscaler \
    --min-count 0 \
    --max-count 30 \
    --mode User \
    --labels azure.com/e2e-az-name=spot
```

### Workload Identity (IRSA equivalent)

Workload Identity allows pods to assume Azure managed identities without node-level credentials.

```bash
# Get OIDC issuer URL
OIDC_ISSUER=$(az aks show \
    --resource-group $RESOURCE_GROUP \
    --name aks-my-app-prod-eastus-001 \
    --query oidcIssuerProfile.issuerUrl --output tsv)

# Create a user-assigned managed identity for the workload
IDENTITY=$(az identity create \
    --resource-group $RESOURCE_GROUP \
    --name id-my-app-workload \
    --query '{id:id,clientId:clientId,principalId:principalId}')

CLIENT_ID=$(echo $IDENTITY | python3 -c "import sys,json; print(json.load(sys.stdin)['clientId'])")
PRINCIPAL_ID=$(echo $IDENTITY | python3 -c "import sys,json; print(json.load(sys.stdin)['principalId'])")

# Grant the identity access to Key Vault secrets
az keyvault set-policy \
    --name kv-my-app-prod-eastus \
    --object-id $PRINCIPAL_ID \
    --secret-permissions get list

# Create federated credential (links Kubernetes service account to managed identity)
az identity federated-credential create \
    --resource-group $RESOURCE_GROUP \
    --identity-name id-my-app-workload \
    --name fed-cred-my-app \
    --issuer $OIDC_ISSUER \
    --subject "system:serviceaccount:my-app:my-app-sa" \
    --audiences api://AzureADTokenExchange

# Create annotated Kubernetes service account
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: my-app
  annotations:
    azure.workload.identity/client-id: "$CLIENT_ID"
  labels:
    azure.workload.identity/use: "true"
EOF
```

### AKS Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-backend
  namespace: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app-backend
  template:
    metadata:
      labels:
        app: my-app-backend
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: my-app-sa
      nodeSelector:
        role: application
      tolerations:
      - key: workload
        value: application
        effect: NoSchedule
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: my-app-backend
      containers:
      - name: backend
        image: acrmyappprodeastus.azurecr.io/my-app/backend:v1.2.3
        ports:
        - containerPort: 8080
        env:
        - name: APP_ENV
          value: production
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
```

### Cluster Upgrades

```bash
# Check available Kubernetes versions
az aks get-upgrades \
    --resource-group $RESOURCE_GROUP \
    --name aks-my-app-prod-eastus-001 \
    --output table

# Upgrade cluster (control plane first)
az aks upgrade \
    --resource-group $RESOURCE_GROUP \
    --name aks-my-app-prod-eastus-001 \
    --kubernetes-version 1.30 \
    --node-image-upgrade-only false  # upgrade both control plane and node pools
```

---

## Azure Container Instances (ACI)

```bash
# Run a one-off container (no cluster needed)
az container create \
    --resource-group $RESOURCE_GROUP \
    --name aci-migration-job \
    --image ${ACR_NAME}.azurecr.io/my-app/backend:v1.2.3 \
    --cpu 2 \
    --memory 4 \
    --registry-login-server ${ACR_NAME}.azurecr.io \
    --assign-identity \
    --vnet vnet-my-app-prod-eastus-001 \
    --subnet snet-app \
    --restart-policy Never \
    --environment-variables APP_ENV=production \
    --command-line "python manage.py migrate" \
    --secure-environment-variables DB_PASSWORD=secretvalue

# View logs
az container logs \
    --resource-group $RESOURCE_GROUP \
    --name aci-migration-job

# Wait for completion
az container wait \
    --resource-group $RESOURCE_GROUP \
    --name aci-migration-job \
    --condition terminated

# Get exit code
az container show \
    --resource-group $RESOURCE_GROUP \
    --name aci-migration-job \
    --query 'containers[0].instanceView.currentState.exitCode'

# Clean up
az container delete \
    --resource-group $RESOURCE_GROUP \
    --name aci-migration-job --yes
```

---

## References

- [ACR documentation](https://docs.microsoft.com/azure/container-registry/)
- [AKS documentation](https://docs.microsoft.com/azure/aks/)
- [AKS best practices](https://docs.microsoft.com/azure/aks/best-practices)
- [AKS Workload Identity](https://docs.microsoft.com/azure/aks/workload-identity-overview)
- [Azure Container Instances](https://docs.microsoft.com/azure/container-instances/)
---

← [Previous: Redis](../06-databases/redis.md) | [Home](../../README.md) | [Next: ACR →](./acr.md)
