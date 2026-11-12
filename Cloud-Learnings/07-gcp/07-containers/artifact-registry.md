← [Previous: GCP Containers](./README.md) | [Home](../../README.md) | [Next: Cloud Build →](./cloud-build.md)

---

# Artifact Registry

Artifact Registry is GCP's universal artifact management service. It stores Docker images, Helm charts, Maven packages, npm packages, and Python wheels. It replaces Container Registry (`gcr.io`).

---

## Repository Formats

| Format | Description |
|--------|-------------|
| `DOCKER` | OCI-compliant container images |
| `HELM` | Helm charts |
| `MAVEN` | Java artifacts |
| `NPM` | Node.js packages |
| `PYTHON` | Python wheels/sdists |
| `APT` | Debian/Ubuntu packages |
| `YUM` | RPM packages |

---

## Creating a Repository

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"

# Create a Docker repository
gcloud artifacts repositories create my-app \
    --project=$PROJECT \
    --location=$REGION \
    --repository-format=docker \
    --description="My App container images" \
    --immutable-tags \
    --labels=environment=production

# Create a multi-region repository
gcloud artifacts repositories create my-app-global \
    --project=$PROJECT \
    --location=us \
    --repository-format=docker

# Get repository URI
gcloud artifacts repositories describe my-app \
    --project=$PROJECT \
    --location=$REGION \
    --format="value(name)"
# URI format: REGION-docker.pkg.dev/PROJECT/REPO
# Example:    us-central1-docker.pkg.dev/my-app-prod-123456/my-app

# List repositories
gcloud artifacts repositories list \
    --project=$PROJECT \
    --location=$REGION \
    --format="table(name,format,location,createTime)"
```

---

## Building and Pushing Images

```bash
REPO="$REGION-docker.pkg.dev/$PROJECT/my-app"
IMAGE="$REPO/api"
TAG=$(git rev-parse --short HEAD)

# Configure Docker authentication
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

# Build and push locally
docker build -t $IMAGE:$TAG -t $IMAGE:latest .
docker push $IMAGE:$TAG
docker push $IMAGE:latest

# Build with Cloud Build (remote — no local Docker required)
gcloud builds submit \
    --project=$PROJECT \
    --tag=$IMAGE:$TAG \
    .

# Multi-arch build with Cloud Build
gcloud builds submit \
    --project=$PROJECT \
    --config=cloudbuild.yaml \
    --substitutions=_IMAGE=$IMAGE,_TAG=$TAG \
    .
```

---

## Image Management

```bash
# List images in a repository
gcloud artifacts docker images list $REPO/api \
    --project=$PROJECT \
    --include-tags \
    --format="table(IMAGE,TAGS,DIGEST,CREATE_TIME)"

# Describe an image (layers, config)
gcloud artifacts docker images describe $REPO/api:$TAG \
    --project=$PROJECT

# Add a tag to an existing image
gcloud artifacts docker tags add \
    $REPO/api:$TAG \
    $REPO/api:stable

# Delete a specific tag
gcloud artifacts docker tags delete $REPO/api:old-tag \
    --project=$PROJECT --quiet

# Delete all untagged images older than 30 days
gcloud artifacts docker images list $REPO/api \
    --project=$PROJECT \
    --filter="UPDATE_TIME.date('%Y-%m-%d')<$(date -d '30 days ago' '+%Y-%m-%d' 2>/dev/null || date -v-30d '+%Y-%m-%d')" \
    --format="value(DIGEST)" | \
    xargs -I {} gcloud artifacts docker images delete "$REPO/api@{}" \
        --project=$PROJECT --quiet --delete-tags
```

---

## Cleanup Policies

```bash
# Create a cleanup policy — keep only the latest 10 tagged images
cat <<EOF > cleanup-policy.json
[
  {
    "name": "keep-latest-10",
    "action": {"type": "Keep"},
    "mostRecentVersions": {"keepCount": 10},
    "condition": {"tagState": "TAGGED"}
  },
  {
    "name": "delete-untagged",
    "action": {"type": "Delete"},
    "condition": {
      "tagState": "UNTAGGED",
      "olderThan": "86400s"
    }
  }
]
EOF

gcloud artifacts repositories set-cleanup-policies my-app \
    --project=$PROJECT \
    --location=$REGION \
    --policy=cleanup-policy.json
```

---

## Vulnerability Scanning

```bash
# Enable automatic vulnerability scanning on push
gcloud services enable containerscanning.googleapis.com --project=$PROJECT

gcloud artifacts repositories update my-app \
    --project=$PROJECT \
    --location=$REGION \
    --update-labels=scan=enabled

# List vulnerabilities for an image
gcloud artifacts docker images scan $REPO/api:$TAG \
    --project=$PROJECT \
    --remote \
    --format="table(response.scan,response.name)"

# Get vulnerability report
SCAN_ID=$(gcloud artifacts docker images scan $REPO/api:$TAG \
    --project=$PROJECT --remote --format="value(response.name)")
gcloud artifacts docker images list-vulnerabilities $SCAN_ID \
    --project=$PROJECT \
    --format="table(vulnerability.effectiveSeverity,vulnerability.shortDescription,vulnerability.packageIssue[0].affectedPackage)"
```

---

## Grant Access

```bash
# Grant GKE nodes pull access
AKS_SA="sa-gke-nodes@$PROJECT.iam.gserviceaccount.com"
gcloud artifacts repositories add-iam-policy-binding my-app \
    --project=$PROJECT \
    --location=$REGION \
    --member="serviceAccount:$AKS_SA" \
    --role="roles/artifactregistry.reader"

# Grant CI/CD SA push access
gcloud artifacts repositories add-iam-policy-binding my-app \
    --project=$PROJECT \
    --location=$REGION \
    --member="serviceAccount:sa-cicd@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer"
```

---

## References

- [Artifact Registry documentation](https://cloud.google.com/artifact-registry/docs)
- [Docker image management](https://cloud.google.com/artifact-registry/docs/docker/manage-images)
- [Cleanup policies](https://cloud.google.com/artifact-registry/docs/repositories/cleanup-policy)
- [Vulnerability scanning](https://cloud.google.com/artifact-registry/docs/analysis)

---

← [Previous: GCP Containers](./README.md) | [Home](../../README.md) | [Next: Cloud Build →](./cloud-build.md)
