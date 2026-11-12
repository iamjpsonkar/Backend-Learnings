← [Previous: AWS Networking](./aws-networking.md) | [Home](../README.md) | [Next: Databases →](./databases.md)

---

# Troubleshooting: Containers & Kubernetes

Container failures almost always fall into: image pull errors, startup crashes, OOM kills, health check failures, or networking issues between services. ECS and Kubernetes surface these differently but the root causes are the same.

---

## ECS Task Troubleshooting

```bash
CLUSTER="prod-cluster"
SERVICE="order-api"

# Step 1: Check service events (most recent failures appear here)
aws ecs describe-services \
    --cluster $CLUSTER \
    --services $SERVICE \
    --query 'services[0].events[0:10].{CreatedAt:createdAt,Message:message}'

# Common events:
# "service is unable to consistently start tasks successfully" → task is crashing
# "resource is not up to the required health check" → health check failing
# "(service X) has reached a steady state" → normal

# Step 2: Find stopped tasks (last 1 hour)
aws ecs list-tasks \
    --cluster $CLUSTER \
    --service-name $SERVICE \
    --desired-status STOPPED \
    --query 'taskArns'

# Step 3: Describe a stopped task — look for stopCode and stoppedReason
TASK_ARN="arn:aws:ecs:us-east-1:123456789012:task/prod-cluster/abc123"

aws ecs describe-tasks \
    --cluster $CLUSTER \
    --tasks $TASK_ARN \
    --query 'tasks[0].{
        StopCode:stopCode,
        StopReason:stoppedReason,
        LastStatus:lastStatus,
        Container:containers[0].{
            Exit:exitCode,
            Reason:reason,
            Health:healthStatus
        }
    }'

# Common stop codes:
# TaskFailedToStart → container failed before starting (image pull, permission issue)
# EssentialContainerExited → main container exited
# UserInitiated → manual stop
# ServiceSchedulerInitiated → service replaced unhealthy task

# Step 4: Read CloudWatch logs for the stopped task
LOG_GROUP="/ecs/$SERVICE"
TASK_ID="abc123"  # short ID from task ARN

aws logs get-log-events \
    --log-group-name $LOG_GROUP \
    --log-stream-name "ecs/$SERVICE/$TASK_ID" \
    --limit 100 \
    --query 'events[*].message' \
    --output text
```

### ECR Authentication Errors

```bash
# Error: "CannotPullContainerError: pull access denied"
# Cause 1: ECR auth token expired (valid only 12 hours)
# Fix: execution role must have ecr:GetAuthorizationToken + ecr:BatchGetImage

# Check execution role permissions
TASK_DEF="order-api:5"
EXEC_ROLE_ARN=$(aws ecs describe-task-definition \
    --task-definition $TASK_DEF \
    --query 'taskDefinition.executionRoleArn' --output text)

aws iam simulate-principal-policy \
    --policy-source-arn $EXEC_ROLE_ARN \
    --action-names ecr:GetAuthorizationToken ecr:BatchGetImage ecr:GetDownloadUrlForLayer \
    --query 'EvaluationResults[*].{Action:EvalActionName,Decision:EvalDecision}'

# Cause 2: Image URI in wrong region
# ECR URI format: ACCOUNT.dkr.ecr.REGION.amazonaws.com/REPO:TAG
# Check: ensure region in URI matches cluster region

# Cause 3: Cross-account ECR — missing resource policy on ECR repo
aws ecr get-repository-policy \
    --repository-name order-api \
    --region us-east-1
```

### Health Check Failures

```bash
# ECS task keeps getting replaced?
# Check health check configuration in task definition
aws ecs describe-task-definition \
    --task-definition order-api \
    --query 'taskDefinition.containerDefinitions[0].healthCheck'

# Expected: command returns exit 0 for healthy
# Test health check locally:
docker run --rm your-image:latest \
    sh -c "curl -sf http://localhost:8080/health/ready || exit 1"

# ALB target group health check settings
aws elbv2 describe-target-groups \
    --names order-api-tg \
    --query 'TargetGroups[0].{
        HealthCheckPath:HealthCheckPath,
        HealthyThreshold:HealthyThresholdCount,
        UnhealthyThreshold:UnhealthyThresholdCount,
        Interval:HealthCheckIntervalSeconds,
        Timeout:HealthCheckTimeoutSeconds,
        Matcher:Matcher.HttpCode
    }'

# If startPeriod is too short, increase it (container needs time to start)
# ECS task health check: startPeriod = 60 seconds minimum for Java/JVM apps
```

---

## Kubernetes Pod Troubleshooting

