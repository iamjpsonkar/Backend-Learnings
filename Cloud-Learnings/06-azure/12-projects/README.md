← [Previous: Terraform on Azure](../11-iac/terraform-azure.md) | [Home](../../README.md) | [Next: Static Website →](./static-website.md)

---

# Azure Projects

Hands-on projects that combine multiple Azure services into complete, production-ready architectures.

---

## Project 1 — Static Website with Azure CDN

**Goal:** Host a React/Vue/static site on Blob Storage with CDN acceleration, custom domain, and HTTPS.

**Services:** Blob Storage (static website) · Azure CDN (or Azure Front Door) · Azure DNS

```bash
RESOURCE_GROUP="rg-my-website-production"
LOCATION="eastus"
ACCOUNT_NAME="stmywebsiteprodeastus"
CDN_PROFILE="cdn-my-website-prod"
CDN_ENDPOINT="mywebsite"
DOMAIN="www.example.com"

az group create --name $RESOURCE_GROUP --location $LOCATION

# Create storage account with static website enabled
az storage account create \
    --resource-group $RESOURCE_GROUP \
    --name $ACCOUNT_NAME \
    --sku Standard_ZRS \
    --kind StorageV2

az storage blob service-properties update \
    --account-name $ACCOUNT_NAME \
    --static-website true \
    --index-document index.html \
    --404-document 404.html

# Get the static website origin URL
ORIGIN=$(az storage account show \
    --resource-group $RESOURCE_GROUP \
    --name $ACCOUNT_NAME \
    --query primaryEndpoints.web --output tsv | sed 's|https://||' | sed 's|/||')
echo "Origin: $ORIGIN"

# Create CDN profile + endpoint
az cdn profile create \
    --resource-group $RESOURCE_GROUP \
    --name $CDN_PROFILE \
    --sku Standard_Microsoft

az cdn endpoint create \
    --resource-group $RESOURCE_GROUP \
    --profile-name $CDN_PROFILE \
    --name $CDN_ENDPOINT \
    --origin $ORIGIN \
    --origin-host-header $ORIGIN \
    --enable-compression true \
    --query-string-caching-behavior IgnoreQueryString

# Enable HTTPS with a CDN-managed certificate (free)
az cdn custom-domain enable-https \
    --resource-group $RESOURCE_GROUP \
    --profile-name $CDN_PROFILE \
    --endpoint-name $CDN_ENDPOINT \
    --name my-custom-domain

# Upload site content
az storage blob upload-batch \
    --account-name $ACCOUNT_NAME \
    --destination '$web' \
    --source ./dist \
    --pattern "**" \
    --content-cache-control "public, max-age=31536000" \
    --overwrite

# Set short cache for index.html (so deployments propagate quickly)
az storage blob upload \
    --account-name $ACCOUNT_NAME \
    --container-name '$web' \
    --name index.html \
    --file ./dist/index.html \
    --content-cache-control "public, max-age=60" \
    --content-type "text/html" \
    --overwrite

# Purge CDN cache after deployment
az cdn endpoint purge \
    --resource-group $RESOURCE_GROUP \
    --profile-name $CDN_PROFILE \
    --name $CDN_ENDPOINT \
    --content-paths "/*"
```

**Cost estimate:** ~$2–5/month (storage + CDN egress, varies by traffic).

---

## Project 2 — Secure Hub-and-Spoke VNet

**Goal:** Production-grade network with a hub VNet (shared services) and spoke VNet (application), enforcing all traffic through Azure Firewall.

**Services:** VNet · VNet Peering · Azure Firewall · Azure Bastion · NSG · Private DNS Zones

