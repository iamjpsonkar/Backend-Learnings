← [Previous: DevOps Engineer Roadmap](./devops-engineer.md) | [Home](../README.md) | [Next: Interview Prep →](../27-interview-prep/README.md)

---

# SRE Roadmap

A Site Reliability Engineer applies software engineering to operations. The focus is on measuring and improving reliability, responding to incidents, and building systems that are observable and self-healing.

**Prerequisite:** Cloud Engineer Roadmap Phase 1–3, plus comfortable with Python or Go.

---

## Phase 1: Reliability Fundamentals (3–4 weeks)

```
Week 1–2: SLIs, SLOs, Error Budgets
  ├── Defining meaningful SLIs (request success rate, latency)   → 16-sre/slos-slis.md
  ├── Setting SLO targets by service tier
  ├── Error budget math and burn rate alerts
  └── Sloth / pyrra for SLO management

Week 3–4: Observability Stack
  ├── Prometheus data model + PromQL                            → 15-observability/metrics.md
  ├── Multi-window burn rate alerting                           → 16-sre/error-budgets.md
  ├── Structured logging and Loki                               → 15-observability/logging.md
  └── Distributed tracing with OpenTelemetry                   → 15-observability/tracing.md
```

**Milestone:** Define SLOs for a service and build alerting that pages on burn rate, not raw errors.

---

## Phase 2: Incident Response (2–3 weeks)

```
Week 5–6: Incident Management
  ├── Incident severity levels and declaration criteria          → 16-sre/on-call.md
  ├── On-call setup: PagerDuty schedules, escalation policies
  ├── Incident commander role, communication templates
  └── Runbook writing and testing                               → 19-disaster-recovery/dr-runbooks.md

Week 7: Postmortems
  ├── Blameless postmortem process                              → 16-sre/postmortems.md
  ├── 5 Whys analysis
  ├── Action item tracking to closure
  └── Sharing learnings across teams
```

**Milestone:** Run a practice incident drill. Execute a DR runbook. Write a postmortem for the drill.

---

## Phase 3: Toil Reduction and Automation (3–4 weeks)

```
Week 8–9: Identify and Measure Toil
  ├── Toil taxonomy and time tracking                           → 16-sre/toil-reduction.md
  ├── Automate common tasks (restarts, scaling, cert renewal)
  ├── Self-service tooling for developers (Slack bots, APIs)
  └── Automated runbooks with decision logic

Week 10–11: Reliability Patterns
  ├── Circuit breakers, retries with exponential backoff        → 09-containers/
  ├── Graceful degradation and fallbacks
  ├── Rate limiting and load shedding
  └── Kubernetes liveness/readiness/startup probes             → 10-kubernetes/
```

---

## Phase 4: Capacity Planning and Performance (3–4 weeks)

```
Week 12–13: Load Testing
  ├── k6: ramping scenarios, constant arrival rate             → 16-sre/capacity-planning.md
  ├── Locust: Python-based load testing
  ├── Interpreting results: latency percentiles, error rate
  └── Finding the breaking point (saturation point)

Week 14–15: Resource Management
  ├── CPU throttling vs OOMKilled — how to identify each
  ├── VPA recommendations and right-sizing pods
  ├── Demand forecasting from historical CloudWatch metrics
  └── Pre-scaling for planned events (product launches)
```

**Milestone:** Run a load test, identify the bottleneck, fix it, re-test to confirm.

---

## Phase 5: Chaos Engineering (2–3 weeks)

```
Week 16–17: Game Days
  ├── LitmusChaos experiments (pod delete, network latency)    → 16-sre/chaos-engineering.md
  ├── AWS FIS (Fault Injection Simulator) experiments
  ├── Game day planning and execution
  └── Measuring hypothesis vs actual outcome
```

**Milestone:** Run a chaos experiment that intentionally fails a component; verify the SLO holds.

---

## Phase 6: Disaster Recovery (2–3 weeks)

```
Week 18–19: DR Planning and Execution
  ├── RPO/RTO targets by service tier                          → 19-disaster-recovery/rpo-rto.md
  ├── Backup strategies and testing cadence                    → 19-disaster-recovery/
  ├── Failover pattern selection                               → 19-disaster-recovery/failover-patterns.md
  └── DR drill execution and measurement
```

**Milestone:** Execute a full DR drill and measure actual MTTR against RTO target.

---

## SRE Bookshelf

| Book | Key Topics |
|------|-----------|
| *Site Reliability Engineering* (Google) | SRE philosophy, error budgets, incident response |
| *The Site Reliability Workbook* (Google) | Practical implementation of SRE practices |
| *Implementing Service Level Objectives* (Hidalgo) | SLO definition, measurement, and tooling |
| *Chaos Engineering* (Rosenthal) | Building confidence through controlled failure |
| *Database Reliability Engineering* (Campbell) | Applying SRE to database operations |

---

## Certifications

| Certification | When to take | Validates |
|--------------|-------------|----------|
| AWS DevOps Engineer Professional | After Phase 3 | Operational practices on AWS |
| CKA (Certified Kubernetes Administrator) | After Phase 1 | Kubernetes operations |
| Prometheus Certified Associate (PCA) | After Phase 1 | Prometheus + PromQL |

---

← [Previous: DevOps Engineer Roadmap](./devops-engineer.md) | [Home](../README.md) | [Next: Interview Prep →](../27-interview-prep/README.md)
