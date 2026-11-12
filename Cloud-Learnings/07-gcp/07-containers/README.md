← [Previous: BigQuery](../06-databases/bigquery.md) | [Home](../../README.md) | [Next: Artifact Registry →](./artifact-registry.md)

---

# GCP Containers

---

## Service Overview

| Service | AWS Equivalent | Use Case |
|---------|----------------|---------|
| **Artifact Registry** | ECR | Container image registry (also packages: Maven, npm, Python) |
| **Cloud Build** | CodeBuild | Managed CI — build, test, push images |
| **Google Kubernetes Engine (GKE)** | EKS | Managed Kubernetes |
| **Cloud Run** | ECS Fargate / App Runner | Serverless containers — no cluster management |
| **Cloud Run Jobs** | ECS run-task / AWS Batch | One-off or scheduled container jobs |

---

## Artifact Registry

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"

# Create a Docker repository
gcloud artifacts repositories create my-app \
    --project=$PROJECT_ID \
    --repository-format=docker \
    --location=$REGION \
    --description="My App container images" \
    --labels=environment=production

# Authenticate Docker to Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push (using Cloud Build — no local Docker needed)
gcloud builds submit \
    --project=$PROJECT_ID \
    --region=$REGION \
    --tag=${REGION}-docker.pkg.dev/${PROJECT_ID}/my-app/backend:v1.2.3 \
    --timeout=20m \
    .

# Tag and push locally
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/my-app/backend:v1.2.3 .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/my-app/backend:v1.2.3

# List images and tags
gcloud artifacts docker images list ${REGION}-docker.pkg.dev/${PROJECT_ID}/my-app \
    --include-tags \
    --format="table(IMAGE,TAGS,CREATE_TIME,UPDATE_TIME)"

# Configure cleanup policy (keep last 10 tagged, delete untagged after 7 days)
gcloud artifacts repositories set-cleanup-policies my-app \
    --project=$PROJECT_ID \
    --location=$REGION \
    --policy=cleanup-policy.json
```

```json
[
  {
    "name": "keep-tagged",
    "action": {"type": "Keep"},
    "mostRecentVersions": {"keepCount": 10}
  },
  {
    "name": "delete-untagged",
    "action": {"type": "Delete"},
    "condition": {"tagState": "UNTAGGED", "olderThan": "7d"}
  }
]
```

---

## Cloud Build

```yaml
# cloudbuild.yaml — build, test, push
steps:
  # Run unit tests
  - name: "python:3.11-slim"
    id: test
    entrypoint: bash
    args:
      - -c
      - |
        pip install -r requirements.txt
        python -m pytest tests/unit -v --junitxml=test-results.xml
    env:
      - "ENV=test"

  # Build Docker image with cache
  - name: "gcr.io/cloud-builders/docker"
    id: build
    args:
      - build
      - --cache-from
      - "${_REGION}-docker.pkg.dev/$PROJECT_ID/my-app/backend:latest"
      - --tag
      - "${_REGION}-docker.pkg.dev/$PROJECT_ID/my-app/backend:$COMMIT_SHA"
      - --tag
      - "${_REGION}-docker.pkg.dev/$PROJECT_ID/my-app/backend:latest"
      - .

  # Push image
  - name: "gcr.io/cloud-builders/docker"
    id: push
    args:
      - push
      - "--all-tags"
      - "${_REGION}-docker.pkg.dev/$PROJECT_ID/my-app/backend"

  # Deploy to Cloud Run (staging)
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    id: deploy-staging
    args:
      - run
      - deploy
      - my-app-api-staging
      - --image=${_REGION}-docker.pkg.dev/$PROJECT_ID/my-app/backend:$COMMIT_SHA
      - --region=${_REGION}
      - --project=$PROJECT_ID

substitutions:
  _REGION: us-central1

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: E2_HIGHCPU_8

artifacts:
  objects:
    location: "gs://${PROJECT_ID}-build-artifacts/"
    paths: ["test-results.xml"]
```

```bash
# Submit a build manually
gcloud builds submit \
    --project=$PROJECT_ID \
    --config=cloudbuild.yaml \
    --substitutions=_REGION=us-central1 \
    .

# Create a build trigger (GitHub push → build)
gcloud builds triggers create github \
    --project=$PROJECT_ID \
    --name="push-to-main" \
    --repo-owner=your-org \
    --repo-name=your-repo \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml \
    --region=$REGION

# List recent builds
gcloud builds list --project=$PROJECT_ID --limit=10 \
    --format="table(id,status,startTime,finishTime,source.repoSource.branchName)"
```

---

## Google Kubernetes Engine (GKE)

### Create a Cluster (Autopilot — recommended)

GKE Autopilot manages node provisioning, scaling, and security automatically. Pay per pod, not per node.

```bash
# Create Autopilot cluster (no node pool management needed)
gcloud container clusters create-auto gke-my-app-prod-us-central1 \
    --project=$PROJECT_ID \
    --region=$REGION \
    --network=vpc-my-app-prod \
    --subnetwork=snet-gke-us-central1 \
    --cluster-secondary-range-name=pods \
    --services-secondary-range-name=services \
    --enable-private-nodes \
    --master-ipv4-cidr=172.16.0.0/28 \
    --enable-master-authorized-networks \
    --master-authorized-networks=10.0.0.0/8 \
    --labels=environment=production

