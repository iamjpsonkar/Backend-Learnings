← [Previous: Deployment Strategies](./deployment-strategies.md) | [Home](../README.md) | [Next: Security (Batch 20) →](../14-security/README.md)

---

# Production Pipelines

A production-grade CI/CD pipeline is not just build + deploy — it includes quality gates, security scanning, observability integration, and operational controls.

---

## Pipeline Anatomy

```
┌─────────────────────────────────────────────────────────────────────┐
│  SOURCE EVENT                                                        │
│  Pull Request → CI gates (fast feedback, ~5 min)                    │
│  Merge to main → Full pipeline (~15 min)                            │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
         ┌──────────▼──────────┐
         │  1. BUILD            │  lint, type-check, unit tests
         │     ~3 min           │  fail fast — cheapest gates first
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  2. SECURITY SCAN   │  SAST, dependency audit, secrets scan
         │     ~2 min           │  fail on critical/high CVEs
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  3. PACKAGE          │  build container image, sign it
         │     ~3 min           │  push to registry with SHA tag
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  4. INTEGRATION TEST │  deploy ephemeral env, run e2e tests
         │     ~5 min           │  destroy env on completion
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  5. DEPLOY STAGING  │  automated, no approval
         │     ~2 min           │  health checks + smoke tests
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  6. APPROVAL GATE   │  required reviewer(s) sign off
         │     human            │  or auto-promote after soak time
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  7. DEPLOY PROD      │  canary 10% → metrics → 100%
         │     ~10 min          │  auto-rollback on error rate spike
         └─────────────────────┘
```

---

## End-to-End GitHub Actions Pipeline

