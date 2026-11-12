← [Previous: Containerized API](./containerized-api.md) | [Home](../README.md) | [Next: Observability Stack →](./observability-stack.md)

---

# Project: CI/CD Pipeline

Build a complete deployment pipeline: automated tests, Docker build, security scanning, staging deploy with smoke tests, and production deploy with manual approval gate. Everything runs on GitHub Actions with OIDC — no stored AWS credentials.

**Estimated cost:** ~$5–10/month (ECR + ECS deployments; GitHub Actions free tier usually sufficient)
**Time to complete:** 2–3 hours

---

## Pipeline Overview

```
Push to feature branch
  │
  ▼
[ CI ] ─────────────────────────────────────────────────────────
  ├── 1. Lint + unit tests
  ├── 2. Docker build
  ├── 3. Container security scan (Trivy)
  └── 4. SAST (Semgrep)

Merge to main
  │
  ▼
[ CD: Staging ] ─────────────────────────────────────────────────
  ├── 5. Push image to ECR
  ├── 6. Deploy to staging ECS
  ├── 7. Run smoke tests
  └── 8. Notify Slack

Manual approval gate
  │
  ▼
[ CD: Production ] ──────────────────────────────────────────────
  ├── 9. Deploy to production ECS (blue/green)
  ├── 10. Health check
  └── 11. Rollback if unhealthy
```

---

## Step 1: OIDC Trust Role

```hcl
# terraform/iam.tf

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  count           = data.aws_iam_openid_connect_provider.github == null ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_actions" {
  name = "github-actions-deploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = "arn:aws:iam::${var.account_id}:oidc-provider/token.actions.githubusercontent.com"
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_actions" {
  name = "deploy-policy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          "ecr:BatchGetImage",
          "ecr:DescribeImages",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "iam:PassRole",
        ]
        Resource = "*"
      }
    ]
  })
}
```

---

## Step 2: GitHub Actions Workflow

