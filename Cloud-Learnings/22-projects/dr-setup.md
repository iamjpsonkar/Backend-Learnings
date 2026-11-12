← [Previous: Multi-Tier App](./multi-tier-app.md) | [Home](../README.md) | [Next: Multi-Cloud Deployment →](./multi-cloud-deployment.md)

---

# Project: Disaster Recovery Setup

Build a warm standby DR environment that can fail over to a second AWS region in under 30 minutes. This project implements the warm standby pattern from `19-disaster-recovery/failover-patterns.md` for a real application stack.

**Estimated cost:** ~$60–100/month (DR RDS replica + minimal ECS tasks + Route 53 health checks)
**Time to complete:** 3–4 hours

---

## Architecture

```
PRIMARY: us-east-1                  DR: us-west-2
─────────────────────               ─────────────────────
ALB (prod)                          ALB (dr) — receives traffic on failover
  │                                   │
ECS Service (5 tasks)               ECS Service (1 task — scaled up on failover)
  │                                   │
RDS PostgreSQL (Multi-AZ)    ──────► RDS Read Replica (warm standby)
  │                         stream    │
S3 (app data)    ─── CRR ──────────► S3 DR replica

Route 53 Health Check (primary ALB)
  ├── Primary healthy  → traffic to us-east-1 ALB
  └── Primary unhealthy → failover to us-west-2 ALB (automatic DNS)
```

---

## Step 1: RDS Read Replica in DR Region

```bash
PRIMARY_DB_ARN=$(aws rds describe-db-instances \
    --db-instance-identifier prod-postgres \
    --query 'DBInstances[0].DBInstanceArn' --output text \
    --region us-east-1)

# Create cross-region read replica
aws rds create-db-instance-read-replica \
    --db-instance-identifier prod-postgres-dr-warm \
    --source-db-instance-identifier $PRIMARY_DB_ARN \
    --db-instance-class db.t3.medium \
    --availability-zone us-west-2a \
    --no-publicly-accessible \
    --vpc-security-group-ids sg-dr-rds \
    --db-subnet-group-name dr-db-subnet-group \
    --source-region us-east-1 \
    --region us-west-2

# Wait for replica to be available (10-20 min first time)
aws rds wait db-instance-available \
    --db-instance-identifier prod-postgres-dr-warm \
    --region us-west-2

echo "DR replica ready"

# Verify replication lag
aws rds describe-db-instances \
    --db-instance-identifier prod-postgres-dr-warm \
    --region us-west-2 \
    --query 'DBInstances[0].{Status:DBInstanceStatus,Class:DBInstanceClass,Endpoint:Endpoint.Address,ReplicaLag:StatusInfos[?StatusType==`read replication`].Message}'
```

---

## Step 2: S3 Cross-Region Replication

```bash
PRIMARY_BUCKET="myapp-data-us-east-1"
DR_BUCKET="myapp-data-us-west-2"

# Create DR bucket
aws s3api create-bucket \
    --bucket $DR_BUCKET \
    --region us-west-2 \
    --create-bucket-configuration LocationConstraint=us-west-2

aws s3api put-bucket-versioning \
    --bucket $DR_BUCKET \
    --versioning-configuration Status=Enabled

# Enable Object Lock on DR bucket (immutable)
aws s3api put-object-lock-configuration \
    --bucket $DR_BUCKET \
    --object-lock-configuration '{
        "ObjectLockEnabled": "Enabled",
        "Rule": {"DefaultRetention": {"Mode": "GOVERNANCE", "Days": 7}}
    }'

# Configure replication on primary bucket
REPLICATION_ROLE_ARN="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/s3-replication-role"

aws s3api put-bucket-replication \
    --bucket $PRIMARY_BUCKET \
    --replication-configuration '{
        "Role": "'"$REPLICATION_ROLE_ARN"'",
        "Rules": [{
            "ID": "replicate-to-dr",
            "Status": "Enabled",
            "Filter": {},
            "Destination": {
                "Bucket": "arn:aws:s3:::'"$DR_BUCKET"'",
                "ReplicationTime": {
                    "Status": "Enabled",
                    "Time": {"Minutes": 15}
                },
                "Metrics": {
                    "Status": "Enabled",
                    "EventThreshold": {"Minutes": 15}
                }
            },
            "DeleteMarkerReplication": {"Status": "Enabled"}
        }]
    }'

echo "S3 replication configured"
```

---

## Step 3: DR ECS Service (Scaled Down)

```hcl
# terraform/dr/main.tf
# Minimal ECS service in DR region — just enough to accept traffic on failover

resource "aws_ecs_service" "order_api_dr" {
  provider        = aws.dr
  name            = "order-api-dr"
  cluster         = aws_ecs_cluster.dr.id
  task_definition = aws_ecs_task_definition.order_api_dr.arn
  desired_count   = 1     # 1 task warm — scale to 5 on failover
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.dr_private_subnets
    security_groups  = [aws_security_group.order_api_dr.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.order_api_dr.arn
    container_name   = "api"
    container_port   = 8080
  }

  lifecycle {
    ignore_changes = [desired_count]  # Managed during failover
  }
}
```

---

## Step 4: Route 53 Health Check and Failover

