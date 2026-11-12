← [Previous: AWS Containers](./README.md) | [Home](../../README.md) | [Next: ECS →](./ecs.md)

---

# Amazon ECR (Elastic Container Registry)

ECR is a fully managed private container registry. It integrates natively with ECS, EKS, Lambda, CodePipeline, and the Docker CLI. Images are stored encrypted at rest in S3 and scanned for vulnerabilities by Amazon Inspector.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Registry** | One private registry per AWS account per region (`{account}.dkr.ecr.{region}.amazonaws.com`) |
| **Repository** | A named collection of container images (analogous to a Docker Hub repo) |
| **Image tag** | Mutable label pointing to an image digest (e.g., `latest`, `v1.2.3`) |
| **Immutable tags** | Setting that prevents overwriting an existing tag — recommended for production |
| **Image scanning** | Basic (on push) or Enhanced (Inspector — continuous CVE scanning) |
| **Lifecycle policy** | Rules to automatically expire old images and control storage costs |
| **Replication** | Cross-region and cross-account replication of images |
| **Pull-through cache** | Proxy public registries (Docker Hub, ECR Public, Quay) through ECR to avoid rate limits |

---

## Creating a Repository

```bash
# Create a private repository with immutable tags and scan-on-push
REPO_URI=$(aws ecr create-repository \
    --repository-name my-app/backend \
    --image-scanning-configuration scanOnPush=true \
    --image-tag-mutability IMMUTABLE \
    --encryption-configuration encryptionType=AES256 \
    --tags Key=Environment,Value=production Key=Service,Value=my-app \
    --query 'repository.repositoryUri' --output text)

echo "Repository URI: $REPO_URI"
# Output: 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app/backend

# List repositories
aws ecr describe-repositories \
    --query 'repositories[*].{Name:repositoryName,URI:repositoryUri,Mutability:imageTagMutability,ScanOnPush:imageScanningConfiguration.scanOnPush}' \
    --output table
```

---

## Authenticating and Pushing Images

```bash
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Authenticate Docker to ECR (token valid for 12 hours)
aws ecr get-login-password --region $REGION | \
    docker login --username AWS --password-stdin $REGISTRY

# Build, tag, and push
IMAGE_TAG="v1.2.3"
docker build -t my-app/backend:$IMAGE_TAG .
docker tag my-app/backend:$IMAGE_TAG $REGISTRY/my-app/backend:$IMAGE_TAG
docker push $REGISTRY/my-app/backend:$IMAGE_TAG

# List images in the repository
aws ecr describe-images \
    --repository-name my-app/backend \
    --query 'imageDetails[*].{Tags:imageTags,Digest:imageDigest,PushedAt:imagePushedAt,SizeMB:imageSizeInBytes}' \
    --output table
```

---

## Lifecycle Policies

```bash
# Keep only the last 10 tagged images; expire all untagged images after 1 day
aws ecr put-lifecycle-policy \
    --repository-name my-app/backend \
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

# Preview what would be deleted (dry run)
aws ecr get-lifecycle-policy-preview \
    --repository-name my-app/backend
```

---

## Image Scanning

```bash
# Enhanced scanning (Inspector) — enable at registry level
aws ecr put-registry-scanning-configuration \
    --scan-type ENHANCED \
    --rules '[{
        "repositoryFilters": [{"filter": "*", "filterType": "WILDCARD"}],
        "scanFrequency": "CONTINUOUS_SCAN"
    }]'

# Basic scanning — trigger manual scan on an existing image
aws ecr start-image-scan \
    --repository-name my-app/backend \
    --image-id imageTag=v1.2.3

# Get scan findings
aws ecr describe-image-scan-findings \
    --repository-name my-app/backend \
    --image-id imageTag=v1.2.3 \
    --query 'imageScanFindings.findings[?severity==`CRITICAL` || severity==`HIGH`].{Name:name,Severity:severity,URI:uri}' \
    --output table
```

---

## Repository Policies

```bash
# Allow another account (or ECS task role) to pull from this repository
aws ecr set-repository-policy \
    --repository-name my-app/backend \
    --policy-text '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCrossAccountPull",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::222222222222:root"
                },
                "Action": [
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:BatchCheckLayerAvailability"
                ]
            }
        ]
    }'
```

---

## Cross-Region Replication

```bash
# Replicate all images to eu-west-1 (disaster recovery / latency)
aws ecr put-replication-configuration \
    --replication-configuration '{
        "rules": [{
            "destinations": [{
                "region": "eu-west-1",
                "registryId": "123456789012"
            }],
            "repositoryFilters": [{
                "filter": "my-app/",
                "filterType": "PREFIX_MATCH"
            }]
        }]
    }'
```

---

## Pull-Through Cache

```bash
# Configure ECR to proxy Docker Hub (avoids pull rate limits in CI)
aws ecr create-pull-through-cache-rule \
    --ecr-repository-prefix "dockerhub" \
    --upstream-registry-url "registry-1.docker.io" \
    --credential-arn arn:aws:secretsmanager:us-east-1:123456789012:secret:ecr-dockerhub-creds

# Pull through cache — image is cached in your ECR after first pull
docker pull $REGISTRY/dockerhub/library/nginx:1.25-alpine
```

---

## IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:BatchCheckLayerAvailability",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload"
            ],
            "Resource": "arn:aws:ecr:us-east-1:123456789012:repository/my-app/*"
        }
    ]
}
```

**Note:** `ecr:GetAuthorizationToken` must be on `Resource: "*"` — it has no resource-level permission.

---

## References

- [ECR documentation](https://docs.aws.amazon.com/ecr/latest/userguide/)
- [Lifecycle policy examples](https://docs.aws.amazon.com/ecr/latest/userguide/lifecycle_policy_examples.html)
- [ECR pricing](https://aws.amazon.com/ecr/pricing/)
---

← [Previous: AWS Containers](./README.md) | [Home](../../README.md) | [Next: ECS →](./ecs.md)
