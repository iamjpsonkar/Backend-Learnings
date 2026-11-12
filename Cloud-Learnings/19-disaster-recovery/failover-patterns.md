← [Previous: Backup Strategies](./backup-strategies.md) | [Home](../README.md) | [Next: DR Runbooks →](./dr-runbooks.md)

---

# Failover Patterns

Failover patterns determine how quickly and at what cost you can recover. Choose based on your RTO/RPO requirements.

---

## Pattern Comparison

```
Cost ──────────────────────────────────────────────────────────► High
Low              Pilot Light        Warm Standby      Active-Active
RTO Hours          30-60 min          10-30 min          Seconds
RPO Hours          Minutes            Seconds            Near-zero
│                      │                  │                  │
Backup only       Core infra        Scaled-down       Full capacity
+ restore         pre-deployed       always running     both regions
                  (must scale up)    (just scale out)   (instant)
```

---

## 1. Backup & Restore (Tier 1)

```bash
# Procedure: restore RDS + ECS service in DR region

# 1. Restore database from cross-region backup
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier prod-postgres-dr \
    --db-snapshot-identifier arn:aws:rds:us-east-1:123456789012:snapshot:prod-postgres-daily \
    --db-instance-class db.t3.medium \
    --vpc-security-group-ids sg-dr-db \
    --db-subnet-group-name dr-db-subnet-group \
    --no-publicly-accessible \
    --region us-west-2

# 2. Wait for database (10-30 min)
aws rds wait db-instance-available \
    --db-instance-identifier prod-postgres-dr \
    --region us-west-2

# 3. Deploy application stack from IaC
cd terraform/environments/us-west-2-dr
terraform apply -var="db_endpoint=$(aws rds describe-db-instances \
    --db-instance-identifier prod-postgres-dr \
    --region us-west-2 \
    --query 'DBInstances[0].Endpoint.Address' --output text)"

# 4. Update Route 53 to point to DR region
aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch '{
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "api.my-app.com",
                "Type": "A",
                "AliasTarget": {
                    "HostedZoneId": "Z35SXDOTRQ7X7K",
                    "DNSName": "dr-alb.us-west-2.elb.amazonaws.com",
                    "EvaluateTargetHealth": true
                }
            }
        }]
    }'
```

---

## 2. Pilot Light (Tier 2)

Keep minimal core infrastructure always running in DR region. Scale it up when needed.

```hcl
# terraform/modules/pilot-light/main.tf
# Always running: VPC, subnets, security groups, RDS replica, ECR
# NOT running: ECS services (deployed on failover), large EC2s

# Core: RDS read replica in DR region (promoted on failover)
resource "aws_db_instance" "dr_replica" {
  identifier                = "prod-postgres-dr-replica"
  replicate_source_db       = var.primary_db_arn
  instance_class            = "db.t3.small"   # Small — scale up on failover
  publicly_accessible       = false
  vpc_security_group_ids    = [aws_security_group.dr_db.id]
  db_subnet_group_name      = aws_db_subnet_group.dr.name
  skip_final_snapshot       = false
  final_snapshot_identifier = "dr-replica-final-${formatdate("YYYYMMDD", timestamp())}"
  tags = { role = "dr-replica", environment = "dr" }
}

# Core: VPC networking (always present)
module "dr_vpc" {
  source = "../../modules/vpc"
  region = "us-west-2"
  cidr   = "10.1.0.0/16"
  tags   = { environment = "dr" }
}
```

```bash
# FAILOVER PROCEDURE (30-60 min)

# Step 1: Promote RDS replica to primary
aws rds promote-read-replica \
    --db-instance-identifier prod-postgres-dr-replica \
    --region us-west-2

aws rds wait db-instance-available \
    --db-instance-identifier prod-postgres-dr-replica \
    --region us-west-2

# Step 2: Scale up RDS instance class
aws rds modify-db-instance \
    --db-instance-identifier prod-postgres-dr-replica \
    --db-instance-class db.t3.large \
    --apply-immediately \
    --region us-west-2

# Step 3: Deploy ECS services (using pre-built images in DR ECR)
aws ecs create-service \
    --cluster dr-cluster \
    --service-name order-api \
    --task-definition order-api:latest \
    --desired-count 3 \
    --region us-west-2

# Step 4: Update DNS
# (same as Tier 1 above)
```

---

## 3. Warm Standby (Tier 3)

A scaled-down but fully operational copy. Just increase capacity on failover.

