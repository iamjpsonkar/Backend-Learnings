← [Previous: AWS CI/CD](./README.md) | [Home](../../README.md) | [Next: CodeDeploy →](./codedeploy.md)

---

# AWS CodeBuild

CodeBuild is a fully managed build service. It compiles source code, runs tests, and produces deployable artifacts. There are no build servers to provision or scale — CodeBuild runs each build in a fresh, isolated Docker container.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Project** | Build configuration: source, environment, buildspec, artifacts, cache |
| **buildspec.yml** | YAML file that defines the build phases and commands |
| **Environment** | The Docker image and compute type used for the build |
| **Phases** | `install` → `pre_build` → `build` → `post_build` |
| **Artifacts** | Files produced by the build, uploaded to S3 |
| **Cache** | S3 or local cache to speed up dependency installation |
| **VPC config** | Allows CodeBuild to reach private resources (RDS, internal APIs) |
| **Service role** | IAM role CodeBuild assumes during the build |

---

## buildspec.yml Reference

```yaml
version: 0.2

env:
  variables:
    APP_ENV: production
  parameter-store:
    SONAR_TOKEN: /ci/sonar-token
  secrets-manager:
    DOCKER_HUB_PASSWORD: ci/docker-hub:password

phases:
  install:
    runtime-versions:
      python: "3.12"
      nodejs: "20"
    commands:
      - pip install --upgrade pip
      - pip install -r requirements.txt

  pre_build:
    commands:
      - echo "Running tests..."
      - pytest tests/ --junitxml=test-results/results.xml
      - echo "Logging in to ECR..."
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION |
          docker login --username AWS --password-stdin $ECR_REGISTRY

  build:
    commands:
      - echo "Building Docker image..."
      - docker build
          --cache-from $ECR_REGISTRY/$IMAGE_REPO:cache
          --tag $ECR_REGISTRY/$IMAGE_REPO:$CODEBUILD_RESOLVED_SOURCE_VERSION
          --tag $ECR_REGISTRY/$IMAGE_REPO:latest
          .

  post_build:
    commands:
      - echo "Pushing image to ECR..."
      - docker push $ECR_REGISTRY/$IMAGE_REPO:$CODEBUILD_RESOLVED_SOURCE_VERSION
      - docker push $ECR_REGISTRY/$IMAGE_REPO:latest
      - printf '[{"name":"backend","imageUri":"%s"}]'
          $ECR_REGISTRY/$IMAGE_REPO:$CODEBUILD_RESOLVED_SOURCE_VERSION > imagedefinitions.json

artifacts:
  files:
    - imagedefinitions.json
    - appspec.yml
    - taskdef.json
  discard-paths: no

reports:
  test-results:
    files:
      - "test-results/results.xml"
    file-format: JUNITXML

cache:
  paths:
    - "/root/.cache/pip/**/*"
    - "/root/.npm/**/*"
```

---

## Creating a CodeBuild Project

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com"
ARTIFACT_BUCKET="my-codebuild-artifacts-${ACCOUNT_ID}"

# Create artifact bucket
aws s3api create-bucket --bucket $ARTIFACT_BUCKET --region us-east-1

# Create the CodeBuild project
aws codebuild create-project \
    --name my-app-build \
    --description "Build and test my-app backend" \
    --source '{
        "type": "GITHUB",
        "location": "https://github.com/my-org/my-app.git",
        "buildspec": "buildspec.yml",
        "gitCloneDepth": 1,
        "reportBuildStatus": true
    }' \
    --environment '{
        "type": "LINUX_CONTAINER",
        "computeType": "BUILD_GENERAL1_MEDIUM",
        "image": "aws/codebuild/standard:7.0",
        "privilegedMode": true,
        "environmentVariables": [
            {"name": "ECR_REGISTRY", "value": "'"$ECR_REGISTRY"'"},
            {"name": "IMAGE_REPO", "value": "my-app/backend"},
            {"name": "AWS_DEFAULT_REGION", "value": "us-east-1"}
        ]
    }' \
    --artifacts '{
        "type": "S3",
        "location": "'"$ARTIFACT_BUCKET"'",
        "name": "build-output",
        "packaging": "ZIP"
    }' \
    --cache '{
        "type": "S3",
        "location": "'"$ARTIFACT_BUCKET"'/cache"
    }' \
    --service-role arn:aws:iam::$ACCOUNT_ID:role/CodeBuildServiceRole \
    --logs-config '{
        "cloudWatchLogs": {
            "status": "ENABLED",
            "groupName": "/codebuild/my-app-build",
            "streamName": "build"
        }
    }' \
    --tags key=Environment,value=production

