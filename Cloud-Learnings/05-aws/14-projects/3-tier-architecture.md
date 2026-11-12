← [Previous: AWS Projects](./README.md) | [Home](../../README.md) | [Next: Secure VPC →](./secure-vpc.md)

---

# Project: 3-Tier Architecture on AWS

A production-ready 3-tier web application: presentation (ALB), logic (ECS Fargate), and data (RDS + ElastiCache). Includes auto scaling, secrets management, observability, and CI/CD integration.

---

## Architecture

```
Internet
    │
    ▼
Route 53 ──→ CloudFront (optional CDN for API)
    │
    ▼
ALB (public, HTTPS 443)                          Tier 1: Presentation
    │
    ├── /api/* → App Target Group
    └── /health → health-check
    │
    ▼
ECS Fargate (private subnets, auto scaling)       Tier 2: Application
    ├── Task: my-app-backend (port 8080)
    ├── Pulls image from ECR
    ├── Reads secrets from Secrets Manager
    └── Writes to RDS via connection pool (RDS Proxy)
    │
    ├──────────────────────────────────────
    ▼                                    ▼
RDS Aurora PostgreSQL (isolated)     ElastiCache Redis (private)   Tier 3: Data
    ├── Writer (primary)              └── Session cache
    └── Reader (replica)                  Rate limiting
```

---

## Prerequisites

- Secure VPC from [secure-vpc.md](./secure-vpc.md) with `VPC_ID`, `PRIVATE_SUBNET_A/B`, `ISOLATED_SUBNET_A/B`, security groups
- ECR repository with a built application image
- ACM certificate for your domain

---

## Step 1: RDS Aurora PostgreSQL

```bash
REGION="us-east-1"
DB_SG="sg-db"      # from secure-vpc project
ISOLATED_SUBNET_A="subnet-iso-a"
ISOLATED_SUBNET_B="subnet-iso-b"

# Create DB subnet group
aws rds create-db-subnet-group \
    --db-subnet-group-name production-db-subnets \
    --db-subnet-group-description "Isolated subnets for Aurora" \
    --subnet-ids $ISOLATED_SUBNET_A $ISOLATED_SUBNET_B \
    --tags Key=Environment,Value=production

# Create Aurora PostgreSQL cluster
CLUSTER_ID=$(aws rds create-db-cluster \
    --db-cluster-identifier production-aurora \
    --engine aurora-postgresql \
    --engine-version "15.4" \
    --master-username dbadmin \
    --manage-master-user-password \
    --db-subnet-group-name production-db-subnets \
    --vpc-security-group-ids $DB_SG \
    --no-publicly-accessible \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "sun:04:30-sun:05:30" \
    --storage-encrypted \
    --enable-cloudwatch-logs-exports postgresql \
    --tags Key=Environment,Value=production \
    --query 'DBCluster.DBClusterIdentifier' --output text)

# Writer instance
aws rds create-db-instance \
    --db-instance-identifier production-aurora-writer \
    --db-cluster-identifier $CLUSTER_ID \
    --db-instance-class db.r7g.large \
    --engine aurora-postgresql \
    --tags Key=Environment,Value=production

# Reader instance (for read replicas and analytics)
aws rds create-db-instance \
    --db-instance-identifier production-aurora-reader \
    --db-cluster-identifier $CLUSTER_ID \
    --db-instance-class db.r7g.large \
    --engine aurora-postgresql \
    --tags Key=Environment,Value=production

aws rds wait db-cluster-available --db-cluster-identifier $CLUSTER_ID
echo "Aurora cluster ready"

# Get cluster endpoint
aws rds describe-db-clusters \
    --db-cluster-identifier $CLUSTER_ID \
    --query 'DBClusters[0].{Writer:Endpoint,Reader:ReaderEndpoint,Port:Port}'
```

---

## Step 2: RDS Proxy (Connection Pooling)

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get the Secrets Manager ARN for the master user password
SECRET_ARN=$(aws rds describe-db-clusters \
    --db-cluster-identifier $CLUSTER_ID \
    --query 'DBClusters[0].MasterUserSecret.SecretArn' --output text)

aws rds create-db-proxy \
    --db-proxy-name production-aurora-proxy \
    --engine-family POSTGRESQL \
    --auth '[{
        "AuthScheme": "SECRETS",
        "SecretArn": "'"$SECRET_ARN"'",
        "IAMAuth": "REQUIRED"
    }]' \
    --role-arn arn:aws:iam::$ACCOUNT_ID:role/RDSProxyRole \
    --vpc-subnet-ids $ISOLATED_SUBNET_A $ISOLATED_SUBNET_B \
    --vpc-security-group-ids $DB_SG \
    --no-require-tls \
    --tags Key=Environment,Value=production

