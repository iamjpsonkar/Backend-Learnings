← [Previous: AMI & Launch Templates](./ami-launch-templates.md) | [Home](../../README.md) | [Next: Load Balancers →](./load-balancers.md)

---

# Auto Scaling Groups

An Auto Scaling Group (ASG) manages a fleet of EC2 instances, automatically adjusting the number of instances based on demand, health checks, and schedules. ASGs work with launch templates and integrate with Application Load Balancers for health-aware traffic distribution.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Minimum capacity** | Floor — ASG will never have fewer instances |
| **Maximum capacity** | Ceiling — ASG will never exceed this count |
| **Desired capacity** | Target count — ASG actively tries to maintain this |
| **Health check** | EC2 status check or ELB health check; unhealthy instances are replaced |
| **Cooldown period** | Pause after a scaling action before another can start |
| **Warm-up period** | Time before a new instance is counted in metrics |
| **Lifecycle hook** | Pause instance at launch or termination to run custom actions |
| **Instance refresh** | Rolling AMI/config update without service interruption |

---

## Creating an Auto Scaling Group

```bash
LT_ID="lt-0abc1234"
ALB_TG_ARN="arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-app/abc123"

# Create the ASG
aws autoscaling create-auto-scaling-group \
    --auto-scaling-group-name my-app-asg \
    --launch-template "LaunchTemplateId=$LT_ID,Version=\$Default" \
    --min-size 2 \
    --max-size 10 \
    --desired-capacity 3 \
    --vpc-zone-identifier "subnet-priv-1a,subnet-priv-1b" \
    --target-group-arns $ALB_TG_ARN \
    --health-check-type ELB \
    --health-check-grace-period 120 \
    --default-cooldown 300 \
    --tags \
        "Key=Name,Value=my-app,PropagateAtLaunch=true" \
        "Key=Environment,Value=production,PropagateAtLaunch=true" \
    --termination-policies "OldestLaunchTemplate,OldestInstance"

echo "ASG created: my-app-asg"

# Verify
aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-names my-app-asg \
    --query 'AutoScalingGroups[0].{
        Name:AutoScalingGroupName,
        Min:MinSize,
        Max:MaxSize,
        Desired:DesiredCapacity,
        Instances:length(Instances),
        Status:Status
    }'
```

---

## Scaling Policies

### Target Tracking (Recommended — Simplest)

Target tracking maintains a specific metric at a target value. AWS automatically creates and manages the CloudWatch alarms.

```bash
ASG_NAME="my-app-asg"

# Scale to keep CPU at 50% (most common starting point)
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name $ASG_NAME \
    --policy-name cpu-target-tracking \
    --policy-type TargetTrackingScaling \
    --target-tracking-configuration '{
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ASGAverageCPUUtilization"
        },
        "TargetValue": 50.0,
        "DisableScaleIn": false
    }'

# Target tracking on ALB requests per target
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name $ASG_NAME \
    --policy-name alb-request-tracking \
    --policy-type TargetTrackingScaling \
    --target-tracking-configuration '{
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ALBRequestCountPerTarget",
            "ResourceLabel": "app/my-alb/abc123/targetgroup/my-app/def456"
        },
        "TargetValue": 1000.0
    }'

# Target tracking on a custom CloudWatch metric
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name $ASG_NAME \
    --policy-name queue-depth-tracking \
    --policy-type TargetTrackingScaling \
    --target-tracking-configuration '{
        "CustomizedMetricSpecification": {
            "MetricName": "ApproximateNumberOfMessagesVisible",
            "Namespace": "AWS/SQS",
            "Dimensions": [{"Name": "QueueName", "Value": "my-app-queue"}],
            "Statistic": "Average"
        },
        "TargetValue": 100.0
    }'
```

### Step Scaling

Step scaling allows different scaling increments at different alarm thresholds.

