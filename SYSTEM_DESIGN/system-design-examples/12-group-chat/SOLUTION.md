# Complete Solution: Group Chat

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Create groups, manage roles/membership, send ordered text/media messages, mention
users, sync history across devices, moderate content, and support both private
groups and public channels with millions of members.

Targets: 50 million daily users, 2 billion messages/day, p99 durable send below
300 ms, online delivery below 1 second, and strict message order within a group
shard. Presence, typing, and reactions may be eventually consistent.

## 2. Capacity estimation

```text
average writes/s = 2B / 86,400 ~= 23K
peak writes/s at 5x           ~= 116K
raw text at 1 KB/message      ~= 2 TB/day
```

Fan-out dominates. Sending one message to a million-member channel must not create
one million durable inbox writes synchronously. Use a hybrid based on group size
and activity.

## 3. APIs and events

```text
POST /groups                         create group
POST /groups/{id}/members            add/invite member
DELETE /groups/{id}/members/{user}   remove member
POST /groups/{id}/messages           fallback HTTP send
GET  /groups/{id}/messages?after_sequence=...
POST /groups/{id}/read {through_sequence}
```

WebSocket send includes `group_id`, `client_message_id`, `observed_group_version`,
and body. Server returns `message_id` and group sequence.

## 4. Data model

```text
Group(id, type=PRIVATE|PUBLIC, owner, home_region,
      membership_version, last_sequence, fanout_mode, state)
Membership(group_id, user_id, role, joined_sequence,
           left_sequence|null, membership_version)
Message(group_id, sequence, message_id, sender_id,
        client_message_id, body_ref, created_at, moderation_state)
UserGroup(user_id, group_id, last_visible_sequence, unread_hint, preferences)
Receipt(user_id, device_id, group_id, read_through, delivered_through)
```

Membership history is sequence-aware. A user may read messages where
`joined_sequence <= message.sequence < left_sequence`; current membership alone is
insufficient for historical authorization.

## 5. Architecture

```text
clients -> WebSocket gateways -> group router -> group partition leader
                                                |        |
                                          message store  event log
                                                           |
                    +--------------------------------------+----------------+
                    |                                                       |
            small-group fan-out                                     public-channel index
            -> user inbox hints                                     -> shared-log readers

membership service -> versioned membership cache
moderation/media/push/notifications consume durable events
```

One leader orders a group. Extremely active public channels may be assigned a
dedicated partition; if a single channel exceeds one leader, explicitly weaken
global order into substreams rather than pretending it remains total.

## 6. Step-by-step workflow

### Membership change

1. Authorized role submits command with expected membership version.
2. Group leader serializes change, increments version, and records audit event.
3. `joined_sequence` is current `last_sequence + 1`; removal records
   `left_sequence = last_sequence + 1`.
4. Invalidation updates gateway/member caches.
5. Removed users' live subscriptions are closed; history authorization uses bounds.

### Send

1. Gateway authenticates and sends command to group leader.
2. Leader loads membership snapshot/version and verifies sender role at next
   sequence.
3. It deduplicates client ID, allocates sequence, commits message plus outbox.
4. Sender receives durable acknowledgement.
5. Hybrid fan-out updates small-group member inbox hints or publishes one shared
   channel event for large groups.
6. Connected members receive event; offline devices recover from history.

## 7. Core send logic

```text
function send(actor, command):
    routeToGroupLeader(command.groupId)
    transaction on group partition:
        group = groups.getForUpdate(command.groupId)
        member = memberships.get(group.id, actor.userId)
        nextSeq = group.lastSequence + 1
        require memberCanSendAt(member, nextSeq)

        key = (group.id, actor.userId, command.clientMessageId)
        old = dedupe.get(key)
        if old exists: return old.acceptedResponse

        validateBodyAndMedia(command.body)
        message = Message(group.id, nextSeq, uniqueId(), actor.userId,
                          command.clientMessageId, command.bodyRef, now())
        messages.insert(message)
        dedupe.insert(key, message.id, nextSeq)
        group.lastSequence = nextSeq
        outbox.insert(GroupMessageCommitted(group.id, nextSeq, message.id,
                                            group.membershipVersion))
    return accepted(message)
```

The membership check and message commit share the group serialization boundary, so
a removal and send have a deterministic order.

## 8. Hybrid fan-out