```yaml
# .github/workflows/production.yml
name: Production Pipeline

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read
  packages: write
  security-events: write   # For SARIF upload

env:
  REGISTRY: ghcr.io
  IMAGE: ghcr.io/${{ github.repository }}/api

concurrency:
  group: production-${{ github.ref }}
  cancel-in-progress: false   # Never cancel production deploys

jobs:
  # ─── 1. Build & Test ─────────────────────────────────────
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - run: pip install -r requirements-dev.txt

      - name: Lint
        run: ruff check . && mypy src/

      - name: Unit tests
        run: |
          pytest tests/unit/ \
              --junitxml=junit.xml \
              --cov=src --cov-report=xml \
              -q --tb=short

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: "*.xml"

  # ─── 2. Security Scan ────────────────────────────────────
  security:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4

      # Dependency vulnerability scan
      - name: pip-audit
        run: |
          pip install pip-audit
          pip-audit -r requirements.txt --format json -o pip-audit.json
          pip-audit -r requirements.txt --severity high

      # SAST
      - uses: github/codeql-action/init@v3
        with:
          languages: python
      - uses: github/codeql-action/analyze@v3
        with:
          output: sarif-results

      # Secrets scan
      - uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}

  # ─── 3. Build Image ──────────────────────────────────────
  build:
    runs-on: ubuntu-latest
    needs: [test, security]
    outputs:
      image-tag: ${{ env.IMAGE }}:${{ github.sha }}
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            ${{ env.IMAGE }}:${{ github.sha }}
            ${{ env.IMAGE }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: true
          sbom: true

      # Container image scan
      - uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.IMAGE }}:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
          severity: CRITICAL,HIGH
          exit-code: 1

      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-results.sarif

      # Sign image with Cosign
      - uses: sigstore/cosign-installer@v3
      - run: |
          cosign sign --yes \
              --rekor-url=https://rekor.sigstore.dev \
              ${{ env.IMAGE }}@${{ steps.build.outputs.digest }}

  # ─── 4. Integration Tests ────────────────────────────────
  integration:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_CI }}
          aws-region: us-east-1

      - name: Deploy ephemeral environment
        id: ephemeral
        run: |
          ENV_NAME="ci-${{ github.run_id }}"
          ./scripts/deploy-ephemeral.sh $ENV_NAME ${{ needs.build.outputs.image-tag }}
          echo "env-url=https://${ENV_NAME}.test.my-app.com" >> $GITHUB_OUTPUT

      - name: Run e2e tests
        run: |
          pytest tests/e2e/ \
              -v --tb=short \
              --base-url ${{ steps.ephemeral.outputs.env-url }}
        timeout-minutes: 10

      - name: Destroy ephemeral environment
        if: always()
        run: ./scripts/destroy-ephemeral.sh ci-${{ github.run_id }}

  # ─── 5. Deploy Staging ───────────────────────────────────
  deploy-staging:
    runs-on: ubuntu-latest
    needs: integration
    environment:
      name: staging
      url: https://staging.my-app.com
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_STAGING }}
          aws-region: us-east-1

      - name: Deploy to staging
        run: |
          aws ecs update-service \
              --cluster my-app-staging \
              --service my-app-api \
              --force-new-deployment
          aws ecs wait services-stable \
              --cluster my-app-staging \
              --services my-app-api

      - name: Smoke test staging
        run: |
          STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
              https://staging.my-app.com/health/ready)
          [ "$STATUS" = "200" ] || (echo "Smoke test failed: $STATUS" && exit 1)

  # ─── 6+7. Approve + Deploy Production ────────────────────
  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    environment:
      name: production         # Requires reviewer approval in GitHub Settings
      url: https://my-app.com
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_PROD }}
          aws-region: us-east-1

      # Canary deploy: 10% first
      - name: Canary deploy (10%)
        run: |
          aws ecs update-service \
              --cluster my-app-production \
              --service my-app-api-canary \
              --task-definition my-app-api:$(./scripts/get-task-def-rev.sh) \
              --desired-count 1
          sleep 300   # Observe for 5 min

      # Check error rate before promoting
      - name: Check canary error rate
        run: |
          ERROR_RATE=$(aws cloudwatch get-metric-statistics \
              --namespace MyApp \
              --metric-name ErrorRate \
              --dimensions Name=Service,Value=my-app-api-canary \
              --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
              --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
              --period 300 \
              --statistics Average \
              --query 'Datapoints[0].Average' \
              --output text)
          echo "Canary error rate: ${ERROR_RATE}%"
          awk "BEGIN { if ($ERROR_RATE > 1.0) { print \"Error rate too high\"; exit 1 } }"

      # Full production deploy
      - name: Full production deploy
        run: |
          aws ecs update-service \
              --cluster my-app-production \
              --service my-app-api \
              --task-definition my-app-api:$(./scripts/get-task-def-rev.sh) \
              --force-new-deployment
          aws ecs wait services-stable \
              --cluster my-app-production \
              --services my-app-api

          # Scale down canary
          aws ecs update-service \
              --cluster my-app-production \
              --service my-app-api-canary \
              --desired-count 0

      - name: Post-deploy verification
        run: |
          # Check health
          for endpoint in /health/ready /health/live /api/v1/status; do
            STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
                https://my-app.com${endpoint} 2>/dev/null)
            echo "${endpoint}: ${STATUS}"
            [ "$STATUS" = "200" ] || (echo "FAILED: $endpoint returned $STATUS" && exit 1)
          done

      - name: Notify deployment
        if: always()
        uses: slackapi/slack-github-action@v2
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
          payload: |
            {
              "text": "${{ job.status == 'success' && '✅' || '❌' }} Production deploy *${{ job.status }}*",
              "blocks": [{
                "type": "section",
                "text": {
                  "type": "mrkdwn",
                  "text": "${{ job.status == 'success' && '✅' || '❌' }} *my-app* deployed to production\nCommit: `${{ github.sha }}`\nActor: ${{ github.actor }}\n<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View run>"
                }
              }]
            }
```

---

## Operational Controls

```yaml
# Scheduled pipeline health check
on:
  schedule:
    - cron: '0 */4 * * *'   # Every 4 hours

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - name: Check all environments
        run: |
          for env in staging production; do
            STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
                https://${env}.my-app.com/health/ready 2>/dev/null || echo "000")
            echo "$env: $STATUS"
            [ "$STATUS" != "200" ] && echo "::warning::$env health check failed: $STATUS"
          done
```

---

## Key Pipeline Principles

1. **Fail fast** — cheapest gates first (lint before build, build before deploy)
2. **Parallel where possible** — run security scans in parallel with unit tests
3. **Artifact immutability** — tag images with commit SHA, never overwrite
4. **Keyless auth** — OIDC everywhere, no stored long-lived credentials
5. **Every merge is a potential release** — keep main always deployable
6. **Canary before full rollout** — always validate with a subset of production traffic
7. **Automated rollback** — if error rate spikes, roll back without human intervention
8. **Observable pipelines** — pipeline failures go to the same on-call channel as production alerts

---

## References

- [DORA metrics](https://dora.dev/research/2023/dora-report/)
- [GitHub Actions environment protection rules](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Cosign (image signing)](https://docs.sigstore.dev/cosign/signing/overview/)
- [Supply chain security (SLSA)](https://slsa.dev/)

---

← [Previous: Deployment Strategies](./deployment-strategies.md) | [Home](../README.md) | [Next: Security (Batch 20) →](../14-security/README.md)
