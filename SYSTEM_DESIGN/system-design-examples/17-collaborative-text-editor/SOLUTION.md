# Complete Solution: Collaborative Text Editor

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Multiple users edit one text document concurrently, see remote edits/cursors,
reconnect after network loss, retain version history, and enforce permissions.
Edits should appear locally immediately and converge to identical text for every
connected client.

Targets: 10 million documents, up to 100 editors on a hot document, 20 operations/
second/editor bursts, remote-edit propagation below 200 ms p99, and durable history
after server acknowledgement.

This design selects Operational Transformation (OT) with one ordered document
leader. Fully decentralized offline-first editing would favor a CRDT and different
metadata/garbage-collection trade-offs.

## 2. Capacity estimation

A hot document can produce 2,000 operations/s. If one encoded operation averages
200 bytes, it produces 400 KB/s before fan-out. Fan-out to 100 users is up to
40 MB/s for that document, so cursor events need sampling and operations batching.

Snapshot every 1,000 operations or 5 minutes. Store operation history needed for
active base revisions and version/audit retention; compact older history into
immutable snapshots.

## 3. Operation and data model

Represent text changes as retain/insert/delete components:

```text
Operation [retain(5), insert("hello"), delete(2), retain(rest)]
```

```text
Document(id, owner, current_revision, snapshot_revision,
         snapshot_ref, leader_epoch, state)
Operation(document_id, revision, operation_id, actor_id,
          client_id, client_sequence, base_revision, delta, created_at)
ACL(document_id, principal, role, version)
ClientSession(document_id, client_id, ack_revision, connection_epoch)
```

Unique `(document, client_id, client_sequence)` deduplicates retries. Revision is
strictly increasing within a document.

## 4. Protocol

```text
join {document_id, last_revision} -> snapshot or operation tail
submit {operation_id, client_sequence, base_revision, delta}
ack {operation_id, committed_revision, transformed_delta}
remote_operation {revision, actor, delta}
cursor {anchor, head, based_on_revision}  // ephemeral
```

The client keeps `serverRevision`, one outstanding operation, and a buffer of
local operations created while the outstanding operation awaits acknowledgement.

## 5. Architecture

```text
clients -> regional WebSocket gateways -> document router -> document leader
                                                  |          |
                                            operation log  session broadcast
                                                  |
                                  snapshot worker -> object storage

ACL service/cache and audit protect every document session
```

Consistent hashing assigns documents to leaders. A replicated log/database stores
accepted operations; gateways and cursor presence are disposable.

## 6. Step-by-step workflow

### Join

1. Authenticate and authorize document read/edit role.
2. Route to current document leader and create connection epoch.
3. If client's revision is retained, return operation tail; otherwise send latest
   snapshot plus tail after snapshot revision.
4. Client applies data, verifies final revision, then starts live stream.

### Local edit

1. Editor applies change immediately to local text.
2. Client expresses it relative to current local document.
3. If no outstanding operation, send it with server revision; otherwise compose it
   into local buffer.
4. Leader transforms incoming operation against every accepted operation after its
   base revision.
5. Leader durably appends transformed operation and assigns next revision.
6. Sender receives ACK; other clients receive committed operation.
7. Each client transforms incoming operation against its own outstanding/buffered
   local work before applying.

## 7. OT transform rules

For two concurrent operations A and B based on the same document, produce A' and
B' such that applying A then B' equals applying B then A'. Define deterministic
tie-breaking for simultaneous inserts, for example actor/client ID order.

Examples:

```text
base: "cat"
A: insert "s" at 0       -> "scat"
B: delete "a" at 1       -> "ct"

transform B against A: delete position 2
A then B'                -> "sct"
transform A against B: insert position 0
B then A'                -> "sct"
```

All language SDKs must share golden transform tests for insert/insert,
insert/delete, delete/delete overlaps, Unicode indexing, and tie-breaks. Use one
index unit (Unicode code points or UTF-16 units) consistently.

## 8. Server submit logic

```text
function submit(actor, command):
    require acl.canEdit(actor, command.documentId)
    routeToLeader(command.documentId)

    dedupeKey = (command.documentId, command.clientId,
                 command.clientSequence)
    old = operationLog.findByDedupe(dedupeKey)
    if old exists: return ack(old)

    transaction on document:
        doc = documents.getForUpdate(command.documentId)
        require command.baseRevision >= doc.compactionFloor
        require command.baseRevision <= doc.currentRevision

        transformed = command.delta
        for accepted in operationLog.range(command.baseRevision + 1,
                                           doc.currentRevision):
            transformed = transform(transformed, accepted.delta,
                                    tieBreak=(command.clientId, accepted.clientId))

        validateOperation(transformed, documentLengthAt(doc.currentRevision))
        revision = doc.currentRevision + 1
        operationLog.insert(revision, dedupeKey, command.baseRevision, transformed)
        doc.currentRevision = revision
        outbox.insert(OperationCommitted(doc.id, revision, transformed, actor.id))
    return ack(revision, transformed)
```

