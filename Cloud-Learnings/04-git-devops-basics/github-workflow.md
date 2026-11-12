← [Previous: Git Basics](./git-basics.md) | [Home](../README.md) | [Next: SSH Keys →](./ssh-keys.md)

---

# GitHub Workflow

GitHub adds collaboration features on top of Git: pull requests, code review, branch protection, and CI/CD via GitHub Actions. This document covers the day-to-day workflow for cloud and DevOps teams.

---

## Core Workflow: Feature Branch → Pull Request → Merge

```
main ─────────────────────────────────────────────────────────▶
         │                                         ▲
         │ git switch -c feature/add-s3-bucket     │ PR merged
         ▼                                         │
      feature/add-s3-bucket ──────────────────────▶
         (commits, push, open PR, review, approve)
```

1. Create a branch from `main`
2. Make commits on the branch
3. Push branch to GitHub
4. Open a Pull Request
5. Team reviews and approves
6. CI checks pass
7. Merge (and delete the branch)

---

## Daily Workflow

```bash
# Start of day: sync with main
git switch main
git pull --rebase origin main

# Create feature branch
git switch -c feat/deploy-cloudfront-distribution

# ... make changes, run tests locally ...

# Stage and commit incrementally
git add -p                              # interactive hunk staging
git commit -m "feat: add CloudFront origin configuration"
git commit -m "feat: configure ALB as CloudFront origin"
git commit -m "test: add integration test for CloudFront routing"

# Push and open PR
git push -u origin feat/deploy-cloudfront-distribution

# GitHub CLI: open PR from terminal
gh pr create \
    --title "feat: deploy CloudFront distribution for api.example.com" \
    --body "## Summary
- Adds CloudFront distribution fronting the ALB
- Configures HTTPS with ACM certificate
- Sets 5-minute TTL on API responses

## Test plan
- [ ] CloudFront distribution status: Deployed
- [ ] https://api.example.com returns 200 OK
- [ ] X-Cache header shows Hit on second request

Closes #42" \
    --reviewer alice,bob \
    --label "infrastructure"

# View PR status
gh pr view
gh pr checks
```

---

## Branching Strategy

### GitHub Flow (Recommended for most teams)

Simple: one long-lived `main` branch, short-lived feature branches.

```
main      ──────────────────────────────────────────────────▶
              ▲           ▲                     ▲
              │           │                     │
feat/auth ────┘           │                     │
                feat/s3 ──┘                     │
                                   fix/cors ────┘
```

- `main` is always deployable
- Feature branches are short-lived (1–3 days ideally)
- Merge via PR with at least 1 approval
- Deploy immediately after merge

### Gitflow (For teams with scheduled releases)

```
main      ──────────────────────────────────────────────────▶
             ▲ merge                         ▲ merge
             │                               │
develop ─────┴───────────────────────────────┴──────────────▶
              ▲         ▲           ▲
              │         │           │
          feat/a    feat/b    release/1.2 (frozen, only bugfixes)
```

Branches: `main`, `develop`, `feature/*`, `release/*`, `hotfix/*`

Use Gitflow when: you have multiple versions in production, scheduled release cycles, or long QA phases.

### Trunk-Based Development

All developers commit directly to `main` (or very short-lived branches ≤1 day). Requires feature flags for incomplete features. Used by Google, Meta — enables continuous deployment.

---

## Pull Requests

### PR Best Practices

- **Small PRs**: one logical change, ideally under 400 lines changed
- **Clear description**: what changed, why, how to test, screenshots if UI
- **Link issues**: `Closes #123` auto-closes the issue on merge
- **Self-review**: review your own diff before requesting others
- **Draft PRs**: use for early feedback on work in progress

### PR Description Template

```markdown
## Summary
Brief description of what this PR does and why.

## Changes
- Added X
- Modified Y to fix Z
- Removed deprecated W

## Test plan
- [ ] Unit tests pass: `pytest tests/`
- [ ] Manual test: describe what to click/run
- [ ] No regressions in related functionality

## Screenshots (if UI change)

## References
- Closes #123
- Related to #456
- RFC: link-to-design-doc
```

### Reviewing Code

```bash
# Check out a PR locally for testing
gh pr checkout 42

# Review with comments in GitHub, then:
gh pr review 42 --approve --body "LGTM! One nit above but not blocking."
gh pr review 42 --request-changes --body "Please add error handling for the S3 timeout case."
gh pr review 42 --comment --body "Nit: consider extracting this into a helper function."
```

**Review checklist:**
- Does the code do what the PR description says?
- Is the logic correct? Edge cases handled?
- Are there tests? Do they actually test the right things?
- Any security issues (hardcoded credentials, injection vulnerabilities)?
- Is the code readable and maintainable?
- Are error messages useful? Logging adequate?
- Does it match existing style and patterns?

---

## Branch Protection Rules

Branch protection prevents direct pushes to important branches and enforces quality gates.

**Recommended rules for `main`:**

```
Settings → Branches → Branch protection rules → main

☑ Require a pull request before merging
    ☑ Require approvals: 1 (or 2 for production-critical repos)
    ☑ Dismiss stale pull request approvals when new commits are pushed
    ☑ Require review from Code Owners

☑ Require status checks to pass before merging
    ☑ Require branches to be up to date before merging
    Required status checks: (add your CI jobs here)
      - test / unit-tests
      - test / integration-tests
      - security / dependency-scan

☑ Require conversation resolution before merging

☑ Require signed commits (optional; good for compliance)

☑ Do not allow bypassing the above settings
```

