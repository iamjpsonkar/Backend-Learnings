← [Previous: Static Website](./static-website.md) | [Home](../../README.md) | [Next: GCP →](../../07-gcp/README.md)

---

# Project: Microservice Deployment on AKS

Deploy a production-grade Python microservice on AKS with private ACR, Workload Identity for secretless Azure service access, Horizontal Pod Autoscaler, and full observability.

---

## Architecture

```
GitHub Actions CI/CD
  │
  ▼ (docker build + push)
Azure Container Registry (acrmyappprodeastus.azurecr.io)
  │
  ▼ (image pull via AcrPull role)
AKS Cluster (aks-my-app-prod-eastus-001)
  ├── Namespace: my-app
  ├── Deployment: my-app (3 replicas, anti-affinity across zones)
  ├── HPA: 3–20 replicas on CPU/memory
  ├── Service: ClusterIP + Ingress (AGIC or ingress-nginx)
  └── ServiceAccount + Workload Identity → Key Vault, Cosmos DB, Redis

Private networking:
  ├── ACR Private Endpoint
  ├── Key Vault Private Endpoint
  └── Cosmos DB Private Endpoint
```

---

## 1. Infrastructure Prerequisites

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
CLUSTER_NAME="aks-my-app-prod-eastus-001"
ACR_NAME="acrmyappprodeastus"
KV_NAME="kv-my-app-prod-eastus"
NAMESPACE="my-app"

# Ensure AKS has Workload Identity enabled (see aks.md)
# Ensure ACR is attached to AKS with AcrPull role
# Ensure Key Vault private endpoint exists (see key-vault.md)

# Create Kubernetes namespace
kubectl create namespace $NAMESPACE
kubectl label namespace $NAMESPACE \
    azure.workload.identity/use=true \
    environment=production
```

---

## 2. Workload Identity Setup

```bash
# Create user-assigned managed identity
az identity create \
    --resource-group $RESOURCE_GROUP \
    --name id-my-app-workload

CLIENT_ID=$(az identity show \
    --resource-group $RESOURCE_GROUP \
    --name id-my-app-workload --query clientId -o tsv)

PRINCIPAL_ID=$(az identity show \
    --resource-group $RESOURCE_GROUP \
    --name id-my-app-workload --query principalId -o tsv)

# Grant identity access to Azure services
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Key Vault Secrets User" \
    --scope $(az keyvault show --resource-group $RESOURCE_GROUP \
        --name $KV_NAME --query id -o tsv)

az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Cosmos DB Built-in Data Contributor" \
    --scope $(az cosmosdb show --resource-group $RESOURCE_GROUP \
        --name cosmos-my-app-prod-eastus --query id -o tsv)

# Get OIDC issuer URL
OIDC_ISSUER=$(az aks show \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --query "oidcIssuerProfile.issuerUrl" -o tsv)

# Create federated identity credential
az identity federated-credential create \
    --resource-group $RESOURCE_GROUP \
    --identity-name id-my-app-workload \
    --name aks-my-app \
    --issuer $OIDC_ISSUER \
    --subject "system:serviceaccount:$NAMESPACE:my-app-sa" \
    --audiences "api://AzureADTokenExchange"
```

---

## 3. Kubernetes Manifests

```yaml
# k8s/serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: my-app
  annotations:
    azure.workload.identity/client-id: "YOUR_CLIENT_ID"  # From $CLIENT_ID above
  labels:
    azure.workload.identity/use: "true"
```

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-app
  labels:
    app: my-app
    version: "1.0.0"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: my-app
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: my-app-sa
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: my-app

      containers:
        - name: my-app
          image: acrmyappprodeastus.azurecr.io/my-app:1.0.0
          ports:
            - containerPort: 8080
              name: http

          env:
            - name: ENV
              value: production
            - name: KEY_VAULT_URL
              value: "https://kv-my-app-prod-eastus.vault.azure.net"
            - name: COSMOS_ACCOUNT_URL
              value: "https://cosmos-my-app-prod-eastus.documents.azure.com:443/"
            - name: APPLICATIONINSIGHTS_CONNECTION_STRING
              valueFrom:
                secretKeyRef:
                  name: my-app-secrets
                  key: appinsights-connection-string

          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 1000m
              memory: 512Mi

          readinessProbe:
            httpGet:
              path: /healthz/ready
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3

          livenessProbe:
            httpGet:
              path: /healthz/live
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 30
            failureThreshold: 3

          startupProbe:
            httpGet:
              path: /healthz/live
              port: 8080
            failureThreshold: 30
            periodSeconds: 5

          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]

      securityContext:
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
```

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: my-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 25
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
```

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: my-app
spec:
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
      name: http
---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  namespace: my-app
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  tls:
    - hosts:
        - api.example.com
      secretName: my-app-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-app
                port:
                  name: http
```

---

## 4. CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  id-token: write
  contents: read

env:
  ACR_NAME: acrmyappprodeastus
  CLUSTER_NAME: aks-my-app-prod-eastus-001
  RESOURCE_GROUP: rg-my-app-prod-eastus
  NAMESPACE: my-app

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.tag.outputs.tag }}

    steps:
      - uses: actions/checkout@v4

      - name: Generate image tag
        id: tag
        run: echo "tag=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT

      - name: Azure Login
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Build and push with ACR Tasks
        run: |
          az acr build \
            --registry $ACR_NAME \
            --image "my-app:${{ steps.tag.outputs.tag }}" \
            --image "my-app:latest" \
            --file Dockerfile .

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'

    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Get AKS credentials
        run: |
          az aks get-credentials \
            --resource-group $RESOURCE_GROUP \
            --name $CLUSTER_NAME \
            --overwrite-existing

      - name: Deploy to AKS
        run: |
          IMAGE="${ACR_NAME}.azurecr.io/my-app:${{ needs.build-and-push.outputs.image-tag }}"
          kubectl set image deployment/my-app my-app=$IMAGE -n $NAMESPACE
          kubectl rollout status deployment/my-app -n $NAMESPACE --timeout=5m

      - name: Verify deployment
        run: |
          kubectl get pods -n $NAMESPACE -l app=my-app
          kubectl get hpa -n $NAMESPACE
```

---

## 5. Monitoring and Alerts

```bash
# Alert when pod restart count > 5 in 5 minutes
az monitor scheduled-query create \
    --resource-group rg-platform-monitoring-eastus \
    --name "aks-pod-restarts-alert" \
    --scopes $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus --query id -o tsv) \
    --condition-query "KubePodInventory | where Namespace == 'my-app' | where PodRestartCount > 5 | where TimeGenerated > ago(5m)" \
    --condition "count > 0" \
    --evaluation-frequency PT5M \
    --window-duration PT5M \
    --severity 2 \
    --action-groups $(az monitor action-group show \
        --resource-group rg-platform-monitoring-eastus \
        --name ag-platform-alerts --query id -o tsv)
```

---

← [Previous: Static Website](./static-website.md) | [Home](../../README.md) | [Next: GCP →](../../07-gcp/README.md)