Serializing at one leader avoids two operations receiving the same revision. The
leader may batch multiple commands in one storage commit while preserving order.

## 9. Client rebase logic

```text
state outstanding = null
state buffer = identityOperation

onLocalEdit(op):
    applyLocally(op)
    if outstanding is null:
        outstanding = op
        send(op, baseRevision=serverRevision)
    else:
        buffer = compose(buffer, op)

onAck(committedRevision):
    serverRevision = committedRevision
    outstanding = null
    if not buffer.isIdentity:
        outstanding = buffer
        buffer = identityOperation
        send(outstanding, baseRevision=serverRevision)

onRemote(remote):
    if outstanding exists:
        (remote, outstanding) = transformPair(remote, outstanding)
    if not buffer.isIdentity:
        (remote, buffer) = transformPair(remote, buffer)
    applyLocally(remote)
    serverRevision = remote.revision
```

Production clients carefully order ACK and remote events; protocol includes
revision so gaps trigger resync rather than guesswork.

## 10. Snapshots and compaction

1. Worker reads snapshot R and operations R+1..N.
2. It applies operations deterministically and writes immutable snapshot N.
3. Transaction conditionally advances `snapshot_revision` if document still has a
   compatible head.
4. Retain operation tail needed by active clients and audit/version policy.
5. Clients older than compaction floor receive snapshot instead of long replay.

Snapshot checksum plus deterministic replay detects corruption.

## 11. Offline editing

Short disconnections retain queued OT operations if base remains available. For a
long offline period beyond compaction, client downloads current snapshot and
performs a three-way text merge against its saved base, showing conflicts when
intent is ambiguous. OT is not falsely advertised as effortless unlimited offline
merge; choose a text CRDT if that is a primary requirement.

## 12. Cursors and presence

Cursor/selection changes are ephemeral, sampled (for example 10/s), and tagged
with revision. Clients transform cursor positions through later operations.
Dropping a cursor event is acceptable. Cursor fan-out and user presence never
block durable edits.

## 13. Permissions and sharing changes

ACL version is checked on join and periodically/on change events. Removing edit
permission closes or downgrades live session. Leader rechecks permission before
commit, not only at socket connection. Share-link tokens are scoped, expiring, and
revocable.

## 14. Failure handling

| Failure | Behavior |
| --- | --- |
| Gateway fails | Client reconnects with last revision and outstanding op ID |
| Leader fails | Fenced replica resumes from committed revision; client retries dedupe key |
| ACK lost after commit | Retry returns original committed operation/revision |
| Broadcast lost | Client detects revision gap and fetches tail/snapshot |
| Snapshot worker fails | Operation log remains authoritative; retry snapshot |
| Client base compacted | Send current snapshot and perform explicit rebase/merge |
| ACL service unavailable | Existing short cached grants may continue; new/privileged actions fail safely |
| Hot document overload | Dedicated leader, batching, cursor shedding, editor/admission cap |

## 15. Security and privacy

- Document/operation authorization, short connection tokens, encrypted transport/
  storage, and private snapshot/object origins.
- Sanitize rendered rich text/embeds; bound operations and document size.
- Rate-limit edits/cursors and prevent malicious transform complexity.
- Audit sharing, export, deletion, and privileged access; minimize content logs.
- Retention, legal hold, account deletion, backups, and data residency are explicit.
- End-to-end encryption conflicts with server-side OT unless transformation operates
  on encrypted structure; that requires a different design.

## 16. Observability

Measure join/load time, operation submit/commit/broadcast p99, transform count and
CPU, revision gaps/resync, dedupe retries, leader moves, hot documents, active
editors, operation-log length, snapshot duration/lag/failure, cursor drops, ACL
denials/staleness, offline merge conflicts, storage, and convergence errors.

Property tests generate concurrent operations and assert convergence. Chaos tests
lose ACK/broadcast, kill leader, compact during reconnect, change ACL mid-edit, and
compare every client's final checksum.

## 17. Implementation path

1. **MVP:** single-user documents, immutable revisions/snapshots, permissions.
2. **Realtime ordered edits:** document leader, OT library with golden/property
   tests, operation log, dedupe, WebSocket broadcast, reconnect tail.
3. **Scale/features:** snapshots/compaction, cursor/presence, comments/history,
   batching, hot-document isolation, media/embeds.
4. **Global/operational:** regional document homes, fenced failover, long-offline
   merge policy, privacy lifecycle, chaos/load and restore tests.

## 18. Final design

Use one fenced ordering leader and durable operation log per document, OT to
transform concurrent operations, optimistic clients with outstanding/buffer rebase,
and immutable snapshots for compaction. The central invariant is convergence:
every accepted operation receives one revision, and transforming concurrent work
must produce identical document text regardless of arrival order.
