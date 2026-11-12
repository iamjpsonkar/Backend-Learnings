← [Previous: Docker Compose](./docker-compose.md) | [Home](../README.md) | [Next: Kubernetes →](../10-kubernetes/README.md)

---

# Container Registries

A container registry stores and distributes container images. Registries provide versioning (tags), vulnerability scanning, access control, and geographic replication.

---

## Registry Comparison

| Registry | Provider | Type | Key Features |
|----------|---------|------|-------------|
| **Docker Hub** | Docker | Public + Private | Largest public registry, free public repos, rate-limited pulls |
| **Amazon ECR** | AWS | Private | Integrated with ECS/EKS, IAM auth, lifecycle policies |
| **Google Artifact Registry** | GCP | Private | Replaces GCR, supports Docker + Maven + npm + Python |
| **Azure Container Registry** | Azure | Private | Integrated with AKS, geo-replication, tasks |
| **GitHub Container Registry** | GitHub | Public + Private | Free for public repos, GHCR packages tied to repos |
| **Quay.io** | Red Hat | Public + Private | Strong security scanning, used by OpenShift |
| **Harbor** | CNCF OSS | Self-hosted | Full-featured, runs on any Kubernetes cluster |

---

## Docker Hub

```bash
# Authenticate
docker login
# Prompts for Docker Hub username and password/token
# Use a Personal Access Token (PAT) instead of password — scoped, revocable

# Pull a public image
docker pull nginx:1.27-alpine
docker pull python:3.12-slim

# Tag a local image for Docker Hub
# Format: docker.io/<username>/<repo>:<tag>
docker tag my-app:latest youruser/my-app:v1.2.3
docker tag my-app:latest youruser/my-app:latest

# Push
docker push youruser/my-app:v1.2.3
docker push youruser/my-app:latest

# Pull your private image
docker pull youruser/my-app:v1.2.3

# Logout
docker logout
```

### Docker Hub Rate Limits

| Account | Pull Rate Limit |
|---------|----------------|
| Anonymous | 100 pulls / 6 hours (per IP) |
| Free (authenticated) | 200 pulls / 6 hours |
| Pro / Team | Unlimited |

> In CI/CD, always authenticate to avoid anonymous rate limits — even for public images.

---

## Amazon ECR

```bash
ACCOUNT_ID="123456789012"
REGION="us-east-1"
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Create a repository
aws ecr create-repository \
    --repository-name my-app/api \
    --region $REGION \
    --image-tag-mutability IMMUTABLE \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256

# Authenticate Docker to ECR (token valid for 12 hours)
aws ecr get-login-password --region $REGION | \
    docker login --username AWS --password-stdin $REGISTRY

# Tag and push
docker tag my-app:v1.2.3 ${REGISTRY}/my-app/api:v1.2.3
docker tag my-app:v1.2.3 ${REGISTRY}/my-app/api:latest
docker push ${REGISTRY}/my-app/api:v1.2.3
docker push ${REGISTRY}/my-app/api:latest

# Pull
docker pull ${REGISTRY}/my-app/api:v1.2.3

# List images in a repository
aws ecr describe-images \
    --repository-name my-app/api \
    --region $REGION \
    --query 'imageDetails[*].{Tags:imageTags,Pushed:imagePushedAt,Size:imageSizeInBytes}' \
    --output table

# Describe repositories
aws ecr describe-repositories \
    --region $REGION \
    --query 'repositories[*].{Name:repositoryName,URI:repositoryUri}' \
    --output table
```

### ECR Lifecycle Policy

```bash
# Keep last 10 tagged images; expire untagged images after 1 day
aws ecr put-lifecycle-policy \
    --repository-name my-app/api \
    --region $REGION \
    --lifecycle-policy-text '{
        "rules": [
            {
                "rulePriority": 1,
                "description": "Expire untagged images after 1 day",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "sinceImagePushed",
                    "countUnit": "days",
                    "countNumber": 1
                },
                "action": {"type": "expire"}
            },
            {
                "rulePriority": 2,
                "description": "Keep last 10 tagged images",
                "selection": {
                    "tagStatus": "tagged",
                    "tagPrefixList": ["v"],
                    "countType": "imageCountMoreThan",
                    "countNumber": 10
                },
                "action": {"type": "expire"}
            }
        ]
    }'
```

### ECR in GitHub Actions (OIDC — No Stored Keys)

```yaml
jobs:
  build-push:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-ecr
          aws-region: us-east-1

      - name: Log in to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ steps.login-ecr.outputs.registry }}/my-app/api:${{ github.sha }}
            ${{ steps.login-ecr.outputs.registry }}/my-app/api:latest
          cache-from: type=registry,ref=${{ steps.login-ecr.outputs.registry }}/my-app/api:cache
          cache-to: type=registry,ref=${{ steps.login-ecr.outputs.registry }}/my-app/api:cache,mode=max
```

---

## Google Artifact Registry

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"
REGISTRY="${REGION}-docker.pkg.dev"
REPO="${REGISTRY}/${PROJECT_ID}/my-app"

# Create a Docker repository
gcloud artifacts repositories create my-app \
    --project=$PROJECT_ID \
    --repository-format=docker \
    --location=$REGION \
    --description="My App container images"

# Authenticate Docker
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Tag and push
docker tag my-app:v1.2.3 ${REPO}/api:v1.2.3
docker push ${REPO}/api:v1.2.3

# Pull
docker pull ${REPO}/api:v1.2.3