```yaml
# .github/workflows/pipeline.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, "feature/**"]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: order-api
  ECS_CLUSTER: order-api-cluster
  ECS_SERVICE_STAGING: order-api-staging
  ECS_SERVICE_PROD: order-api-prod
  CONTAINER_NAME: api

jobs:
  # ─── CI ─────────────────────────────────────────────────────────────────────
  test:
    name: Lint & Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Lint
        run: |
          ruff check .
          ruff format --check .

      - name: Unit tests
        run: pytest tests/unit/ -v --tb=short --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml

  build:
    name: Build & Scan
    runs-on: ubuntu-latest
    needs: test
    permissions:
      id-token: write
      contents: read
      security-events: write

    outputs:
      image-tag: ${{ steps.meta.outputs.version }}
      ecr-registry: ${{ steps.login-ecr.outputs.registry }}

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/github-actions-deploy-role
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}
          tags: |
            type=sha,prefix=,format=short
            type=ref,event=branch
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}

      - name: Build image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          load: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Trivy security scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ steps.meta.outputs.version }}
          format: sarif
          output: trivy-results.sarif
          severity: HIGH,CRITICAL
          exit-code: 1   # Fail on HIGH/CRITICAL

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-results.sarif

      - name: SAST scan (Semgrep)
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/python
            p/owasp-top-ten
            p/secrets

      - name: Push image
        if: github.ref == 'refs/heads/main'
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}

  # ─── CD: Staging ─────────────────────────────────────────────────────────────
  deploy-staging:
    name: Deploy → Staging
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/github-actions-deploy-role
          aws-region: ${{ env.AWS_REGION }}

      - name: Download task definition
        run: |
          aws ecs describe-task-definition \
              --task-definition order-api-staging \
              --query taskDefinition > task-definition.json

      - name: Update image in task definition
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: ${{ env.CONTAINER_NAME }}
          image: ${{ needs.build.outputs.ecr-registry }}/${{ env.ECR_REPOSITORY }}:${{ needs.build.outputs.image-tag }}

      - name: Deploy to staging ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: ${{ env.ECS_SERVICE_STAGING }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true

      - name: Smoke tests
        run: |
          STAGING_URL="https://staging.api.myapp.com"
          # Health check
          for i in {1..5}; do
            STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$STAGING_URL/health/ready")
            [ "$STATUS" = "200" ] && echo "Health check passed" && break
            echo "Attempt $i: status $STATUS — retrying..."
            sleep 10
          done
          [ "$STATUS" = "200" ] || (echo "Smoke test FAILED" && exit 1)

          # Functional check
          RESPONSE=$(curl -sf -X POST "$STAGING_URL/orders" \
              -H "Content-Type: application/json" \
              -d '{"user_id":"smoke-test","items":[{"product_id":"p1","name":"Test","price":1.00,"quantity":1}]}')
          echo "$RESPONSE" | jq -e '.order_id' > /dev/null || (echo "Order creation failed" && exit 1)
          echo "Smoke tests passed"

  # ─── CD: Production ──────────────────────────────────────────────────────────
  deploy-production:
    name: Deploy → Production
    runs-on: ubuntu-latest
    needs: [build, deploy-staging]
    if: github.ref == 'refs/heads/main'
    environment: production    # requires manual approval in GitHub Environments

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/github-actions-deploy-role
          aws-region: ${{ env.AWS_REGION }}

      - name: Download task definition
        run: |
          aws ecs describe-task-definition \
              --task-definition order-api-prod \
              --query taskDefinition > task-definition.json

      - name: Update image in task definition
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: ${{ env.CONTAINER_NAME }}
          image: ${{ needs.build.outputs.ecr-registry }}/${{ env.ECR_REPOSITORY }}:${{ needs.build.outputs.image-tag }}

      - name: Deploy to production
        id: deploy
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: ${{ env.ECS_SERVICE_PROD }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true

      - name: Production health check
        id: health
        run: |
          PROD_URL="https://api.myapp.com"
          for i in {1..10}; do
            STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$PROD_URL/health/ready" 2>/dev/null || echo "000")
            [ "$STATUS" = "200" ] && echo "Production healthy" && exit 0
            echo "Attempt $i: $STATUS — waiting..."
            sleep 15
          done
          echo "Production health check FAILED"
          exit 1

      - name: Rollback on failure
        if: failure() && steps.deploy.outcome == 'success'
        run: |
          echo "Deployment succeeded but health check failed — rolling back"
          # Get previous task definition revision
          PREV_REVISION=$(aws ecs describe-task-definition \
              --task-definition order-api-prod \
              --query 'taskDefinition.revision' --output text)
          ROLLBACK_REVISION=$((PREV_REVISION - 1))

          aws ecs update-service \
              --cluster $ECS_CLUSTER \
              --service $ECS_SERVICE_PROD \
              --task-definition "order-api-prod:$ROLLBACK_REVISION"

          echo "Rollback to revision $ROLLBACK_REVISION initiated"
```

---

## Step 3: GitHub Environments Configuration

```bash
# Via GitHub CLI — set required reviewers for production
gh api repos/$ORG/$REPO/environments/production \
    --method PUT \
    --field wait_timer=0 \
    --field reviewers='[{"type":"User","id":USER_ID}]' \
    --field deployment_branch_policy='{"protected_branches":true,"custom_branch_policies":false}'

# Set environment variables
gh variable set AWS_ACCOUNT_ID --env staging --body "123456789012"
gh variable set AWS_ACCOUNT_ID --env production --body "123456789012"
```

---

## Verification

```bash
# Watch a deployment
gh run watch $(gh run list --limit 1 --json databaseId -q '.[0].databaseId')

# Check deployment history
gh run list --workflow pipeline.yml --limit 10

# View logs for a specific step
gh run view --log RUN_ID
```

---

← [Previous: Containerized API](./containerized-api.md) | [Home](../README.md) | [Next: Observability Stack →](./observability-stack.md)
