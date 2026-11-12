← [Previous: Serverless API](./serverless-api.md) | [Home](../README.md) | [Next: CI/CD Pipeline →](./cicd-pipeline.md)

---

# Project: Containerized API

Build and deploy a production-grade containerized REST API on ECS Fargate with RDS PostgreSQL, a private network, secrets management, health checks, and auto-scaling.

**Estimated cost:** ~$50–80/month (ECS Fargate + RDS t3.micro + ALB)
**Time to complete:** 2–3 hours

---

## Architecture

```
Internet
  │  HTTPS (443)
  ▼
Application Load Balancer (public)
  │
  ▼
ECS Fargate Service (private subnets)
  ├── order-api container (FastAPI)
  │     └── reads DB_PASSWORD from SSM Parameter Store
  └── Auto Scaling (1→10 tasks based on CPU/RPS)
        │
        ▼
RDS PostgreSQL (private subnets, Multi-AZ)
  └── Automated backups (7-day retention)
```

---

## Step 1: Application Code

```python
# app/main.py
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncpg

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
)

# ─── DB Pool ──────────────────────────────────────────────────────────────────

DB_POOL: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global DB_POOL
    logger.info("Connecting to database", extra={"host": os.environ["DB_HOST"]})
    DB_POOL = await asyncpg.create_pool(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", 5432)),
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        min_size=2,
        max_size=10,
        command_timeout=10,
    )
    logger.info("Database pool created")

    # Create table if it doesn't exist
    async with DB_POOL.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                total NUMERIC(12,2) NOT NULL,
                items JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
    logger.info("Schema initialized")

    yield

    await DB_POOL.close()
    logger.info("Database pool closed")


app = FastAPI(title="Order API", lifespan=lifespan)


async def get_db() -> asyncpg.Connection:
    async with DB_POOL.acquire() as conn:
        yield conn


# ─── Models ───────────────────────────────────────────────────────────────────

class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int = 1


class CreateOrderRequest(BaseModel):
    user_id: str
    items: list[OrderItem]


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health/ready")
async def health_ready():
    """ECS health check — verifies DB connectivity."""
    try:
        async with DB_POOL.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "ready"}
    except Exception as exc:
        logger.error("Health check failed", extra={"error": str(exc)})
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.get("/health/live")
async def health_live():
    return {"status": "alive"}


@app.post("/orders", status_code=201)
async def create_order(
    request: Request,
    body: CreateOrderRequest,
    db: asyncpg.Connection = Depends(get_db),
):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    logger.info("Creating order", extra={
        "request_id": request_id,
        "user_id": body.user_id,
        "item_count": len(body.items),
    })

    total = sum(item.price * item.quantity for item in body.items)
    items_json = [item.model_dump() for item in body.items]

    row = await db.fetchrow(
        "INSERT INTO orders (user_id, total, items) VALUES ($1, $2, $3::jsonb) RETURNING id, status, created_at",
        body.user_id, total, str(items_json).replace("'", '"'),
    )

    logger.info("Order created", extra={
        "request_id": request_id,
        "order_id": str(row["id"]),
        "total": str(total),
    })
    return {"order_id": str(row["id"]), "status": row["status"], "total": str(total)}


@app.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    request: Request,
    db: asyncpg.Connection = Depends(get_db),
):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    logger.info("Fetching order", extra={"request_id": request_id, "order_id": order_id})

    row = await db.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")

    return dict(row)
```

---

## Step 2: Dockerfile

```dockerfile
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser

WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser app/ .

USER appuser
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/live')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
```

---

## Step 3: Infrastructure with Terraform

```hcl
# terraform/main.tf

# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.app}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.region}a", "${var.region}b"]
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets = ["10.0.10.0/24", "10.0.11.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = false  # HA: one per AZ
  enable_dns_hostnames = true

  tags = { project = var.app }
}

# RDS PostgreSQL
resource "aws_db_instance" "main" {
  identifier             = "${var.app}-postgres"
  engine                 = "postgres"
  engine_version         = "16.2"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  max_allocated_storage  = 100
  storage_encrypted      = true
  db_name                = "appdb"
  username               = "app"
  password               = random_password.db.result
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  multi_az               = var.environment == "prod"
  backup_retention_period = 7
  deletion_protection    = var.environment == "prod"
  skip_final_snapshot    = var.environment != "prod"
  tags = { project = var.app }
}

# SSM: store DB password for ECS task to read
resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.app}/${var.environment}/db-password"
  type  = "SecureString"
  value = random_password.db.result
  tags  = { project = var.app }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.app}-cluster"
  setting { name = "containerInsights"; value = "enabled" }
  tags = { project = var.app }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.app}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "api"
    image = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
    portMappings = [{ containerPort = 8080, protocol = "tcp" }]
    environment = [
      { name = "DB_HOST", value = aws_db_instance.main.address },
      { name = "DB_NAME", value = "appdb" },
      { name = "DB_USER", value = "app" },
    ]
    secrets = [
      { name = "DB_PASSWORD", valueFrom = aws_ssm_parameter.db_password.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.app}-api"
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "ecs"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8080/health/ready')\""]
      interval    = 30
      timeout     = 10
      retries     = 3
      startPeriod = 60
    }
  }])
}

# ECS Service
resource "aws_ecs_service" "api" {
  name                               = "${var.app}-api"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.api.arn
  desired_count                      = 2
  launch_type                        = "FARGATE"
  health_check_grace_period_seconds  = 60

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8080
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}

# Auto Scaling
resource "aws_appautoscaling_target" "api" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = 70.0
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
```

---

## Step 4: Build and Deploy

```bash
# Authenticate to ECR
aws ecr get-login-password --region $REGION \
    | docker login --username AWS --password-stdin $ECR_URI

# Build and push
docker build -t order-api:latest .
docker tag order-api:latest $ECR_URI:latest
docker push $ECR_URI:latest

# Deploy with Terraform
cd terraform
terraform init
terraform plan -var="image_tag=latest" -out=tfplan
terraform apply tfplan

# Force new deployment (rolling update)
aws ecs update-service \
    --cluster "${APP}-cluster" \
    --service "${APP}-api" \
    --force-new-deployment \
    --region $REGION

# Watch rollout
aws ecs wait services-stable \
    --cluster "${APP}-cluster" \
    --services "${APP}-api" \
    --region $REGION
echo "Deployment stable"
```

---

## Verification

```bash
ALB_DNS=$(terraform output -raw alb_dns_name)

# Health check
curl -sf "https://$ALB_DNS/health/ready"

# Create order
curl -sf -X POST "https://$ALB_DNS/orders" \
    -H "Content-Type: application/json" \
    -d '{"user_id": "user-123", "items": [{"product_id": "p1", "name": "Widget", "price": 9.99, "quantity": 2}]}'

# Check ECS service status
aws ecs describe-services \
    --cluster "${APP}-cluster" \
    --services "${APP}-api" \
    --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}'
```

---

## Teardown

```bash
# Scale down first (avoids stuck tasks)
aws ecs update-service \
    --cluster "${APP}-cluster" \
    --service "${APP}-api" \
    --desired-count 0

# Destroy infrastructure
terraform destroy -var="image_tag=latest"
```

---

← [Previous: Serverless API](./serverless-api.md) | [Home](../README.md) | [Next: CI/CD Pipeline →](./cicd-pipeline.md)
