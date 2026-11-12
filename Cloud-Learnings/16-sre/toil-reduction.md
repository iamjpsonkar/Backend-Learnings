← [Previous: Error Budgets](./error-budgets.md) | [Home](../README.md) | [Next: On-Call →](./on-call.md)

---

# Toil Reduction

Toil is manual, repetitive, automatable operational work that scales with service growth. Google SRE caps toil at 50% of an SRE's time — the rest is engineering work that reduces future toil.

---

## What Is Toil?

Toil has all these characteristics:

- **Manual** — requires a human to execute
- **Repetitive** — same steps done over and over
- **Automatable** — a computer could do it with the right code
- **Tactical** — reactive, not proactive
- **No enduring value** — doing it doesn't permanently improve anything
- **Scales with traffic** — doubles when your service doubles

**Not toil**: incident response (requires human judgment), architectural decisions, writing automation code, postmortems.

---

## Identifying Toil

```bash
# Run a toil audit: look at what on-call engineers actually do
# 1. Export PagerDuty/OpsGenie incident log for last 90 days
# 2. Categorize each incident by resolution action

# Common toil categories:
# - Manual database queries to diagnose issues
# - Restarting services that regularly crash
# - Certificate renewals
# - Onboarding access provisioning
# - Manually scaling resources during known traffic spikes
# - Answering "is X deployed to prod?" questions
# - Rotating credentials that lack auto-rotation
```

### Toil Tracking Template

```markdown
## Toil Inventory

| Task | Frequency | Time (min) | Priority | Owner | Automation Status |
|------|-----------|------------|----------|-------|------------------|
| Restart order-api when queue backs up | 3x/week | 15 | High | @team | In progress |
| Manually provision dev database | 2x/week | 30 | High | @team | Open |
| Renew SSL certs for internal services | Monthly | 60 | Medium | @team | Open |
| Grant S3 access to new engineers | 2x/week | 20 | Low | @team | Open |
| Scale ECS service before Monday peak | Weekly | 10 | Medium | @team | Open |

Total toil per week: ~210 min (35%) — target: < 50%
```

---

## Automation Patterns

### Pattern 1: Auto-Restart Crashlooping Services

```yaml
# Kubernetes: liveness probe + restart policy eliminates most manual restarts
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: order-api
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            failureThreshold: 3      # Restart after 3 consecutive failures
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            periodSeconds: 5
            failureThreshold: 2      # Remove from load balancer after 2 failures
```

### Pattern 2: Auto-Scaling (Eliminate Manual Scaling)

```python
# AWS: Lambda that scales ECS services on a schedule or metric
import boto3
import logging
import os

logger = logging.getLogger(__name__)
ecs = boto3.client("ecs")

CLUSTER = os.environ["ECS_CLUSTER"]
SERVICE = os.environ["ECS_SERVICE"]


def lambda_handler(event: dict, context) -> None:
    """Scale ECS service based on schedule or SNS event."""
    desired_count = event.get("desired_count")
    if desired_count is None:
        logger.error("Missing desired_count in event", extra={"event": event})
        return

    logger.info(
        "Scaling ECS service",
        extra={"cluster": CLUSTER, "service": SERVICE, "desired_count": desired_count},
    )
    response = ecs.update_service(
        cluster=CLUSTER,
        service=SERVICE,
        desiredCount=int(desired_count),
    )
    logger.info(
        "Scaling complete",
        extra={"service": SERVICE, "new_count": desired_count,
               "previous_count": response["service"]["desiredCount"]},
    )
```

```bash
# EventBridge rule: scale up Monday 8am, scale down Sunday 10pm
aws events put-rule \
    --name scale-up-monday \
    --schedule-expression "cron(0 8 ? * MON *)" \
    --state ENABLED

aws events put-targets \
    --rule scale-up-monday \
    --targets '[{"Id":"1","Arn":"arn:aws:lambda:...:ScaleService","Input":"{\"desired_count\":20}"}]'
```