```bash
# Scale out aggressively at high CPU, scale in conservatively
SCALE_OUT_ARN=$(aws autoscaling put-scaling-policy \
    --auto-scaling-group-name $ASG_NAME \
    --policy-name scale-out-step \
    --policy-type StepScaling \
    --adjustment-type ChangeInCapacity \
    --step-adjustments \
        "MetricIntervalLowerBound=0,MetricIntervalUpperBound=20,ScalingAdjustment=1" \
        "MetricIntervalLowerBound=20,MetricIntervalUpperBound=40,ScalingAdjustment=2" \
        "MetricIntervalLowerBound=40,ScalingAdjustment=4" \
    --estimated-instance-warmup 120 \
    --query 'PolicyARN' --output text)

# Create CloudWatch alarm to trigger the scale-out policy
aws cloudwatch put-metric-alarm \
    --alarm-name my-app-high-cpu \
    --alarm-description "Trigger scale out when CPU > 70%" \
    --namespace AWS/EC2 \
    --metric-name CPUUtilization \
    --dimensions Name=AutoScalingGroupName,Value=$ASG_NAME \
    --statistic Average \
    --period 60 \
    --evaluation-periods 2 \
    --threshold 70 \
    --comparison-operator GreaterThanThreshold \
    --alarm-actions $SCALE_OUT_ARN
```

### Scheduled Scaling

```bash
# Scale up before business hours (UTC)
aws autoscaling put-scheduled-update-group-action \
    --auto-scaling-group-name $ASG_NAME \
    --scheduled-action-name scale-up-morning \
    --recurrence "0 7 * * MON-FRI" \
    --min-size 4 \
    --desired-capacity 6

# Scale down after business hours
aws autoscaling put-scheduled-update-group-action \
    --auto-scaling-group-name $ASG_NAME \
    --scheduled-action-name scale-down-evening \
    --recurrence "0 20 * * MON-FRI" \
    --min-size 2 \
    --desired-capacity 2

# One-time scale-up for a known traffic event (e.g., product launch)
aws autoscaling put-scheduled-update-group-action \
    --auto-scaling-group-name $ASG_NAME \
    --scheduled-action-name product-launch \
    --start-time "2026-06-01T09:00:00Z" \
    --min-size 10 \
    --desired-capacity 10
```

### Predictive Scaling

Predictive scaling uses ML to forecast load 48 hours ahead and proactively adds capacity.

```bash
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name $ASG_NAME \
    --policy-name predictive-cpu \
    --policy-type PredictiveScaling \
    --predictive-scaling-configuration '{
        "MetricSpecifications": [{
            "TargetValue": 50.0,
            "PredefinedMetricPairSpecification": {
                "PredefinedMetricType": "ASGCPUUtilization"
            }
        }],
        "Mode": "ForecastAndScale",
        "SchedulingBufferTime": 300
    }'
```

---

## Lifecycle Hooks

Lifecycle hooks pause instance state transitions (pending or terminating) to allow custom actions (e.g., warm up caches, drain connections, deregister from service discovery).

```bash
# Hook at launch: pause before instance is InService
# Use this to wait for the app to fully warm up
aws autoscaling put-lifecycle-hook \
    --lifecycle-hook-name launch-ready \
    --auto-scaling-group-name $ASG_NAME \
    --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING \
    --default-result CONTINUE \
    --heartbeat-timeout 300 \
    --notification-target-arn arn:aws:sqs:us-east-1:123456789012:my-asg-hooks \
    --role-arn arn:aws:iam::123456789012:role/ASGHookRole

# Hook at termination: pause before instance is terminated
# Use this to drain connections, flush caches, deregister
aws autoscaling put-lifecycle-hook \
    --lifecycle-hook-name graceful-shutdown \
    --auto-scaling-group-name $ASG_NAME \
    --lifecycle-transition autoscaling:EC2_INSTANCE_TERMINATING \
    --default-result CONTINUE \
    --heartbeat-timeout 60

# Signal completion from within the instance (e.g., app startup script)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
aws autoscaling complete-lifecycle-action \
    --lifecycle-hook-name launch-ready \
    --auto-scaling-group-name $ASG_NAME \
    --instance-id $INSTANCE_ID \
    --lifecycle-action-result CONTINUE
```

---

## Instance Refresh (Rolling AMI Updates)

Instance refresh replaces all instances in the ASG with new ones from an updated launch template — rolling update with health checks.

