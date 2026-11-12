# Online Auction

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

List items, accept valid bids, maintain current winner, extend closing rules, notify users, and settle.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Auction(id,seller,start,end,state,version); Bid(auction,sequence,bidder,amount,created_at); settlement references winning bid.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
client -> bid gateway -> auction leader/ordered log -> state store -> event fan-out; close scheduler -> settlement
```

Route one auction to a leader, append bids durably in order, enforce increments/reserve, use server receipt time, and shard unrelated auctions.

## Failure, security, and observability

Fence leaders, deduplicate bid IDs, recover by replay, protect against bots/fraud, and monitor acceptance latency, leader changes, hot auctions, and close delay.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

A single leader gives deterministic fairness per auction; multi-leader bidding improves regional latency but requires a conflict rule users may view as unfair.
