# Incident Response — Advanced

**Difficulty**: Advanced
**Profile**: `core apps observability`
**Time estimate**: 2–3 hours

---

## Scenario

It is 2 AM. Your on-call alert fired: **"API error rate > 10% for 5 minutes"**. You need to diagnose and resolve the incident using only the tools available in the platform.

This exercise simulates a realistic incident with multiple potential causes. You must triage, diagnose, and resolve it — then write a postmortem.

---

## Setup

```bash
./run.sh start core apps observability

# Inject the incident
docker exec cloud-learnings-lab-sample-api-1 \
  sh -c "echo 'INJECT_FAULT=true' >> /tmp/fault.env"
# (or simulate by running the broken-api app)
```

Alternative: use the broken-apps scenario:
```bash
docker compose --project-name cloud-learnings-lab \
  --profile apps run --rm broken-api
```

---

## Tasks

### Task 1 — Acknowledge and triage (5 minutes)

You receive a PagerDuty-style alert. Start your incident timer.

Answer these within 5 minutes:
- Which service is affected?
- What is the current error rate?
- When did it start?
- Is it getting worse, stable, or recovering?
- What is the blast radius? (how many users affected?)

Use Grafana (http://localhost:3000) and Prometheus (http://localhost:9090).

### Task 2 — Hypothesis generation

Based on your triage, generate at least 3 hypotheses for root cause:

```
H1: Database connection pool exhausted
H2: Memory leak causing OOM restarts
H3: Downstream service dependency failing
H4: Bad deployment (config change)
H5: Traffic spike overwhelming the service
```

Rank them by likelihood.

### Task 3 — Systematic investigation

Investigate each hypothesis in order:

**Check logs:**
```bash
# Last 100 error lines
docker logs cloud-learnings-lab-sample-api-1 --tail 100 | grep ERROR

# Loki query
{container="sample-api"} |= "ERROR" | json | line_format "{{.level}} {{.message}}"
```

**Check resource usage:**
```bash
docker stats cloud-learnings-lab-sample-api-1 --no-stream
```

**Check database:**
```bash
docker exec cloud-learnings-lab-postgres-1 \
  psql -U appuser -d appdb \
  -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
```

**Check traces:**
- Open Grafana → Explore → Tempo
- Find traces with `status=error`
- Click through to see which span failed

### Task 4 — Identify root cause

From your investigation, identify:
- The exact component that is failing
- The specific error message
- The first occurrence time
- What changed before the incident

### Task 5 — Mitigate

Apply one of:
- Restart the affected container
- Roll back a config change
- Scale up replicas
- Fix and redeploy

Verify the error rate returns to < 1%.

### Task 6 — Write the postmortem

Create `postmortem-YYYY-MM-DD.md` with:

```markdown
# Postmortem — [Incident Title]

## Timeline
- HH:MM — Alert fired
- HH:MM — Triage started
- HH:MM — Root cause identified
- HH:MM — Mitigation applied
- HH:MM — Incident resolved

## Root Cause
[1-2 sentence description]

## Impact
- Duration: X minutes
- Error rate at peak: X%
- Affected endpoints: [list]

## Timeline (detailed)
[bullet points with timestamps]

## Root Cause Analysis
[5 Whys or similar]

## Action Items
- [ ] Short-term: [fix the symptom]
- [ ] Long-term: [prevent recurrence]
- [ ] Process: [improve monitoring/alerting]

## Lessons Learned
[What we learned]
```

---

## Success criteria

- [ ] Service and error rate identified within 5 minutes
- [ ] 3+ hypotheses generated and ranked
- [ ] Systematic investigation using logs, metrics, traces, and resources
- [ ] Root cause identified with evidence
- [ ] Mitigation applied and error rate confirmed normal
- [ ] Postmortem written with timeline and action items
