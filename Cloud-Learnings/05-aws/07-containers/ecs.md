← [Previous: ECR](./ecr.md) | [Home](../../README.md) | [Next: EKS →](./eks.md)

---

# Amazon ECS (Elastic Container Service)

ECS is a fully managed container orchestration service. You define what to run (task definitions) and ECS decides where to run it. With the Fargate launch type there are no EC2 instances to manage — AWS runs containers on its infrastructure and bills per vCPU-second and GB-second.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Cluster** | Logical grouping of tasks and services |
| **Task definition** | Blueprint: container image, CPU/memory, ports, IAM roles, volumes |
| **Task** | A running instance of a task definition (one or more containers) |
| **Service** | Keeps N tasks running; integrates with ALB and auto scaling |
| **Launch type** | **Fargate** (serverless) or **EC2** (you manage the instances) |
| **Task role** | IAM role assumed by the containers inside the task (application permissions) |
| **Execution role** | IAM role used by ECS agent to pull images and push logs |
| **Capacity provider** | Fargate, Fargate Spot, or an EC2 Auto Scaling Group |

---

## Launch Type Comparison

| | Fargate | EC2 |
|--|---------|-----|
| Infrastructure management | None | You manage ASG, AMI, patching |
| Pricing | Per task vCPU/memory-second | Per EC2 instance (always on) |
| Spot savings | Fargate Spot (~70% discount) | Spot instances |
| GPU support | No | Yes (GPU instance types) |
| Windows containers | Yes | Yes |
| Bin-packing control | No | Yes (task placement strategies) |

---

## Creating a Cluster

```bash
# Create a Fargate cluster
aws ecs create-cluster \
    --cluster-name production \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy \
        capacityProvider=FARGATE,weight=1,base=1 \
        capacityProvider=FARGATE_SPOT,weight=4 \
    --settings name=containerInsights,value=enabled \
    --tags key=Environment,value=production

# Verify
aws ecs describe-clusters \
    --clusters production \
    --query 'clusters[0].{Name:clusterName,Status:status,Tasks:runningTasksCount,Providers:capacityProviders}'
```

---

## Task Definitions

```bash
# Register a Fargate task definition
aws ecs register-task-definition \
    --family my-app-backend \
    --requires-compatibilities FARGATE \
    --network-mode awsvpc \
    --cpu "512" \
    --memory "1024" \
    --execution-role-arn arn:aws:iam::123456789012:role/ECSTaskExecutionRole \
    --task-role-arn arn:aws:iam::123456789012:role/my-app-task-role \
    --container-definitions '[
        {
            "name": "backend",
            "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app/backend:v1.2.3",
            "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
            "essential": true,
            "environment": [
                {"name": "APP_ENV", "value": "production"},
                {"name": "PORT", "value": "8080"}
            ],
            "secrets": [
                {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/my-app/database"},
                {"name": "API_KEY", "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/prod/my-app/api-key"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/my-app-backend",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs"
                }
            },
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            },
            "cpu": 512,
            "memory": 1024
        }
    ]'

# Create CloudWatch log group for the task
aws logs create-log-group --log-group-name "/ecs/my-app-backend"
aws logs put-retention-policy --log-group-name "/ecs/my-app-backend" --retention-in-days 30
```

---

## ECS Service (with ALB)

```bash
VPC_ID="vpc-0123456789abcdef0"
PRIVATE_SUBNET_1="subnet-0123456789abcdef1"
PRIVATE_SUBNET_2="subnet-0123456789abcdef2"
TG_ARN="arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-app-tg/abc123"

# Security group for ECS tasks (allow ALB → port 8080)
ECS_SG=$(aws ec2 create-security-group \
    --group-name my-app-ecs-tasks \
    --description "ECS tasks — allow ALB on 8080" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG \
    --protocol tcp --port 8080 \
    --source-group $ALB_SG  # ALB security group ID

# Create the ECS service
aws ecs create-service \
    --cluster production \
    --service-name my-app-backend \
    --task-definition my-app-backend:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={
        subnets=[$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2],
        securityGroups=[$ECS_SG],
        assignPublicIp=DISABLED
    }" \
    --load-balancers "targetGroupArn=$TG_ARN,containerName=backend,containerPort=8080" \
    --health-check-grace-period-seconds 60 \
    --deployment-configuration "minimumHealthyPercent=50,maximumPercent=200" \
    --deployment-controller type=ECS \
    --enable-execute-command \
    --tags key=Environment,value=production

# Wait for the service to stabilize
aws ecs wait services-stable --cluster production --services my-app-backend
echo "Service is stable"
```

