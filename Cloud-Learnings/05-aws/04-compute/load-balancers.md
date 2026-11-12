← [Previous: Auto Scaling](./auto-scaling.md) | [Home](../../README.md) | [Next: Lambda →](./lambda.md)

---

# AWS Load Balancers

AWS Elastic Load Balancing (ELB) distributes incoming traffic across multiple targets (EC2, containers, Lambda, IP addresses). There are three types: Application Load Balancer (ALB), Network Load Balancer (NLB), and Gateway Load Balancer (GLB).

---

## Load Balancer Comparison

| | ALB | NLB | GLB |
|--|-----|-----|-----|
| OSI Layer | 7 (HTTP/HTTPS/gRPC) | 4 (TCP/UDP/TLS) | 3 (IP packets) |
| Protocol | HTTP, HTTPS, WebSocket, gRPC | TCP, UDP, TLS, TCP_UDP | IP (GENEVE) |
| Routing | Path, host, headers, query strings, method | Port, IP | All traffic |
| Targets | EC2, containers, Lambda, IPs | EC2, containers, IPs | Third-party appliances |
| Static IP | Via associated NLB | Yes (one per AZ) | No |
| TLS termination | Yes | Yes (passthrough or termination) | No |
| Use case | Web apps, APIs, microservices | High-performance TCP, gaming, IoT, NLB in front of ALB | Firewalls, IDS/IPS, deep packet inspection |
| Hourly cost | ~$0.008/LCU | ~$0.006/NLCU | ~$0.004/GLCU |

---

## Application Load Balancer (ALB)

### Create an ALB

```bash
VPC_ID="vpc-0abc1234"
SG_ALB="sg-0alb1234"

# Create the ALB (internet-facing for public, internal for private)
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name my-app-alb \
    --type application \
    --scheme internet-facing \
    --subnets subnet-public-1a subnet-public-1b \
    --security-groups $SG_ALB \
    --tags Key=Name,Value=my-app-alb Key=Environment,Value=production \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text)

ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --query 'LoadBalancers[0].DNSName' --output text)

echo "ALB ARN: $ALB_ARN"
echo "ALB DNS: $ALB_DNS"
```

### Create Target Groups

```bash
# Target group for the main app (EC2 instances)
TG_APP=$(aws elbv2 create-target-group \
    --name my-app-tg \
    --protocol HTTP \
    --port 8080 \
    --vpc-id $VPC_ID \
    --target-type instance \
    --health-check-protocol HTTP \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --matcher HttpCode=200 \
    --tags Key=Name,Value=my-app-tg \
    --query 'TargetGroups[0].TargetGroupArn' --output text)

# Target group for a static API (Lambda)
TG_LAMBDA=$(aws elbv2 create-target-group \
    --name static-api-tg \
    --target-type lambda \
    --tags Key=Name,Value=static-api-tg \
    --query 'TargetGroups[0].TargetGroupArn' --output text)

# Register EC2 instances manually (usually done via ASG)
aws elbv2 register-targets \
    --target-group-arn $TG_APP \
    --targets Id=i-0abc1234 Id=i-0def5678

# Register a Lambda function as a target
aws lambda add-permission \
    --function-name my-static-api \
    --action lambda:InvokeFunction \
    --principal elasticloadbalancing.amazonaws.com \
    --source-arn $TG_LAMBDA \
    --statement-id alb-invoke

aws elbv2 register-targets \
    --target-group-arn $TG_LAMBDA \
    --targets Id=arn:aws:lambda:us-east-1:123456789012:function:my-static-api
```

### Create Listeners and Rules