```hcl
# terraform/modules/warm-standby/main.tf

# Fully operational stack at 25% capacity
resource "aws_db_instance" "dr_standby" {
  identifier         = "prod-postgres-dr-warm"
  instance_class     = "db.t3.medium"   # Smaller than prod (db.t3.xlarge)
  replicate_source_db = var.primary_db_arn
  multi_az           = false            # Single-AZ in DR (Multi-AZ in prod)
}

resource "aws_ecs_service" "order_api_dr" {
  name            = "order-api-dr"
  cluster         = aws_ecs_cluster.dr.id
  task_definition = var.task_definition_arn
  desired_count   = 1    # 1 task (vs 5 in prod) — just enough to accept traffic
}

resource "aws_autoscaling_group" "dr_workers" {
  min_size         = 1
  max_size         = 20   # Can scale to full capacity
  desired_capacity = 1
}
```

```bash
# FAILOVER PROCEDURE (10-30 min)

# Step 1: Stop replication, promote DR database to primary
aws rds promote-read-replica \
    --db-instance-identifier prod-postgres-dr-warm \
    --region us-west-2

# Step 2: Scale out services
aws ecs update-service \
    --cluster dr-cluster \
    --service order-api-dr \
    --desired-count 5 \     # Match production capacity
    --region us-west-2

# Step 3: Update DNS (fast — TTL should be pre-set to 60s)
aws route53 change-resource-record-sets ... # (same as above)

# Step 4: Verify health
curl -f https://api.my-app.com/health/ready
```

---

## 4. Active-Active / Multi-Region (Tier 4)

Traffic runs simultaneously in both regions. No failover procedure — routing adjusts automatically.

```
Internet
    │
    ▼
Route 53 Latency-based routing
    ├── us-east-1 ALB  (50% of traffic → nearest users)
    └── us-west-2 ALB  (50% of traffic)
         │
         ▼
ECS Services (both regions, full capacity)
         │
         ▼
Aurora Global Database
    ├── us-east-1 Primary (writes)
    └── us-west-2 Read replica (reads + promoted on failover)
```

```bash
# Aurora Global Database: < 1 second replication lag
aws rds create-global-cluster \
    --global-cluster-identifier my-app-global \
    --source-db-cluster-identifier prod-aurora-cluster \
    --engine aurora-postgresql \
    --engine-version 15.4

aws rds create-db-cluster \
    --db-cluster-identifier prod-aurora-dr \
    --global-cluster-identifier my-app-global \
    --engine aurora-postgresql \
    --db-subnet-group-name dr-db-subnet-group \
    --region us-west-2

# Route 53: latency-based routing
aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch '{
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "api.my-app.com",
                    "Type": "A",
                    "SetIdentifier": "us-east-1",
                    "Region": "us-east-1",
                    "AliasTarget": {
                        "HostedZoneId": "Z35SXDOTRQ7X7K",
                        "DNSName": "prod-alb.us-east-1.elb.amazonaws.com",
                        "EvaluateTargetHealth": true
                    }
                }
            },
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "api.my-app.com",
                    "Type": "A",
                    "SetIdentifier": "us-west-2",
                    "Region": "us-west-2",
                    "AliasTarget": {
                        "HostedZoneId": "Z1H1FL5HABSF5",
                        "DNSName": "dr-alb.us-west-2.elb.amazonaws.com",
                        "EvaluateTargetHealth": true
                    }
                }
            }
        ]
    }'

# Manual failover: promote Aurora secondary to primary (< 1 min)
aws rds failover-global-cluster \
    --global-cluster-identifier my-app-global \
    --target-db-cluster-identifier prod-aurora-dr
```

---

## Route 53 Health Checks

```bash
# Create health check for automatic DNS failover
aws route53 create-health-check \
    --caller-reference $(uuidgen) \
    --health-check-config '{
        "Type": "HTTPS",
        "FullyQualifiedDomainName": "api.my-app.com",
        "ResourcePath": "/health/ready",
        "RequestInterval": 10,
        "FailureThreshold": 3,
        "MeasureLatency": true,
        "Regions": ["us-east-1","us-west-2","eu-west-1"]
    }'

# Associate health check with record set
# (add HealthCheckId to the Route 53 change-batch above)
```

---

## References

- [AWS DR strategies](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)
- [Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)
- [Route 53 health checks](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html)

---

← [Previous: Backup Strategies](./backup-strategies.md) | [Home](../README.md) | [Next: DR Runbooks →](./dr-runbooks.md)
