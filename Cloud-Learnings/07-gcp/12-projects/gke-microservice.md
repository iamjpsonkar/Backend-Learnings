← [Previous: Static Website](./static-website.md) | [Home](../../README.md) | [Next: Cloud Run API →](./cloud-run-api.md)

---

# Project: GKE Microservice

Deploy a production-grade microservice on a private GKE Autopilot cluster with Workload Identity, Cloud SQL, Secret Manager, Cloud Monitoring, and a full GitHub Actions CI/CD pipeline.

---

## Architecture

```
GitHub Actions
    │
    ├── Build & push image → Artifact Registry
    └── Deploy → GKE Autopilot (private)
                    │
           Workload Identity
                    │
           ┌────────┼────────────────────┐
           ▼        ▼                    ▼
      Cloud SQL  Secret Manager   Cloud Monitoring
    (PostgreSQL) (DB password,     (metrics, traces,
                  API keys)         logs via OTel)
```

---

## Prerequisites

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"
CLUSTER="gke-my-app-prod"
AR_REPO="us-central1-docker.pkg.dev/$PROJECT/my-app"
APP_SA="sa-my-app@$PROJECT.iam.gserviceaccount.com"

# 1. GKE cluster (see gke.md for creation)
# 2. Artifact Registry repo (see artifact-registry.md)
# 3. Cloud SQL instance (see cloud-sql.md)
# 4. App service account with required roles
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$APP_SA" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$APP_SA" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$APP_SA" \
    --role="roles/cloudtrace.agent"

gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$APP_SA" \
    --role="roles/monitoring.metricWriter"

gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$APP_SA" \
    --role="roles/logging.logWriter"

# 5. Workload Identity binding
gcloud iam service-accounts add-iam-policy-binding $APP_SA \
    --project=$PROJECT \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:$PROJECT.svc.id.goog[production/my-app]"
```

---

## Kubernetes Manifests

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    environment: production
---
# serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  namespace: production
  annotations:
    iam.gke.io/gcp-service-account: sa-my-app@my-app-prod-123456.iam.gserviceaccount.com
---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-app-config
  namespace: production
data:
  GCP_PROJECT: "my-app-prod-123456"
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  DB_HOST: "10.0.0.5"   # Cloud SQL private IP
  DB_PORT: "5432"
  DB_NAME: "my_app"
  DB_USER: "my_app"
---
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
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: my-app
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: api
          image: us-central1-docker.pkg.dev/my-app-prod-123456/my-app/api:COMMIT_SHA
          ports:
            - name: http
              containerPort: 8080
          envFrom:
            - configMapRef:
                name: my-app-config
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: my-app-secrets
                  key: db-password
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
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 5"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
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
# ingress.yaml
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

## External Secrets (Secret Manager → Kubernetes Secret)

```bash
# Option A: Use the External Secrets Operator (recommended)
# Install External Secrets Operator via Helm:
helm repo add external-secrets https://charts.external-secrets.io
helm upgrade --install external-secrets external-secrets/external-secrets \
    --namespace external-secrets \
    --create-namespace

# Create a SecretStore pointing to Secret Manager
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: gcp-secret-manager
  namespace: production
spec:
  provider:
    gcpsm:
      projectID: my-app-prod-123456
EOF

# Create an ExternalSecret
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: my-app-secrets
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: gcp-secret-manager
    kind: SecretStore
  target:
    name: my-app-secrets
    creationPolicy: Owner
  data:
    - secretKey: db-password
      remoteRef:
        key: db-password
        version: latest
EOF
```

---

## GitHub Actions CI/CD

```yaml
# .github/workflows/deploy-gke.yml
name: Deploy to GKE

on:
  push:
    branches: [main]
    paths: ["backend/**", "k8s/**"]

permissions:
  id-token: write
  contents: read

env:
  PROJECT_ID: my-app-prod-123456
  REGION: us-central1
  CLUSTER: gke-my-app-prod
  AR_REPO: us-central1-docker.pkg.dev/my-app-prod-123456/my-app
  IMAGE: api

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.CICD_SA_EMAIL }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev --quiet

      - name: Set image tag
        id: meta
        run: echo "tag=${{ env.AR_REPO }}/${{ env.IMAGE }}:${{ github.sha }}" >> $GITHUB_OUTPUT

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: backend
          push: true
          tags: |
            ${{ steps.meta.outputs.tag }}
            ${{ env.AR_REPO }}/${{ env.IMAGE }}:latest
          cache-from: type=registry,ref=${{ env.AR_REPO }}/${{ env.IMAGE }}:latest
          cache-to: type=inline

      - name: Get GKE credentials
        uses: google-github-actions/get-gke-credentials@v2
        with:
          cluster_name: ${{ env.CLUSTER }}
          location: ${{ env.REGION }}

      - name: Deploy to GKE
        run: |
          kubectl set image deployment/my-app \
              api=${{ steps.meta.outputs.tag }} \
              -n production

          kubectl rollout status deployment/my-app \
              -n production \
              --timeout=300s

      - name: Verify deployment
        run: |
          kubectl get pods -n production -l app=my-app
          kubectl get ingress my-app -n production
```

---

## References

- [GKE Autopilot](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [External Secrets Operator](https://external-secrets.io/latest/)
- [GKE security hardening](https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster)

---

← [Previous: Static Website](./static-website.md) | [Home](../../README.md) | [Next: Cloud Run API →](./cloud-run-api.md)
