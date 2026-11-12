← [Previous: Data Migration](../20-migration/data-migration.md) | [Home](../README.md) | [Next: Strategy →](./strategy.md)

---

# Multi-Cloud

Multi-cloud means running workloads across two or more cloud providers intentionally. It is not the same as having accidentally ended up with AWS and Azure because different teams made different choices.

---

## Why Multi-Cloud

| Driver | Description |
|--------|-------------|
| **Avoid vendor lock-in** | Retain negotiating power, no single-vendor dependency |
| **Best-of-breed services** | GCP BigQuery for analytics, AWS for compute, Azure for enterprise identity |
| **Regulatory requirements** | Some regions mandate data residency with providers not available on one cloud |
| **Resilience** | Active-active across providers for extreme availability targets |
| **M&A / consolidation** | Acquired companies bring their existing cloud footprint |

---

## Trade-offs

```
Benefits                                 Costs
─────────────────────────────────────    ─────────────────────────────────────
No vendor lock-in                        Operational complexity multiplied
Best service per workload                Staff must know 2+ cloud providers
Negotiating leverage                     Security policies duplicated everywhere
Geographic flexibility                   Data transfer costs between providers
Resilience (no shared fate)              Consistent observability harder
                                         IaC tooling must span providers
```

---

## Multi-Cloud Maturity

```
Level 1: Accidental multi-cloud     — Different teams use different providers
Level 2: Workload-specific          — Deliberate: "BigQuery for analytics, AWS for compute"
Level 3: Portable applications      — Containers + abstracted IaC + federated identity
Level 4: Active-active multi-cloud  — Traffic splits across providers, automatic failover
```

Most organizations should target **Level 2–3**. Level 4 is rarely justified by the operational cost.

---

## Topics

| File | Topics |
|------|--------|
| [Strategy](./strategy.md) | When to use multi-cloud, vendor lock-in analysis, workload placement |
| [Networking](./networking.md) | Inter-cloud connectivity, VPN, Direct Connect, ExpressRoute |
| [Identity](./identity.md) | Cross-cloud IAM federation, OIDC, Workload Identity |
| [Data Replication](./data-replication.md) | Cross-cloud data sync, CDC, conflict resolution |
| [IaC Abstractions](./iac-abstractions.md) | Terraform multi-provider, Pulumi, provider abstraction patterns |

---

## References

- [CNCF Multi-cloud landscape](https://landscape.cncf.io/)
- [AWS multi-cloud guidance](https://docs.aws.amazon.com/whitepapers/latest/aws-multi-cloud/)
- [HashiCorp multi-cloud patterns](https://developer.hashicorp.com/terraform/tutorials/networking)

---

← [Previous: Data Migration](../20-migration/data-migration.md) | [Home](../README.md) | [Next: Strategy →](./strategy.md)