aws rds wait db-proxy-available --db-proxy-name production-aurora-proxy
PROXY_ENDPOINT=$(aws rds describe-db-proxies \
    --db-proxy-name production-aurora-proxy \
    --query 'DBProxies[0].Endpoint' --output text)
echo "Proxy endpoint: $PROXY_ENDPOINT"

# Register the cluster with the proxy
aws rds register-db-proxy-targets \
    --db-proxy-name production-aurora-proxy \
    --db-cluster-identifiers $CLUSTER_ID
```

---

## Step 3: ElastiCache Redis

```bash
CACHE_SG="sg-cache"
PRIVATE_SUBNET_A="subnet-priv-a"
PRIVATE_SUBNET_B="subnet-priv-b"

aws elasticache create-subnet-group \
    --cache-subnet-group-name production-cache-subnets \
    --cache-subnet-group-description "Private subnets for Redis" \
    --subnet-ids $PRIVATE_SUBNET_A $PRIVATE_SUBNET_B

aws elasticache create-replication-group \
    --replication-group-id production-redis \
    --description "Session cache and rate limiting" \
    --cache-node-type cache.r7g.large \
    --engine redis \
    --engine-version "7.1" \
    --num-cache-clusters 2 \
    --cache-subnet-group-name production-cache-subnets \
    --security-group-ids $CACHE_SG \
    --automatic-failover-enabled \
    --multi-az-enabled \
    --at-rest-encryption-enabled \
    --transit-encryption-enabled \
    --snapshot-retention-limit 1 \
    --tags Key=Environment,Value=production

aws elasticache wait replication-group-available \
    --replication-group-id production-redis
echo "Redis ready"

REDIS_ENDPOINT=$(aws elasticache describe-replication-groups \
    --replication-group-id production-redis \
    --query 'ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint.Address' --output text)
```

---

## Step 4: ECS Fargate Service

```bash
APP_SG="sg-app"
ALB_SG="sg-alb"
VPC_ID="vpc-xxx"
ALB_SUBNET_A="subnet-pub-a"
ALB_SUBNET_B="subnet-pub-b"
CERT_ARN="arn:aws:acm:us-east-1:123456789012:certificate/xxx"

# Create CloudWatch log group
aws logs create-log-group --log-group-name "/ecs/my-app-backend"
aws logs put-retention-policy --log-group-name "/ecs/my-app-backend" --retention-in-days 30

# Register task definition
aws ecs register-task-definition \
    --family my-app-backend \
    --requires-compatibilities FARGATE \
    --network-mode awsvpc \
    --cpu "1024" --memory "2048" \
    --execution-role-arn arn:aws:iam::$ACCOUNT_ID:role/ECSTaskExecutionRole \
    --task-role-arn arn:aws:iam::$ACCOUNT_ID:role/my-app-task-role \
    --container-definitions '[{
        "name": "backend",
        "image": "'"$ACCOUNT_ID"'.dkr.ecr.us-east-1.amazonaws.com/my-app/backend:latest",
        "portMappings": [{"containerPort": 8080}],
        "essential": true,
        "secrets": [
            {"name": "DB_PASSWORD", "valueFrom": "'"$SECRET_ARN"':password::"}
        ],
        "environment": [
            {"name": "DB_HOST", "value": "'"$PROXY_ENDPOINT"'"},
            {"name": "DB_PORT", "value": "5432"},
            {"name": "DB_NAME", "value": "myapp"},
            {"name": "REDIS_HOST", "value": "'"$REDIS_ENDPOINT"'"},
            {"name": "APP_ENV", "value": "production"}
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
            "interval": 30, "timeout": 5, "retries": 3, "startPeriod": 60
        }
    }]'

# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name production-alb \
    --subnets $ALB_SUBNET_A $ALB_SUBNET_B \
    --security-groups $ALB_SG \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4 \
    --tags Key=Environment,Value=production \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Target group
TG_ARN=$(aws elbv2 create-target-group \
    --name production-app-tg \
    --protocol HTTP --port 8080 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --query 'TargetGroups[0].TargetGroupArn' --output text)

# HTTPS listener
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTPS --port 443 \
    --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
    --certificates CertificateArn=$CERT_ARN \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN

# HTTP redirect to HTTPS
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP --port 80 \
    --default-actions 'Type=redirect,RedirectConfig={Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'