```bash
RESOURCE_GROUP="rg-my-app-network"
LOCATION="eastus"

az group create --name $RESOURCE_GROUP --location $LOCATION

# Hub VNet — shared services (Firewall, Bastion, DNS resolver)
az network vnet create \
    --resource-group $RESOURCE_GROUP \
    --name vnet-hub-prod-eastus \
    --address-prefix 10.0.0.0/16 \
    --subnet-name AzureFirewallSubnet \
    --subnet-prefix 10.0.1.0/26  # /26 minimum required by Azure Firewall

az network vnet subnet create \
    --resource-group $RESOURCE_GROUP \
    --vnet-name vnet-hub-prod-eastus \
    --name AzureBastionSubnet \
    --address-prefix 10.0.2.0/27  # /27 minimum required by Bastion

# Spoke VNet — application workloads
az network vnet create \
    --resource-group $RESOURCE_GROUP \
    --name vnet-spoke-prod-eastus \
    --address-prefix 10.1.0.0/16

for SUBNET in "snet-app:10.1.1.0/24" "snet-data:10.1.2.0/24" "snet-pe:10.1.3.0/24"; do
    NAME="${SUBNET%%:*}"
    CIDR="${SUBNET##*:}"
    az network vnet subnet create \
        --resource-group $RESOURCE_GROUP \
        --vnet-name vnet-spoke-prod-eastus \
        --name $NAME \
        --address-prefix $CIDR
done

# VNet Peering — hub → spoke
az network vnet peering create \
    --resource-group $RESOURCE_GROUP \
    --name peer-hub-to-spoke \
    --vnet-name vnet-hub-prod-eastus \
    --remote-vnet vnet-spoke-prod-eastus \
    --allow-forwarded-traffic true \
    --allow-gateway-transit false

# VNet Peering — spoke → hub
az network vnet peering create \
    --resource-group $RESOURCE_GROUP \
    --name peer-spoke-to-hub \
    --vnet-name vnet-spoke-prod-eastus \
    --remote-vnet vnet-hub-prod-eastus \
    --allow-forwarded-traffic true \
    --use-remote-gateways false

# Azure Firewall (Standard SKU)
az network public-ip create \
    --resource-group $RESOURCE_GROUP \
    --name pip-firewall-hub-prod-eastus \
    --sku Standard --zone 1 2 3

az network firewall create \
    --resource-group $RESOURCE_GROUP \
    --name afw-hub-prod-eastus \
    --location $LOCATION \
    --sku-name AZFW_VNet \
    --sku-tier Standard

az network firewall ip-config create \
    --resource-group $RESOURCE_GROUP \
    --firewall-name afw-hub-prod-eastus \
    --name ipconfig-afw \
    --public-ip-address pip-firewall-hub-prod-eastus \
    --vnet-name vnet-hub-prod-eastus

# Get Firewall private IP for route table
FW_PRIVATE_IP=$(az network firewall show \
    --resource-group $RESOURCE_GROUP \
    --name afw-hub-prod-eastus \
    --query 'ipConfigurations[0].privateIPAddress' --output tsv)

# Force all spoke traffic through Firewall via UDR
az network route-table create \
    --resource-group $RESOURCE_GROUP \
    --name rt-spoke-prod-eastus \
    --disable-bgp-route-propagation true

az network route-table route create \
    --resource-group $RESOURCE_GROUP \
    --route-table-name rt-spoke-prod-eastus \
    --name default-to-firewall \
    --address-prefix 0.0.0.0/0 \
    --next-hop-type VirtualAppliance \
    --next-hop-ip-address $FW_PRIVATE_IP

# Associate route table with spoke subnets
for SUBNET in snet-app snet-data; do
    az network vnet subnet update \
        --resource-group $RESOURCE_GROUP \
        --vnet-name vnet-spoke-prod-eastus \
        --name $SUBNET \
        --route-table rt-spoke-prod-eastus
done
```

---

## Project 3 — Containerized Microservice on AKS

**Goal:** Deploy a Python microservice to AKS with private ACR, Workload Identity for Key Vault access, ALB ingress, HPA, and Azure Monitor integration.

**Services:** ACR · AKS · Key Vault · Azure Monitor · Azure Load Balancer · Workload Identity

```bash
RESOURCE_GROUP="rg-my-app-production"
LOCATION="eastus"
ACR_NAME="acrmyappprodeastus"
AKS_NAME="aks-my-app-prod-eastus-001"
KV_NAME="kv-my-app-prod-eastus"

# 1. Create ACR and AKS (full commands in 07-containers/README.md)
# Assume both are already provisioned with Workload Identity enabled

# 2. Build and push image
az acr build \
    --registry $ACR_NAME \
    --image my-app/api:$GIT_SHA \
    --file Dockerfile \
    .

# 3. Get cluster credentials
az aks get-credentials \
    --resource-group $RESOURCE_GROUP \
    --name $AKS_NAME \
    --overwrite-existing

# 4. Create namespace and service account
kubectl create namespace my-app

# Get Workload Identity client ID (set up per 07-containers/README.md)
CLIENT_ID=$(az identity show \
    --resource-group $RESOURCE_GROUP \
    --name id-my-app-workload \
    --query clientId --output tsv)

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

# 5. Deploy application
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-api
  namespace: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app-api
  template:
    metadata:
      labels:
        app: my-app-api
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: my-app-sa
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: my-app-api
      containers:
      - name: api
        image: ${ACR_NAME}.azurecr.io/my-app/api:${GIT_SHA}
        ports:
        - containerPort: 8080
        env:
        - name: KEY_VAULT_NAME
          value: "${KV_NAME}"
        - name: APP_ENV
          value: production
        resources:
          requests:
            cpu: "250m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: my-app-api
  namespace: my-app
spec:
  selector:
    app: my-app-api
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-api
  namespace: my-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
EOF

# 6. Verify rollout
kubectl rollout status deployment/my-app-api -n my-app
kubectl get pods -n my-app -o wide
```

---

## Project 4 — Serverless API Backend

**Goal:** Build a REST API using Azure Functions with a Cosmos DB backend, Key Vault for secrets, Service Bus for async order processing, and Application Insights for observability.

**Services:** Azure Functions · Cosmos DB · Service Bus · Key Vault · Application Insights

**Architecture:**

