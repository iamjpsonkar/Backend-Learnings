← [Previous: Postmortems](../16-sre/postmortems.md) | [Home](../README.md) | [Next: Cost Visibility →](./cost-visibility.md)

---

# FinOps

FinOps (Financial Operations) is the practice of bringing financial accountability to cloud spending. It aligns engineering, finance, and business teams around cost visibility, optimization, and informed trade-offs.

---

## FinOps Lifecycle

```
Inform → Optimize → Operate
  │           │          │
Cost       Rightsize   Budgets
tagging    Reserved    Anomaly
Dashboards Instances   detection
Showback   Spot usage  Unit econ.
```

---

## Core Principles

1. **Teams need cost visibility** — engineers can't optimize what they can't see
2. **Everyone is responsible** — cost is a shared metric, not just finance's problem
3. **Centralize practice, decentralize decisions** — central platform, team-level ownership
4. **Trade-offs are business decisions** — sometimes spending more is the right choice
5. **Unit economics over total cost** — cost-per-order matters more than total EC2 spend

---

## Topics

| File | Topics |
|------|--------|
| [Cost Visibility](./cost-visibility.md) | Cost Explorer, tagging strategy, billing alarms, dashboards |
| [Rightsizing](./rightsizing.md) | EC2/RDS/K8s rightsizing, Compute Optimizer, idle resource detection |
| [Reserved & Savings Plans](./reserved-savings.md) | RIs, Savings Plans, Committed Use Discounts, coverage targets |
| [Storage Optimization](./storage-optimization.md) | S3 tiering, lifecycle, EBS rightsizing, snapshot cleanup |
| [Kubernetes Costs](./kubernetes-costs.md) | Kubecost, namespace allocation, Spot nodes, bin-packing |
| [FinOps Culture](./finops-culture.md) | Unit economics, showback/chargeback, anomaly detection |

---

## References

- [FinOps Foundation](https://www.finops.org/)
- [AWS Cost Management](https://docs.aws.amazon.com/cost-management/)
- [GCP Cost Management](https://cloud.google.com/cost-management)
- [Azure Cost Management](https://learn.microsoft.com/en-us/azure/cost-management-billing/)

---

← [Previous: Postmortems](../16-sre/postmortems.md) | [Home](../README.md) | [Next: Cost Visibility →](./cost-visibility.md)
