← [Previous: Databases](./databases.md) | [Home](../README.md) | [Next: Performance →](./performance.md)

---

# Troubleshooting: CI/CD

CI/CD failures cost engineering time disproportionate to their complexity. Most failures are permission errors, environment variable mismatches, or test flakiness. This guide covers GitHub Actions, ECR, and ECS deploy issues.

---

## GitHub Actions Failures

### OIDC / AWS Authentication

```bash
# Error: "Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity"
# Cause 1: Role trust policy doesn't match the branch/repo

# Check trust policy
aws iam get-role \
    --role-name github-actions-deploy-role \
    --query 'Role.AssumeRolePolicyDocument'

# The sub claim format: repo:ORG/REPO:ref:refs/heads/BRANCH
# Or for any event:    repo:ORG/REPO:*
# Check the exact sub claim in your workflow:
# token.actions.githubusercontent.com:sub: repo:myorg/myrepo:ref:refs/heads/main

# Fix: update trust policy to match the sub claim pattern
cat > trust-patch.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Federated": "arn:aws:iam::ACCOUNT:oidc-provider/token.actions.githubusercontent.com"
        },
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
}
EOF

aws iam update-assume-role-policy \
    --role-name github-actions-deploy-role \
    --policy-document file://trust-patch.json

# Cause 2: Workflow missing permissions block
# Add to workflow job:
# permissions:
#   id-token: write
#   contents: read
```

### ECR Push Failures

```bash
# Error: "no basic auth credentials" / "unauthorized: authentication required"
# The ECR login step failed or token expired (tokens valid 12 hours)

# Debug in workflow:
- name: Verify ECR login
  run: |
    aws ecr get-login-password --region us-east-1 | \
        docker login --username AWS --password-stdin \
        ${{ steps.login-ecr.outputs.registry }}
    docker pull ${{ steps.login-ecr.outputs.registry }}/order-api:latest || echo "No existing image (ok for first push)"

# Error: "denied: User is not authorized to perform: ecr:InitiateLayerUpload"
# Fix: add ECR permissions to deploy role
aws iam put-role-policy \
    --role-name github-actions-deploy-role \
    --policy-name ecr-push \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": "*"
        }]
    }'
```

### ECS Deploy Failures

```bash
# Error: "InvalidParameterException: TaskDefinition is inactive"
# Fix: register a new revision before deploying
# The aws-actions/amazon-ecs-deploy-task-definition action does this automatically

# Error: "Service deployment was found unsuccessful"
# The service entered FAILED state during deployment

# Check deployment events
SERVICE="order-api"
CLUSTER="prod-cluster"

aws ecs describe-services \
    --cluster $CLUSTER \
    --services $SERVICE \
    --query 'services[0].deployments[*].{
        Status:status,
        Desired:desiredCount,
        Running:runningCount,
        Failed:failedTasks,
        Created:createdAt,
        Updated:updatedAt
    }'

# Check if circuit breaker triggered
aws ecs describe-services \
    --cluster $CLUSTER \
    --services $SERVICE \
    --query 'services[0].deployments[0].rolloutState'
# COMPLETED = success
# FAILED = circuit breaker triggered rollback
# IN_PROGRESS = still deploying

# Check recent events for the failure reason
aws ecs describe-services \
    --cluster $CLUSTER \
    --services $SERVICE \
    --query 'services[0].events[0:5].message'
```

### Docker Layer Cache Issues in CI

```yaml
# Workflow: cache not being used
# Diagnose: check cache hit rate in GitHub Actions UI
# Or add explicit cache check:
- name: Check cache
  uses: actions/cache@v4
  id: docker-cache
  with:
    path: /tmp/.buildx-cache
    key: ${{ runner.os }}-buildx-${{ hashFiles('**/Dockerfile', '**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-buildx-

- name: Build with cache
  uses: docker/build-push-action@v5
  with:
    cache-from: type=local,src=/tmp/.buildx-cache
    cache-to: type=local,dest=/tmp/.buildx-cache-new,mode=max

# Rotate cache to prevent unbounded growth
- name: Move cache
  run: |
    rm -rf /tmp/.buildx-cache
    mv /tmp/.buildx-cache-new /tmp/.buildx-cache
```

