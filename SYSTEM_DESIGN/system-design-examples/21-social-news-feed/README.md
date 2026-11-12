# Social News Feed

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Create posts, follow users, fetch a ranked cursor-paginated feed, and enforce visibility.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

User, Follow, Post, FeedEntry(user, rank_key, post_id). Store posts by author; keep generated feed entries as rebuildable derived data.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
client -> feed API -> feed cache/store -> post/graph services; post event -> fan-out/ranking
```

Fan out on write for ordinary authors and merge celebrity posts on read. Partition inboxes by user, rank with stable cursors, and hydrate posts in batches.

## Failure, security, and observability

Rebuild inboxes from post/follow logs, filter privacy at read time, bound fan-out retries, and monitor fan-out lag, feed latency, hot authors, and stale entries.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Write fan-out makes reads cheap but explodes for celebrities; the hybrid model adds read complexity while containing write amplification.
