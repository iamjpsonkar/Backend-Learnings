← [Previous: CI/CD & GitOps](./README.md) | [Home](../README.md) | [Next: GitLab CI →](./gitlab-ci.md)

---

# GitHub Actions

GitHub Actions is GitHub's native CI/CD platform. Workflows are YAML files in `.github/workflows/` that trigger on GitHub events.

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Workflow** | YAML file defining when and what to run |
| **Event** | Trigger: `push`, `pull_request`, `schedule`, `workflow_dispatch`, etc. |
| **Job** | Set of steps running on a single runner |
| **Step** | Individual task: shell command or `uses: action@version` |
| **Runner** | VM where the job runs (`ubuntu-latest`, `windows-latest`, `macos-latest`) |
| **Action** | Reusable step published to the marketplace |
| **Environment** | Named deployment target with protection rules and secrets |
| **Context** | Runtime data: `github.*`, `env.*`, `secrets.*`, `vars.*`, `jobs.*` |

---

## Basic CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"

jobs:
  test:
    name: Test (${{ matrix.os }})
    runs-on: ${{ matrix.os }}

    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        python: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Lint
        run: |
          ruff check .
          mypy src/

      - name: Test
        run: pytest tests/ -v --cov=src --cov-report=xml --tb=short

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        if: matrix.os == 'ubuntu-latest' && matrix.python == '3.12'
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: coverage.xml
```

---

## Build and Deploy Workflow

```yaml
# .github/workflows/deploy.yml
name: Build & Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: "Target environment"
        required: true
        default: staging
        type: choice
        options: [staging, production]

permissions:
  id-token: write   # Required for OIDC auth (AWS, GCP, Azure)
  contents: read
  packages: write   # For GitHub Container Registry

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=sha-
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}

      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.my-app.com

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_STAGING }}
          aws-region: us-east-1

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
              --cluster my-app-staging \
              --service my-app-api \
              --force-new-deployment \
              --region us-east-1

          aws ecs wait services-stable \
              --cluster my-app-staging \
              --services my-app-api

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production      # Has required reviewers configured in GitHub
      url: https://my-app.com

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_PROD }}
          aws-region: us-east-1

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
              --cluster my-app-production \
              --service my-app-api \
              --force-new-deployment \
              --region us-east-1

          aws ecs wait services-stable \
              --cluster my-app-production \
              --services my-app-api
```

---

## Reusable Workflows

```yaml
# .github/workflows/_docker-build.yml  (reusable — prefixed with _)
name: Docker Build (reusable)

on:
  workflow_call:
    inputs:
      image-name:
        required: true
        type: string
      context:
        required: false
        type: string
        default: "."
      push:
        required: false
        type: boolean
        default: true
    outputs:
      image-tag:
        description: "Full image tag including registry"
        value: ${{ jobs.build.outputs.image-tag }}
    secrets:
      registry-password:
        required: true

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}

    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3

      - name: Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ inputs.image-name }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ${{ inputs.context }}
          push: ${{ inputs.push }}
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

```yaml
# .github/workflows/ci.yml — calls the reusable workflow
jobs:
  build-api:
    uses: ./.github/workflows/_docker-build.yml
    with:
      image-name: ghcr.io/${{ github.repository }}/api
      context: backend/
    secrets:
      registry-password: ${{ secrets.GITHUB_TOKEN }}

  build-worker:
    uses: ./.github/workflows/_docker-build.yml
    with:
      image-name: ghcr.io/${{ github.repository }}/worker
      context: worker/
    secrets:
      registry-password: ${{ secrets.GITHUB_TOKEN }}
```

---

## Composite Actions

```yaml
# .github/actions/setup-python-env/action.yml
name: Setup Python Environment
description: Install Python and project dependencies with caching

inputs:
  python-version:
    description: Python version
    required: false
    default: "3.12"
  install-dev:
    description: Install dev dependencies
    required: false
    default: "true"

runs:
  using: composite
  steps:
    - uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python-version }}
        cache: pip

    - name: Install dependencies
      shell: bash
      run: |
        pip install -r requirements.txt
        if [ "${{ inputs.install-dev }}" == "true" ]; then
          pip install -r requirements-dev.txt
        fi
```

```yaml
# Use the composite action
steps:
  - uses: ./.github/actions/setup-python-env
    with:
      python-version: "3.12"
      install-dev: "true"
```

---

## Concurrency and Caching

```yaml
# Cancel in-progress runs for the same branch
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

# Cache node_modules
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-

# Cache pip
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
```

---

## OIDC Authentication (Keyless)

```yaml
# AWS OIDC (no stored credentials)
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
    aws-region: us-east-1
    # No access key/secret needed

# GCP OIDC
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: projects/123/locations/global/workloadIdentityPools/github/providers/github
    service_account: sa-cicd@my-project.iam.gserviceaccount.com

# Azure OIDC
- uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

---

## References

- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [Reusable workflows](https://docs.github.com/en/actions/sharing-automations/reusing-workflows)
- [OIDC with AWS](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [Actions Marketplace](https://github.com/marketplace?type=actions)

---

← [Previous: CI/CD & GitOps](./README.md) | [Home](../README.md) | [Next: GitLab CI →](./gitlab-ci.md)
