← [Previous: DR Runbooks](../19-disaster-recovery/dr-runbooks.md) | [Home](../README.md) | [Next: Assessment →](./assessment.md)

---

# Cloud Migration

Cloud migration is the process of moving workloads from on-premises or one cloud environment to another. The 6Rs framework provides a structured way to decide the right approach for each workload.

---

## The 6Rs

| Strategy | Description | Effort | Best when |
|----------|-------------|--------|-----------|
| **Retire** | Decommission — application is no longer needed | None | End-of-life apps |
| **Retain** | Keep on-premises for now | None | Not ready to migrate |
| **Rehost** (Lift & Shift) | Move to cloud with no changes | Low | Legacy apps, quick wins |
| **Replatform** (Lift & Reshape) | Minor optimizations without redesign | Medium | Managed DB, containers |
| **Repurchase** | Replace with SaaS | Medium | Commodity software |
| **Refactor** (Re-architect) | Redesign for cloud-native | High | Strategic, long-term |

---

## Migration Factory Approach

```
Discover → Assess → Plan → Migrate → Optimize → Operate
    │           │       │       │          │          │
  Inventory  6Rs map   Wave   Execute    Cost/      BAU
  TCO calc   TCO       plan   test       perf       handoff
```

---

## Topics

| File | Topics |
|------|--------|
| [Assessment](./assessment.md) | Discovery, 6Rs mapping, TCO analysis, migration readiness |
| [Lift & Shift](./lift-and-shift.md) | AWS MGN, VM import, rehost patterns |
| [Replatform](./replatform.md) | Containerization, managed databases, PaaS migration |
| [Refactor](./refactor.md) | Microservices decomposition, strangler fig pattern |
| [Data Migration](./data-migration.md) | AWS DMS, Snowball, large-scale data transfer |

---

## References

- [AWS Migration Hub](https://docs.aws.amazon.com/migrationhub/latest/ug/)
- [AWS Application Migration Service](https://docs.aws.amazon.com/mgn/latest/ug/)
- [AWS Database Migration Service](https://docs.aws.amazon.com/dms/latest/userguide/)
- [Google Cloud Migrate](https://cloud.google.com/migrate)

---

← [Previous: DR Runbooks](../19-disaster-recovery/dr-runbooks.md) | [Home](../README.md) | [Next: Assessment →](./assessment.md)