```
Client → API Management → Azure Functions (HTTP trigger)
                                  ↓
                             Cosmos DB (orders container)
                                  ↓
                         Service Bus (order-events topic)
                                  ↓
                    Azure Functions (Service Bus trigger)
                         → fulfillment logic
```

```bash
RESOURCE_GROUP="rg-my-api-production"
LOCATION="eastus"

az group create --name $RESOURCE_GROUP --location $LOCATION

# Provision all backing services
# Storage (required by Functions runtime)
az storage account create \
    --resource-group $RESOURCE_GROUP \
    --name stmyapiprodeastus \
    --sku Standard_ZRS \
    --kind StorageV2

# Application Insights
az monitor log-analytics workspace create \
    --resource-group $RESOURCE_GROUP \
    --workspace-name law-my-api-prod-eastus \
    --sku PerGB2018

az monitor app-insights component create \
    --resource-group $RESOURCE_GROUP \
    --app appi-my-api-prod-eastus \
    --location $LOCATION \
    --kind web \
    --workspace law-my-api-prod-eastus

# Cosmos DB
az cosmosdb create \
    --resource-group $RESOURCE_GROUP \
    --name cosmos-my-api-prod-eastus \
    --kind GlobalDocumentDB \
    --locations regionName=$LOCATION failoverPriority=0 isZoneRedundant=true \
    --default-consistency-level Session

az cosmosdb sql database create \
    --resource-group $RESOURCE_GROUP \
    --account-name cosmos-my-api-prod-eastus \
    --name myapi

az cosmosdb sql container create \
    --resource-group $RESOURCE_GROUP \
    --account-name cosmos-my-api-prod-eastus \
    --database-name myapi \
    --name orders \
    --partition-key-path "/customerId" \
    --throughput 400

# Service Bus
az servicebus namespace create \
    --resource-group $RESOURCE_GROUP \
    --name sb-my-api-prod-eastus \
    --sku Standard

az servicebus topic create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name sb-my-api-prod-eastus \
    --name order-events

az servicebus topic subscription create \
    --resource-group $RESOURCE_GROUP \
    --namespace-name sb-my-api-prod-eastus \
    --topic-name order-events \
    --name fulfillment-service \
    --max-delivery-count 5

# Function App (Consumption — Python 3.11)
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --name func-my-api-prod-eastus \
    --storage-account stmyapiprodeastus \
    --consumption-plan-location $LOCATION \
    --runtime python \
    --runtime-version "3.11" \
    --functions-version 4 \
    --os-type Linux \
    --assign-identity \
    --tags Environment=production

# Wire up App Settings (Key Vault references for secrets)
FUNC_IDENTITY=$(az functionapp identity show \
    --resource-group $RESOURCE_GROUP \
    --name func-my-api-prod-eastus \
    --query principalId --output tsv)

# Grant Function App access to read Cosmos DB key from Key Vault
# (Assumes Key Vault already exists — created with RBAC model)
az role assignment create \
    --assignee $FUNC_IDENTITY \
    --role "Key Vault Secrets User" \
    --scope $(az keyvault show \
        --name kv-my-api-prod-eastus \
        --query id --output tsv)

az functionapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name func-my-api-prod-eastus \
    --settings \
        APPLICATIONINSIGHTS_CONNECTION_STRING=$(az monitor app-insights component show \
            --resource-group $RESOURCE_GROUP \
            --app appi-my-api-prod-eastus \
            --query connectionString --output tsv) \
        COSMOS_ENDPOINT="https://cosmos-my-api-prod-eastus.documents.azure.com:443/" \
        COSMOS_KEY="@Microsoft.KeyVault(SecretUri=https://kv-my-api-prod-eastus.vault.azure.net/secrets/cosmos-key/)" \
        SERVICEBUS_CONN="@Microsoft.KeyVault(SecretUri=https://kv-my-api-prod-eastus.vault.azure.net/secrets/servicebus-conn/)"
```

**Cost estimate (low traffic):** ~$5–15/month (Cosmos 400 RU/s + Service Bus Standard + Functions Consumption + Application Insights).

---

## Project Cost Summary

| Project | Key Services | Estimated Monthly Cost |
|---------|-------------|----------------------|
| Static Website | Blob + CDN | ~$2–5 |
| Hub-and-Spoke Network | VNet + Firewall + Bastion | ~$1,500+ (Firewall ~$900/mo) |
| AKS Microservice | AKS (3× D4s_v5) + ACR Premium | ~$500–700 |
| Serverless API | Functions + Cosmos + Service Bus + App Insights | ~$5–50 (traffic-dependent) |

> Costs are approximate and vary by region, traffic, and retention settings. Use the [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) for accurate estimates.

---

## References

- [Azure Architecture Center](https://docs.microsoft.com/azure/architecture/)
- [Azure Reference Architectures](https://docs.microsoft.com/azure/architecture/reference-architectures/)
- [Azure Well-Architected Framework](https://docs.microsoft.com/azure/architecture/framework/)
- [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/)
---

← [Previous: Terraform on Azure](../11-iac/terraform-azure.md) | [Home](../../README.md) | [Next: Static Website →](./static-website.md)
