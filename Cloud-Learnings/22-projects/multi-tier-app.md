← [Previous: Data Pipeline](./data-pipeline.md) | [Home](../README.md) | [Next: DR Setup →](./dr-setup.md)

---

# Project: Multi-Tier Web Application

Deploy a classic 3-tier architecture: a public-facing web tier (EC2 Auto Scaling + ALB), an application tier (private EC2), and a highly available database tier (RDS Multi-AZ). This pattern is the foundation for many enterprise production workloads.

**Estimated cost:** ~$150–250/month (EC2 + RDS Multi-AZ + ALB + NAT Gateway)
**Time to complete:** 3–4 hours

---

## Architecture

```
Internet
  │  HTTPS (443) / HTTP (80 → redirect)
  ▼
Application Load Balancer  (public subnets, 2 AZs)
  │
  ├── Target Group: web-tier
  │       └── Auto Scaling Group  (public subnets)
  │             ├── EC2: web-01 (Nginx → app tier)
  │             └── EC2: web-02
  │
  └── (Alternatively: forward directly to app tier on port 8080)

  App Tier ALB or direct (private subnets)
  ├── Auto Scaling Group (private subnets)
  │     ├── EC2: app-01 (FastAPI / Node)
  │     └── EC2: app-02
  │
  ▼
RDS PostgreSQL Multi-AZ  (private subnets)
  ├── Primary: us-east-1a
  └── Standby: us-east-1b  (auto-failover ~1-2 min)
```

---

## Step 1: VPC and Networking (Terraform)

```hcl
# terraform/vpc.tf

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.app}-vpc"
  cidr = "10.0.0.0/16"

  azs              = ["${var.region}a", "${var.region}b"]
  public_subnets   = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets  = ["10.0.10.0/24", "10.0.11.0/24"]
  database_subnets = ["10.0.20.0/24", "10.0.21.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = false  # One per AZ for HA
  enable_dns_hostnames   = true
  create_database_subnet_group = true

  tags = { project = var.app, managed_by = "terraform" }
}

# Security Groups
resource "aws_security_group" "alb" {
  name   = "${var.app}-alb-sg"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from internet"
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP redirect"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "app" {
  name   = "${var.app}-app-sg"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "From ALB only"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds" {
  name   = "${var.app}-rds-sg"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
    description     = "PostgreSQL from app tier only"
  }
}
```

---

## Step 2: RDS Multi-AZ

```hcl
# terraform/rds.tf

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.app}/${var.environment}/db-password"
  type  = "SecureString"
  value = random_password.db.result
}

resource "aws_db_instance" "main" {
  identifier                  = "${var.app}-postgres"
  engine                      = "postgres"
  engine_version              = "16.2"
  instance_class              = "db.t3.small"
  allocated_storage           = 50
  max_allocated_storage       = 500
  storage_type                = "gp3"
  storage_encrypted           = true
  db_name                     = "appdb"
  username                    = "appuser"
  password                    = random_password.db.result
  db_subnet_group_name        = module.vpc.database_subnet_group_name
  vpc_security_group_ids      = [aws_security_group.rds.id]
  multi_az                    = true
  backup_retention_period     = 7
  backup_window               = "03:00-04:00"
  maintenance_window          = "sun:04:00-sun:05:00"
  auto_minor_version_upgrade  = true
  deletion_protection         = true
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${var.app}-final-snapshot"
  performance_insights_enabled = true
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  tags = { project = var.app }
}
```

---

## Step 3: Launch Template and Auto Scaling

