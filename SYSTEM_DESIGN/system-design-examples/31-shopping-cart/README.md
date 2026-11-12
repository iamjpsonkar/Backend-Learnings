# Shopping Cart

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Maintain anonymous and user carts, merge sessions, update quantities, expire data, and preserve checkout snapshots.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Cart(id,user,version,expires_at); CartItem(cart,sku,quantity,added_at). Price and availability remain references until checkout.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
client -> cart API -> partitioned cart store/cache; checkout -> cart snapshot -> pricing/inventory
```

Partition by cart ID, use optimistic versions, TTL inactive carts, merge deterministically on login, and avoid synchronous calls on every edit.

## Failure, security, and observability

Use idempotency keys, quantity limits, signed anonymous IDs, encryption, and monitor update conflicts, latency, merge errors, cart age, and checkout conversion.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Storing prices in carts improves display stability but risks staleness; authoritative repricing at checkout is safer.