# List images
gcloud artifacts docker images list $REPO \
    --include-tags \
    --format="table(IMAGE,TAGS,CREATE_TIME)"

# Build and push without local Docker (Cloud Build)
gcloud builds submit \
    --project=$PROJECT_ID \
    --region=$REGION \
    --tag=${REPO}/api:v1.2.3 \
    .
```

### Artifact Registry in GitHub Actions (OIDC)

```yaml
jobs:
  build-push:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: "projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
          service_account: "ci-builder@my-app-production.iam.gserviceaccount.com"

      - uses: docker/login-action@v3
        with:
          registry: us-central1-docker.pkg.dev
          username: oauth2accesstoken
          password: ${{ steps.auth.outputs.access_token }}

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: us-central1-docker.pkg.dev/my-app-production/my-app/api:${{ github.sha }}
```

---

## Azure Container Registry (ACR)

```bash
ACR_NAME="myappprod"
REGISTRY="${ACR_NAME}.azurecr.io"
RESOURCE_GROUP="rg-my-app-production"

# Create registry
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Premium \
    --admin-enabled false \
    --location eastus

# Authenticate
az acr login --name $ACR_NAME

# Tag and push
docker tag my-app:v1.2.3 ${REGISTRY}/my-app/api:v1.2.3
docker push ${REGISTRY}/my-app/api:v1.2.3

# Build in the cloud (no local Docker needed)
az acr build \
    --registry $ACR_NAME \
    --image my-app/api:v1.2.3 \
    --file Dockerfile \
    .

# List repositories
az acr repository list --name $ACR_NAME --output table

# List tags for a repository
az acr repository show-tags \
    --name $ACR_NAME \
    --repository my-app/api \
    --output table

# Delete a tag
az acr repository delete \
    --name $ACR_NAME \
    --image my-app/api:v1.0.0 \
    --yes
```

---

## GitHub Container Registry (GHCR)

GHCR packages are tied to a GitHub user or organization. Public packages are free with no rate limits.

```bash
# Authenticate using a GitHub Personal Access Token (needs write:packages scope)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Tag and push
# Format: ghcr.io/<owner>/<repo>/<image>:<tag>
docker tag my-app:v1.2.3 ghcr.io/your-org/your-repo/api:v1.2.3
docker push ghcr.io/your-org/your-repo/api:v1.2.3

# Pull
docker pull ghcr.io/your-org/your-repo/api:v1.2.3
```

### GHCR in GitHub Actions (No PAT Needed)

```yaml
jobs:
  build-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}  # automatic — no PAT needed

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/my-app:${{ github.sha }}
            ghcr.io/${{ github.repository_owner }}/my-app:latest
```

---

## Self-Hosted Harbor

Harbor is a CNCF graduated open-source registry with role-based access, vulnerability scanning (Trivy), image signing (Cosign), and replication.

```bash
# Install via Helm on Kubernetes
helm repo add harbor https://helm.goharbor.io
helm repo update

helm install harbor harbor/harbor \
    --namespace harbor \
    --create-namespace \
    --set expose.type=ingress \
    --set expose.ingress.hosts.core=registry.internal.example.com \
    --set externalURL=https://registry.internal.example.com \
    --set harborAdminPassword=Admin12345 \
    --set persistence.persistentVolumeClaim.registry.size=100Gi

# Log in to Harbor
docker login registry.internal.example.com

# Tag and push
docker tag my-app:v1.2.3 registry.internal.example.com/my-project/api:v1.2.3
docker push registry.internal.example.com/my-project/api:v1.2.3
```

---

## Image Signing (Cosign)

Cosign signs container images with a cryptographic signature to ensure integrity and provenance.

```bash
# Install cosign
brew install cosign  # macOS

# Generate a key pair
cosign generate-key-pair

# Sign an image (after pushing to registry)
cosign sign --key cosign.key \
    ghcr.io/your-org/your-repo/api:v1.2.3

# Verify a signature before pulling (in your deployment pipeline)
cosign verify --key cosign.pub \
    ghcr.io/your-org/your-repo/api:v1.2.3

# Sign with a cloud KMS key (no key file to manage)
cosign sign --key gcpkms://projects/PROJECT/locations/REGION/keyRings/RING/cryptoKeys/KEY \
    us-central1-docker.pkg.dev/my-app/my-repo/api:v1.2.3
```

---

## Pull Secret for Kubernetes

Kubernetes needs credentials to pull from private registries.

```bash
# Create a pull secret for ECR
kubectl create secret docker-registry ecr-pull-secret \
    --docker-server=123456789.dkr.ecr.us-east-1.amazonaws.com \
    --docker-username=AWS \
    --docker-password=$(aws ecr get-login-password --region us-east-1) \
    --namespace=my-app

# Reference it in a Pod spec
# spec:
#   imagePullSecrets:
#   - name: ecr-pull-secret
```

---

## References

- [Docker Hub](https://hub.docker.com)
- [Amazon ECR documentation](https://docs.aws.amazon.com/ecr/)
- [Google Artifact Registry](https://cloud.google.com/artifact-registry/docs)
- [Azure Container Registry](https://docs.microsoft.com/azure/container-registry/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Harbor documentation](https://goharbor.io/docs/)
- [Cosign](https://docs.sigstore.dev/signing/quickstart/)
---

← [Previous: Docker Compose](./docker-compose.md) | [Home](../README.md) | [Next: Kubernetes →](../10-kubernetes/README.md)