---

## Terraform CI/CD Issues

```bash
# Error: "Error acquiring the state lock"
# Another process holds the DynamoDB lock
LOCK_TABLE="terraform-locks"
LOCK_ID="multi-cloud/prod/terraform.tfstate"

aws dynamodb get-item \
    --table-name $LOCK_TABLE \
    --key '{"LockID": {"S": "'"$LOCK_ID"'"}}' \
    --region us-east-1

# If lock is stale (process died), force-unlock
# Get the lock ID from the error message, then:
terraform force-unlock LOCK_ID_FROM_ERROR

# Error: "Error: Provider configuration not present"
# Cause: terraform plan run before init, or different workspace
terraform init -reconfigure
terraform workspace list
terraform workspace select prod

# Error: "state snapshot was created by Terraform v1.x.x, not by the current version"
# Fix: upgrade Terraform version in CI to match what created the state
# Or: upgrade state with the newer version once
terraform state pull > current.tfstate
# Inspect, then push back with newer version

# S3 backend: state lock contention in parallel CI jobs
# Fix: use separate state files per PR (workspaces) or serialize jobs
```

---

## Deployment Rollback

```bash
# ECS: rollback to previous task definition revision
SERVICE="order-api"
CLUSTER="prod-cluster"

# Get current task definition family and revision
CURRENT_TD=$(aws ecs describe-services \
    --cluster $CLUSTER \
    --services $SERVICE \
    --query 'services[0].taskDefinition' --output text)

# Current: order-api:15 → rollback to order-api:14
FAMILY=$(echo $CURRENT_TD | cut -d: -f1 | awk -F/ '{print $NF}')
CURRENT_REV=$(echo $CURRENT_TD | cut -d: -f2)
PREV_REV=$((CURRENT_REV - 1))

echo "Rolling back from revision $CURRENT_REV to $PREV_REV"

aws ecs update-service \
    --cluster $CLUSTER \
    --service $SERVICE \
    --task-definition "${FAMILY}:${PREV_REV}" \
    --force-new-deployment

aws ecs wait services-stable \
    --cluster $CLUSTER \
    --services $SERVICE
echo "Rollback complete"

# Kubernetes: rollback deployment
kubectl rollout undo deployment/order-api -n prod
kubectl rollout status deployment/order-api -n prod

# Verify rollback
kubectl rollout history deployment/order-api -n prod
```

---

## Flaky Tests

```bash
# Identify flaky tests in CI (failed then passed without code change)
# GitHub Actions: look for "re-run failed jobs" patterns in run history
gh run list --workflow ci.yml --limit 30 --json conclusion,databaseId \
    | jq '[.[] | select(.conclusion == "failure")] | length'

# Run tests multiple times to surface flaky tests
for i in {1..5}; do
    pytest tests/ -x --tb=short 2>&1 | tail -5
done

# Common causes:
# 1. Test depends on ordering — use pytest-randomly to detect
pip install pytest-randomly
pytest tests/ --randomly-seed=12345

# 2. Test shares state via global variable / database / file
# Fix: use proper test fixtures with setup/teardown
# pytest: use function-scoped fixtures, not module-scoped

# 3. Time-dependent test (datetime.now() comparisons)
# Fix: use freezegun or mock datetime

# 4. Race condition in async tests
# Fix: use asyncio.sleep() between setup and assertion, or proper await
```

---

## References

- [GitHub Actions debugging](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/enabling-debug-logging)
- [ECS deployment circuit breaker](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html)
- [Terraform state troubleshooting](https://developer.hashicorp.com/terraform/language/state/locking)

---

← [Previous: Databases](./databases.md) | [Home](../README.md) | [Next: Performance →](./performance.md)