### CODEOWNERS

Automatically assign reviewers based on which files are changed:

```
# CODEOWNERS (place in .github/ or root directory)

# Default owners for all files
*                   @org/platform-team

# Infrastructure code requires IaC team review
*.tf                @org/infra-team
terraform/          @org/infra-team

# AWS-specific configuration
05-aws/             @org/aws-team

# Security configuration always needs security team
**/security*        @org/security-team
**/iam*             @org/security-team

# CI/CD pipelines
.github/            @org/devops-team
```

---

## GitHub Actions — CI/CD Basics

GitHub Actions runs automated workflows triggered by repository events.

### Workflow File Location

All workflow files live in `.github/workflows/` with `.yml` extension.

### Key Concepts

| Concept | Meaning |
|---------|---------|
| **Workflow** | An automated process defined in a YAML file |
| **Trigger (on)** | The event that starts the workflow (push, PR, schedule, manual) |
| **Job** | A set of steps that run on the same runner |
| **Step** | A single task: run a command or use an Action |
| **Action** | A reusable unit of work (from GitHub Marketplace or your own) |
| **Runner** | The machine that executes jobs (GitHub-hosted or self-hosted) |

### Basic CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Run tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run linter
        run: flake8 src/ tests/

      - name: Run tests
        run: pytest tests/ -v --tb=short

      - name: Upload coverage report
        uses: codecov/codecov-action@v4
        if: always()
```

### Deploying to AWS

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main]

permissions:
  id-token: write    # required for OIDC
  contents: read

jobs:
  deploy:
    name: Deploy ECS service
    runs-on: ubuntu-latest
    environment: production    # requires manual approval if configured

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC — no long-lived keys)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
          aws-region: us-east-1

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push Docker image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/my-app:$IMAGE_TAG .
          docker push $ECR_REGISTRY/my-app:$IMAGE_TAG

      - name: Deploy to ECS
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          aws ecs update-service \
            --cluster production \
            --service my-app \
            --force-new-deployment
          aws ecs wait services-stable \
            --cluster production \
            --services my-app
```

### OIDC Authentication (No Long-Lived AWS Keys)

Never store AWS access keys as GitHub Secrets. Use OIDC (OpenID Connect) instead — GitHub Actions requests a short-lived token from AWS.

```bash
# Create IAM role for GitHub Actions (one-time setup)
aws iam create-role \
    --role-name github-actions-deploy \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"},
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:*"
                }
            }
        }]
    }'
```

### Useful Workflow Patterns

```yaml
# Run on specific paths only (avoid unnecessary CI)
on:
  push:
    paths:
      - "src/**"
      - "requirements.txt"
      - ".github/workflows/**"

# Matrix: test on multiple versions
jobs:
  test:
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

# Conditional steps
- name: Deploy to production
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  run: ./deploy.sh

# Reuse secrets
- name: Configure AWS
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
    aws-region: ${{ vars.AWS_REGION }}

# Artifacts: pass files between jobs
- name: Upload build artifact
  uses: actions/upload-artifact@v4
  with:
    name: build
    path: dist/

- name: Download build artifact
  uses: actions/download-artifact@v4
  with:
    name: build
```

---

## GitHub CLI (gh) Quick Reference

```bash
# Authentication
gh auth login

# Repos
gh repo create myorg/myrepo --private
gh repo clone myorg/myrepo
gh repo view --web                      # open in browser

# Pull requests
gh pr create --fill                     # auto-fill title and body from commits
gh pr list
gh pr view 42
gh pr checkout 42                       # check out PR locally
gh pr merge 42 --squash                 # merge with squash
gh pr close 42

# Issues
gh issue create --title "Bug: 502 on login" --label bug
gh issue list --state open
gh issue close 42

# Actions / CI
gh run list
gh run view 12345
gh run watch                            # live watch current run

# Secrets
gh secret set AWS_DEPLOY_ROLE_ARN --body "arn:aws:iam::123456789012:role/..."
gh secret list

# Releases
gh release create v1.2.0 \
    --title "v1.2.0 — CloudFront integration" \
    --notes "See CHANGELOG.md for details" \
    dist/*.tar.gz
```

---

## Common GitHub Patterns

### Squash and Merge Strategy

For keeping a clean `main` history — all commits in a feature branch become one commit on `main`.

Configure in: Settings → General → Pull Requests → Allow squash merging

Advantages: clean linear history; each commit on `main` = one feature/fix

### Auto-delete Head Branches

Configure in: Settings → General → Pull Requests → Automatically delete head branches

### Protected Environment with Manual Approval

```yaml
jobs:
  deploy-production:
    environment: production      # requires approval from environment reviewers
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh production
```

Configure in: Settings → Environments → production → Required reviewers

---

## References

- [GitHub documentation](https://docs.github.com/)
- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [GitHub CLI manual](https://cli.github.com/manual/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [OIDC with AWS and GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
---

← [Previous: Git Basics](./git-basics.md) | [Home](../README.md) | [Next: SSH Keys →](./ssh-keys.md)
