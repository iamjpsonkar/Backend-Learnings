← [Previous: AKS](./aks.md) | [Home](../../README.md) | [Next: Azure Serverless →](../08-serverless/README.md)

---

# Azure Container Instances (ACI)

ACI runs containers on-demand without managing any infrastructure. It is best for short-lived tasks, batch jobs, CI/CD build steps, and burst compute alongside AKS (virtual nodes).

---

## ACI vs AKS vs App Service

| Feature | ACI | AKS | App Service |
|---------|-----|-----|-------------|
| Infrastructure management | None | Node pools | None |
| Startup time | Seconds | Minutes (node scale) | Seconds |
| Persistent state | No (ephemeral) | PVC | Storage mounts |
| Networking | VNet injection or public IP | VNet | VNet integration |
| Orchestration | None (use container groups) | Full Kubernetes | Platform-managed |
| Use case | Jobs, burst, CI/CD | Long-running microservices | Web apps, APIs |

---

## Container Groups

ACI deploys **container groups** — one or more containers that share a network namespace, lifecycle, and storage. Equivalent to a Kubernetes pod.

---

## Running a Container

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"

# Run a single container (public image, public IP)
az container create \
    --resource-group $RESOURCE_GROUP \
    --name aci-job-001 \
    --image mcr.microsoft.com/azuredocs/aci-helloworld \
    --cpu 1 \
    --memory 1.5 \
    --restart-policy Never \
    --os-type Linux \
    --ports 80 \
    --dns-name-label aci-my-app-demo

# Run from ACR (using managed identity)
az container create \
    --resource-group $RESOURCE_GROUP \
    --name aci-job-002 \
    --image acrmyappprodeastus.azurecr.io/my-batch-job:latest \
    --cpu 2 \
    --memory 4 \
    --restart-policy Never \
    --assign-identity $(az identity show \
        --resource-group $RESOURCE_GROUP \
        --name id-my-app-workload --query id -o tsv) \
    --acr-identity $(az identity show \
        --resource-group $RESOURCE_GROUP \
        --name id-my-app-workload --query id -o tsv) \
    --environment-variables \
        ENV=production \
    --secure-environment-variables \
        DB_PASSWORD=secret123

# Get container logs
az container logs \
    --resource-group $RESOURCE_GROUP \
    --name aci-job-002

# Show container details
az container show \
    --resource-group $RESOURCE_GROUP \
    --name aci-job-002 \
    --query '{State:instanceView.state,StartTime:instanceView.currentState.startTime,ExitCode:instanceView.currentState.exitCode}' \
    --output json

# Delete when done
az container delete \
    --resource-group $RESOURCE_GROUP \
    --name aci-job-002 \
    --yes
```

---

## Multi-Container Group (YAML)

```yaml
# container-group.yaml
apiVersion: 2021-10-01
name: aci-multi-container
location: eastus
properties:
  containers:
    - name: app
      properties:
        image: acrmyappprodeastus.azurecr.io/my-app:latest
        resources:
          requests:
            cpu: 1
            memoryInGB: 2
        ports:
          - port: 8080
        environmentVariables:
          - name: ENV
            value: production
          - name: DB_PASSWORD
            secureValue: "$(DB_PASSWORD)"
        volumeMounts:
          - name: shared-data
            mountPath: /data

    - name: log-exporter
      properties:
        image: fluent/fluent-bit:latest
        resources:
          requests:
            cpu: 0.5
            memoryInGB: 0.5
        volumeMounts:
          - name: shared-data
            mountPath: /data

  volumes:
    - name: shared-data
      emptyDir: {}

  osType: Linux
  restartPolicy: Never

  imageRegistryCredentials:
    - server: acrmyappprodeastus.azurecr.io
      identity: /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-my-app-workload

  ipAddress:
    type: Private
    ports:
      - port: 8080

  subnetIds:
    - id: /subscriptions/$SUBSCRIPTION_ID/resourceGroups/rg-my-app-prod-eastus/providers/Microsoft.Network/virtualNetworks/vnet-my-app-prod-eastus-001/subnets/snet-app
```

```bash
# Deploy from YAML
az container create \
    --resource-group $RESOURCE_GROUP \
    --file container-group.yaml
```

---

## VNet Injection

```bash
# Create ACI in a VNet subnet (no public IP — private connectivity)
az container create \
    --resource-group $RESOURCE_GROUP \
    --name aci-private-job \
    --image acrmyappprodeastus.azurecr.io/my-job:latest \
    --cpu 2 \
    --memory 4 \
    --restart-policy Never \
    --vnet vnet-my-app-prod-eastus-001 \
    --subnet snet-app \
    --no-wait  # Long-running jobs — don't block

# Check status later
az container show \
    --resource-group $RESOURCE_GROUP \
    --name aci-private-job \
    --query 'instanceView.state'
```

---

## ACI as AKS Virtual Nodes (Burst)

AKS can schedule pods onto ACI instead of node VMs when node pools are full — instant burst capacity.

```bash
# Enable virtual nodes add-on
az aks enable-addons \
    --resource-group $RESOURCE_GROUP \
    --name aks-my-app-prod-eastus-001 \
    --addons virtual-node \
    --subnet-name snet-aci  # Dedicated subnet for ACI-scheduled pods
```

```yaml
# Schedule a burst pod to virtual node (ACI)
apiVersion: v1
kind: Pod
metadata:
  name: burst-job
spec:
  nodeSelector:
    kubernetes.io/role: agent
    beta.kubernetes.io/os: linux
    type: virtual-kubelet
  tolerations:
    - key: virtual-kubelet.io/provider
      operator: Exists
  containers:
    - name: burst
      image: acrmyappprodeastus.azurecr.io/my-batch:latest
      resources:
        requests:
          cpu: "4"
          memory: "8Gi"
```

---

## Useful Commands

```bash
# List all container instances
az container list \
    --resource-group $RESOURCE_GROUP \
    --output table

# Execute a command inside a running container
az container exec \
    --resource-group $RESOURCE_GROUP \
    --name aci-job-001 \
    --exec-command "/bin/sh"

# Attach to container output stream
az container attach \
    --resource-group $RESOURCE_GROUP \
    --name aci-job-001

# Get events (useful for debugging pull failures)
az container show \
    --resource-group $RESOURCE_GROUP \
    --name aci-job-001 \
    --query 'containers[0].instanceView.events[*].{Type:type,Message:message,Time:firstTimestamp}' \
    --output table
```

---

## References

- [Azure Container Instances documentation](https://docs.microsoft.com/azure/container-instances/)
- [Container groups](https://docs.microsoft.com/azure/container-instances/container-instances-container-groups)
- [Virtual nodes with AKS](https://docs.microsoft.com/azure/aks/virtual-nodes)

---

← [Previous: AKS](./aks.md) | [Home](../../README.md) | [Next: Azure Serverless →](../08-serverless/README.md)
