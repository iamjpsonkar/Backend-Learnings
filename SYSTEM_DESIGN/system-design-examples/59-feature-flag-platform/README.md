# Feature Flag Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Author flags, target cohorts, distribute signed snapshots, evaluate locally, audit changes, and provide kill switches.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Flag(id,key,type,rules,default,version); Environment; immutable Snapshot; EvaluationEvent sampled separately.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
admin -> validation/approval -> config store -> regional relays/CDN/stream -> SDK local evaluation
```

Compile deterministic rules, hash subjects for stable percentage rollout, push versions with polling fallback, cache last-known-good, and limit event volume.

## Failure, security, and observability

Fail to safe defaults, canary changes, prevent PII leakage in attributes, require approvals, and monitor propagation age, evaluation errors, stale SDKs, and rollback use.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Local evaluation is resilient and fast but exposes rules to clients; server evaluation protects rules but adds network latency and dependency.
