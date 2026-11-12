← [Previous: Lift & Shift](./lift-and-shift.md) | [Home](../README.md) | [Next: Refactor →](./refactor.md)

---

# Replatform (Lift & Reshape)

Replatform makes targeted optimizations without re-architecting. The application logic stays the same; the infrastructure layer changes to use managed services. Common examples: moving from self-managed MySQL on EC2 to RDS, or from bare Java JARs on VMs to ECS containers.

---

## Containerization

Converting an application from a VM-deployed process to a container is the most common replatform pattern.

### Analyze and Containerize

```dockerfile
# Step 1: Start from the exact base image matching the OS
# Check source server: cat /etc/os-release
FROM amazonlinux:2023

# Step 2: Install only runtime dependencies (not build tools)
RUN dnf install -y \
    java-17-amazon-corretto-headless \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# Step 3: Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser

WORKDIR /app

# Step 4: Copy pre-built artifact
COPY --chown=appuser:appuser target/order-service-1.0.jar app.jar

# Step 5: Externalize all configuration (no hardcoded values)
# App reads from: environment variables, /app/config/ mount, or AWS SSM
ENV JAVA_OPTS="-Xms512m -Xmx1g -XX:+UseG1GC"

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf http://localhost:8080/health/ready || exit 1

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
```

### Build and Push to ECR

```bash
# Create ECR repository
aws ecr create-repository \
    --repository-name order-service \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    --region us-east-1

ECR_URI=$(aws ecr describe-repositories \
    --repository-names order-service \
    --query 'repositories[0].repositoryUri' --output text)

# Authenticate
aws ecr get-login-password --region us-east-1 \
    | docker login --username AWS --password-stdin $ECR_URI

# Build and push
docker build -t order-service:v1.0 .
docker tag order-service:v1.0 $ECR_URI:v1.0
docker push $ECR_URI:v1.0
```

### Deploy to ECS Fargate

```bash
# Task definition
cat > task-definition.json << EOF
{
    "family": "order-service",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
    "taskRoleArn": "arn:aws:iam::123456789012:role/order-service-task-role",
    "containerDefinitions": [{
        "name": "order-service",
        "image": "${ECR_URI}:v1.0",
        "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
        "environment": [
            {"name": "SPRING_PROFILES_ACTIVE", "value": "prod"}
        ],
        "secrets": [
            {"name": "DB_PASSWORD", "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/prod/order-service/db-password"}
        ],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": "/ecs/order-service",
                "awslogs-region": "us-east-1",
                "awslogs-stream-prefix": "ecs"
            }
        },
        "healthCheck": {
            "command": ["CMD-SHELL", "curl -sf http://localhost:8080/health/ready || exit 1"],
            "interval": 30,
            "timeout": 10,
            "retries": 3,
            "startPeriod": 60
        }
    }]
}
EOF

aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create ECS service
aws ecs create-service \
    --cluster prod-cluster \
    --service-name order-service \
    --task-definition order-service:1 \
    --desired-count 3 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-priv-a,subnet-priv-b],securityGroups=[sg-order-service],assignPublicIp=DISABLED}" \
    --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=order-service,containerPort=8080" \
    --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100" \
    --health-check-grace-period-seconds 60
```

---

## Managed Database Migration

Migrating from self-managed MySQL/PostgreSQL on EC2 to RDS eliminates patching, backups, and HA configuration.

### Using AWS DMS for Database Replatform

