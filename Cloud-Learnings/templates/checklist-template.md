# Checklist: {Topic / Operation Name}

<!-- USAGE: Copy this file when creating an operational checklist, readiness review,
     or pre/post-deployment gate. Remove HTML comments before committing.
     Checklists are action-oriented: every item must be verifiable (yes/no/done). -->

> **Type:** {Pre-deployment / Post-deployment / Security review / Cost review / Incident response / Other}
> **Applies to:** {service, environment, or scenario}
> **Run by:** {role — e.g., Platform Engineer, Developer, SRE, Security Engineer}

---

## How to Use This Checklist

<!-- Brief instructions on when and how to run this. -->

Run this checklist before/after/during {event}. Every item must be confirmed before proceeding to {next step}.

Mark each item:
- `[x]` — Done / confirmed
- `[ ]` — Not done
- `[N/A]` — Not applicable to this context (add a note explaining why)

---

## {Section 1: e.g., "Infrastructure"}

- [ ] **{Item}** — {what to check and what the expected state is}
- [ ] **{Item}** — ...
- [ ] **{Item}** — ...

**How to verify:**
```bash
{verification command}
```

---

## {Section 2: e.g., "Networking"}

- [ ] **{Item}** — ...
- [ ] **{Item}** — ...
- [ ] **{Item}** — ...

---

## {Section 3: e.g., "Security"}

- [ ] **No long-lived credentials in code or environment variables** — Confirm via `git grep` and environment audit
- [ ] **Least-privilege IAM roles attached** — Each service has only the permissions it needs
- [ ] **Encryption at rest enabled** — S3 SSE, EBS encryption, RDS encryption enabled
- [ ] **Encryption in transit enforced** — TLS 1.2+ required on all endpoints
- [ ] **Secrets stored in {Secrets Manager / Parameter Store}** — No plaintext secrets in config files
- [ ] **Security groups follow least-access** — No 0.0.0.0/0 inbound except on intended public endpoints
- [ ] **{Item}** — ...

---

## {Section 4: e.g., "Observability"}

- [ ] **Logs are being collected** — Verify log group exists and retention is set
- [ ] **Metrics dashboard exists** — At minimum: error rate, latency, throughput
- [ ] **Alerts configured** — On-call will be notified if {error threshold} is breached
- [ ] **{Item}** — ...

---

## {Section 5: e.g., "Deployment Readiness"}

- [ ] **{Item}** — ...
- [ ] **{Item}** — ...
- [ ] **Rollback procedure tested** — Can revert to previous version within {target time}
- [ ] **Database migrations are backward-compatible** — Old code can run against new schema if rollback needed

---

## {Section 6: e.g., "Cost"}

- [ ] **Budget alert configured** — Alert fires before {X}% of budget is consumed
- [ ] **Resources tagged** — All resources have required tags: {tag list}
- [ ] **No orphaned resources** — Verified no unused EIPs, EBS volumes, old snapshots
- [ ] **{Item}** — ...

---

## Sign-off

<!-- Required approvals before the operation proceeds. -->

| Role | Name | Date | Signature |
|------|------|------|-----------|
| {Role 1} | | | |
| {Role 2} | | | |

---

## Notes / Exceptions

<!-- Record any items marked N/A, any deferred items, and the rationale. -->

| Item | Decision | Rationale | Owner | Due date |
|------|----------|-----------|-------|----------|
| | | | | |

---

## Post-Completion

- [ ] Checklist archived with the deployment record / incident ticket
- [ ] Any deferred items tracked in {issue tracker}
- [ ] Lessons learned documented if any items revealed gaps

---

## References

- [Runbook for this operation]({relative path})
- [Related checklist: {name}]({relative path})
- [Official best practices]({URL})