```hcl
# terraform/asg.tf

# AMI: Amazon Linux 2023
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# IAM instance profile
resource "aws_iam_instance_profile" "app" {
  name = "${var.app}-instance-profile"
  role = aws_iam_role.app_instance.name
}

resource "aws_launch_template" "app" {
  name_prefix   = "${var.app}-app-"
  image_id      = data.aws_ami.al2023.id
  instance_type = "t3.small"

  iam_instance_profile { arn = aws_iam_instance_profile.app.arn }
  vpc_security_group_ids = [aws_security_group.app.id]

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"   # IMDSv2 only
    http_put_response_hop_limit = 1
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 30
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -euo pipefail
    yum install -y python3.12 python3.12-pip
    pip3.12 install fastapi uvicorn[standard] asyncpg boto3

    # Get DB credentials from SSM
    DB_HOST="${aws_db_instance.main.address}"
    DB_PASSWORD=$(aws ssm get-parameter \
        --name "/${var.app}/${var.environment}/db-password" \
        --with-decryption \
        --region ${var.region} \
        --query Parameter.Value \
        --output text)

    # Write app config
    cat > /etc/app.env << ENVEOF
    DB_HOST=$DB_HOST
    DB_NAME=appdb
    DB_USER=appuser
    DB_PASSWORD=$DB_PASSWORD
    ENVEOF

    # Deploy application (in production: pull from S3 artifact)
    aws s3 cp s3://${var.artifact_bucket}/app.zip /opt/app.zip
    unzip -o /opt/app.zip -d /opt/app

    # Start application service
    systemctl enable app
    systemctl start app
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = { project = var.app, tier = "app" }
  }
}

resource "aws_autoscaling_group" "app" {
  name                = "${var.app}-app-asg"
  min_size            = 2
  max_size            = 8
  desired_capacity    = 2
  vpc_zone_identifier = module.vpc.private_subnets
  target_group_arns   = [aws_lb_target_group.app.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 120

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 100
      instance_warmup        = 120
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.app}-app"
    propagate_at_launch = true
  }
}

# Target tracking scaling policy
resource "aws_autoscaling_policy" "app_cpu" {
  name                   = "${var.app}-cpu-tracking"
  autoscaling_group_name = aws_autoscaling_group.app.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    target_value = 70.0
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
  }
}
```

---

## Step 4: Application Load Balancer

```hcl
# terraform/alb.tf

resource "aws_lb" "main" {
  name               = "${var.app}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets

  enable_deletion_protection = true
  enable_http2               = true
  drop_invalid_header_fields = true

  access_logs {
    bucket  = aws_s3_bucket.alb_logs.id
    prefix  = "alb"
    enabled = true
  }

  tags = { project = var.app }
}

resource "aws_lb_target_group" "app" {
  name     = "${var.app}-app-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = module.vpc.vpc_id

  health_check {
    path                = "/health/ready"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 10
    matcher             = "200"
  }

  deregistration_delay = 30
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
```

---

## Step 5: Deploy and Verify

```bash
cd terraform
terraform init
terraform plan -var-file=prod.tfvars -out=tfplan
terraform apply tfplan

# Get ALB DNS
ALB_DNS=$(terraform output -raw alb_dns_name)

# Wait for instances to be healthy
aws elbv2 wait target-in-service \
    --target-group-arn $(terraform output -raw target_group_arn) \
    --targets Id=$(terraform output -raw instance_ids)

# Test
curl -sf "https://$ALB_DNS/health/ready"

# Check ASG activity
aws autoscaling describe-scaling-activities \
    --auto-scaling-group-name "${APP}-app-asg" \
    --max-records 10 \
    --query 'Activities[*].{Status:StatusCode,Cause:Cause}' \
    --output table

# Simulate load to test scaling
ab -n 10000 -c 50 https://$ALB_DNS/api/v1/products

# Watch ASG scale
watch -n 5 'aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-names '"${APP}-app-asg"' \
    --query '"'"'AutoScalingGroups[0].{Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,Running:length(Instances[?LifecycleState==`InService`])}'"'"''
```

---

## Teardown

```bash
# Remove deletion protection
aws rds modify-db-instance \
    --db-instance-identifier "${APP}-postgres" \
    --no-deletion-protection \
    --apply-immediately

# Disable ALB deletion protection
aws elbv2 modify-load-balancer-attributes \
    --load-balancer-arn $ALB_ARN \
    --attributes Key=deletion_protection.enabled,Value=false

# Destroy
terraform destroy -var-file=prod.tfvars
```

---

← [Previous: Data Pipeline](./data-pipeline.md) | [Home](../README.md) | [Next: DR Setup →](./dr-setup.md)
