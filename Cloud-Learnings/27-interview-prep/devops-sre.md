← [Previous: System Design](./system-design.md) | [Home](../README.md) | [Next: References →](../28-references/README.md)

---

# Interview Prep: DevOps & SRE

---

## CI/CD

**Q: Walk me through your ideal CI/CD pipeline for a containerized application.**

```
1. Developer pushes code → PR created
   ├── Lint + unit tests (fast, < 2 min)
   ├── Docker build (with layer caching)
   ├── Security scan: Trivy (image), Semgrep (SAST), pip-audit (dependencies)
   └── DAST on PR environment (optional for API changes)

2. PR merged to main
   ├── Build tagged Docker image (SHA tag)
   ├── Push to ECR with scan on push
   ├── Deploy to staging ECS (rolling update)
   ├── Run smoke tests against staging
   └── Notify: "Ready for production approval"

3. Manual approval (production environment in GitHub)
   ├── Deploy to production (ECS circuit breaker enabled)
   ├── Wait for service stability
   ├── Run health checks
   └── Rollback automatically if health checks fail
```

Key principles: short feedback loops, no stored credentials (OIDC), fail fast (tests run before build), rollback is automated.

---

**Q: How do you handle database migrations in a CI/CD pipeline?**

The constraint: you can't run migrations and deploy simultaneously if the migration is breaking (removes a column the old code reads).

**Expand-contract (backward-compatible) migrations:**
1. **Expand**: add the new column/table as nullable (old code ignores it, runs fine)
2. **Backfill**: populate new column (can run concurrently)
3. **Switch**: deploy new code that uses the new column
4. **Contract**: remove old column (old code is gone, safe to delete)

In the pipeline:
```yaml
- name: Run migrations
  run: |
    aws ecs run-task \
        --cluster $ECS_CLUSTER \
        --task-definition my-app-migrate \
        --launch-type FARGATE \
        ...
    # Wait for task to complete and check exit code
```

Migrations run before the new application version deploys. Always test rollback: `alembic downgrade -1` or `flyway undo`.

---

**Q: What does "immutable infrastructure" mean and why is it better than mutable?**

**Mutable**: SSH into servers, run `apt upgrade`, edit config files. State drifts over time. No two servers are identical. Rollback means SSHing back in and undoing changes. Snowflake servers.

**Immutable**: never modify running infrastructure. To change: build a new AMI or Docker image → deploy new instances → terminate old. Infrastructure as code defines everything.

Benefits: identical environments (no "works on staging, fails on prod"), rollback = deploy previous version, auditability (every change is a code commit), no configuration drift.

AWS implementation: EC2 Auto Scaling with launch templates (replace instances with new AMIs), ECS/EKS (replace containers, never exec in and change things).

---

## Reliability

**Q: What is an error budget and how does it influence engineering decisions?**

An error budget is `1 - SLO`. If your SLO is 99.9% availability, your monthly error budget is 0.1% × ~730 hours = ~43 minutes of downtime per month.

It creates a shared language between product and engineering:
- **Budget remaining**: confidence to deploy aggressively, run experiments, reduce feature flags
- **Budget exhausted**: freeze non-critical deploys, focus on reliability work, incident review mandatory
- **Budget burning fast** (high burn rate alert): page on-call immediately, investigate, halt risky changes

Without an error budget, availability discussions are subjective. With one, they're quantitative: "We have 20 minutes of budget left this month; this risky deploy can wait."

---

**Q: Describe how you would handle a P1 incident.**

```
T+0: Alert fires (PagerDuty pages on-call)
  └── On-call acknowledges < 5 min

T+5: Incident channel opened (#incidents)
  ├── Incident commander (IC) self-assigns or is assigned
  ├── Status page updated: "Investigating service disruption"
  └── Severity assessed (P1 = revenue impact / data loss / security)

T+5-30: Diagnosis
  ├── IC coordinates, delegates: "Alice — check ECS tasks. Bob — check DB connections."
  ├── Check: recent deploys, alerts timeline, CloudWatch logs, traces
  └── Form hypothesis, test one at a time

T+30 (if not resolved): Escalate
  ├── Engineering manager notified
  └── Consider DR failover if primary region issue

Resolution:
  ├── Apply fix (rollback, scale up, failover, block IP)
  ├── Verify: error rate back to baseline, health checks green
  ├── Status page updated: "Resolved"
  └── Write incident ticket with timeline

T+48h: Blameless postmortem
  ├── What happened, customer impact, timeline
  ├── Root cause (5 Whys)
  └── Action items with owners + due dates
```

