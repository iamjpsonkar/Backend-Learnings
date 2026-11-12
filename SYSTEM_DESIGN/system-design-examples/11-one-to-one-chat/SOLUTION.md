# Complete Solution: One-to-One Chat

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Users send text and media messages, receive them on multiple devices, access
offline history, and see sent/delivered/read status. Preserve message order within
one conversation, deduplicate client retries, and support reconnect/resume.

Targets: 100 million daily users, 99.99% send/history availability, p99 online
delivery below 500 ms, durable acknowledgement only after replicated persistence,
and at-least-once device delivery with client-visible deduplication.

Global ordering, synchronous full-text search, and a claim of exactly-once network
delivery are out of scope.

## 2. Capacity estimation

Assume 50 messages/user/day, 1 KB average text envelope, 3x peak, two recipient
devices, and one year hot history.

```text
messages/day       = 100M * 50                    = 5 billion
average writes/s   = 5B / 86,400                  ~= 58K
peak writes/s      = 58K * 3                      ~= 174K
raw text/year      = 5B * 1 KB * 365              ~= 1.8 PB
device deliveries  = 5B * 2                       = 10B/day average
```

Media bytes dominate and live in object storage/CDN. History is partitioned and
tiered; recent conversations remain in low-latency storage.

## 3. Identity and conversation model

For one-to-one chat, derive a stable conversation ID from sorted user IDs plus a
namespace/version:

```text
conversation_id = hash("dm:v1:" + min(userA,userB) + ":" + max(userA,userB))
```

This prevents duplicate DM threads. If products allow separate threads, use a
random conversation ID and a unique membership/thread rule instead.

## 4. Protocol and APIs

WebSocket command:

```json
{
  "type": "send_message",
  "request_id": "req-91",
  "conversation_id": "c-...",
  "client_message_id": "deviceA-182733",
  "body": {"type": "text", "text": "hello"}
}
```

Server acknowledgement:

```json
{
  "type": "message_accepted",
  "client_message_id": "deviceA-182733",
  "message_id": "m-...",
  "sequence": 9182,
  "created_at": "2026-08-24T17:00:00Z"
}
```

History and state:

```text
GET /v1/conversations/{id}/messages?after_sequence=9100&limit=100
POST /v1/conversations/{id}/delivered {through_sequence}
POST /v1/conversations/{id}/read      {through_sequence}
POST /v1/media/uploads                -> signed multipart upload
```

## 5. Data model

```text
Conversation(id, user_a, user_b, home_region, last_sequence, created_at)
Message(conversation_id, sequence, message_id, sender_id,
        client_message_id, body_ref, type, created_at, state)
DeviceCursor(user_id, device_id, conversation_id,
             delivered_through, read_through, updated_at)
UserConversation(user_id, conversation_id, last_sequence,
                 last_message_at, archived, muted)
```

Primary message key is `(conversation_id, sequence)`. A unique key on
`(conversation_id, sender_id, client_message_id)` deduplicates retries. Store large
media as immutable object references, not inline rows.

## 6. Architecture

```text
clients -> regional WebSocket gateways -> conversation router
                                             |
                                             v
                                  conversation shard/leader
                                      |              |
                              replicated message   durable event log
                                    store              |
                                                       +-> online fan-out -> gateways
                                                       +-> inbox/index updater
                                                       +-> push notifications

history API -> message store/read replicas
media -> signed upload -> scanner/transcoder -> object store/CDN
```

Gateways hold connections but no durable chat state. Consistent hashing routes a
conversation to one ordering shard/leader in its home region.

## 7. Step-by-step workflow

### Connect and resume

1. Client authenticates device and opens WebSocket to nearest gateway.
2. Gateway registers `(user, device, connection)` with short lease.
3. Client sends its latest per-conversation/server sync cursor.
4. Sync API returns missed messages and cursor changes in pages.
5. Only after catch-up does gateway stream new live events.

### Send

1. Gateway validates membership, size, message type, and client message ID.
2. Router sends command to conversation's current leader.
3. Leader deduplicates, allocates next sequence, and persists message to quorum.
4. After durable commit, sender receives accepted acknowledgement.
5. Committed event fans out to every connected recipient/sender device.
6. Offline recipient produces one coalesced push notification, not one per retry.
7. Recipient ACK advances delivered watermark; opening conversation advances read
   watermark and sends receipt event to sender devices.

## 8. Core send logic

```text
function sendMessage(actor, command):
    conversation = conversations.get(command.conversationId)
    require actor.userId in conversation.members
    validateBody(command.body)

    dedupeKey = (conversation.id, actor.userId, command.clientMessageId)
    existing = dedupeIndex.get(dedupeKey)
    if existing exists:
        return accepted(existing.messageId, existing.sequence)

    routeToLeader(conversation.id)

    transaction on conversation partition:
        existing = dedupeIndex.get(dedupeKey)
        if existing exists: return accepted(existing...)

        sequence = conversation.lastSequence + 1
        messageId = uniqueId()
        message = Message(conversation.id, sequence, messageId,
                          actor.userId, command.clientMessageId,
                          storeBody(command.body), now(), ACTIVE)
        messages.insert(message)
        dedupeIndex.insert(dedupeKey, messageId, sequence)
        conversation.lastSequence = sequence
        outbox.insert(MessageCommitted(messageId, conversation.id, sequence))

    return accepted(messageId, sequence)
```

