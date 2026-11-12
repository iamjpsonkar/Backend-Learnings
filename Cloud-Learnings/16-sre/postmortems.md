← [Previous: Chaos Engineering](./chaos-engineering.md) | [Home](../README.md) | [Next: FinOps →](../17-finops/README.md)

---

# Postmortems

A postmortem (also called incident review or retrospective) is a structured analysis of an incident. Its purpose is to understand what happened and prevent recurrence — not to assign blame.

---

## Blameless Culture

**Blame-oriented**: "The engineer pushed bad code without testing."
**Blameless**: "Our deployment process did not prevent a configuration error from reaching production."

Blame focuses on individuals, discourages reporting, and doesn't fix systems. Blameless postmortems assume engineers made reasonable decisions given the information and tools available — and ask what systems failed them.

---

## When to Write a Postmortem

| Trigger | Action |
|---------|--------|
| P0 incident | Required, publish within 24 hours |
| P1 incident | Required, publish within 48 hours |
| P2 with significant user impact | Recommended |
| Near-miss that could have been P0/P1 | Recommended |
| Same issue recurring (> 2x in 30 days) | Required |

---

## Postmortem Template

```markdown
# Postmortem: [Short Title] — INC-YYYY-NNN

**Date:** YYYY-MM-DD
**Severity:** P[0-3]
**Duration:** X hours Y minutes
**Impact:** [Who was affected and how — users, revenue, SLO]
**Status:** Draft | In Review | Published
**Authors:** @name1, @name2
**Reviewers:** @name3, @tech-lead

---

## Summary

[2-3 sentences: what happened, why, and what we're doing to prevent it.
Write this last — it should summarize the full document.]

---

## Impact

- **Users affected:** ~X,XXX users could not complete checkout
- **Revenue impact:** ~$X,XXX in lost transactions (based on average order value)
- **Error budget consumed:** 23% of monthly error budget
- **SLO status:** 30-day availability dropped to 99.71% (SLO: 99.9%)

---

## Timeline (UTC)

| Time | Event |
|------|-------|
| 14:23 | Deployment of order-api v2.4.1 begins |
| 14:31 | Deployment completes |
| 14:38 | Error rate alert fires (5xx rate 4.2%) |
| 14:42 | On-call @name acknowledges alert |
| 14:44 | Root cause identified: bad DB migration |
| 14:47 | Rollback to v2.4.0 initiated |
| 14:51 | Rollback complete, error rate returns to baseline |
| 14:55 | Incident closed |

Total duration: 17 minutes

---

## Root Cause

The v2.4.1 deployment included a database migration that added a NOT NULL column to the
`orders` table without providing a default value. Existing rows had NULL for this column,
causing all SELECT queries that returned those rows to fail with a type error in the
application ORM layer.

**Why was this missed?**
1. The migration was tested in a fresh database, not against a snapshot of production data
2. The CI integration test database is reset on each run and does not contain historical data
3. Code review did not include a reviewer familiar with the migration risk

---

## Contributing Factors

- No staging environment with a recent production data snapshot
- Migration review checklist does not include "check NOT NULL on existing tables"
- Deployment included both application code and migration in the same step
  (no separation of migration-first, then app deploy)

---

## What Went Well

- Alert fired within 7 minutes of deployment (within SLO window)
- On-call acknowledged within 4 minutes
- Root cause identified in 2 minutes (logs clearly showed the column error)
- Rollback completed in 4 minutes
- Runbook was accurate and followed correctly

---

## What Went Wrong

- Integration tests did not use production-like data
- Migration risk was not flagged during code review
- No canary deployment — 100% of traffic hit bad version immediately

---

## Action Items

| Item | Type | Owner | Due | Priority |
|------|------|-------|-----|----------|
| Add DB snapshot from prod to CI integration test DB (refreshed weekly) | Prevention | @infra-team | 2024-02-20 | P1 |
| Add NOT NULL migration check to PR checklist | Process | @eng-lead | 2024-02-15 | P1 |
| Separate DB migration from app deploy in release pipeline | Prevention | @platform | 2024-03-01 | P2 |
| Enable canary deployment (10% → 100%) for order-api | Prevention | @platform | 2024-03-15 | P2 |
| Add migration dry-run step in CI (`--dry-run` flag for all migrations) | Detection | @backend | 2024-02-28 | P2 |

---

## Appendix

### Error log sample
```
ERROR: null value in column "fulfillment_region" of relation "orders"
  violates not-null constraint
  DETAIL: Failing row contains (ord_abc123, 2024-01-15, ..., null)
```

### Metrics graphs
[Link to Grafana snapshot]

### Relevant links
- [Deployment PR](https://github.com/my-org/my-app/pull/1234)
- [Migration diff](https://github.com/my-org/my-app/commit/abc123)
- [Runbook used](https://wiki.my-app.com/runbooks/order-api-errors)
```

---

## Running the Review Meeting

```markdown
## Postmortem Review Meeting Guide

Duration: 30–60 minutes (no more — escalate remaining items async)

### Opening (2 min)
- Restate blameless culture: "We are here to improve systems, not assign blame"
- Any observer can call out blame-oriented language

### Timeline walkthrough (10 min)
- Walk through timeline chronologically
- Any corrections from participants?
- Add annotations for "should we have known sooner?"

### Root cause discussion (10 min)
- "Why did this happen?" → drill down with 5 Whys
- Avoid "human error" as a root cause — ask what enabled the error
- Stop when you reach a system boundary you can change

### Action items (10 min)
- Assign owners and due dates for each item
- Classify: Prevention, Detection, Mitigation, Response
- No unowned action items leave this meeting

### Close (2 min)
- When will the document be published?
- Who needs to be notified (stakeholders, affected teams)?
```

---

## 5 Whys Example

```
Problem: Production database migration caused 17 minutes of elevated errors

Why 1: The migration added a NOT NULL column without a default to a table with existing rows
Why 2: The test database was empty — migration succeeded there
Why 3: Integration tests use an empty database, not a prod-like snapshot
Why 4: We don't have a process to refresh the integration test DB with anonymized prod data
Why 5: No one owned the task of setting this up, and it was never prioritized

Root cause: Lack of prod-like test data in CI, combined with no migration review checklist

Fix: Add weekly refresh of anonymized prod snapshot to CI DB (Action item #1)
```

---

## Tracking Action Items

```bash
# Don't let action items die in a document — track them in your issue tracker

# GitHub: create issues from action items
gh issue create \
    --title "Add prod DB snapshot to CI integration tests" \
    --body "From postmortem INC-2024-042. Due: 2024-02-20. Owner: @infra-team" \
    --label "reliability,postmortem" \
    --assignee "infra-team-lead" \
    --milestone "Reliability Sprint Q1"

# Monthly review: how are we doing on postmortem action items?
gh issue list --label postmortem --state open \
    --json title,assignees,milestone,createdAt \
    | jq '.[] | {title, due: .milestone.dueOn, assignees: [.assignees[].login]}'
```

---

## References

- [Google SRE Book — Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)
- [Google Postmortem Template](https://sre.google/sre-book/example-postmortem/)
- [PagerDuty Postmortem Guide](https://response.pagerduty.com/after/post_mortem_process/)
- [Etsy Blameless Postmortems](https://www.etsy.com/codeascraft/blameless-postmortems/)

---

← [Previous: Chaos Engineering](./chaos-engineering.md) | [Home](../README.md) | [Next: FinOps →](../17-finops/README.md)