# Get credentials
gcloud container clusters get-credentials gke-my-app-prod-us-central1 \
    --project=$PROJECT_ID \
    --region=$REGION

kubectl get nodes
```

### Create a Standard Cluster (with node pools — more control)

```bash
# Standard cluster with 3-zone node pool
gcloud container clusters create gke-my-app-standard-us-central1 \
    --project=$PROJECT_ID \
    --region=$REGION \
    --num-nodes=1 \
    --node-locations=us-central1-a,us-central1-b,us-central1-c \
    --machine-type=n2-standard-4 \
    --disk-type=pd-ssd \
    --disk-size=100 \
    --network=vpc-my-app-prod \
    --subnetwork=snet-gke-us-central1 \
    --cluster-secondary-range-name=pods \
    --services-secondary-range-name=services \
    --enable-private-nodes \
    --master-ipv4-cidr=172.16.0.0/28 \
    --enable-ip-alias \
    --workload-pool=${PROJECT_ID}.svc.id.goog \
    --enable-autoscaling \
    --min-nodes=1 \
    --max-nodes=10 \
    --enable-autorepair \
    --enable-autoupgrade \
    --labels=environment=production \
    --release-channel=regular

# Add a Spot node pool (cost-optimized for batch/ML)
gcloud container node-pools create spot-pool \
    --project=$PROJECT_ID \
    --cluster=gke-my-app-standard-us-central1 \
    --region=$REGION \
    --machine-type=n2-standard-4 \
    --spot \
    --num-nodes=0 \
    --enable-autoscaling \
    --min-nodes=0 \
    --max-nodes=20 \
    --node-taints=cloud.google.com/gke-spot=true:NoSchedule
```

### Workload Identity (IRSA equivalent)

Workload Identity links a Kubernetes service account to a GCP service account — no key files needed.

```bash
# Kubernetes service account
kubectl create namespace my-app
kubectl create serviceaccount my-app-sa --namespace my-app

# GCP service account
SA_EMAIL="my-app-workload@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud iam service-accounts create my-app-workload \
    --project=$PROJECT_ID \
    --display-name="My App GKE Workload"

# Grant the GCP SA roles it needs
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudtrace.agent"

# Bind: allow KSA to impersonate the GCP SA
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --project=$PROJECT_ID \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:${PROJECT_ID}.svc.id.goog[my-app/my-app-sa]"

# Annotate the Kubernetes service account
kubectl annotate serviceaccount my-app-sa \
    --namespace=my-app \
    iam.gke.io/gcp-service-account=$SA_EMAIL
```

### Deployment Manifest

```yaml
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
        image: us-central1-docker.pkg.dev/my-app-production/my-app/backend:v1.2.3
        ports:
        - containerPort: 8080
        env:
        - name: GCP_PROJECT_ID
          value: my-app-production
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
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app-api
  namespace: my-app
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app-api
```

---

## Cloud Run

Cloud Run is the recommended option for stateless HTTP services. No cluster management, auto-scales to zero.

```bash
# Deploy from Artifact Registry
gcloud run deploy my-app-api \
    --project=$PROJECT_ID \
    --region=$REGION \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/my-app/backend:v1.2.3 \
    --platform=managed \
    --service-account=my-app-workload@${PROJECT_ID}.iam.gserviceaccount.com \
    --no-allow-unauthenticated \
    --vpc-connector=vpc-connector-us-central1 \
    --vpc-egress=private-ranges-only \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=100 \
    --concurrency=80 \
    --timeout=30 \
    --set-env-vars=GCP_PROJECT_ID=$PROJECT_ID,APP_ENV=production \
    --set-secrets=DB_PASSWORD=api-database-password:latest \
    --labels=environment=production

# Allow invocation from the load balancer's service account
gcloud run services add-iam-policy-binding my-app-api \
    --project=$PROJECT_ID \
    --region=$REGION \
    --member="serviceAccount:lb-invoker@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.invoker"

# Deploy a new revision and split traffic (canary)
gcloud run services update-traffic my-app-api \
    --project=$PROJECT_ID \
    --region=$REGION \
    --to-revisions=my-app-api-00100-xyz=10,LATEST=90  # 10% canary

# Fully migrate to latest
gcloud run services update-traffic my-app-api \
    --project=$PROJECT_ID \
    --region=$REGION \
    --to-latest

# Run a one-off job
gcloud run jobs create db-migration \
    --project=$PROJECT_ID \
    --region=$REGION \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/my-app/backend:v1.2.3 \
    --service-account=my-app-workload@${PROJECT_ID}.iam.gserviceaccount.com \
    --command="python" \
    --args="manage.py,migrate" \
    --set-env-vars=GCP_PROJECT_ID=$PROJECT_ID \
    --max-retries=3 \
    --task-timeout=600

gcloud run jobs execute db-migration \
    --project=$PROJECT_ID \
    --region=$REGION \
    --wait
```

---

## References

- [Artifact Registry documentation](https://cloud.google.com/artifact-registry/docs)
- [Cloud Build documentation](https://cloud.google.com/build/docs)
- [GKE documentation](https://cloud.google.com/kubernetes-engine/docs)
- [GKE Autopilot overview](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview)
- [Cloud Run documentation](https://cloud.google.com/run/docs)
- [GKE Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
---

← [Previous: BigQuery](../06-databases/bigquery.md) | [Home](../../README.md) | [Next: Artifact Registry →](./artifact-registry.md)