# Create CloudWatch log group
aws logs create-log-group --log-group-name "/codebuild/my-app-build"
aws logs put-retention-policy --log-group-name "/codebuild/my-app-build" --retention-in-days 30
```

---

## Starting and Monitoring Builds

```bash
# Start a build manually
BUILD_ID=$(aws codebuild start-build \
    --project-name my-app-build \
    --source-version "main" \
    --environment-variables-override \
        name=APP_ENV,value=staging,type=PLAINTEXT \
    --query 'build.id' --output text)

echo "Build started: $BUILD_ID"

# Poll build status (builds typically take 2–15 minutes)
aws codebuild batch-get-builds \
    --ids "$BUILD_ID" \
    --query 'builds[0].{Status:buildStatus,Phase:currentPhase,Start:startTime,Duration:buildComplete}' \
    --output table

# Get build logs URL
aws codebuild batch-get-builds \
    --ids "$BUILD_ID" \
    --query 'builds[0].logs.deepLink' --output text

# List recent builds
aws codebuild list-builds-for-project \
    --project-name my-app-build \
    --sort-order DESCENDING \
    --query 'ids[:5]' --output text
```

---

## CodeBuild IAM Service Role

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/codebuild/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:GetObjectVersion"
            ],
            "Resource": "arn:aws:s3:::my-codebuild-artifacts/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "ssm:GetParameters",
                "kms:Decrypt"
            ],
            "Resource": [
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:ci/*",
                "arn:aws:ssm:us-east-1:123456789012:parameter/ci/*"
            ]
        }
    ]
}
```

---

## GitHub Integration (Webhooks)

```bash
# Connect CodeBuild to GitHub via a personal access token stored in Secrets Manager
aws codebuild import-source-credentials \
    --server-type GITHUB \
    --auth-type PERSONAL_ACCESS_TOKEN \
    --token $(aws secretsmanager get-secret-value \
        --secret-id ci/github-token --query SecretString --output text)

# Create a webhook: build on every push to main or PR to main
aws codebuild create-webhook \
    --project-name my-app-build \
    --filter-groups '[
        [
            {"type": "EVENT", "pattern": "PUSH"},
            {"type": "HEAD_REF", "pattern": "^refs/heads/main$"}
        ],
        [
            {"type": "EVENT", "pattern": "PULL_REQUEST_CREATED,PULL_REQUEST_UPDATED"},
            {"type": "BASE_REF", "pattern": "^refs/heads/main$"}
        ]
    ]'
```

---

## VPC Configuration (Private Resources)

```bash
# Run CodeBuild inside a VPC to access private RDS, internal APIs, etc.
aws codebuild update-project \
    --name my-app-build \
    --vpc-config '{
        "vpcId": "vpc-0123456789abcdef0",
        "subnets": ["subnet-aaa", "subnet-bbb"],
        "securityGroupIds": ["sg-codebuild"]
    }'
# Note: CodeBuild in a VPC without a NAT Gateway cannot reach the internet
```

---

## Common Compute Types

| Type | vCPU | Memory | Use |
|------|------|--------|-----|
| `BUILD_GENERAL1_SMALL` | 3 | 4 GB | Simple builds, unit tests |
| `BUILD_GENERAL1_MEDIUM` | 7 | 16 GB | Docker builds, most workloads |
| `BUILD_GENERAL1_LARGE` | 15 | 36 GB | Large Docker images, parallel test suites |
| `BUILD_GENERAL1_2XLARGE` | 72 | 144 GB | Very large builds, GPU workloads |

---

## References

- [CodeBuild documentation](https://docs.aws.amazon.com/codebuild/latest/userguide/)
- [buildspec.yml reference](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html)
- [Managed Docker images](https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref-available.html)
- [CodeBuild pricing](https://aws.amazon.com/codebuild/pricing/)
---

← [Previous: AWS CI/CD](./README.md) | [Home](../../README.md) | [Next: CodeDeploy →](./codedeploy.md)