The second dedupe check is inside the transaction because two retry commands may
race. Allocate sequence only in the same transaction as message insertion; gaps
may be allowed, but duplicate sequence must never occur.

## 9. Fan-out and device delivery

```text
function consumeCommitted(event):
    message = messages.get(event.conversationId, event.sequence)
    for user in conversation.members:
        userConversation.upsertMaxSequence(user, conversation.id, event.sequence)
        connections = presence.connectedDevices(user)
        if connections not empty:
            for connection in connections:
                gatewayStream.publish(connection, message)
        else if user != message.sender:
            pushQueue.publishCoalesced(user, conversation.id, event.sequence)
```

Fan-out is at least once. Devices deduplicate by `(conversation, sequence)` or
`message_id`. If online fan-out fails, history sync is the repair path.

## 10. Cursor and receipt logic

Receipts are monotonic watermarks, not one row per message:

```text
function acknowledge(device, conversation, kind, throughSequence):
    require throughSequence <= conversation.lastSequence
    cursor.atomicMax(kind, throughSequence)
    userAggregate.atomicMax(kind, throughSequence)
    publishReceiptIfAggregateAdvanced()
```

An out-of-order or duplicate ACK cannot move a cursor backward. Sender UI marks a
message delivered/read when the recipient user's aggregate watermark reaches its
sequence; products may instead expose per-device receipts.

## 11. History pagination

Read by sequence, not offset:

```text
SELECT ... WHERE conversation_id = ? AND sequence > ?
ORDER BY sequence ASC LIMIT 100
```

For reverse scroll use `sequence < before ORDER BY sequence DESC`. Cursor remains
stable while new messages arrive. Authorize membership on every history request.

## 12. Media flow

1. Client requests signed upload with size/type/checksum.
2. It uploads directly to private object storage.
3. Scanner/transcoder validates and produces immutable media variants.
4. Ready media token can be referenced in a chat message.
5. Recipient receives a short-lived authorized CDN URL.

Never accept an arbitrary object key in a message; verify ownership and READY
state. Deleting a message revokes metadata access before asynchronous blob cleanup.

## 13. Ordering and consistency

- Strict order exists only inside one conversation.
- Durable ACK means message and outbox committed to replicated source of truth.
- Delivery/read receipts are eventually consistent and monotonic.
- Conversation list is a derived read model and may lag; history remains source of
  truth.
- Edits/deletes are new versioned events referencing original sequence, not silent
  in-place history rewrites.

## 14. Multi-region design

Assign each conversation a home region based on members/data policy. Both users
connect locally, but send commands route to home leader for ordering. Replicate
history to secondary regions asynchronously for disaster recovery and local reads
only when staleness semantics allow.

Failover promotes one fenced region/leader epoch. Do not accept concurrent writes
in two regions for the same conversation unless implementing a more complex CRDT
and weaker ordering contract.

## 15. Failure handling

| Failure | Behavior |
| --- | --- |
| WebSocket gateway fails | Client reconnects, reauthenticates, and resumes from cursor |
| Fan-out worker fails | Event log redelivers; device dedupe and history sync repair |
| Conversation leader fails | Replica elected with fenced epoch and committed sequence |
| ACK lost after commit | Client retries same client message ID and gets original result |
| Push provider fails | Queue retries/coalesces; message remains available in sync |
| Read replica lags | Route read-your-write to leader or show sync state explicitly |
| Home region fails | Fence old leader, promote replica, then resume commands |
| Viral media/message | CDN and bounded fan-out queues protect message store |

## 16. Security and privacy

- Authenticate every socket and refresh/expire sessions.
- Authorize membership for send, history, media, receipts, and deletion.
- Encrypt transport and storage; short-lived media URLs and private origins.
- Rate-limit spam, block/report users, scan media and unsafe URLs.
- Minimize message content in logs/traces; audit privileged access.
- End-to-end encryption can encrypt body on clients while server retains routing
  metadata; search/moderation/multi-device key management then require different
  product trade-offs.
- Enforce retention, account deletion, legal hold, and backup deletion policies.

## 17. Observability

Measure connections, reconnects, authentication failures, send-to-commit and
commit-to-device p99, dedupe rate, shard/leader health, replication lag, event and
fan-out backlog, offline sync lag, cursor/receipt delay, push outcomes, media
processing, hot conversations, storage growth, and message correctness gaps.

Synthetic tests send, lose ACK, retry, disconnect recipient, reconnect/sync, mark
read, upload media, fail a gateway/leader, and verify one ordered durable history.

## 18. Implementation path

1. **MVP:** HTTP send/history, relational/partitioned message table, deterministic
   conversation, client IDs, sequence ordering, and polling.
2. **Realtime:** WebSocket gateways, connection presence, durable outbox/fan-out,
   reconnect cursors, and push for offline users.
3. **Multi-device/media:** device cursors, monotonic receipts, signed uploads,
   scanning/CDN, deletion/retention, and abuse controls.
4. **Global scale:** conversation shards/leaders, home regions, replica failover,
   tiered history, load/chaos tests, and regional recovery drills.

## 19. Final design

Use stateless regional gateways and a conversation-partitioned replicated message
store with one ordering leader per conversation, transactional deduplication and
outbox, at-least-once fan-out, and cursor-based recovery. The central invariant is
that a `(conversation, sequence)` is committed once and a client message ID maps
to one result; every lossy realtime path can be repaired from durable ordered
history.
