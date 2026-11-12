← [Previous: Query Optimization](../18-databases/query-optimization.md) | [Home](../README.md) | [Next: RPO & RTO →](./rpo-rto.md)

---

# Disaster Recovery

Disaster recovery (DR) is the ability to restore service after a failure — be it hardware, software, human error, or a regional outage. DR is not backup; backup is one component of DR.

---

## DR vs High Availability

| Aspect | High Availability | Disaster Recovery |
|--------|------------------|------------------|
| Goal | Prevent downtime | Recover from failure |
| Scope | Component-level redundancy | Region/site-level failure |
| Response | Automatic (seconds) | Planned procedure (minutes–hours) |
| Example | Multi-AZ RDS failover | Restore to a different AWS region |

---

## DR Tiers

| Tier | Strategy | RTO | RPO | Cost |
|------|----------|-----|-----|------|
| 1 | Backup & restore | Hours–days | Hours | Lowest |
| 2 | Pilot light | 30–60 min | Minutes | Low |
| 3 | Warm standby | 10–30 min | Seconds–minutes | Medium |
| 4 | Multi-site active-active | Seconds | Near-zero | Highest |

---

## Topics

| File | Topics |
|------|--------|
| [RPO & RTO](./rpo-rto.md) | Defining objectives, DR tiers, cost vs. recovery trade-offs |
| [Backup Strategies](./backup-strategies.md) | 3-2-1 rule, cross-region, cross-account, immutable backups |
| [Failover Patterns](./failover-patterns.md) | Pilot light, warm standby, active-active, DNS failover |
| [DR Runbooks](./dr-runbooks.md) | Step-by-step DR procedures, testing, game days |

---

## References

- [AWS Disaster Recovery](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.html)
- [AWS Well-Architected: Reliability](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)
- [GCP DR planning guide](https://cloud.google.com/solutions/dr-scenarios-planning-guide)

---

← [Previous: Query Optimization](../18-databases/query-optimization.md) | [Home](../README.md) | [Next: RPO & RTO →](./rpo-rto.md)