### Pattern 3: Self-Service Access Provisioning

```python
# Slack bot: /grant-s3-access @user bucket-name
import logging
from slack_bolt import App
import boto3

logger = logging.getLogger(__name__)
app = App()
iam = boto3.client("iam")

ALLOWED_BUCKETS = {"dev-data", "staging-data", "public-assets"}


@app.command("/grant-s3-access")
def grant_s3_access(ack, say, command, client):
    ack()
    parts = command["text"].split()
    if len(parts) != 2:
        say("Usage: /grant-s3-access @username bucket-name")
        return

    username, bucket = parts
    username = username.lstrip("@")

    if bucket not in ALLOWED_BUCKETS:
        say(f"Bucket '{bucket}' is not in the allowlist: {ALLOWED_BUCKETS}")
        logger.warning("Denied S3 access request", extra={"user": username, "bucket": bucket})
        return

    policy_arn = f"arn:aws:iam::123456789012:policy/S3Access-{bucket}"
    iam.attach_user_policy(UserName=username, PolicyArn=policy_arn)
    logger.info("S3 access granted", extra={"user": username, "bucket": bucket,
                "requester": command["user_id"]})
    say(f"Granted `{username}` read access to `{bucket}`")
```

### Pattern 4: Automated Certificate Renewal (cert-manager)

```yaml
# cert-manager: fully automatic TLS cert lifecycle
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@my-app.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - dns01:
          route53:
            region: us-east-1
            hostedZoneID: Z1234567890
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: api-tls
  namespace: production
spec:
  secretName: api-tls-secret
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - api.my-app.com
    - "*.api.my-app.com"
  renewBefore: 720h    # Renew 30 days before expiry — fully automatic
```

---

## Runbook Automation

```python
# Automated runbook: diagnose and attempt auto-remediation
import boto3
import logging
import json

logger = logging.getLogger(__name__)

ecs = boto3.client("ecs")
cw = boto3.client("cloudwatch")


def diagnose_service(cluster: str, service: str) -> dict:
    """Run automated diagnosis steps for a struggling ECS service."""
    logger.info("Starting automated diagnosis", extra={"cluster": cluster, "service": service})
    report = {"cluster": cluster, "service": service, "findings": []}

    # Check 1: Are tasks running?
    resp = ecs.describe_services(cluster=cluster, services=[service])
    svc = resp["services"][0]
    running = svc["runningCount"]
    desired = svc["desiredCount"]
    if running < desired:
        finding = f"DEGRADED: {running}/{desired} tasks running"
        logger.warning(finding, extra={"cluster": cluster, "service": service})
        report["findings"].append(finding)

    # Check 2: Recent task failures
    tasks = ecs.list_tasks(cluster=cluster, family=service, desiredStatus="STOPPED")
    if tasks["taskArns"]:
        task_details = ecs.describe_tasks(cluster=cluster, tasks=tasks["taskArns"][:5])
        for task in task_details["tasks"]:
            for container in task.get("containers", []):
                if container.get("exitCode", 0) != 0:
                    reason = container.get("reason", "unknown")
                    finding = f"Task exit {container['exitCode']}: {reason}"
                    logger.warning(finding, extra={"task_arn": task["taskArn"]})
                    report["findings"].append(finding)

    # Auto-remediation: force new deployment if no recent changes
    if running == 0 and desired > 0:
        logger.warning("Zero running tasks — triggering force deployment",
                       extra={"cluster": cluster, "service": service})
        ecs.update_service(cluster=cluster, service=service, forceNewDeployment=True)
        report["action"] = "Force deployment triggered"

    logger.info("Diagnosis complete", extra={"report": report})
    return report
```

---

## References

- [Google SRE Book — Eliminating Toil](https://sre.google/sre-book/eliminating-toil/)
- [cert-manager](https://cert-manager.io/docs/)
- [AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)

---

← [Previous: Error Budgets](./error-budgets.md) | [Home](../README.md) | [Next: On-Call →](./on-call.md)
