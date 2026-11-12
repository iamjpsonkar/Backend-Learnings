← [Previous: Toil Reduction](./toil-reduction.md) | [Home](../README.md) | [Next: Capacity Planning →](./capacity-planning.md)

---

# On-Call

On-call is the rotation of engineers who respond to production incidents outside of business hours. Sustainable on-call — with good runbooks, clear escalation, and actionable alerts — keeps engineers healthy and services reliable.

---

## On-Call Health Metrics

Track these to prevent burnout and identify toil:

| Metric | Healthy target | Warning |
|--------|---------------|---------|
| Pages per shift (8h) | < 2 | > 5 |
| Time to acknowledge | < 5 min | > 15 min |
| Time to resolve | < 30 min | > 2 hours |
| % alerts requiring manual action | < 30% | > 70% |
| % pages during sleep hours | < 20% | > 40% |
| Consecutive on-call weeks | 0 | > 2 |

---

## PagerDuty Setup

```python
# Create PagerDuty schedule via API
import httpx
import logging
import os

logger = logging.getLogger(__name__)

PD_TOKEN = os.environ["PAGERDUTY_TOKEN"]
HEADERS = {
    "Authorization": f"Token token={PD_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/vnd.pagerduty+json;version=2",
}


async def create_schedule(name: str, user_ids: list[str]) -> str:
    """Create a weekly rotation schedule. Returns schedule ID."""
    payload = {
        "schedule": {
            "type": "schedule",
            "name": name,
            "time_zone": "America/New_York",
            "schedule_layers": [{
                "name": "Primary Rotation",
                "start": "2024-01-01T00:00:00-05:00",
                "rotation_virtual_start": "2024-01-01T00:00:00-05:00",
                "rotation_turn_length_seconds": 604800,  # 1 week
                "users": [{"user": {"id": uid, "type": "user_reference"}} for uid in user_ids],
                "restrictions": [
                    # Only on-call during business hours Mon-Fri (low-urgency override)
                    {
                        "type": "weekly_restriction",
                        "start_time_of_day": "09:00:00",
                        "duration_seconds": 57600,  # 16 hours
                        "start_day_of_week": 1,  # Monday
                    }
                ],
            }],
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.pagerduty.com/schedules",
            json=payload,
            headers=HEADERS,
        )
        response.raise_for_status()
        schedule_id = response.json()["schedule"]["id"]
        logger.info("Schedule created", extra={"name": name, "schedule_id": schedule_id})
        return schedule_id
```

---

## Escalation Policy

```
Level 1: Primary on-call (page immediately)
          │ No acknowledgement in 5 min
          ▼
Level 2: Secondary on-call (backup)
          │ No acknowledgement in 10 min
          ▼
Level 3: Engineering manager
          │ No acknowledgement in 15 min
          ▼
Level 4: VP Engineering (P0 incidents only)
```

```bash
# Terraform: PagerDuty escalation policy
resource "pagerduty_escalation_policy" "backend" {
  name      = "Backend Engineering"
  num_loops = 2

  rule {
    escalation_delay_in_minutes = 5
    target {
      type = "schedule_reference"
      id   = pagerduty_schedule.primary.id
    }
  }

  rule {
    escalation_delay_in_minutes = 5
    target {
      type = "schedule_reference"
      id   = pagerduty_schedule.secondary.id
    }
  }

  rule {
    escalation_delay_in_minutes = 10
    target {
      type = "user_reference"
      id   = data.pagerduty_user.eng_manager.id
    }
  }
}
```

---

## Runbook Template

```markdown
# Runbook: [Alert Name]

**Alert:** `OrderAPIHighErrorRate`
**Severity:** P1
**Owner:** Backend team
**Last tested:** YYYY-MM-DD

## What does this mean?
The Order API is returning HTTP 5xx errors at > 1% of requests for > 5 minutes.

## Immediate Steps (< 5 min)

1. **Check dashboards**: [Service Overview](https://grafana.my-app.com/d/api-overview)
   - Which endpoints are erroring?
   - Did this start after a recent deployment?

2. **Check recent deployments**:
   ```bash
   kubectl rollout history deployment/order-api -n production
   ```

3. **Check pod logs**:
   ```bash
   kubectl logs -l app=order-api -n production --tail=100 --since=10m
   ```

## Likely Causes and Fixes

### Cause 1: Recent bad deployment
**Symptoms**: Error rate spiked immediately after deploy
**Fix**: Roll back
```bash
kubectl rollout undo deployment/order-api -n production
kubectl rollout status deployment/order-api -n production
```

### Cause 2: Database connection exhaustion
**Symptoms**: Errors with "too many connections" or "connection pool exhausted"
**Check**:
```sql
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
```
**Fix**: Restart the connection pool by rolling the deployment:
```bash
kubectl rollout restart deployment/order-api -n production
```

### Cause 3: Downstream dependency failure (inventory service)
**Symptoms**: Errors concentrated on order creation endpoints
**Check**: [Inventory Service Dashboard](https://grafana.my-app.com/d/inventory)
**Fix**: Enable circuit breaker (feature flag: `inventory_circuit_breaker`)
```bash
aws ssm put-parameter --name /prod/flags/inventory_circuit_breaker --value true --overwrite
```

## Escalation
If not resolved in 30 min: escalate to @engineering-leads in #incidents

## Post-Incident
- File incident report within 24 hours
- Schedule postmortem if P0/P1
```

---

## Alert Noise Reduction

```yaml
# Prometheus: inhibition rules to reduce noise during outages
# If a node is down, suppress all alerts from that node
inhibit_rules:
  - source_match:
      alertname: NodeDown
    target_match_re:
      alertname: .*
    equal: [node]

  # If database is down, suppress all app-level errors (they're downstream effects)
  - source_match:
      alertname: PostgresDown
    target_match_re:
      alertname: HighErrorRate|SlowQueries
    equal: [environment]

# Silence a known flapping alert during maintenance
# Via Alertmanager API
curl -XPOST http://alertmanager:9093/api/v2/silences \
    -H 'Content-Type: application/json' \
    -d '{
        "matchers": [{"name": "alertname", "value": "HighMemory", "isRegex": false}],
        "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "endsAt": "'$(date -u -d '+2 hours' +%Y-%m-%dT%H:%M:%SZ)'",
        "comment": "Maintenance window — memory upgrade in progress",
        "createdBy": "operator@my-app.com"
    }'
```

---

## On-Call Handoff Checklist

```markdown
## On-Call Handoff — [Date]

**Outgoing:** @name
**Incoming:** @name

### Active Issues
- [ ] Any open P0/P1 incidents?
- [ ] Any degraded services (P2)?
- [ ] Any ongoing investigations?

### Upcoming Risks
- [ ] Scheduled maintenance windows this week?
- [ ] Planned deployments of risky changes?
- [ ] Known flaky alerts to watch for?

### Metrics Summary
- Error budget remaining: XX%
- Pages this week: X
- MTTD (mean time to detect): Xm
- MTTR (mean time to resolve): Xm

### Outstanding Action Items
- [ ] [Link to open incidents / Jira tickets]
```

---

## References

- [Google SRE Book — Being On-Call](https://sre.google/sre-book/being-on-call/)
- [PagerDuty API](https://developer.pagerduty.com/api-reference/)
- [Runbook best practices](https://response.pagerduty.com/during/runbooks/)

---

← [Previous: Toil Reduction](./toil-reduction.md) | [Home](../README.md) | [Next: Capacity Planning →](./capacity-planning.md)