---

## Deploying a New Image Version

```bash
# Update service to use a new task definition revision (rolling deploy)
aws ecs update-service \
    --cluster production \
    --service my-app-backend \
    --task-definition my-app-backend:2 \
    --force-new-deployment

# Monitor deployment progress
aws ecs describe-services \
    --cluster production \
    --services my-app-backend \
    --query 'services[0].deployments[*].{Status:status,Desired:desiredCount,Running:runningCount,Pending:pendingCount,TaskDef:taskDefinition}'
```

---

## Service Auto Scaling

```bash
# Register the ECS service as a scalable target
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/production/my-app-backend \
    --min-capacity 2 \
    --max-capacity 20

# Target tracking: scale based on ALB requests per target
aws application-autoscaling put-scaling-policy \
    --policy-name my-app-alb-request-count \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/production/my-app-backend \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
        "TargetValue": 1000,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ALBRequestCountPerTarget",
            "ResourceLabel": "app/my-alb/abc123/targetgroup/my-app-tg/def456"
        },
        "ScaleOutCooldown": 60,
        "ScaleInCooldown": 300
    }'

# Target tracking: scale on CPU utilization
aws application-autoscaling put-scaling-policy \
    --policy-name my-app-cpu \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/production/my-app-backend \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
        "TargetValue": 60,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
        },
        "ScaleOutCooldown": 60,
        "ScaleInCooldown": 120
    }'
```

---

## ECS Exec (Debugging Running Containers)

```bash
# Run an interactive shell in a running Fargate task (requires --enable-execute-command on service)
TASK_ARN=$(aws ecs list-tasks \
    --cluster production \
    --service-name my-app-backend \
    --query 'taskArns[0]' --output text)

aws ecs execute-command \
    --cluster production \
    --task $TASK_ARN \
    --container backend \
    --interactive \
    --command "/bin/sh"
```

---

## IAM Roles Required

```bash
# Execution role — ECS agent uses this to pull images and push logs
# Attach: AmazonECSTaskExecutionRolePolicy
# Add inline for Secrets Manager access:
cat <<'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "ssm:GetParameters",
                "kms:Decrypt"
            ],
            "Resource": [
                "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/my-app/*",
                "arn:aws:ssm:us-east-1:123456789012:parameter/prod/my-app/*"
            ]
        }
    ]
}
EOF

# Task role — application code running in the container uses this
# Grant only the permissions the app needs (S3, DynamoDB, SQS, etc.)
```

---

## Running One-Off Tasks

```bash
# Run a database migration task (one-off, not a service)
aws ecs run-task \
    --cluster production \
    --task-definition my-app-backend:2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={
        subnets=[$PRIVATE_SUBNET_1],
        securityGroups=[$ECS_SG],
        assignPublicIp=DISABLED
    }" \
    --overrides '{
        "containerOverrides": [{
            "name": "backend",
            "command": ["python", "manage.py", "migrate"],
            "environment": [{"name": "RUN_MIGRATIONS", "value": "true"}]
        }]
    }' \
    --count 1
```

---

## Key Metrics and Alarms

```bash
# Alarm on high CPU across all tasks in the service
aws cloudwatch put-metric-alarm \
    --alarm-name "ecs-my-app-high-cpu" \
    --namespace AWS/ECS \
    --metric-name CPUUtilization \
    --dimensions Name=ClusterName,Value=production Name=ServiceName,Value=my-app-backend \
    --statistic Average --period 300 --threshold 80 \
    --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts \
    --treat-missing-data notBreaching

# Alarm: running task count drops below desired
aws cloudwatch put-metric-alarm \
    --alarm-name "ecs-my-app-task-count-low" \
    --namespace AWS/ECS \
    --metric-name RunningTaskCount \
    --dimensions Name=ClusterName,Value=production Name=ServiceName,Value=my-app-backend \
    --statistic Average --period 60 --threshold 2 \
    --comparison-operator LessThanThreshold --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts \
    --treat-missing-data breaching
```

---

## References

- [ECS documentation](https://docs.aws.amazon.com/ecs/latest/developerguide/)
- [Fargate task sizing](https://docs.aws.amazon.com/ecs/latest/developerguide/task-cpu-memory-error.html)
- [ECS task networking](https://docs.aws.amazon.com/ecs/latest/developerguide/task-networking.html)
- [ECS pricing](https://aws.amazon.com/ecs/pricing/)
---

← [Previous: ECR](./ecr.md) | [Home](../../README.md) | [Next: EKS →](./eks.md)