Never skip the postmortem for a P1 — the lessons are the most valuable part.

---

**Q: What is toil and why does it matter in SRE?**

Toil is operational work that:
- Is manual (requires a human to do it)
- Is repetitive (happens over and over)
- Is automatable (a machine could do it)
- Scales with service growth (more services = more toil)
- Has no enduring value (it keeps things running but doesn't improve them)

Why it matters: if SRE teams spend > 50% of their time on toil, they can't work on reliability improvements. Google's SRE model caps toil at 50%.

Examples: manually restarting crashed services, manually rotating certificates, manually responding to monitoring alerts by SSHing into boxes, manual deploy checklists.

Fix: automate using Kubernetes health probes, cert-manager, auto-scaling, self-service developer tooling.

---

## Infrastructure as Code

**Q: How do you manage Terraform state in a team?**

Remote state with locking:
- **S3 backend**: state stored in S3 (versioned bucket for history + rollback)
- **DynamoDB table**: state locking (prevents concurrent applies that could corrupt state)
- **State per environment**: separate state files (or workspaces) for dev/staging/prod

```hcl
terraform {
  backend "s3" {
    bucket         = "mycompany-terraform-state"
    key            = "myapp/prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

Team workflow: Terraform runs in CI (not on developer laptops). `plan` on PR, `apply` on merge to main. Never apply locally in production — use `terraform console` for inspection only.

---

**Q: How do you handle secrets in Terraform?**

Never store secrets in `.tfvars` files or as Terraform state. Options:

1. **Secrets Manager / SSM + data sources**: reference existing secrets, don't create them in Terraform
```hcl
data "aws_secretsmanager_secret_version" "db" {
  secret_id = "/prod/db-password"
}
# Never: resource "aws_secretsmanager_secret_version" "db" { secret_string = var.db_password }
```

2. **`sensitive = true` on variables**: prevents values from appearing in plan/apply output (but they're still in state)

3. **Separate state for secrets**: use a separate Terraform workspace with restricted access for secret resources

4. **Out-of-band secret creation**: create the secret manually or via a dedicated secrets management tool, reference it by ARN in Terraform

---

## Containers and Kubernetes

**Q: A pod is in CrashLoopBackOff. How do you diagnose it?**

```bash
# Step 1: Get the pod status
kubectl describe pod <pod-name> -n <namespace>
# Look at: State, Last State (exit code, reason), Events at bottom

# Step 2: Read the logs from the crashed container
kubectl logs <pod-name> -n <namespace> --previous
# If multi-container: --container <container-name>

# Step 3: Decode the exit code
# Exit 1 = application error (check application logs)
# Exit 137 = OOMKilled (increase memory limit)
# Exit 139 = segfault (application crash, often a native dependency)
# Exit 143 = SIGTERM not handled (app doesn't gracefully shut down)

# Step 4: Test locally
docker run --rm <image>:<tag>  # does it crash locally too?
```

Common causes: missing environment variable, wrong command/entrypoint, can't connect to database on startup, read-only filesystem but app tries to write, insufficient memory (OOMKilled).

---

**Q: What is the difference between a liveness probe and a readiness probe?**

**Readiness probe**: "Is this pod ready to receive traffic?" If readiness fails, the pod is removed from the Service endpoints (load balancer stops sending traffic). The pod continues running. Used for: warming up, dependent service unavailable.

**Liveness probe**: "Is this pod still alive (not stuck/deadlocked)?" If liveness fails, Kubernetes kills and restarts the container. Used for: detecting deadlocks or irrecoverable states.

**Startup probe**: for slow-starting containers. Disables liveness/readiness until the startup probe passes. Prevents premature restart during JVM startup, database migration, etc.

Rule of thumb: always have readiness. Add liveness only if you have a specific failure mode (deadlock) that doesn't self-resolve. Never make liveness probe dependent on external services (causes cascading failures).

---

← [Previous: System Design](./system-design.md) | [Home](../README.md) | [Next: References →](../28-references/README.md)
