# Complete Solution: Shared Whiteboard

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Users create boards, draw strokes, add/move/delete shapes and text, manage layers,
see cursors, work through short disconnections, and reload version history. Support
50 simultaneous editors on hot boards and very large canvases without loading every
object.

Targets: durable operation acknowledgement p99 below 250 ms, remote propagation
below 300 ms, convergent state after reconnect, and loss-tolerant cursor latency
below 100 ms. Embedded assets are scanned and stored separately.

## 2. Capacity estimation

Assume 1 million active boards, 50 users/hot board, pointer input sampled to 10
updates/s/user, and durable object operations averaging 500 bytes.

A hot board produces 500 cursor/pointer events/s but far fewer committed object
operations. Separate ephemeral traffic so pointer movement cannot crowd out
durable mutations. Snapshot after 5,000 operations or 5 minutes.

## 3. Object and operation model

```text
Board(id, owner, current_revision, snapshot_revision, snapshot_ref,
      home_region, state)
Object(board_id, object_id, type, properties, layer_id,
       bounds, field_versions, deleted_version)
Operation(board_id, revision, operation_id, actor, client_sequence,
          logical_time, mutation, created_at)
Asset(id, owner, object_key, checksum, state)
ACL(board_id, principal, role, version)
```

Use object/field-level last-writer-wins registers with Lamport timestamp plus actor
tie-break, an ordered list CRDT for layer/z-order, and tombstones for deletion.
Stroke points are immutable chunks rather than thousands of mutable fields.

## 4. Architecture

```text
clients -> WebSocket gateways -> board router -> board session shard
                                              |         |
                                       operation log  live broadcast
                                              |
                                  materializer/snapshot -> object storage

spatial tile index <--- object bounds
assets -> signed upload -> scan -> object store/CDN
```

One shard assigns durable revisions for replay/audit, while CRDT rules make object
mutations converge and permit offline submission.

## 5. Step-by-step workflow

### Load

1. Authenticate and authorize board.
2. Fetch latest snapshot manifest and only spatial tiles intersecting viewport.
3. Apply operation tail after snapshot revision.
4. Join live stream at exact revision; a gap triggers tail reload.

### Edit

1. Client applies local mutation immediately with unique operation ID and Lamport
   timestamp.
2. It sends operation plus known board revision.
3. Shard validates ACL, object/asset references, size, and mutation type.
4. Shard deduplicates, assigns revision, appends durably, and broadcasts.
5. Clients merge operation by CRDT field/list/tombstone rules.
6. Materializer updates object state and spatial tiles asynchronously.

## 6. Core merge logic

```text
function applyOperation(boardState, op):
    if seenOperationIds.contains(op.id): return boardState
    object = boardState.objects.getOrCreate(op.objectId)

    if op.type == DELETE:
        if op.version > object.deletedVersion:
            object.deletedVersion = op.version
        remember(op.id); return boardState

    if object.deletedVersion >= op.version:
        remember(op.id); return boardState

    if op.type == SET_FIELDS:
        for (field,value) in op.fields:
            if op.version > object.fieldVersions[field]:
                object[field] = value
                object.fieldVersions[field] = op.version

    if op.type == APPEND_STROKE_CHUNK:
        object.strokeChunks.addIfAbsent(op.chunkId, op.points)

    if op.type == MOVE_IN_LAYER_ORDER:
        boardState.layerOrder.applyCrdtMove(op)

    remember(op.id)
    return boardState
```

`version = (lamport_counter, actor_id)` supplies deterministic total tie-break.
Delete wins only against older/equal updates; explicit restore creates a new object
generation rather than accidentally resurrecting an old ID.

## 7. Server acceptance logic

```text
function submit(actor, command):
    require acl.canEdit(actor, command.boardId)
    require command.size <= MAX_OPERATION_BYTES
    validateMutationAndAssetOwnership(command)

    transaction on board shard:
        old = dedupe.get(command.boardId, command.operationId)
        if old exists: return ack(old.revision)
        board = boards.getForUpdate(command.boardId)
        revision = board.currentRevision + 1
        operationLog.insert(board.id, revision, command)
        dedupe.insert(board.id, command.operationId, revision)
        board.currentRevision = revision
        outbox.insert(BoardOperationCommitted(board.id, revision))
    return ack(revision)
```

CRDT merge handles concurrent intent, but revision still gives efficient gap
detection, deterministic snapshots, and history.

