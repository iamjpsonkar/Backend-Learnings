← [Previous: CodeBuild](./codebuild.md) | [Home](../../README.md) | [Next: CodePipeline →](./codepipeline.md)

---

# AWS CodeDeploy

CodeDeploy automates application deployments to EC2, on-premises servers, ECS, and Lambda. It supports rolling, blue/green, canary, and all-at-once deployment strategies with automatic rollback on failure.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Application** | Logical container grouping deployment groups and revisions |
| **Deployment group** | Target infrastructure (EC2 tags, ASG, ECS cluster/service, Lambda function) |
| **Revision** | The deployable artifact: S3 zip (EC2), container image (ECS), or Lambda version |
| **Deployment configuration** | How many targets are updated at once (all-at-once, half-at-a-time, one-at-a-time, custom) |
| **appspec.yml** | Deployment instructions — files to copy, lifecycle hooks to run (EC2) or container config (ECS/Lambda) |
| **Lifecycle hooks** | Shell scripts or Lambda functions run at defined stages (BeforeInstall, AfterInstall, ValidateService) |
| **Rollback** | Automatic or manual re-deployment of the previous successful revision |

---

## Deployment Strategies by Platform

| Strategy | EC2 | ECS | Lambda |
|----------|-----|-----|--------|
| All-at-once | Yes | No | No |
| Rolling (N at a time) | Yes | No | No |
| Blue/green | Yes | Yes | Yes |
| Canary (% then 100%) | No | No | Yes |
| Linear (% per interval) | No | No | Yes |

---

## EC2 Deployments

### appspec.yml for EC2

```yaml
version: 0.0
os: linux

files:
  - source: /
    destination: /opt/my-app

permissions:
  - object: /opt/my-app
    owner: myapp
    group: myapp
    mode: "644"
    type:
      - file
  - object: /opt/my-app/scripts
    mode: "755"
    type:
      - file

hooks:
  BeforeInstall:
    - location: scripts/stop_server.sh
      timeout: 30
      runas: root
  AfterInstall:
    - location: scripts/install_dependencies.sh
      timeout: 120
      runas: root
  ApplicationStart:
    - location: scripts/start_server.sh
      timeout: 60
      runas: root
  ValidateService:
    - location: scripts/validate_health.sh
      timeout: 60
      runas: root
```

```bash
# scripts/validate_health.sh
#!/bin/bash
MAX_RETRIES=10
RETRY_DELAY=5

for i in $(seq 1 $MAX_RETRIES); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
    if [ "$HTTP_CODE" = "200" ]; then
        echo "Health check passed"
        exit 0
    fi
    echo "Attempt $i: got $HTTP_CODE, retrying in ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY
done
echo "Health check failed after $MAX_RETRIES attempts"
exit 1
```

```bash
# Create CodeDeploy application for EC2
aws deploy create-application \
    --application-name my-app-ec2 \
    --compute-platform Server

# Create deployment group targeting an Auto Scaling Group
aws deploy create-deployment-group \
    --application-name my-app-ec2 \
    --deployment-group-name production \
    --deployment-config-name CodeDeployDefault.HalfAtATime \
    --auto-scaling-groups my-app-asg \
    --service-role-arn arn:aws:iam::123456789012:role/CodeDeployServiceRole \
    --load-balancer-info '{
        "targetGroupInfoList": [{"name": "my-app-tg"}]
    }' \
    --auto-rollback-configuration enabled=true,events=DEPLOYMENT_FAILURE,DEPLOYMENT_STOP_ON_ALARM \
    --alarm-configuration alarms=[{name=high-error-rate}],enabled=true \
    --tags Key=Environment,Value=production

# Create a deployment from S3
aws deploy create-deployment \
    --application-name my-app-ec2 \
    --deployment-group-name production \
    --s3-location bucket=my-artifacts-bucket,key=my-app/v1.2.3.zip,bundleType=zip \
    --deployment-config-name CodeDeployDefault.HalfAtATime \
    --description "Deploy v1.2.3"
```

---

## ECS Blue/Green Deployments

With ECS + CodeDeploy blue/green, CodeDeploy manages two ECS task sets (blue = current, green = new). Traffic is shifted from blue to green using the ALB listener; if validation fails, traffic flips back.

### appspec.yml for ECS

```yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: "arn:aws:ecs:us-east-1:123456789012:task-definition/my-app-backend:2"
        LoadBalancerInfo:
          ContainerName: "backend"
          ContainerPort: 8080
        PlatformVersion: "LATEST"

Hooks:
  - BeforeAllowTraffic: "arn:aws:lambda:us-east-1:123456789012:function:pre-traffic-check"
  - AfterAllowTraffic: "arn:aws:lambda:us-east-1:123456789012:function:post-traffic-check"
```

