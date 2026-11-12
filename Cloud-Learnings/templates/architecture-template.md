# Architecture: {Pattern / System Name}

<!-- USAGE: Copy this file when documenting an architecture pattern, reference design,
     or multi-service system. Remove HTML comments before committing.
     Use in 22-projects/, provider sections, or stand-alone architecture docs. -->

> **Pattern type:** {Web Application / Data Pipeline / Event-Driven / Microservices / Serverless / Hybrid / Other}
> **Cloud provider(s):** {AWS / Azure / GCP / Multi-cloud / Cloud-agnostic}
> **Services involved:** {comma-separated list}

---

## Overview

<!-- 3–5 sentences. What is this architecture? What problem does it solve at a system level?
     Who uses this pattern and in what scale / context? -->

...

---

## Architecture Diagram

<!-- Primary diagram showing the full system. Use Mermaid first.
     For complex diagrams, reference an SVG or drawio asset. -->

```mermaid
graph TD
    A[{Component}] --> B[{Component}]
    B --> C[{Component}]
    C --> D[{Component}]
```

<!-- Or use an image asset if available: -->
<!-- <img src="../../assets/diagrams/svg/{pattern-name}.svg" alt="{Pattern Name} Architecture Diagram"/> -->

---

## Components

<!-- One row per service or component in the architecture. -->

| Component | Service / Tool | Role |
|-----------|---------------|------|
| {name} | {service} | ... |
| {name} | {service} | ... |
| {name} | {service} | ... |

---

## Data Flow

<!-- Describe how data or requests move through the system, step by step. -->

1. **{Step 1}:** ...
2. **{Step 2}:** ...
3. **{Step 3}:** ...
4. **{Step 4}:** ...

---

## Design Decisions

<!-- Why were these specific services or approaches chosen?
     For each key decision, state what was considered and why this option was selected. -->

### {Decision 1: e.g., "Why Lambda over EC2"}

**Options considered:** ...
**Chosen approach:** ...
**Reason:** ...

### {Decision 2}

**Options considered:** ...
**Chosen approach:** ...
**Reason:** ...

---

## Scalability

<!-- How does this architecture handle increased load?
     What are the scaling bottlenecks and how are they addressed? -->

| Component | Scaling mechanism | Bottleneck |
|-----------|------------------|------------|
| {component} | {auto-scaling / manual / serverless} | ... |
| {component} | {mechanism} | ... |

---

## Reliability and Fault Tolerance

<!-- How does the system survive failures?
     Cover: redundancy, retries, circuit breakers, failover. -->

- **Single points of failure:** {none / list them}
- **Redundancy:** ...
- **Retry / backoff:** ...
- **Failover:** ...
- **RTO target:** {recovery time objective}
- **RPO target:** {recovery point objective}

---

## Security

<!-- How is the system secured across each layer. -->

| Layer | Control |
|-------|---------|
| Network | {VPC, security groups, NACLs, private subnets} |
| Identity | {IAM roles, least privilege, no long-lived keys} |
| Data at rest | {encryption with KMS / managed keys} |
| Data in transit | {TLS 1.2+, VPC endpoints} |
| Secrets | {Secrets Manager / Parameter Store — no env vars} |
| Logging | {CloudTrail / CloudWatch / audit trail} |

---

## Observability

<!-- What is monitored? How are failures detected? -->

| Signal | Tool | Alert condition |
|--------|------|----------------|
| Metrics | {CloudWatch / Prometheus / Datadog} | {condition} |
| Logs | {CloudWatch Logs / ELK / Loki} | {condition} |
| Traces | {X-Ray / Jaeger / OTEL} | {condition} |
| Uptime | {Route 53 health checks / Pingdom} | {condition} |

---

## Cost Profile

<!-- Rough cost breakdown by component at a reference scale.
     Be transparent about assumptions. -->

| Component | Billing model | Estimated cost at {X scale} |
|-----------|--------------|------------------------------|
| {service} | {per request / per hour / per GB} | ~${X}/month |
| {service} | {billing model} | ~${X}/month |

**Cost optimization levers:**
- ...
- ...

---

## Trade-offs

<!-- Honest assessment of the trade-offs in this architecture. -->

| Pro | Con |
|-----|-----|
| ... | ... |
| ... | ... |

---

## Variations

<!-- Common modifications of this base pattern for different requirements. -->

### {Variation 1: e.g., "Multi-region active-active"}

Modify by: ...

### {Variation 2}

Modify by: ...

---

## Implementation Guide

<!-- Pointer to the hands-on project that builds this architecture, if one exists. -->

See the step-by-step implementation: [{project-name}]({relative path to project-template doc})

---

## References

- [Reference architecture documentation]({URL})
- [Well-Architected Framework guidance]({URL})
- [Related pattern: {name}]({relative path})
