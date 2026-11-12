← [Previous: GitHub Actions](./github-actions.md) | [Home](../README.md) | [Next: Jenkins →](./jenkins.md)

---

# GitLab CI/CD

GitLab CI/CD is defined in `.gitlab-ci.yml` at the root of your repository. It supports stages, jobs, runners, environments, and Auto DevOps.

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Pipeline** | Full CI/CD run triggered by an event |
| **Stage** | Named phase — jobs in the same stage run in parallel |
| **Job** | Named set of scripts running on a runner |
| **Runner** | Agent that executes jobs (shared, group, or project-specific) |
| **Artifact** | Files produced by a job, passed to later jobs |
| **Cache** | Reusable files between pipelines (e.g., `node_modules`) |
| **Environment** | Named deployment target with history and rollback |
| **Rules** | Control when a job runs (`rules:` replaces `only`/`except`) |

---

## Basic Pipeline

```yaml
# .gitlab-ci.yml

default:
  image: python:3.12-slim
  tags:
    - linux                         # Use runners with the 'linux' tag

variables:
  PYTHON_VERSION: "3.12"
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

stages:
  - lint
  - test
  - build
  - deploy

# Global cache (shared across jobs)
cache:
  key:
    files:
      - requirements*.txt
  paths:
    - .cache/pip
    - .venv/

# ─── Lint stage ───────────────────────────────────────
ruff:
  stage: lint
  before_script:
    - pip install ruff mypy --quiet
  script:
    - ruff check .
    - mypy src/ --ignore-missing-imports
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == "main"'

# ─── Test stage ───────────────────────────────────────
pytest:
  stage: test
  before_script:
    - pip install -r requirements-dev.txt --quiet
  script:
    - pytest tests/ -v --cov=src --cov-report=xml --cov-report=term-missing --tb=short
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    when: always
    reports:
      junit: test-results.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    expire_in: 1 week
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'

# ─── Build stage ──────────────────────────────────────
build-image:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  variables:
    IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
    IMAGE_LATEST: $CI_REGISTRY_IMAGE:latest
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build
        --cache-from $IMAGE_LATEST
        --build-arg BUILDKIT_INLINE_CACHE=1
        -t $IMAGE
        -t $IMAGE_LATEST
        .
    - docker push $IMAGE
    - docker push $IMAGE_LATEST
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
```

---

## Environments and Deployments

```yaml
# Deploy to staging (auto on main)
deploy-staging:
  stage: deploy
  image: registry.gitlab.com/gitlab-org/cloud-deploy/aws-base:latest
  environment:
    name: staging
    url: https://staging.my-app.com
    on_stop: stop-staging
  variables:
    ECS_CLUSTER: my-app-staging
    ECS_SERVICE: my-app-api
  script:
    - aws ecs update-service
        --cluster $ECS_CLUSTER
        --service $ECS_SERVICE
        --force-new-deployment
    - aws ecs wait services-stable
        --cluster $ECS_CLUSTER
        --services $ECS_SERVICE
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'

# Stop (teardown) staging environment
stop-staging:
  stage: deploy
  environment:
    name: staging
    action: stop
  script:
    - aws ecs update-service --cluster my-app-staging --service my-app-api --desired-count 0
  when: manual
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'

# Deploy to production — manual gate
deploy-production:
  stage: deploy
  image: registry.gitlab.com/gitlab-org/cloud-deploy/aws-base:latest
  environment:
    name: production
    url: https://my-app.com
  variables:
    ECS_CLUSTER: my-app-production
    ECS_SERVICE: my-app-api
  script:
    - aws ecs update-service
        --cluster $ECS_CLUSTER
        --service $ECS_SERVICE
        --force-new-deployment
    - aws ecs wait services-stable
        --cluster $ECS_CLUSTER
        --services $ECS_SERVICE
  when: manual                # Requires manual click in GitLab UI
  allow_failure: false
  needs:
    - deploy-staging
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
```

---

## Rules (Conditional Jobs)

```yaml
# Run on MRs targeting main, or on main branch pushes
job-name:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event" && $CI_MERGE_REQUEST_TARGET_BRANCH_NAME == "main"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'

# Run only on tag pushes (release)
release-job:
  rules:
    - if: '$CI_COMMIT_TAG =~ /^v[0-9]+\.[0-9]+\.[0-9]+$/'

# Skip if commit message contains [skip ci]
skip-ci:
  rules:
    - if: '$CI_COMMIT_MESSAGE =~ /\[skip ci\]/'
      when: never
    - when: always

# Run on schedule only
scheduled-job:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "schedule"'
```

---

## Reusable Components

### Include

```yaml
# .gitlab-ci.yml — include shared templates
include:
  - local: .gitlab/ci/build.yml
  - local: .gitlab/ci/deploy.yml
  - project: my-org/ci-templates
    ref: v1.5.0
    file: /templates/python.yml
  - template: Security/SAST.gitlab-ci.yml   # GitLab built-in templates
```

### Extends

```yaml
# Define a base job
.deploy-base:
  image: registry.gitlab.com/gitlab-org/cloud-deploy/aws-base:latest
  before_script:
    - aws configure set region us-east-1
  script:
    - aws ecs update-service
        --cluster $ECS_CLUSTER
        --service $ECS_SERVICE
        --force-new-deployment

# Inherit and override
deploy-staging:
  extends: .deploy-base
  environment: staging
  variables:
    ECS_CLUSTER: my-app-staging
    ECS_SERVICE: my-app-api

deploy-production:
  extends: .deploy-base
  environment: production
  variables:
    ECS_CLUSTER: my-app-production
    ECS_SERVICE: my-app-api
  when: manual
```

### Parallel Matrix

```yaml
test:
  script: pytest tests/ -k $TEST_SUITE
  parallel:
    matrix:
      - TEST_SUITE: unit
        PYTHON_VERSION: "3.11"
      - TEST_SUITE: unit
        PYTHON_VERSION: "3.12"
      - TEST_SUITE: integration
        PYTHON_VERSION: "3.12"
```

---

## Artifacts and Dependencies

```yaml
build:
  stage: build
  script:
    - make build
    - cp -r dist/ artifacts/
  artifacts:
    paths:
      - artifacts/
    expire_in: 1 hour

deploy:
  stage: deploy
  needs:
    - job: build
      artifacts: true     # Download artifacts from 'build' job
  script:
    - ls artifacts/       # Available here
    - ./deploy.sh artifacts/
```

---

## Runners

```bash
# Install GitLab Runner
curl -L https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh | sudo bash
sudo apt-get install gitlab-runner

# Register runner
sudo gitlab-runner register \
    --url https://gitlab.com \
    --registration-token YOUR_TOKEN \
    --executor docker \
    --docker-image "alpine:latest" \
    --description "my-docker-runner" \
    --tag-list "linux,docker" \
    --run-untagged false \
    --locked false
```

---

## References

- [GitLab CI/CD documentation](https://docs.gitlab.com/ee/ci/)
- [CI/CD YAML reference](https://docs.gitlab.com/ee/ci/yaml/)
- [Predefined variables](https://docs.gitlab.com/ee/ci/variables/predefined_variables.html)
- [GitLab Runner](https://docs.gitlab.com/runner/)

---

← [Previous: GitHub Actions](./github-actions.md) | [Home](../README.md) | [Next: Jenkins →](./jenkins.md)