```bash
# Create application for ECS
aws deploy create-application \
    --application-name my-app-ecs \
    --compute-platform ECS

# Create ECS deployment group with blue/green
aws deploy create-deployment-group \
    --application-name my-app-ecs \
    --deployment-group-name production \
    --deployment-config-name CodeDeployDefault.ECSAllAtOnce \
    --service-role-arn arn:aws:iam::123456789012:role/CodeDeployECSRole \
    --ecs-services clusterName=production,serviceName=my-app-backend \
    --load-balancer-info '{
        "targetGroupPairInfoList": [{
            "targetGroups": [
                {"name": "my-app-blue-tg"},
                {"name": "my-app-green-tg"}
            ],
            "prodTrafficRoute": {"listenerArns": ["arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/my-alb/abc123/listener/443"]},
            "testTrafficRoute": {"listenerArns": ["arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/my-alb/abc123/listener/8080"]}
        }]
    }' \
    --blue-green-deployment-configuration '{
        "terminateBlueInstancesOnDeploymentSuccess": {
            "action": "TERMINATE",
            "terminationWaitTimeInMinutes": 5
        },
        "deploymentReadyOption": {
            "actionOnTimeout": "CONTINUE_DEPLOYMENT",
            "waitTimeInMinutes": 0
        }
    }' \
    --auto-rollback-configuration enabled=true,events=DEPLOYMENT_FAILURE

# Deploy new task definition
aws deploy create-deployment \
    --application-name my-app-ecs \
    --deployment-group-name production \
    --revision '{
        "revisionType": "AppSpecContent",
        "appSpecContent": {
            "content": "{\"version\":0.0,\"Resources\":[{\"TargetService\":{\"Type\":\"AWS::ECS::Service\",\"Properties\":{\"TaskDefinition\":\"arn:aws:ecs:us-east-1:123456789012:task-definition/my-app-backend:3\",\"LoadBalancerInfo\":{\"ContainerName\":\"backend\",\"ContainerPort\":8080}}}}]}"
        }
    }'
```

---

## Lambda Deployments

```bash
# Create application for Lambda
aws deploy create-application \
    --application-name my-lambda-app \
    --compute-platform Lambda

# Create deployment group with canary (10% for 5 minutes, then 100%)
aws deploy create-deployment-group \
    --application-name my-lambda-app \
    --deployment-group-name production \
    --deployment-config-name CodeDeployDefault.LambdaCanary10Percent5Minutes \
    --service-role-arn arn:aws:iam::123456789012:role/CodeDeployLambdaRole \
    --alarm-configuration '{
        "alarms": [{"name": "my-lambda-error-rate"}],
        "enabled": true
    }' \
    --auto-rollback-configuration enabled=true,events=DEPLOYMENT_FAILURE,DEPLOYMENT_STOP_ON_ALARM
```

### appspec.yml for Lambda

```yaml
version: 0.0
Resources:
  - MyFunction:
      Type: AWS::Lambda::Function
      Properties:
        Name: my-lambda-function
        Alias: live
        CurrentVersion: "1"
        TargetVersion: "2"

Hooks:
  - BeforeAllowTraffic: !Sub "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:pre-traffic-validate"
  - AfterAllowTraffic: !Sub "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:post-traffic-validate"
```

---

## Monitoring Deployments

```bash
# Get deployment status
aws deploy get-deployment \
    --deployment-id d-ABC123XYZ \
    --query 'deploymentInfo.{Status:status,ErrorCode:errorInformation.code,ErrorMsg:errorInformation.message,Overview:deploymentOverview}'

# List deployment targets and their status
aws deploy list-deployment-targets \
    --deployment-id d-ABC123XYZ \
    --query 'targetIds' --output text | xargs -I{} \
    aws deploy get-deployment-target \
        --deployment-id d-ABC123XYZ \
        --target-id {} \
        --query 'deploymentTarget.ecsTarget.{Status:status,TaskSets:taskSetsInfo[*].{Arn:taskSetArn,Status:status,TrafficWeight:trafficWeight}}'

# Stop and rollback a deployment
aws deploy stop-deployment \
    --deployment-id d-ABC123XYZ \
    --auto-rollback-enabled

# List recent deployments
aws deploy list-deployments \
    --application-name my-app-ecs \
    --deployment-group-name production \
    --create-time-range start=$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
    --include-only-statuses Failed Stopped \
    --query 'deployments' --output text
```

---

## Deployment Configurations Reference

| Config | Target | Meaning |
|--------|--------|---------|
| `CodeDeployDefault.AllAtOnce` | EC2/Lambda | All targets at once |
| `CodeDeployDefault.HalfAtATime` | EC2 | 50% at a time |
| `CodeDeployDefault.OneAtATime` | EC2 | 1 instance at a time (safest, slowest) |
| `CodeDeployDefault.ECSAllAtOnce` | ECS | Shift all traffic to new task set |
| `CodeDeployDefault.ECSLinear10PercentEvery1Minutes` | ECS | +10% traffic every minute |
| `CodeDeployDefault.ECSCanary10Percent5Minutes` | ECS | 10% for 5min, then 100% |
| `CodeDeployDefault.LambdaCanary10Percent5Minutes` | Lambda | 10% for 5min, then 100% |
| `CodeDeployDefault.LambdaLinear10PercentEvery1Minute` | Lambda | +10% weight every minute |

---

## References

- [CodeDeploy documentation](https://docs.aws.amazon.com/codedeploy/latest/userguide/)
- [appspec.yml reference](https://docs.aws.amazon.com/codedeploy/latest/userguide/reference-appspec-file.html)
- [ECS blue/green deployments](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-create-ecs-cfn.html)
- [CodeDeploy pricing](https://aws.amazon.com/codedeploy/pricing/)
---

← [Previous: CodeBuild](./codebuild.md) | [Home](../../README.md) | [Next: CodePipeline →](./codepipeline.md)
