# One-to-One Chat

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Support durable conversations, multi-device delivery, offline sync, receipts, and per-conversation ordering.

Set measurable availability and latency targets, estimate peak load and retained
data, and state the ordering and consistency guarantees explicitly.

## APIs and data model

POST /conversations/{id}/messages uses a client message ID; GET messages uses a cursor; device ACKs advance delivered/read watermarks.

Conversation(id, members); Message(conversation_id, sequence, sender, body_ref, created_at); DeviceCursor(device, conversation, delivered, read).

## High-level design

```text
client -> WebSocket gateway -> conversation shard -> message log -> recipient fan-out
```

Assign sequence numbers within a conversation shard, persist before acknowledging, push to connected devices, and let offline clients sync from their cursor.

## Reliability, security, and operations

Deduplicate client IDs, resume sessions after reconnect, encrypt transport and stored content, enforce membership on every access, and retain tombstones for deletion.

Monitor send-to-persist and send-to-device latency, reconnects, undelivered backlog, duplicate attempts, and shard hot spots.

## Key trade-off

Strict order per conversation is practical; global ordering is unnecessary and would reduce availability.
