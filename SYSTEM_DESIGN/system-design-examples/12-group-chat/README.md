# Group Chat

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Add membership history, roles, mentions, moderation, receipts, and groups ranging from small teams to public channels.

Set measurable availability and latency targets, estimate peak load and retained
data, and state the ordering and consistency guarantees explicitly.

## APIs and data model

Message send includes group ID and idempotency key; membership changes have versions; history reads use stable cursors.

Group(id, type, version); Membership(group, user, role, joined_seq, left_seq); Message(group, seq, sender, payload).

## High-level design

```text
client -> gateway -> group shard -> durable log -> fan-out service -> inbox/device streams
```

Fan out on write for small groups and on read for huge groups; cache membership snapshots and partition public channels by message range.

## Reliability, security, and operations

Authorize against membership version, preserve moderation/audit events, isolate slow subscribers, and rebuild derived inboxes from the group log.

Track publish latency, fan-out lag, active sockets, hot groups, membership-cache staleness, and moderation queue age.

## Key trade-off

Per-recipient inboxes speed reads but amplify writes; shared logs reduce writes but make unread state and filtering more expensive.