```bash
# Create DMS replication instance
aws dms create-replication-instance \
    --replication-instance-identifier prod-dms-instance \
    --replication-instance-class dms.t3.medium \
    --allocated-storage 100 \
    --publicly-accessible false \
    --vpc-security-group-ids sg-dms \
    --replication-subnet-group-identifier dms-subnet-group \
    --multi-az false

# Source endpoint (EC2 MySQL)
aws dms create-endpoint \
    --endpoint-identifier source-mysql-ec2 \
    --endpoint-type source \
    --engine-name mysql \
    --server-name 10.0.1.50 \
    --port 3306 \
    --database-name myapp \
    --username dms_user \
    --password $DB_PASSWORD

# Target endpoint (RDS MySQL)
aws dms create-endpoint \
    --endpoint-identifier target-rds-mysql \
    --endpoint-type target \
    --engine-name mysql \
    --server-name prod-mysql.cluster-xxxx.us-east-1.rds.amazonaws.com \
    --port 3306 \
    --database-name myapp \
    --username dms_user \
    --password $RDS_PASSWORD

# Test connections
aws dms test-connection \
    --replication-instance-arn $REP_INSTANCE_ARN \
    --endpoint-arn $SOURCE_ENDPOINT_ARN

# Create migration task (full-load + CDC for near-zero downtime)
aws dms create-replication-task \
    --replication-task-identifier myapp-migration \
    --source-endpoint-arn $SOURCE_ENDPOINT_ARN \
    --target-endpoint-arn $TARGET_ENDPOINT_ARN \
    --replication-instance-arn $REP_INSTANCE_ARN \
    --migration-type full-load-and-cdc \
    --table-mappings '{
        "rules": [{
            "rule-type": "selection",
            "rule-id": "1",
            "rule-name": "include-all",
            "object-locator": {"schema-name": "myapp", "table-name": "%"},
            "rule-action": "include"
        }]
    }' \
    --replication-task-settings '{
        "TargetMetadata": {"TargetSchema": "myapp", "SupportLobs": true},
        "FullLoadSettings": {"TargetTablePrepMode": "DROP_AND_CREATE"},
        "Logging": {"EnableLogging": true}
    }'

# Start task
aws dms start-replication-task \
    --replication-task-arn $TASK_ARN \
    --start-replication-task-type start-replication

# Monitor replication lag
aws dms describe-replication-tasks \
    --filters Name=replication-task-arn,Values=$TASK_ARN \
    --query 'ReplicationTasks[0].ReplicationTaskStats.{
        FullLoadProgress:FullLoadProgressPercent,
        CDCLatency:CDCLatencySource,
        TablesLoaded:TablesLoaded,
        TablesQueued:TablesQueued
    }'
```

### RDS Configuration for Production

```bash
# Create RDS parameter group (optimize for workload)
aws rds create-db-parameter-group \
    --db-parameter-group-name prod-mysql8-params \
    --db-parameter-group-family mysql8.0 \
    --description "Production MySQL 8.0 parameters"

aws rds modify-db-parameter-group \
    --db-parameter-group-name prod-mysql8-params \
    --parameters \
        "ParameterName=innodb_buffer_pool_size,ParameterValue={DBInstanceClassMemory*3/4},ApplyMethod=pending-reboot" \
        "ParameterName=max_connections,ParameterValue=500,ApplyMethod=pending-reboot" \
        "ParameterName=slow_query_log,ParameterValue=1,ApplyMethod=immediate" \
        "ParameterName=long_query_time,ParameterValue=1,ApplyMethod=immediate"

# Create RDS instance (Multi-AZ, encrypted, with PITR)
aws rds create-db-instance \
    --db-instance-identifier prod-mysql \
    --db-instance-class db.t3.large \
    --engine mysql \
    --engine-version 8.0.35 \
    --master-username admin \
    --master-user-password $RDS_ADMIN_PASSWORD \
    --db-parameter-group-name prod-mysql8-params \
    --vpc-security-group-ids sg-rds \
    --db-subnet-group-name prod-db-subnet-group \
    --multi-az \
    --storage-type gp3 \
    --allocated-storage 100 \
    --max-allocated-storage 1000 \
    --storage-encrypted \
    --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abc123 \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "sun:04:00-sun:05:00" \
    --enable-performance-insights \
    --performance-insights-retention-period 7 \
    --monitoring-interval 60 \
    --monitoring-role-arn arn:aws:iam::123456789012:role/rds-monitoring-role \
    --enable-cloudwatch-logs-exports '["error","slowquery","audit"]' \
    --deletion-protection \
    --no-publicly-accessible
```

---

## PaaS Migration Patterns

### Move Scheduled Jobs to AWS Batch / Lambda

