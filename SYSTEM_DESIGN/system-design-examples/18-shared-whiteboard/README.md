# Shared Whiteboard

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Synchronize strokes, shapes, text, layers, selections, and cursors for large, long-lived boards.

Set measurable availability and latency targets, estimate peak load and retained
data, and state the ordering and consistency guarantees explicitly.

## APIs and data model

Clients send idempotent object operations; subscriptions stream ordered changes since a board revision; snapshots accelerate load.

Board(id, snapshot_rev, snapshot_ref); Object(board, object_id, type, properties, version, deleted); Operation(board, rev, actor, mutation).

## High-level design

```text
client -> board session shard -> operation log -> participants; snapshot worker -> object store
```

Partition very large boards into spatial tiles/layers, coalesce pointer events, send viewport-relevant objects, and snapshot/compact tombstones.

## Reliability, security, and operations

Use object versions or CRDT rules, preserve offline operation IDs, authorize board access, sanitize embedded content, and recover sessions from the log.

Track board-load time, operation latency, bytes per session, dropped/coalesced events, snapshot lag, and hot tiles.

## Key trade-off

A single ordered board log simplifies conflict resolution; spatial partitioning scales huge boards but complicates operations spanning tiles.
