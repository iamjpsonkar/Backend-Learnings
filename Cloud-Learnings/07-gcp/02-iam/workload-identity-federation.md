← [Previous: Service Accounts](./service-accounts.md) | [Home](../../README.md) | [Next: GCP Networking →](../03-networking/README.md)

---

# GCP Workload Identity Federation

Workload Identity Federation lets external workloads (GitHub Actions, AWS, on-premises) authenticate to GCP without service account key files — using short-lived tokens from their own identity provider.

---

## How It Works

```
GitHub Actions job
  │
  ├── GitHub issues OIDC token (JWT)
  │   (sub: repo:my-org/my-repo:ref:refs/heads/main)
  │
  ▼
GCP Workload Identity Pool + Provider
  ├── Validates the JWT against GitHub's JWKS endpoint
  ├── Maps token claims to a service account
  │
  ▼
Service Account Token
  └── Short-lived access token for GCP APIs
```

---

## Setup — GitHub Actions OIDC

```bash
PROJECT="my-app-prod-123456"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format="value(projectNumber)")
SA_EMAIL="sa-github-deploy@$PROJECT.iam.gserviceaccount.com"

# 1. Create a Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
    --location=global \
    --display-name="GitHub Actions Pool" \
    --description="Federated identity for GitHub Actions CI/CD" \
    --project=$PROJECT

# 2. Create a Provider within the pool (GitHub's OIDC)
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --location=global \
    --workload-identity-pool=github-pool \
    --display-name="GitHub OIDC Provider" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository == 'my-org/my-app'" \
    --project=$PROJECT

# 3. Create the service account
gcloud iam service-accounts create sa-github-deploy \
    --display-name="GitHub Actions Deploy SA" \
    --project=$PROJECT

# 4. Grant deploy permissions to the SA
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.developer"

gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/container.developer"

gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/artifactregistry.writer"

# 5. Allow the Workload Identity Pool to impersonate the SA
# For a specific repo (most restrictive — recommended)
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/my-org/my-app" \
    --role="roles/iam.workloadIdentityUser" \
    --project=$PROJECT

# For main branch only (even more restrictive)
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --member="principal://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/subject/repo:my-org/my-app:ref:refs/heads/main" \
    --role="roles/iam.workloadIdentityUser" \
    --project=$PROJECT

# 6. Get the Workload Identity Provider resource name (needed in GitHub Actions)
gcloud iam workload-identity-pools providers describe github-provider \
    --location=global \
    --workload-identity-pool=github-pool \
    --project=$PROJECT \
    --format="value(name)"
# Output: projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

---

## GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to GCP

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  id-token: write   # Required for OIDC token request
  contents: read

env:
  PROJECT_ID: my-app-prod-123456
  REGION: us-central1

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP (OIDC — no key files)
        id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: "projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
          service_account: "sa-github-deploy@my-app-prod-123456.iam.gserviceaccount.com"

      - name: Setup gcloud
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

      - name: Build and Push
        run: |
          IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/my-app/api:${{ github.sha }}"
          docker build -t $IMAGE .
          docker push $IMAGE

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy my-app \
            --image="$REGION-docker.pkg.dev/$PROJECT_ID/my-app/api:${{ github.sha }}" \
            --region=$REGION \
            --project=$PROJECT_ID
```

---

## GKE Workload Identity

GKE Workload Identity lets pods authenticate as a GCP service account without key files.

```bash
PROJECT="my-app-prod-123456"
CLUSTER_NAME="gke-my-app-prod-us-central1"
NAMESPACE="my-app"
KSA_NAME="my-app-sa"  # Kubernetes ServiceAccount name
GSA_EMAIL="sa-my-app@$PROJECT.iam.gserviceaccount.com"

# 1. Create GCP service account (if not exists)
gcloud iam service-accounts create sa-my-app \
    --display-name="My App GKE Workload SA" \
    --project=$PROJECT

# 2. Grant permissions to the GSA
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$GSA_EMAIL" \
    --role="roles/secretmanager.secretAccessor"

# 3. Enable Workload Identity on GKE cluster (if not already)
gcloud container clusters update $CLUSTER_NAME \
    --region=us-central1 \
    --workload-pool="$PROJECT.svc.id.goog"

# 4. Create Kubernetes namespace and ServiceAccount
kubectl create namespace $NAMESPACE
kubectl create serviceaccount $KSA_NAME --namespace=$NAMESPACE

# 5. Bind the Kubernetes SA to the GCP SA
gcloud iam service-accounts add-iam-policy-binding $GSA_EMAIL \
    --member="serviceAccount:$PROJECT.svc.id.goog[$NAMESPACE/$KSA_NAME]" \
    --role="roles/iam.workloadIdentityUser" \
    --project=$PROJECT

# 6. Annotate the Kubernetes ServiceAccount
kubectl annotate serviceaccount $KSA_NAME \
    --namespace=$NAMESPACE \
    "iam.gke.io/gcp-service-account=$GSA_EMAIL"

# 7. In your Pod spec:
# spec:
#   serviceAccountName: my-app-sa
# No other changes needed — ADC automatically uses the Workload Identity token
```

---

## Setup — AWS Workload Identity Federation

```bash
# Allow an AWS role to authenticate to GCP
gcloud iam workload-identity-pools providers create-aws aws-provider \
    --location=global \
    --workload-identity-pool=my-pool \
    --display-name="AWS Provider" \
    --account-id="123456789012" \  # AWS Account ID
    --project=$PROJECT

gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/my-pool/attribute.aws_role/arn:aws:sts::123456789012:assumed-role/my-aws-role" \
    --role="roles/iam.workloadIdentityUser"
```

---

## Listing and Debugging

```bash
# List pools and providers
gcloud iam workload-identity-pools list \
    --location=global --project=$PROJECT --format="table(name,displayName,state)"

gcloud iam workload-identity-pools providers list \
    --location=global \
    --workload-identity-pool=github-pool \
    --project=$PROJECT

# Debug: verify attribute mapping for a token
gcloud iam workload-identity-pools providers describe github-provider \
    --location=global \
    --workload-identity-pool=github-pool \
    --project=$PROJECT \
    --format="json(attributeMapping,attributeCondition)"

# Check SA's workload identity bindings
gcloud iam service-accounts get-iam-policy $SA_EMAIL \
    --project=$PROJECT \
    --format="yaml(bindings)"
```

---

## References

- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GitHub Actions OIDC](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions)
- [GKE Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [google-github-actions/auth](https://github.com/google-github-actions/auth)

---

← [Previous: Service Accounts](./service-accounts.md) | [Home](../../README.md) | [Next: GCP Networking →](../03-networking/README.md)