# ECS cluster and service
aws ecs create-cluster \
    --cluster-name production \
    --settings name=containerInsights,value=enabled \
    --capacity-providers FARGATE FARGATE_SPOT

aws ecs create-service \
    --cluster production \
    --service-name my-app-backend \
    --task-definition my-app-backend:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_A,$PRIVATE_SUBNET_B],securityGroups=[$APP_SG],assignPublicIp=DISABLED}" \
    --load-balancers "targetGroupArn=$TG_ARN,containerName=backend,containerPort=8080" \
    --health-check-grace-period-seconds 60 \
    --deployment-configuration "minimumHealthyPercent=50,maximumPercent=200" \
    --enable-execute-command

aws ecs wait services-stable --cluster production --services my-app-backend
```

---

## Step 5: Auto Scaling

```bash
# Register ECS service as scalable target
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/production/my-app-backend \
    --min-capacity 2 --max-capacity 50

# Target tracking on CPU
aws application-autoscaling put-scaling-policy \
    --policy-name my-app-cpu-scaling \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/production/my-app-backend \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
        "TargetValue": 60,
        "PredefinedMetricSpecification": {"PredefinedMetricType": "ECSServiceAverageCPUUtilization"},
        "ScaleOutCooldown": 60,
        "ScaleInCooldown": 300
    }'
```

---

## Step 6: Observability

```bash
# Alarm: high error rate
aws cloudwatch put-metric-alarm \
    --alarm-name "prod-5xx-errors" \
    --namespace AWS/ApplicationELB \
    --metric-name HTTPCode_Target_5XX_Count \
    --dimensions Name=LoadBalancer,Value=app/production-alb/abc123 \
    --statistic Sum --period 60 --threshold 10 \
    --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:$ACCOUNT_ID:ops-alerts

# Alarm: high latency (P99 > 2 seconds)
aws cloudwatch put-metric-alarm \
    --alarm-name "prod-high-latency" \
    --namespace AWS/ApplicationELB \
    --metric-name TargetResponseTime \
    --dimensions Name=LoadBalancer,Value=app/production-alb/abc123 \
    --extended-statistic p99 --period 300 --threshold 2 \
    --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:$ACCOUNT_ID:ops-alerts

# Alarm: RDS free storage < 10 GB
aws cloudwatch put-metric-alarm \
    --alarm-name "prod-rds-storage-low" \
    --namespace AWS/RDS \
    --metric-name FreeStorageSpace \
    --dimensions Name=DBClusterIdentifier,Value=production-aurora \
    --statistic Minimum --period 300 --threshold 10737418240 \
    --comparison-operator LessThanOrEqualToThreshold --evaluation-periods 1 \
    --alarm-actions arn:aws:sns:us-east-1:$ACCOUNT_ID:ops-alerts

# Alarm: Redis evictions (cache memory pressure)
aws cloudwatch put-metric-alarm \
    --alarm-name "prod-redis-evictions" \
    --namespace AWS/ElastiCache \
    --metric-name Evictions \
    --dimensions Name=ReplicationGroupId,Value=production-redis \
    --statistic Sum --period 300 --threshold 1000 \
    --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 \
    --alarm-actions arn:aws:sns:us-east-1:$ACCOUNT_ID:ops-alerts
```

---

## Cost Estimate

| Service | Size | Monthly Cost |
|---------|------|-------------|
| ECS Fargate (2 tasks, 1vCPU/2GB) | 2 × 0.04856/vCPU-hr + 0.00532/GB-hr | ~$80 |
| ALB | 1 LCU/hour baseline | ~$18 |
| Aurora PostgreSQL | db.r7g.large × 2 | ~$280 |
| RDS Proxy | 1 proxy | ~$15 |
| ElastiCache Redis | cache.r7g.large × 2 | ~$220 |
| NAT Gateways (2) | 1 GB/hr data | ~$65 |
| CloudWatch | Logs + metrics | ~$20 |
| **Total** | | **~$700/month** |

**Right-sizing for dev/staging:** Use db.t4g.medium (Aurora), cache.t4g.micro (Redis), 1 Fargate task → ~$150/month.

---

## References

- [Well-Architected Web Application Lens](https://docs.aws.amazon.com/wellarchitected/latest/web-application-lens/)
- [Aurora documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)
- [ECS Fargate pricing](https://aws.amazon.com/fargate/pricing/)
---

← [Previous: AWS Projects](./README.md) | [Home](../../README.md) | [Next: Secure VPC →](./secure-vpc.md)
