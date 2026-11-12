← [Previous: Cloud Build](./cloud-build.md) | [Home](../../README.md) | [Next: Cloud Run →](./cloud-run.md)

---

# Google Kubernetes Engine (GKE)

GKE is a fully managed Kubernetes service. It supports two modes: **Autopilot** (Google manages nodes) and **Standard** (you manage nodes). Autopilot is recommended for most production workloads.

---

## Autopilot vs Standard

| Feature | Autopilot | Standard |
|---------|-----------|----------|
| Node management | Google | You |
| Billing | Per Pod (CPU/memory/storage) | Per node |
| Node pools | Not configurable | Fully configurable |
| GPUs/TPUs | Limited | Full support |
| OS configuration | Locked | Configurable |
| Best for | Most workloads | Custom hardware, GPUs |

---

## Creating a Cluster

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"
CLUSTER="gke-my-app-prod"
NETWORK="vpc-my-app-prod"
SUBNET="subnet-gke-prod"

# --- Autopilot cluster (recommended) ---
gcloud container clusters create-auto $CLUSTER \
    --project=$PROJECT \
    --region=$REGION \
    --network=projects/$PROJECT/global/networks/$NETWORK \
    --subnetwork=projects/$PROJECT/regions/$REGION/subnetworks/$SUBNET \
    --cluster-secondary-range-name=pods \
    --services-secondary-range-name=services \
    --enable-private-nodes \
    --master-ipv4-cidr=172.16.0.0/28 \
    --enable-master-authorized-networks \
    --master-authorized-networks=10.0.0.0/8 \
    --workload-pool=$PROJECT.svc.id.goog \
    --labels=environment=production,team=platform

# --- Standard cluster (when you need node control) ---
gcloud container clusters create $CLUSTER \
    --project=$PROJECT \
    --region=$REGION \
    --num-nodes=1 \
    --machine-type=e2-standard-4 \
    --disk-size=100 \
    --disk-type=pd-ssd \
    --image-type=COS_CONTAINERD \
    --network=$NETWORK \
    --subnetwork=$SUBNET \
    --cluster-secondary-range-name=pods \
    --services-secondary-range-name=services \
    --enable-private-nodes \
    --master-ipv4-cidr=172.16.0.0/28 \
    --enable-master-authorized-networks \
    --master-authorized-networks=10.0.0.0/8 \
    --workload-pool=$PROJECT.svc.id.goog \
    --enable-shielded-nodes \
    --shielded-secure-boot \
    --shielded-integrity-monitoring \
    --enable-autoscaling \
    --min-nodes=1 \
    --max-nodes=10 \
    --enable-autorepair \
    --enable-autoupgrade \
    --maintenance-window-start="2024-01-01T02:00:00Z" \
    --maintenance-window-end="2024-01-01T06:00:00Z" \
    --maintenance-window-recurrence="FREQ=WEEKLY;BYDAY=SA,SU" \
    --release-channel=regular \
    --labels=environment=production

# Get credentials
gcloud container clusters get-credentials $CLUSTER \
    --project=$PROJECT \
    --region=$REGION
```

---

## Node Pools (Standard Only)

```bash
# Add a high-memory node pool
gcloud container node-pools create high-memory-pool \
    --project=$PROJECT \
    --cluster=$CLUSTER \
    --region=$REGION \
    --machine-type=n2-highmem-8 \
    --num-nodes=1 \
    --min-nodes=0 \
    --max-nodes=5 \
    --enable-autoscaling \
    --disk-size=200 \
    --disk-type=pd-ssd \
    --image-type=COS_CONTAINERD \
    --node-taints=workload=memory-intensive:NoSchedule \
    --node-labels=workload=memory-intensive \
    --enable-autorepair \
    --enable-autoupgrade

# Add a GPU node pool
gcloud container node-pools create gpu-pool \
    --project=$PROJECT \
    --cluster=$CLUSTER \
    --region=$REGION \
    --machine-type=n1-standard-8 \
    --accelerator=type=nvidia-tesla-t4,count=1 \
    --num-nodes=0 \
    --min-nodes=0 \
    --max-nodes=4 \
    --enable-autoscaling \
    --node-taints=nvidia.com/gpu=present:NoSchedule

# List node pools
gcloud container node-pools list \
    --project=$PROJECT \
    --cluster=$CLUSTER \
    --region=$REGION

