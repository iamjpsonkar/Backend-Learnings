# Interview Scenarios

Practice these real-world scenarios to prepare for cloud/DevOps interviews.

## Scenario 1 — Diagnose a Production Outage

**Setup**: Start observability + apps profiles. Stop the sample-api container.

**Challenge**: A monitoring alert fires at 2am. Grafana shows the sample-api is down.
You need to:
1. Identify the failing service from Prometheus alerts
2. Check the logs in Loki for the last error before failure
3. Describe your runbook for recovery
4. Write a brief postmortem

**Skills tested**: Observability, incident response, structured thinking

---

## Scenario 2 — Secure the Platform

**Challenge**: An auditor flags these issues:
1. Database port 5432 is publicly accessible
2. Redis has no password
3. A hardcoded password is found in app code
4. A container runs as root

**Your task**: Fix each issue using:
- Docker Compose network configuration
- Redis authentication
- Environment variables / Vault secrets
- Non-root user in Dockerfile

**Skills tested**: Security, container best practices, secrets management

---

## Scenario 3 — CI/CD Pipeline Design

**Challenge**: Design a CI/CD pipeline using Gitea + Jenkins + Docker Registry that:
1. Runs on every push to main
2. Lints the Dockerfile with Hadolint
3. Builds the Docker image
4. Runs unit tests
5. Pushes to local registry
6. Deploys to the apps profile

Implement it using the cicd profile.

**Skills tested**: CI/CD, Jenkins pipelines, Docker builds

---

## Scenario 4 — Scale a Bottleneck

**Challenge**: The sample-api is slow. From Grafana:
- P95 latency is 500ms
- DB query count is high
- Redis cache hit rate is 0%

**Your task**:
1. Add Redis caching to the `/api/v1/items` endpoint
2. Measure the improvement in Grafana
3. Explain the cache-aside pattern

**Skills tested**: Performance optimization, caching, observability

---

## Scenario 5 — Infrastructure as Code Review

**Challenge**: Review this Terraform code and identify issues:

```hcl
resource "aws_s3_bucket" "data" {
  bucket = "company-data"
}

resource "aws_s3_bucket_policy" "data" {
  bucket = aws_s3_bucket.data.id
  policy = jsonencode({
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:*"
      Resource  = "*"
    }]
  })
}
```

Issues to find:
1. S3 bucket is publicly writable (Principal: "*", Action: "s3:*")
2. No tags for cost allocation
3. No versioning enabled
4. Hard-coded bucket name (not parameterized)
5. No access logging configured

**Skills tested**: IaC security, Terraform, S3 best practices

---

## Mock Interview Prep Checklist

- [ ] Explain Docker networking (bridge, host, overlay)
- [ ] Explain Docker volumes vs bind mounts
- [ ] Explain Kubernetes pod vs deployment vs statefulset
- [ ] Write a Prometheus query for error rate
- [ ] Explain the difference between metrics, logs, traces
- [ ] Explain Vault secret engines and auth methods
- [ ] Explain blue/green vs canary deployment
- [ ] Explain what a dead letter queue is and when to use it
- [ ] Walk through a multi-region failover scenario
- [ ] Explain the shared responsibility model in cloud