```python
# Before: cron job running on EC2
# /etc/cron.d/report-generator
# 0 2 * * * ec2-user python /app/generate_reports.py

# After: EventBridge Scheduler → Lambda (or AWS Batch for long-running jobs)

# Lambda function (for jobs < 15 min)
import boto3
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Replatformed report generator — was a cron job on EC2.
    Now triggered by EventBridge Scheduler at 02:00 UTC daily.
    """
    execution_id = context.aws_request_id
    logger.info("Report generation started", extra={
        "execution_id": execution_id,
        "scheduled_time": event.get("time"),
    })

    try:
        s3 = boto3.client("s3")
        bucket = os.environ["REPORT_BUCKET"]
        report_date = datetime.utcnow().strftime("%Y-%m-%d")

        # Main logic (unchanged from original cron script)
        report_data = generate_report(report_date)

        key = f"reports/{report_date}/daily-report.csv"
        s3.put_object(Bucket=bucket, Key=key, Body=report_data)

        logger.info("Report uploaded successfully", extra={
            "execution_id": execution_id,
            "s3_key": key,
            "report_date": report_date,
        })
        return {"status": "success", "s3_key": key}

    except Exception as exc:
        logger.error("Report generation failed", extra={
            "execution_id": execution_id,
            "error": str(exc),
        }, exc_info=True)
        raise
```

```bash
# Create EventBridge schedule
aws scheduler create-schedule \
    --name daily-report-generator \
    --schedule-expression "cron(0 2 * * ? *)" \
    --schedule-expression-timezone "UTC" \
    --flexible-time-window '{"Mode": "OFF"}' \
    --target '{
        "Arn": "arn:aws:lambda:us-east-1:123456789012:function:report-generator",
        "RoleArn": "arn:aws:iam::123456789012:role/scheduler-lambda-role"
    }'
```

### Move Static Assets to S3 + CloudFront

```bash
# Before: Nginx serving /var/www/static from EC2

# After: S3 + CloudFront (no EC2 needed for static content)

# Create S3 bucket (no public access — CloudFront OAC only)
aws s3api create-bucket \
    --bucket myapp-static-assets \
    --region us-east-1

aws s3api put-public-access-block \
    --bucket myapp-static-assets \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Sync existing assets
aws s3 sync /var/www/static s3://myapp-static-assets/ \
    --delete \
    --cache-control "max-age=31536000,immutable" \
    --exclude "*.html" \
    --include "*"

aws s3 sync /var/www/static s3://myapp-static-assets/ \
    --exclude "*" \
    --include "*.html" \
    --cache-control "no-cache"

# Create CloudFront distribution (OAC for S3)
aws cloudfront create-origin-access-control \
    --origin-access-control-config '{
        "Name": "myapp-s3-oac",
        "OriginAccessControlOriginType": "s3",
        "SigningBehavior": "always",
        "SigningProtocol": "sigv4"
    }'
```

---

## Replatform Decision Guide

| Workload type | Replatform target | Key benefit |
|---------------|------------------|-------------|
| Self-managed MySQL/PostgreSQL on EC2 | Amazon RDS | Automated backups, Multi-AZ, patching |
| Self-managed Redis on EC2 | ElastiCache | Cluster mode, automatic failover |
| App servers on VMs | ECS Fargate | No OS management, auto-scaling |
| Cron jobs on EC2 | EventBridge + Lambda | No always-on compute cost |
| Static files on EC2 Nginx | S3 + CloudFront | Global CDN, zero compute |
| Jenkins on EC2 | AWS CodePipeline / GitHub Actions | Managed CI/CD |
| Elasticsearch on EC2 | OpenSearch Service | Managed upgrades, UltraWarm |

---

## References

- [AWS DMS documentation](https://docs.aws.amazon.com/dms/latest/userguide/)
- [ECS Fargate getting started](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/getting-started-fargate.html)
- [AWS Lambda migration guide](https://docs.aws.amazon.com/lambda/latest/dg/lambda-migration.html)

---

← [Previous: Lift & Shift](./lift-and-shift.md) | [Home](../README.md) | [Next: Refactor →](./refactor.md)