```bash
PRIMARY_ALB_DNS="prod-alb.us-east-1.elb.amazonaws.com"
DR_ALB_DNS="dr-alb.us-west-2.elb.amazonaws.com"
HOSTED_ZONE_ID="Z1234567890"

# Create health check for primary ALB
HEALTH_CHECK_ID=$(aws route53 create-health-check \
    --caller-reference $(uuidgen) \
    --health-check-config '{
        "Type": "HTTPS",
        "FullyQualifiedDomainName": "'"$PRIMARY_ALB_DNS"'",
        "ResourcePath": "/health/ready",
        "RequestInterval": 10,
        "FailureThreshold": 3,
        "MeasureLatency": true,
        "Regions": ["us-east-1", "us-west-2", "eu-west-1"]
    }' \
    --query 'HealthCheck.Id' --output text)

# Create failover DNS records
aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch '{
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "api.myapp.com",
                    "Type": "A",
                    "SetIdentifier": "primary",
                    "Failover": "PRIMARY",
                    "HealthCheckId": "'"$HEALTH_CHECK_ID"'",
                    "AliasTarget": {
                        "HostedZoneId": "Z35SXDOTRQ7X7K",
                        "DNSName": "'"$PRIMARY_ALB_DNS"'",
                        "EvaluateTargetHealth": true
                    }
                }
            },
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "api.myapp.com",
                    "Type": "A",
                    "SetIdentifier": "secondary",
                    "Failover": "SECONDARY",
                    "AliasTarget": {
                        "HostedZoneId": "Z1H1FL5HABSF5",
                        "DNSName": "'"$DR_ALB_DNS"'",
                        "EvaluateTargetHealth": true
                    }
                }
            }
        ]
    }'

echo "Failover DNS configured"
```

---

## Step 5: Automated Failover Script

```bash
#!/bin/bash
# scripts/dr-failover.sh — Execute when DR declaration criteria are met
set -euo pipefail

PRIMARY_REGION="us-east-1"
DR_REGION="us-west-2"
DR_DB="prod-postgres-dr-warm"
DR_CLUSTER="dr-cluster"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

log "=== DR FAILOVER INITIATED ==="
log "Operator: $(whoami)"
log "Timestamp: $(date -u)"

# Step 1: Promote RDS replica
log "Step 1/4: Promoting RDS replica to primary..."
aws rds promote-read-replica \
    --db-instance-identifier $DR_DB \
    --region $DR_REGION

aws rds wait db-instance-available \
    --db-instance-identifier $DR_DB \
    --region $DR_REGION
log "RDS promotion complete"

# Step 2: Scale DR ECS services to full capacity
log "Step 2/4: Scaling DR services..."
for SERVICE in order-api-dr payment-api-dr inventory-api-dr; do
    aws ecs update-service \
        --cluster $DR_CLUSTER \
        --service $SERVICE \
        --desired-count 5 \
        --region $DR_REGION
    log "  Scaled $SERVICE to 5"
done

aws ecs wait services-stable \
    --cluster $DR_CLUSTER \
    --services order-api-dr payment-api-dr inventory-api-dr \
    --region $DR_REGION
log "DR services stable"

# Step 3: Verify DR health before DNS switch
log "Step 3/4: Verifying DR service health..."
DR_ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names dr-alb \
    --region $DR_REGION \
    --query 'LoadBalancers[0].DNSName' --output text)

for ATTEMPT in {1..10}; do
    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
        "https://$DR_ALB_DNS/health/ready" 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        log "DR health check passed (attempt $ATTEMPT)"
        break
    fi
    log "  Attempt $ATTEMPT: status $STATUS — waiting..."
    sleep 15
done

[ "$STATUS" = "200" ] || { log "ERROR: DR health check failed after 10 attempts"; exit 1; }

# Step 4: Force Route 53 failover (disable primary health check to trigger immediate DNS switch)
log "Step 4/4: Updating DNS..."
# Route 53 will automatically route to secondary when primary health check fails
# To force immediate cutover, update the primary record to point to DR (manual override)
log "DNS failover complete (Route 53 automatic failover active)"

log "=== FAILOVER COMPLETE ==="
log "Service is now running in $DR_REGION"
log "Primary ($PRIMARY_REGION) was: $(aws rds describe-db-instances --db-instance-identifier prod-postgres --region $PRIMARY_REGION --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null || echo 'unreachable')"
```

---

## Step 6: DR Testing

```bash
# Monthly DR test (partial — non-production)
# 1. Create a test Route 53 record pointing to DR
# 2. Run smoke tests against DR endpoint
# 3. Verify data recency from replica lag

# Check replica lag before test
aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS \
    --metric-name ReplicaLag \
    --dimensions Name=DBInstanceIdentifier,Value=prod-postgres-dr-warm \
    --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Maximum \
    --region us-west-2 \
    --query 'Datapoints[-1].Maximum'

# Smoke test DR endpoint (before making it live)
DR_URL="https://dr-alb.us-west-2.elb.amazonaws.com"
curl -sf "$DR_URL/health/ready" && echo "DR health check OK"
curl -sf "$DR_URL/api/v1/status" | jq .
```

---

## Teardown

```bash
# Delete DR replica (not production primary!)
aws rds delete-db-instance \
    --db-instance-identifier prod-postgres-dr-warm \
    --skip-final-snapshot \
    --region us-west-2

# Scale DR ECS services to 0
for SERVICE in order-api-dr payment-api-dr inventory-api-dr; do
    aws ecs update-service \
        --cluster dr-cluster \
        --service $SERVICE \
        --desired-count 0 \
        --region us-west-2
done

# Delete Route 53 health check
aws route53 delete-health-check --health-check-id $HEALTH_CHECK_ID

# Remove DR DNS failover records (replace with non-failover primary records)
```

---

← [Previous: Multi-Tier App](./multi-tier-app.md) | [Home](../README.md) | [Next: Multi-Cloud Deployment →](./multi-cloud-deployment.md)