```bash
# Trigger an instance refresh after updating the launch template
aws autoscaling start-instance-refresh \
    --auto-scaling-group-name $ASG_NAME \
    --strategy Rolling \
    --preferences '{
        "MinHealthyPercentage": 90,
        "InstanceWarmup": 120,
        "CheckpointPercentages": [20, 50, 100],
        "CheckpointDelay": 3600
    }'

# Monitor refresh progress
aws autoscaling describe-instance-refreshes \
    --auto-scaling-group-name $ASG_NAME \
    --query 'InstanceRefreshes[0].{
        Status:Status,
        Percent:PercentageComplete,
        InstancesToUpdate:InstancesToUpdate,
        StartTime:StartTime
    }'

# Cancel if something goes wrong
aws autoscaling cancel-instance-refresh --auto-scaling-group-name $ASG_NAME
```

---

## Mixed Instance Types (Spot + On-Demand)

Using a mix of Spot and On-Demand instances can reduce costs by 60–80% for fault-tolerant workloads.

```bash
aws autoscaling create-auto-scaling-group \
    --auto-scaling-group-name my-app-mixed-asg \
    --min-size 2 \
    --max-size 20 \
    --desired-capacity 6 \
    --vpc-zone-identifier "subnet-priv-1a,subnet-priv-1b" \
    --mixed-instances-policy '{
        "LaunchTemplate": {
            "LaunchTemplateSpecification": {
                "LaunchTemplateId": "'$LT_ID'",
                "Version": "$Default"
            },
            "Overrides": [
                {"InstanceType": "m5.large"},
                {"InstanceType": "m5a.large"},
                {"InstanceType": "m6i.large"},
                {"InstanceType": "m6a.large"}
            ]
        },
        "InstancesDistribution": {
            "OnDemandBaseCapacity": 2,
            "OnDemandPercentageAboveBaseCapacity": 20,
            "SpotAllocationStrategy": "capacity-optimized",
            "SpotInstancePools": 4
        }
    }'
```

---

## Monitoring and Troubleshooting

```bash
ASG_NAME="my-app-asg"

# View current instances and their state
aws autoscaling describe-auto-scaling-instances \
    --query 'AutoScalingInstances[?AutoScalingGroupName==`'$ASG_NAME'`].{
        ID:InstanceId,
        State:LifecycleState,
        Health:HealthStatus,
        AZ:AvailabilityZone,
        Type:InstanceType
    }' \
    --output table

# View scaling activity history
aws autoscaling describe-scaling-activities \
    --auto-scaling-group-name $ASG_NAME \
    --max-items 20 \
    --query 'Activities[*].{
        Time:StartTime,
        Cause:Cause,
        Status:StatusCode,
        Detail:StatusMessage
    }' \
    --output table

# View current CloudWatch metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/AutoScaling \
    --metric-name GroupInServiceInstances \
    --dimensions Name=AutoScalingGroupName,Value=$ASG_NAME \
    --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Average \
    --query 'Datapoints[*].{Time:Timestamp,Count:Average}' \
    --output table

# Manually set desired capacity (useful during incident response)
aws autoscaling set-desired-capacity \
    --auto-scaling-group-name $ASG_NAME \
    --desired-capacity 8 \
    --honor-cooldown

# Temporarily suspend scaling (during deployment, maintenance)
aws autoscaling suspend-processes \
    --auto-scaling-group-name $ASG_NAME \
    --scaling-processes Launch Terminate HealthCheck ReplaceUnhealthy

# Resume scaling
aws autoscaling resume-processes \
    --auto-scaling-group-name $ASG_NAME \
    --scaling-processes Launch Terminate HealthCheck ReplaceUnhealthy
```

---

## Common Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Instances launching and terminating in loop | Health check failing too early | Increase `health-check-grace-period` |
| ASG stuck at 0 after scale-in | Min capacity = 0 and desired = 0 | Set min ≥ 1 for production |
| Instances not getting traffic | Not registered with target group, or health check fails | Check target group health, security groups |
| Scale-out not triggering | Cooldown period active | Check scaling activity, reduce cooldown |
| Rolling refresh stuck at checkpoint | Manual checkpoint required | Use `complete-instance-refresh` or cancel |

---

## References

- [Auto Scaling Groups documentation](https://docs.aws.amazon.com/autoscaling/ec2/userguide/auto-scaling-groups.html)
- [Scaling policies](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scale-based-on-demand.html)
- [Instance refresh](https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-instance-refresh.html)
- [Lifecycle hooks](https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html)
---

← [Previous: AMI & Launch Templates](./ami-launch-templates.md) | [Home](../../README.md) | [Next: Load Balancers →](./load-balancers.md)
