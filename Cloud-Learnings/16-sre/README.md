← [Previous: Prometheus & Grafana](../15-observability/prometheus-grafana.md) | [Home](../README.md) | [Next: SLIs & SLOs →](./slos-slis.md)

---

# Site Reliability Engineering (SRE)

SRE applies software engineering discipline to operations. It defines reliability targets, measures compliance, and uses automation to eliminate repetitive work — all to keep services reliable while enabling teams to move fast.

---

## Core Principles

| Principle | Description |
|-----------|-------------|
| **SLIs / SLOs / SLAs** | Define and measure reliability targets objectively |
| **Error budgets** | Balance reliability with velocity — 100% uptime is the wrong goal |
| **Toil reduction** | Automate repetitive operational work |
| **Blameless culture** | Postmortems focus on systems, not people |
| **Capacity planning** | Proactive, not reactive, resource management |
| **Progressive delivery** | Canary releases, feature flags — reduce blast radius |

---

## SRE vs DevOps

| Aspect | DevOps | SRE |
|--------|--------|-----|
| Focus | Culture + process | Reliability engineering |
| Target | Fast, reliable delivery | Defined reliability with error budgets |
| Toil | Reduce gradually | Explicit cap: 50% ops / 50% engineering |
| Incidents | Resolve and move on | Blameless postmortem + action items |
| Origin | Community movement | Google's answer to "who runs prod?" |

---

## Topics

| File | Topics |
|------|--------|
| [SLIs & SLOs](./slos-slis.md) | Defining SLIs, writing SLOs, error rate vs latency SLOs |
| [Error Budgets](./error-budgets.md) | Error budget calculation, burn rate alerts, policy |
| [Toil Reduction](./toil-reduction.md) | Identifying toil, automation strategies |
| [On-Call](./on-call.md) | Rotation setup, runbooks, escalation, reducing alert fatigue |
| [Capacity Planning](./capacity-planning.md) | Load testing, resource projections, headroom |
| [Chaos Engineering](./chaos-engineering.md) | Hypothesis-driven chaos, LitmusChaos, game days |
| [Postmortems](./postmortems.md) | Blameless culture, template, action tracking |

---

## References

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [Google SRE Workbook](https://sre.google/workbook/table-of-contents/)
- [SLO Best Practices](https://sre.google/workbook/implementing-slos/)

---

← [Previous: Prometheus & Grafana](../15-observability/prometheus-grafana.md) | [Home](../README.md) | [Next: SLIs & SLOs →](./slos-slis.md)
