# Configuration Service

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Validate, version, audit, and safely distribute dynamic application configuration to large fleets.

Target multi-zone availability, explicit latency SLOs, capacity estimates, and a
documented consistency model before selecting infrastructure.

## APIs and data model

Writers create drafts, validate, approve, and roll out versions; clients watch scoped keys and retain last-known-good values.

ConfigKey(scope, key); Version(value, schema, author, created_at, checksum); Rollout(version, cohort, state).

## High-level design

```text
admin -> API -> validator/approval -> version store -> rollout controller -> client watches
```

Store immutable versions, distribute signed snapshots through regional relays, canary by cohort, and limit simultaneous reconnects.

## Reliability, security, and operations

Clients validate locally and atomically swap snapshots. Automatic rollback uses health signals; a broken control plane cannot erase cached config.

Audit every change, require least-privilege scopes and multi-party approval for sensitive keys, and track rollout health, age, and rejection counts.

## Key trade-off

Fast global rollout reduces inconsistency but increases blast radius; staged rollout is safer but permits temporary version skew.