## 8. Stroke and pointer handling

- Sample raw pointer input by time/distance and simplify curves client-side.
- Render uncommitted stroke locally and stream ephemeral preview chunks.
- On pointer-up, commit immutable stroke chunks plus style/bounds.
- Cursor/selection/preview events are lossy, coalesced, and never written to durable
  operation log.
- Bound point count and encoded bytes to prevent pathological strokes.

## 9. Spatial partitioning

Map object bounding boxes to quadtree/H3-like canvas tiles. Snapshot manifest lists
tile objects and versions. Viewport load requests tiles plus a margin; objects
crossing tiles have one canonical object record and references from intersected
tiles.

Moving an object updates tile references through materialized events. Until index
catches up, live operation carries old/new bounds so active clients remain correct.

## 10. Snapshots and tombstone garbage collection

1. Materializer loads snapshot R and operations R+1..N.
2. Apply CRDT rules and write immutable board/tile snapshot N with checksum.
3. Atomically advance snapshot pointer.
4. Retain operation tail for active/offline clients and history policy.
5. Remove tombstone only after every supported offline horizon/version vector and
   retained snapshot is beyond it; otherwise old offline updates can resurrect data.

## 11. Offline reconnect

Client retains operation IDs and Lamport counter. On reconnect it downloads missing
tail/snapshot, merges remote operations, then submits local pending operations.
Commutative CRDT fields converge. Semantic conflicts such as two users rewriting
the same text field resolve by deterministic LWW and may surface version history to
restore losing intent.

## 12. Assets

Use signed multipart upload, checksum, malware/type scan, immutable key, and READY
token. An object may reference only an asset owned/authorized for board. Reads use
short authorized CDN URLs. Deletion revokes metadata first and cleans blob later.

## 13. Failure handling

| Failure | Behavior |
| --- | --- |
| Gateway fails | Reconnect using revision and resend unacked operation IDs |
| Board shard fails | Fenced replica resumes committed revision; retries dedupe |
| Broadcast lost | Revision gap triggers operation-tail fetch |
| Materializer/index lags | Operation log/live events remain correct; viewport may fetch fallback |
| Snapshot fails | Keep prior snapshot and replay longer tail |
| Offline client returns late | Merge if within retention; otherwise snapshot plus pending CRDT ops |
| Hot board overload | Dedicated shard, batching, cursor shedding, participant/operation limits |
| Asset scan/store fails | Asset remains non-referenceable PENDING/FAILED |

## 14. Security and privacy

- ACL checks on join, operation, history, snapshot, tile, and asset access.
- Short-lived share links and immediate session revocation on ACL changes.
- Validate/sanitize text, URLs, embeds, fonts, and asset types.
- Bound operations, object count, board size, cursor rate, and snapshot resource use.
- Encrypt data, audit sharing/export/delete/privileged reads, minimize content logs.
- Apply retention, account deletion, legal hold, and regional storage policy.

## 15. Observability

Measure load time by snapshot/tile/tail, operation commit/broadcast p99, dedupe,
revision gaps, CRDT conflicts/tie-breaks, cursor drops, active editors, hot boards,
operation/tombstone count, snapshot duration/lag, spatial-index lag, asset failures,
reconnect/offline merge, and client/server snapshot checksum mismatch.

Property tests randomly reorder/duplicate concurrent operations and assert identical
state. Chaos tests kill shard/gateway/snapshot worker and return offline clients
after delete/move conflicts.

## 16. Implementation path

1. **MVP:** finite canvas, object CRUD, one board transaction leader, operation
   history, snapshots, ACL, and WebSocket broadcast.
2. **Collaboration correctness:** field/list CRDT rules, dedupe, reconnect, cursor/
   stroke separation, property tests, and tombstones.
3. **Large boards:** tile snapshots/index, lazy viewport loading, assets/CDN,
   compaction, hot-board isolation, and history UI.
4. **Global/offline:** home regions/failover, longer offline merge, privacy lifecycle,
   chaos/load and restore drills.

## 17. Final design

Use a revisioned per-board operation log for durability/replay and object-level
CRDTs for convergence, with ephemeral high-rate cursor/stroke previews separated
from committed mutations. Spatial tile snapshots make huge canvases loadable. The
central invariant is that duplicate/reordered operations merge to identical board
state and a tombstoned object cannot be resurrected by an older offline update.