```bash
# Step 1: Check pod status
kubectl get pods -n prod -l app=order-api

# STATUS          MEANING
# Pending         → no node has capacity or PVC not bound
# Init:Error      → init container failed
# CrashLoopBackOff → container crashes immediately on start
# OOMKilled       → ran out of memory
# ImagePullBackOff → can't pull image
# Running (0/1)   → running but not ready (health check failing)

# Step 2: Describe the pod (events + state)
kubectl describe pod -n prod <pod-name>
# Look at: Events section at bottom, State/Last State in container section

# Step 3: Read logs
kubectl logs -n prod <pod-name> --tail=100
kubectl logs -n prod <pod-name> --previous  # logs from previous crashed container
kubectl logs -n prod -l app=order-api --tail=50 --prefix  # all pod logs

# Step 4: Get into a running pod
kubectl exec -it -n prod <pod-name> -- /bin/sh
# If container has no shell:
kubectl debug -it <pod-name> --image=busybox --target=<container-name>
```

### CrashLoopBackOff

```bash
# Read previous container logs
kubectl logs -n prod <pod-name> --previous

# Common causes:
# 1. Missing environment variable → KeyError / undefined reference
kubectl describe pod <pod-name> -n prod | grep -A5 "Environment"

# 2. Wrong command/entrypoint
kubectl get pod <pod-name> -n prod -o jsonpath='{.spec.containers[0].command}'

# 3. Permission denied on read-only filesystem
# Check: readOnlyRootFilesystem: true in securityContext
# Fix: mount writable volumes for /tmp and app-specific write paths
kubectl get pod <pod-name> -n prod -o jsonpath='{.spec.containers[0].securityContext}'

# 4. Health check endpoint not ready in time
# Fix: increase initialDelaySeconds or startupProbe
```

### OOMKilled

```bash
# Check if pod was OOMKilled
kubectl describe pod -n prod <pod-name> | grep -A5 "Last State"
# OOMKilled: Reason = OOMKilled, Exit Code = 137

# Check current memory usage vs limits
kubectl top pods -n prod

# Check node memory pressure
kubectl describe node <node-name> | grep -A5 "Conditions"

# Fix: increase memory limit in deployment
kubectl set resources deployment order-api \
    -n prod \
    --limits=memory=1Gi \
    --requests=memory=512Mi

# Or use VPA (Vertical Pod Autoscaler) to auto-recommend
kubectl get vpa -n prod order-api -o yaml
```

### ImagePullBackOff

```bash
# Get exact error
kubectl describe pod -n prod <pod-name> | grep -A5 "Failed"

# Cause 1: Wrong image tag
kubectl get pod <pod-name> -n prod \
    -o jsonpath='{.spec.containers[0].image}'

# Cause 2: ECR auth issue — check IRSA on service account
kubectl get serviceaccount order-api -n prod -o yaml
# Verify annotation: eks.amazonaws.com/role-arn

# Check IRSA role trust policy allows the OIDC issuer
CLUSTER_OIDC=$(aws eks describe-cluster \
    --name prod-cluster \
    --query 'cluster.identity.oidc.issuer' --output text | sed 's|https://||')

aws iam get-role \
    --role-name order-api-role \
    --query 'Role.AssumeRolePolicyDocument'

# Test ECR pull from within the cluster
kubectl run ecr-test \
    --image=$ECR_URI:latest \
    --restart=Never \
    --serviceaccount=order-api \
    -n prod \
    -- echo "pull succeeded"

kubectl logs -n prod ecr-test
kubectl delete pod ecr-test -n prod
```

---

## Docker Build Failures

```bash
# Layer cache invalidation — build takes too long
# Fix: put frequently-changing layers LAST in Dockerfile
# Bad:  COPY . .  then  RUN pip install
# Good: COPY requirements.txt .  then  RUN pip install  then  COPY . .

# Multi-stage build: wrong COPY --from stage name
# Error: failed to get image manifest: ... not found
docker build --no-cache --progress=plain . 2>&1 | head -50

# BuildKit cache issue — force clean build
docker builder prune
docker build --no-cache -t myimage:latest .

# Check .dockerignore — is it excluding files you need?
cat .dockerignore
# Run build context check:
docker build --no-cache --progress=plain . 2>&1 | grep "Sending build context"

# Diagnose build failure step by step
# Run the failing RUN layer interactively from the previous layer
docker run -it --entrypoint sh <previous-layer-image-id>
# Then manually run the failing command
```

---

## References

- [ECS troubleshooting guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/troubleshooting.html)
- [Kubernetes debug pods](https://kubernetes.io/docs/tasks/debug/debug-application/)
- [kubectl cheatsheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

---

← [Previous: AWS Networking](./aws-networking.md) | [Home](../README.md) | [Next: Databases →](./databases.md)
