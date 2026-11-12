← [Previous: Failover Patterns](./failover-patterns.md) | [Home](../README.md) | [Next: Migration →](../20-migration/README.md)

---

# DR Runbooks

A DR runbook is a step-by-step procedure for recovering from a specific failure scenario. It must be accurate, tested, and accessible — including when the primary systems are down.

---

## Runbook Principles

1. **Store runbooks outside the affected system** — in a Git repo, Confluence, or printout
2. **Every step must be verifiable** — include commands and expected output
3. **Assign a decision owner** — who declares the DR, who executes, who communicates
4. **Set time checkpoints** — "if step 5 takes > 30 min, escalate"
5. **Test quarterly** — untested runbooks have unknown accuracy

---

## DR Declaration Criteria

```markdown
## Criteria for Declaring DR Failover

Invoke DR failover when ONE OR MORE of the following are true:

| Condition | Threshold | Duration |
|-----------|-----------|---------|
| Primary region API error rate | > 50% | > 10 min |
| Primary region API completely unreachable | Any | > 5 min |
| Primary DB unavailable (not just slow) | Not connectable | > 10 min |
| AWS incident affecting us-east-1 | AZ or regional | > 15 min |
| Ransomware or security incident requiring isolation | Any confirmation | Immediate |

DO NOT invoke DR for:
- Elevated error rates < 50% (investigate first)
- Single AZ failure (Multi-AZ handles this)
- Slow performance without total failure
```

---

## Runbook: Region Failover (Warm Standby)

```markdown
# DR-001: Region Failover to us-west-2

**Author:** @platform-team
**Last tested:** YYYY-MM-DD
**Estimated duration:** 20-30 minutes
**Decision maker:** Engineering Manager / On-Call Lead

## Pre-conditions
- DR declaration criteria met (see above)
- Incident commander assigned
- Status page updated: "Investigating service disruption"

## Step 1: Assess and Confirm (5 min)
```bash
# Confirm primary region is actually down (not just connectivity from your machine)
curl -sf https://api.my-app.com/health/ready --max-time 5 || echo "Primary unreachable"

# Check AWS status page
open https://health.aws.amazon.com/health/status

# Check Route 53 health check status
aws route53 get-health-check-status \
    --health-check-id $HEALTH_CHECK_ID \
    --query 'HealthCheckObservations[*].{Region:Region,Status:StatusReport.Status}'
```
Expected: Primary shows FAILURE in > 2 regions

## Step 2: Notify Stakeholders (< 2 min, run in parallel)
- Post in #incidents: "Initiating DR failover to us-west-2. ETA: 20 min."
- Update status page: "Identified issue. Failover in progress."
- Page on-call support lead

## Step 3: Promote DR Database (10-15 min)
```bash
# Promote RDS read replica to standalone primary
aws rds promote-read-replica \
    --db-instance-identifier prod-postgres-dr-warm \
    --region us-west-2

# Wait for promotion (8-12 min typical)
aws rds wait db-instance-available \
    --db-instance-identifier prod-postgres-dr-warm \
    --region us-west-2

# Verify
aws rds describe-db-instances \
    --db-instance-identifier prod-postgres-dr-warm \
    --region us-west-2 \
    --query 'DBInstances[0].{Status:DBInstanceStatus,Class:DBInstanceClass,Endpoint:Endpoint.Address}'
```
Expected: Status = "available", Class = "db.t3.medium"
If not available after 20 min: escalate to DB lead.

## Step 4: Scale DR Services to Production Capacity (5 min)
```bash
for SERVICE in order-api payment-api inventory-api user-api; do
    echo "Scaling $SERVICE..."
    aws ecs update-service \
        --cluster dr-cluster \
        --service "${SERVICE}-dr" \
        --desired-count 5 \
        --region us-west-2
done

# Verify services are stable
aws ecs wait services-stable \
    --cluster dr-cluster \
    --services order-api-dr payment-api-dr inventory-api-dr user-api-dr \
    --region us-west-2
```

## Step 5: Update DNS to DR Region (2 min, takes effect in ~1 min)
```bash
# Update Route 53 to point to DR ALB
aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch file://dr-failover-dns.json

# Monitor DNS propagation
dig api.my-app.com @8.8.8.8
# Should resolve to DR region ALB IP within 60-90s
```

## Step 6: Verify Service Health (3 min)
```bash
# Health checks
for endpoint in /health/ready /health/live /api/v1/status; do
    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" https://api.my-app.com${endpoint} 2>/dev/null)
    echo "${endpoint}: ${STATUS}"
    [ "$STATUS" = "200" ] || echo "WARN: $endpoint returned $STATUS"
done

# Check error rate in DR (Prometheus/CloudWatch)
# Expect elevated errors during transition, should normalize < 5% within 5 min
```

## Step 7: Communicate Resolution (1 min)
- Post in #incidents: "DR failover complete. Service restored in us-west-2."
- Update status page: "Resolved. Service operating normally."
- Start incident timeline for postmortem

## Checkpoints
- [ ] 10 min: Database should be available
- [ ] 20 min: Services should be healthy
- [ ] 30 min: Error rate back to baseline — else escalate

## Rollback (if DR failover makes things worse)
```bash
# Return DNS to primary (if primary recovers)
aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch file://primary-dns.json
```
```

---

## DR Testing Schedule

```markdown
## DR Testing Cadence

### Monthly: Backup restore test
- Restore RDS snapshot to test instance
- Verify data completeness and recency
- Duration: 1 hour
- Owner: DB team

### Quarterly: Partial failover simulation
- Fail over a non-critical service to DR region
- Verify monitoring, alerting, and basic functionality
- Duration: 2 hours
- Owner: Platform team

### Semi-annually: Full DR drill
- Execute complete DR-001 runbook with full team
- Do NOT skip steps — test everything as if it's real
- Include: database promotion, service scaling, DNS update, health verification
- Duration: 4 hours
- Owner: Engineering leadership

### Annually: Chaos day with external observers
- Simulate regional failure without advance notice to on-call
- Measure actual MTTR vs RTO target
- Duration: Full business day
- Owner: CTO / VP Engineering
```

---

## Runbook Verification Checklist

Before declaring a runbook ready for production use:

- [ ] Every command has been tested in a non-production environment
- [ ] All referenced ARNs, IDs, and endpoints are current
- [ ] Runbook stored in Git (versioned) and accessible offline (Confluence/PDF)
- [ ] Runbook reviewed by at least two people who can execute it
- [ ] All prerequisites documented (IAM permissions, tool versions)
- [ ] Estimated time for each step verified against actual test
- [ ] Decision criteria are unambiguous
- [ ] Escalation contacts are current

---

## References

- [AWS DR runbook template](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-runbooks.html)
- [PagerDuty Incident Response](https://response.pagerduty.com/)
- [Google SRE — Emergency Response](https://sre.google/sre-book/emergency-response/)

---

← [Previous: Failover Patterns](./failover-patterns.md) | [Home](../README.md) | [Next: Migration →](../20-migration/README.md)