```bash
# HTTP listener — redirect to HTTPS
LISTENER_HTTP=$(aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}' \
    --query 'Listeners[0].ListenerArn' --output text)

# HTTPS listener — with ACM certificate
CERT_ARN="arn:aws:acm:us-east-1:123456789012:certificate/abc123"

LISTENER_HTTPS=$(aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTPS \
    --port 443 \
    --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
    --certificates CertificateArn=$CERT_ARN \
    --default-actions Type=forward,TargetGroupArn=$TG_APP \
    --query 'Listeners[0].ListenerArn' --output text)

# Add routing rules to the HTTPS listener
# Rule: /api/* → API target group
TG_API="arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/api/abc123"

aws elbv2 create-rule \
    --listener-arn $LISTENER_HTTPS \
    --priority 10 \
    --conditions Field=path-pattern,Values="/api/*" \
    --actions Type=forward,TargetGroupArn=$TG_API

# Rule: api.example.com host header → API target group
aws elbv2 create-rule \
    --listener-arn $LISTENER_HTTPS \
    --priority 20 \
    --conditions Field=host-header,Values="api.example.com" \
    --actions Type=forward,TargetGroupArn=$TG_API

# Rule: /static/* → fixed 301 redirect to CloudFront
aws elbv2 create-rule \
    --listener-arn $LISTENER_HTTPS \
    --priority 30 \
    --conditions Field=path-pattern,Values="/static/*" \
    --actions 'Type=redirect,RedirectConfig={Host=cdn.example.com,Path="/#{path}",StatusCode=HTTP_301}'

# Rule: specific header required (simple API key check)
aws elbv2 create-rule \
    --listener-arn $LISTENER_HTTPS \
    --priority 40 \
    --conditions \
        'Field=http-header,HttpHeaderConfig={HttpHeaderName=X-Api-Version,Values=["v2"]}' \
        'Field=path-pattern,Values="/v2/*"' \
    --actions Type=forward,TargetGroupArn=$TG_API

# Rule: weighted forward (canary deployment — 90% prod, 10% new version)
TG_NEW="arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/app-v2/def456"

aws elbv2 create-rule \
    --listener-arn $LISTENER_HTTPS \
    --priority 50 \
    --conditions Field=path-pattern,Values="/*" \
    --actions '[
        {
            "Type": "forward",
            "ForwardConfig": {
                "TargetGroups": [
                    {"TargetGroupArn": "'$TG_APP'", "Weight": 90},
                    {"TargetGroupArn": "'$TG_NEW'", "Weight": 10}
                ],
                "TargetGroupStickinessConfig": {"Enabled": false}
            }
        }
    ]'
```

### ALB Access Logs

```bash
# Enable access logs (useful for debugging, security analysis)
BUCKET_NAME="my-alb-logs-bucket"
ACCOUNT_ID="123456789012"
REGION="us-east-1"

# ALB needs permission to write to the bucket
aws s3api put-bucket-policy \
    --bucket $BUCKET_NAME \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::127311923021:root"
            },
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::'$BUCKET_NAME'/alb-logs/AWSLogs/'$ACCOUNT_ID'/*"
        }]
    }'

aws elbv2 modify-load-balancer-attributes \
    --load-balancer-arn $ALB_ARN \
    --attributes \
        Key=access_logs.s3.enabled,Value=true \
        Key=access_logs.s3.bucket,Value=$BUCKET_NAME \
        Key=access_logs.s3.prefix,Value=alb-logs
```

---

## Network Load Balancer (NLB)

NLBs operate at Layer 4. They are designed for extreme performance (millions of requests per second, sub-millisecond latency) and provide static IP addresses per AZ.

