← [Previous: Artifact Registry](./artifact-registry.md) | [Home](../../README.md) | [Next: GKE →](./gke.md)

---

# Cloud Build

Cloud Build is a fully managed CI/CD service that executes build steps as Docker containers. It integrates with GitHub, GitLab, Bitbucket, and Cloud Source Repositories.

---

## cloudbuild.yaml Structure

```yaml
# cloudbuild.yaml
steps:
  - id: "test"
    name: "python:3.11"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        pip install -r requirements-dev.txt
        pytest tests/ -v --tb=short

  - id: "build"
    name: "gcr.io/cloud-builders/docker"
    args:
      - "build"
      - "-t"
      - "$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE:$COMMIT_SHA"
      - "-t"
      - "$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE:latest"
      - "--cache-from"
      - "$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE:latest"
      - "."
    waitFor: ["test"]

  - id: "push"
    name: "gcr.io/cloud-builders/docker"
    args:
      - "push"
      - "--all-tags"
      - "$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE"
    waitFor: ["build"]

  - id: "deploy"
    name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    entrypoint: "gcloud"
    args:
      - "run"
      - "deploy"
      - "$_SERVICE_NAME"
      - "--image=$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE:$COMMIT_SHA"
      - "--region=$_REGION"
      - "--project=$PROJECT_ID"
    waitFor: ["push"]

# Built-in substitutions: $PROJECT_ID, $BUILD_ID, $COMMIT_SHA, $BRANCH_NAME, $TAG_NAME, $REPO_NAME
# Custom substitutions: prefix with _
substitutions:
  _REGION: us-central1
  _REPO: my-app
  _IMAGE: api
  _SERVICE_NAME: my-app

images:
  - "$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE:$COMMIT_SHA"
  - "$_REGION-docker.pkg.dev/$PROJECT_ID/$_REPO/$_IMAGE:latest"

timeout: "1200s"

options:
  machineType: "E2_HIGHCPU_8"
  logging: CLOUD_LOGGING_ONLY
  substitution_option: ALLOW_LOOSE
```

---

## Submitting Builds

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"

# Submit a build from current directory
gcloud builds submit \
    --project=$PROJECT \
    --config=cloudbuild.yaml \
    --substitutions=_REGION=$REGION,_IMAGE=api \
    .

# Submit with a specific tag (no cloudbuild.yaml — single build step)
gcloud builds submit \
    --project=$PROJECT \
    --tag="$REGION-docker.pkg.dev/$PROJECT/my-app/api:$(git rev-parse --short HEAD)" \
    .

# View build logs
gcloud builds log BUILD_ID --project=$PROJECT

# List recent builds
gcloud builds list \
    --project=$PROJECT \
    --filter="status=SUCCESS OR status=FAILURE" \
    --format="table(id,status,createTime,duration,substitutions.BRANCH_NAME)"

# Cancel a running build
gcloud builds cancel BUILD_ID --project=$PROJECT
```

---

## Triggers

```bash
# Create a trigger — build on push to main branch
gcloud builds triggers create github \
    --project=$PROJECT \
    --name="main-push" \
    --repo-owner=my-org \
    --repo-name=my-app \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml \
    --substitutions=_REGION=$REGION

# Create a trigger for pull requests (run tests only)
gcloud builds triggers create github \
    --project=$PROJECT \
    --name="pr-validation" \
    --repo-owner=my-org \
    --repo-name=my-app \
    --pull-request-pattern="^main$" \
    --build-config=cloudbuild-test.yaml

# Create a trigger for tagged releases
gcloud builds triggers create github \
    --project=$PROJECT \
    --name="release-deploy" \
    --repo-owner=my-org \
    --repo-name=my-app \
    --tag-pattern="^v[0-9]+\.[0-9]+\.[0-9]+$" \
    --build-config=cloudbuild-release.yaml

# List triggers
gcloud builds triggers list \
    --project=$PROJECT \
    --format="table(name,github.push.branch,status)"

# Manually run a trigger
gcloud builds triggers run main-push \
    --project=$PROJECT \
    --branch=main
```

---

## Private Pools (VPC-Connected Builds)

By default, Cloud Build runs in a public Google network. Private pools run in your VPC.

```bash
# Create a private pool
gcloud builds worker-pools create my-app-pool \
    --project=$PROJECT \
    --region=$REGION \
    --peered-network=projects/$PROJECT/global/networks/vpc-my-app-prod \
    --worker-machine-type=e2-standard-4 \
    --worker-disk-size=100GB

# Use a private pool in cloudbuild.yaml:
# options:
#   pool:
#     name: "projects/PROJECT/locations/REGION/workerPools/my-app-pool"
```

---

## Build Artifacts and Caching

```yaml
# Store test results and binaries as build artifacts
steps:
  - name: "python:3.11"
    script: |
      pip install pytest pytest-html
      pytest tests/ --html=report.html --self-contained-html

artifacts:
  objects:
    location: "gs://my-app-prod-build-artifacts/$BUILD_ID/"
    paths:
      - "report.html"
      - "dist/**"

# Layer caching — pull previous image as cache
steps:
  - name: "gcr.io/cloud-builders/docker"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        docker pull $CACHE_IMAGE:latest || true
        docker build \
          --cache-from $CACHE_IMAGE:latest \
          -t $IMAGE:$COMMIT_SHA \
          --build-arg BUILDKIT_INLINE_CACHE=1 \
          .
```

---

## IAM for Cloud Build

```bash
# Cloud Build service account: PROJECT_NUMBER@cloudbuild.gserviceaccount.com
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format="value(projectNumber)")
BUILD_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

# Grant Cloud Build SA permission to deploy to Cloud Run
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$BUILD_SA" \
    --role="roles/run.developer"

# Grant permission to push to Artifact Registry
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$BUILD_SA" \
    --role="roles/artifactregistry.writer"

# Grant permission to access Secret Manager (for build secrets)
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$BUILD_SA" \
    --role="roles/secretmanager.secretAccessor"
```

---

## Accessing Secrets in Builds

```yaml
# Access Secret Manager secrets in Cloud Build
availableSecrets:
  secretManager:
    - versionName: "projects/$PROJECT_ID/secrets/npm-token/versions/latest"
      env: "NPM_TOKEN"
    - versionName: "projects/$PROJECT_ID/secrets/docker-hub-pass/versions/latest"
      env: "DOCKERHUB_PASSWORD"

steps:
  - name: "node:20"
    secretEnv: ["NPM_TOKEN"]
    script: |
      echo "//registry.npmjs.org/:_authToken=$$NPM_TOKEN" > ~/.npmrc
      npm ci
```

---

## References

- [Cloud Build documentation](https://cloud.google.com/build/docs)
- [cloudbuild.yaml schema](https://cloud.google.com/build/docs/build-config-file-schema)
- [Triggers](https://cloud.google.com/build/docs/triggers)
- [Private pools](https://cloud.google.com/build/docs/private-pools/private-pools-overview)

---

← [Previous: Artifact Registry](./artifact-registry.md) | [Home](../../README.md) | [Next: GKE →](./gke.md)