```text
function handleCommitted(event):
    group = groups.get(event.groupId)
    if group.fanoutMode == INBOX:             // small/medium private groups
        for page in memberships.activeAt(event.sequence):
            bulkUpsertMax(userGroup, page.users, event.groupId, event.sequence)
            pushOnline(page.users, event)
    else:                                     // huge public channels
        channelAvailability.updateMax(event.groupId, event.sequence)
        pushOnlyActiveSubscribers(event.groupId, event)
```

Threshold is based on member count, write rate, online fraction, and inbox cost,
not one hard universal number. Conversion between modes is versioned and derived
state can rebuild from group log.

## 9. Reads and unread state

History reads directly from `(group, sequence)` and filter membership bounds plus
moderation. Stable cursors avoid offset pagination.

Unread count is a hint:

```text
unread ~= visibleLastSequence - user.readThrough - hidden/moderated adjustments
```

For huge channels, show `99+` or compute approximate counts instead of materializing
per-message unread rows. `readThrough` advances using atomic max.

## 10. Mentions, reactions, typing, and presence

- Parse mentions on committed message and notify only valid members, asynchronously.
- Reactions use unique `(message,user,emoji)` and async counters; they do not alter
  message order.
- Typing/presence are lossy TTL events sent only to currently subscribed clients.
- A failure in these features never blocks durable message send/history.

## 11. Moderation and deletion

Automated moderation can mark message `PENDING` for high-risk public groups or
publish then quarantine based on policy. Moderator actions are immutable events.
Deletion changes visibility/tombstone and purges media asynchronously; sequence is
never reused. Clients receive redaction event for cached copies.

## 12. Large-channel controls

- Dedicated partitions for high message-rate channels.
- Admission/rate limits per sender and group.
- Only active subscribers receive live push; others read shared log.
- Coalesce notifications and counters.
- Cache recent immutable message pages at edge/read replicas.
- Use slow-mode and moderation queues to protect public channels.

## 13. Multi-region ordering

Each group has one fenced home-region leader. Gateways route sends there, while
regional replicas serve authorized history within staleness policy. Region failover
promotes one replica epoch. Active-active writers would require conflict/order
semantics visible to users and are not selected for this design.

## 14. Failure handling

| Failure | Behavior |
| --- | --- |
| Gateway fails | Reconnect and resume by group sequence |
| Fan-out worker fails | Replay log; duplicate live delivery is client-deduped |
| Inbox update missing | History/shared log remains source of truth; rebuild hint |
| Group leader fails | Fenced replica resumes after committed last sequence |
| Membership cache stale | Leader authoritative check prevents invalid sends; reads recheck bounds |
| Push provider fails | Offline notification retries/coalesces; history remains available |
| Moderation service fails | Apply group policy: queue public messages or allow private flow with later scan |
| Home region fails | Fence old epoch, promote replica, then resume sends |

## 15. Security and privacy

- Role-based create/invite/remove/admin/moderate permissions.
- Membership bounds checked on every history/media access.
- Private object storage and short-lived authorized media URLs.
- Spam limits, abuse reporting, block relationships, malware/link scanning.
- Encrypt transport/storage and minimize content in logs.
- Audit membership/moderation/admin actions and enforce retention/deletion/legal
  requirements.
- Optional E2EE changes server moderation/search and group key rotation; document
  this as a separate cryptographic product design.

## 16. Observability

Measure send commit and delivery p99, leader/shard load, active sockets, fan-out and
inbox lag, shared-channel subscribers, membership cache/version lag, denied sends/
reads, reconnect sync volume, unread/receipt delay, moderation queue age, push
outcomes, hot groups, storage and media growth, and failover recovery.

Test concurrent remove/send, membership leave/rejoin history, lost ACK/retry,
fan-out replay, mode conversion, million-member channel, leader/zone loss, and
moderation outage.

## 17. Implementation path

1. **MVP:** private groups, SQL/partitioned message log, membership table, one
   leader/transaction per group, HTTP send/history, sequence cursors.
2. **Realtime:** gateways, durable outbox/fan-out, reconnect, device receipts,
   push, media, and moderation.
3. **Scale:** partitioned leaders, membership caches, inbox read models, hybrid
   fan-out, shared public-channel logs, hot-group isolation, history tiering.
4. **Global resilience:** home regions, replicas/fencing, zone failover, chaos and
   load tests, retention/privacy operations.

## 18. Final design

Use one ordered replicated log per group with membership changes serialized against
message sequences, transactional deduplication/outbox, and hybrid fan-out: inbox
hints for small groups and shared-log reads for huge channels. The central
invariant is that authorization is evaluated at a definite group sequence and all
realtime/derived delivery state can be reconstructed from durable ordered history.