```bash
# Create an NLB (internal, for microservice-to-microservice communication)
NLB_ARN=$(aws elbv2 create-load-balancer \
    --name my-service-nlb \
    --type network \
    --scheme internal \
    --subnets subnet-private-1a subnet-private-1b \
    --tags Key=Name,Value=my-service-nlb \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Create TCP target group (health check on port 8080)
TG_NLB=$(aws elbv2 create-target-group \
    --name my-service-nlb-tg \
    --protocol TCP \
    --port 8080 \
    --vpc-id $VPC_ID \
    --target-type instance \
    --health-check-protocol HTTP \
    --health-check-path /health \
    --health-check-port 8080 \
    --query 'TargetGroups[0].TargetGroupArn' --output text)

# TLS listener with ACM certificate (NLB terminates TLS)
aws elbv2 create-listener \
    --load-balancer-arn $NLB_ARN \
    --protocol TLS \
    --port 443 \
    --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
    --certificates CertificateArn=$CERT_ARN \
    --default-actions Type=forward,TargetGroupArn=$TG_NLB

# Allocate an Elastic IP for the NLB (for NLBs created in a subnet)
EIP_A=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
EIP_B=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)

aws elbv2 create-load-balancer \
    --name my-static-ip-nlb \
    --type network \
    --scheme internet-facing \
    --subnet-mappings \
        SubnetId=subnet-public-1a,AllocationId=$EIP_A \
        SubnetId=subnet-public-1b,AllocationId=$EIP_B
```

---

## Health Check Endpoint Example

A well-designed health check endpoint is critical. It should return 200 only when the instance is truly ready to serve traffic.

```python
# app/health.py — example health check endpoint (Flask)
from flask import Flask, jsonify
import logging

logger = logging.getLogger(__name__)
app = Flask(__name__)

@app.route('/health')
def health():
    """
    ALB/NLB health check endpoint.
    Returns 200 OK when all critical dependencies are reachable.
    Returns 503 when any critical dependency is unavailable.
    """
    logger.debug("Health check requested")
    checks = {}
    healthy = True

    # Check database connectivity
    try:
        db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        logger.warning("Health check: database unavailable: %s", e)
        checks["database"] = "unavailable"
        healthy = False

    # Check cache connectivity
    try:
        cache.ping()
        checks["cache"] = "ok"
    except Exception as e:
        logger.warning("Health check: cache unavailable: %s", e)
        checks["cache"] = "degraded"
        # Cache failure is non-critical — do not mark unhealthy

    status = "healthy" if healthy else "unhealthy"
    code = 200 if healthy else 503
    logger.info("Health check result: %s %s", status, checks)
    return jsonify({"status": status, "checks": checks}), code
```

---

## Viewing Target Health

```bash
TG_ARN="arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-app/abc123"

# Check health of all targets
aws elbv2 describe-target-health \
    --target-group-arn $TG_ARN \
    --query 'TargetHealthDescriptions[*].{
        Target:Target.Id,
        Port:Target.Port,
        State:TargetHealth.State,
        Reason:TargetHealth.Reason,
        Description:TargetHealth.Description
    }' \
    --output table
```

### Health State Reference

| State | Meaning |
|-------|---------|
| `healthy` | Target is receiving traffic |
| `unhealthy` | Health check failing; traffic not sent |
| `initial` | Registering, waiting for first health check |
| `draining` | Deregistering; existing connections finishing |
| `unused` | Target group not associated with a listener |

---

## Sticky Sessions

```bash
# Enable sticky sessions on a target group (cookie-based)
aws elbv2 modify-target-group-attributes \
    --target-group-arn $TG_APP \
    --attributes \
        Key=stickiness.enabled,Value=true \
        Key=stickiness.type,Value=lb_cookie \
        Key=stickiness.lb_cookie.duration_seconds,Value=86400

# Application-controlled stickiness (use your app's session cookie)
aws elbv2 modify-target-group-attributes \
    --target-group-arn $TG_APP \
    --attributes \
        Key=stickiness.enabled,Value=true \
        Key=stickiness.type,Value=app_cookie \
        Key=stickiness.app_cookie.cookie_name,Value=SESSIONID \
        Key=stickiness.app_cookie.duration_seconds,Value=86400
```

---

## References

- [Application Load Balancer documentation](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)
- [Network Load Balancer documentation](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/)
- [ELB security policies](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listener.html#describe-ssl-policies)
- [ALB pricing](https://aws.amazon.com/elasticloadbalancing/pricing/)
---

← [Previous: Auto Scaling](./auto-scaling.md) | [Home](../../README.md) | [Next: Lambda →](./lambda.md)