# Delete a node pool
gcloud container node-pools delete old-pool \
    --project=$PROJECT \
    --cluster=$CLUSTER \
    --region=$REGION
```

---

## Workload Identity

Workload Identity lets Pods authenticate to Google Cloud APIs using a Kubernetes service account bound to a GCP service account — no key files needed.

```bash
# 1. Ensure the cluster has Workload Identity enabled
gcloud container clusters update $CLUSTER \
    --project=$PROJECT \
    --region=$REGION \
    --workload-pool=$PROJECT.svc.id.goog

# 2. Create GCP service account
GCP_SA="sa-my-app@$PROJECT.iam.gserviceaccount.com"
gcloud iam service-accounts create sa-my-app \
    --project=$PROJECT \
    --display-name="My App GKE workload"

# 3. Grant necessary permissions to GCP SA
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$GCP_SA" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$GCP_SA" \
    --role="roles/secretmanager.secretAccessor"

# 4. Create Kubernetes service account
kubectl create serviceaccount my-app \
    --namespace=production

# 5. Bind KSA → GSA
gcloud iam service-accounts add-iam-policy-binding $GCP_SA \
    --project=$PROJECT \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:$PROJECT.svc.id.goog[production/my-app]"

# 6. Annotate the KSA
kubectl annotate serviceaccount my-app \
    --namespace=production \
    iam.gke.io/gcp-service-account=$GCP_SA
```

---

## Kubernetes Manifests

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: production
  labels:
    app: my-app
    version: "1.0"
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
        version: "1.0"
    spec:
      serviceAccountName: my-app  # KSA with Workload Identity
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: api
          image: us-central1-docker.pkg.dev/my-app-prod-123456/my-app/api:latest
          ports:
            - containerPort: 8080
          env:
            - name: GCP_PROJECT
              value: "my-app-prod-123456"
            - name: ENVIRONMENT
              value: "production"
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            failureThreshold: 3
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 5"]
      terminationGracePeriodSeconds: 30
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: my-app
---
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app
  namespace: production
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
          averageUtilization: 60
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 75
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: production
spec:
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
---
# ingress.yaml — uses GKE Ingress (creates Cloud Load Balancer)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  namespace: production
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "my-app-ip"
    networking.gke.io/managed-certificates: "my-app-cert"
    kubernetes.io/ingress.allow-http: "false"
spec:
  rules:
    - host: api.my-app.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-app
                port:
                  number: 80
---
# managed-certificate.yaml
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: my-app-cert
  namespace: production
spec:
  domains:
    - api.my-app.com
```

---

## Cluster Upgrades

```bash
# Check available versions
gcloud container get-server-config \
    --project=$PROJECT \
    --region=$REGION \
    --format="yaml(channels)"

# Upgrade control plane
gcloud container clusters upgrade $CLUSTER \
    --project=$PROJECT \
    --region=$REGION \
    --master \
    --cluster-version=1.30

# Upgrade a node pool
gcloud container clusters upgrade $CLUSTER \
    --project=$PROJECT \
    --region=$REGION \
    --node-pool=default-pool \
    --cluster-version=1.30

# Set release channel (auto-upgrades)
gcloud container clusters update $CLUSTER \
    --project=$PROJECT \
    --region=$REGION \
    --release-channel=regular
```

---

## Useful Operations

```bash
# List clusters
gcloud container clusters list --project=$PROJECT

# Resize a node pool
gcloud container clusters resize $CLUSTER \
    --project=$PROJECT \
    --region=$REGION \
    --node-pool=default-pool \
    --num-nodes=3

# View cluster credentials
kubectl config current-context
kubectl config get-clusters

# Cordon + drain a node (before maintenance)
kubectl cordon NODE_NAME
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# Check Pod resource usage
kubectl top pods -n production --sort-by=cpu
kubectl top nodes

# Describe a failing Pod
kubectl describe pod POD_NAME -n production
kubectl logs POD_NAME -n production --previous
```

---

## References

- [GKE documentation](https://cloud.google.com/kubernetes-engine/docs)
- [Autopilot overview](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [GKE security best practices](https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster)

---

← [Previous: Cloud Build](./cloud-build.md) | [Home](../../README.md) | [Next: Cloud Run →](./cloud-run.md)
