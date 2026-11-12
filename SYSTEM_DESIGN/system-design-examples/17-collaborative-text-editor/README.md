# Collaborative Text Editor

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Edit shared documents concurrently, show cursors, work offline, retain versions, and manage permissions.

Set measurable availability and latency targets, estimate peak load and retained
data, and state the ordering and consistency guarantees explicitly.

## APIs and data model

Clients submit operations with document/version and operation ID; streams return accepted operations and snapshots.

Document(id, owner, snapshot_version, snapshot_ref); Operation(document, seq, actor, client_id, base_version, delta); ACL(document, principal, role).

## High-level design

```text
client -> collaboration session -> document leader/log -> broadcast; compactor -> snapshots/object store
```

Use OT with a document leader or a CRDT for decentralized/offline edits, batch cursor updates, and compact operations into periodic snapshots.

## Reliability, security, and operations

Deduplicate operations, resume from sequence, fence stale leaders, validate permissions continuously, encrypt documents, and retain audit events.

Measure operation commit/broadcast latency, transform conflicts, reconnect catch-up, log length, snapshot time, and active editors.

## Key trade-off

OT produces compact documents but needs ordered transformation; CRDTs merge offline naturally but use more metadata and complex garbage collection.
