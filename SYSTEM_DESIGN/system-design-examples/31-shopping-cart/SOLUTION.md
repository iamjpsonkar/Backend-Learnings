# Complete Solution: Shopping Cart

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Anonymous and authenticated users add, set, and remove SKU quantities, view carts
across devices, merge a guest cart on login, apply promotion codes, and begin
checkout from an immutable cart snapshot. Inactive carts expire. Product display
data may be cached, but checkout revalidates price, promotion, tax, and inventory.

Targets: read/update p99 below 150/250 ms, 99.99% read and 99.9% write availability,
no acknowledged item mutation lost, and read-your-writes within a session. Cart state
is strongly consistent per cart/version. Catalog/price/stock decoration is eventual;
the cart never promises inventory or a final price.

## 2. Capacity estimation

Assume 100 million active carts, 20 mutations/cart/day, five reads/mutation, ten
items/cart, 200 bytes/item, and 5x peak.

- Mutations average about 23,000/s and peak around 120,000/s.
- Reads average about 116,000/s and peak around 580,000/s.
- Active cart rows/items consume roughly 200 GB at 2 KB/cart before indexes,
  replication, idempotency records, and history; a conservative 10 KB/cart is 1 TB.
- Partition capacity by cart ID and isolate hot/bot clients with quotas.
- Idempotency data only needs the retry horizon; cart tombstones outlive late events.

## 3. APIs

```text
POST   /v1/carts                                  Idempotency-Key
GET    /v1/carts/{cartId}
PUT    /v1/carts/{cartId}/items/{sku}             {quantity} If-Match, Idempotency-Key
DELETE /v1/carts/{cartId}/items/{sku}              If-Match, Idempotency-Key
PUT    /v1/carts/{cartId}/promotion-codes/{code}  If-Match, Idempotency-Key
POST   /v1/carts/{cartId}/merge                   {sourceCartId} Idempotency-Key
POST   /v1/carts/{cartId}/checkout-snapshots      If-Match, Idempotency-Key
DELETE /v1/carts/{cartId}                         If-Match
```

Return cart version/ETag on every read/write. Bound distinct SKUs, quantity/SKU,
promotion codes, body size, mutation rate, inactive lifetime, and checkout attempts.
An anonymous cart token is random, signed, scoped, expiring, and rotated on login.

## 4. Data model and invariants

```text
Cart(id, owner_user_id, state, version, currency, market,
     created_at, updated_at, expires_at, merged_into_id)
CartItem(cart_id, sku, quantity, selected, added_at, updated_at,
         observed_price, observed_price_version, item_version)
CartPromotion(cart_id, code, state, observed_discount, promotion_version)
Idempotency(cart_id, actor_key, request_key, request_hash,
            response_ref, expires_at)
CheckoutSnapshot(id, cart_id, cart_version, owner_user_id, market,
                 items_json, promotions_json, created_at, expires_at)
CartEvent(cart_id, version, type, payload, created_at)
Outbox(id, aggregate_id, event_type, payload, published_at)
```

Invariants: one row per `(cart, SKU)`, quantity is positive and bounded, cart version
increments once per successful logical mutation, a checkout snapshot never changes,
and a merged/expired/checked-out cart rejects mutations. Adding to cart does not
reserve stock.

## 5. Architecture

```text
clients -> edge/auth -> stateless cart API -> partitioned cart database
                           |                     |          |
                       Redis read cache      outbox      TTL index
                                                  |          |
                                            analytics   expiry workers

checkout service -> immutable snapshot API -> pricing/promotion/tax/inventory/order
catalog service -> batch decoration/cache (not authoritative cart writes)
identity/login -> cart merge transaction/coordinator
```

Keep cart rows and items colocated by cart ID for conditional transactions. The
database is authoritative; cache uses versioned whole-cart documents and can be
discarded. Route a user's active authenticated cart consistently while retaining a
directory for anonymous IDs.

## 6. Step-by-step workflow

### Item update

1. Authenticate owner or verify anonymous capability token; validate SKU/quantity,
   request hash, version, limits, and active state.
2. Transactionally claim idempotency key, compare cart version, upsert/delete item,
   increment cart version/TTL, and write event/outbox.
3. Return the committed cart/version. After commit, invalidate or write-through cache;
   duplicate requests return the original response.
4. Read path loads authoritative/cache cart, then batch decorates SKUs with current
   names/images and indicative prices/availability. It labels changed/unavailable
   items instead of silently deleting them.

### Checkout handoff

1. Create immutable snapshot conditioned on the client cart version.
2. Checkout resolves authoritative SKU, seller, price, promotions, tax, shipping,
   and inventory reservation from snapshot IDs/quantities.
3. Show/reconfirm changes when required, then create order/payment through their own
   idempotent workflow. Cart is marked converted only from an authoritative order event.

## 7. Core item mutation logic

```text
function setQuantity(actor, cartId, sku, quantity, expectedVersion, requestKey):
    require 0 <= quantity <= MAX_QUANTITY_PER_SKU
    requestHash = hash(cartId, sku, quantity, expectedVersion)

    transaction on shard(cartId):
        prior = idempotency.get(cartId, actor.key, requestKey)
        if prior exists:
            require prior.requestHash == requestHash
            return prior.response

        cart = carts.getForUpdate(cartId)
        require cart.state == ACTIVE and mayMutate(actor, cart)
        require cart.version == expectedVersion
        require quantity == 0 or validSkuShape(sku)

        if quantity == 0: items.delete(cartId, sku)
        else: items.upsert(cartId, sku, quantity, now)
        require items.count(cartId) <= MAX_DISTINCT_ITEMS

        cart.version += 1
        cart.updatedAt = now
        cart.expiresAt = now + ACTIVE_CART_TTL
        response = snapshotCurrentCart(cart)
        idempotency.insert(requestKey, requestHash, response, RETRY_TTL)
        outbox.insert(CartChanged(cart.id, cart.version, sku, quantity))
    cache.invalidateIfOlder(cartId, response.version)
    return response
```

`If-Match` mismatch returns 409 with current cart, enabling the client to reapply
intent. A set-quantity command is preferable to increment because retries and
multi-device reconciliation are unambiguous. If increment is offered, idempotency is
mandatory.

## 8. Guest-to-user merge logic

Merge policy must be explicit. A common choice is union by SKU with capped sum (or
maximum, depending product), preserve the earliest added time, keep destination
selection, and revalidate all promotions later.

```text
function mergeGuestCart(user, guestId, destinationId, requestKey):
    lockIds = sort([guestId, destinationId])
    transaction locking carts in lockIds order:
        if mergeIdempotency.exists(user.id, requestKey): return prior
        guest = carts.getForUpdate(guestId)
        dest = carts.getForUpdate(destinationId)
        require guest.state == ACTIVE and guest.ownerUserId == null
        require validGuestCapability(user.loginSession, guestId)
        require dest.state == ACTIVE and dest.ownerUserId == user.id

        for sourceItem in items.list(guestId):
            target = items.get(destinationId, sourceItem.sku)
            mergedQty = min(MAX_QUANTITY_PER_SKU,
                            sourceItem.quantity + (target?.quantity ?? 0))
            items.upsert(destinationId, sourceItem.sku, mergedQty,
                         minAddedAt(sourceItem, target))
        enforceDistinctItemLimitDeterministically(destinationId)
        mark promotions PENDING_REVALIDATION
        dest.version += 1
        guest.state = MERGED
        guest.mergedIntoId = dest.id
        guest.version += 1
        record result and outbox in same transaction
    rotate/delete guest capability token
    return destination snapshot
```

If two carts live on different shards, route all active carts for one user/merge
session to a home shard, or use a merge-intent saga: freeze source, copy idempotently,
mark merged, then unfreeze destination. Never delete source before destination commit.

## 9. Multi-device conflict semantics

Optimistic cart version prevents silent lost updates. Clients receiving 409 fetch the
new version and decide whether to reapply their operation. Because commands set an
absolute quantity, concurrent changes to different SKUs can be safely auto-rebased;
same-SKU changes require last explicit intent/product UX rather than hidden arithmetic.

For offline clients, retain a unique operation ID and server-known base version.
Replay operations in client order, surfacing rejected limits/deleted SKUs. Do not use
generic last-write-wins timestamps from untrusted device clocks.

## 10. Price, promotions, and stock

Cart items store an observed price/version only for display/change explanation. Read
decoration may show cached availability, but neither is a promise. At checkout:

```text
for item in immutableSnapshot.items:
    product = catalog.requirePurchasable(item.sku, snapshot.market)
    quote = pricing.quote(product, user, quantity, now)
    promotion = promotions.evaluate(snapshot.codes, fullBasket, user, quote)
    reservation = inventory.reserve(item.sku, quantity,
                                    checkoutId, expiresAt, idempotencyKey)
```

The resulting quote/reservation versions are stored with the order draft. If price
or quantity changes beyond policy, return a reconfirmation response. Compensate all
acquired reservations if checkout aborts.

## 11. Checkout snapshot and cart lifecycle

```text
function createCheckoutSnapshot(actor, cartId, expectedVersion, requestKey):
    transaction:
        prior = idempotency.get(cartId, actor.key, requestKey)
        if prior exists: return prior
        cart = carts.getForUpdate(cartId)
        require mayMutate(actor, cart) and cart.state == ACTIVE
        require cart.version == expectedVersion and items.count(cartId) > 0
        snapshot = snapshots.insertImmutable(cart, items.list(cartId),
                                             promotions.list(cartId))
        remember idempotency and emit CheckoutStarted(snapshot.id)
    return snapshot
```

Snapshot creation need not freeze shopping: user may keep editing cart version N+1
while checkout uses snapshot N. Order completion conditionally marks the relevant
cart/snapshot converted; it must not erase newer user additions. Product policy may
instead fork a fresh cart after checkout.

## 12. Cache and storage scaling

- Cache a complete serialized cart under `(cart_id, version)` or use compare-version
  writes; never allow an old fill to overwrite a newer cached version.
- Cache-aside reads verify owner/token and decorate separately so catalog churn does
  not rewrite carts.
- Partition by hash(cart ID), split logical partitions, and replicate across zones.
- Keep per-user active-cart mapping in an identity directory with compare-and-set.
- Large/bot carts have strict item/byte limits; do not let one row exceed database or
  cache-safe values.

## 13. Expiration and cleanup

Maintain a coarse time-bucket expiry index rather than one timer per cart. Worker
claims due entries and conditionally expires only if stored `expires_at` is still due
and version/state match; a recent mutation makes the stale expiry entry harmless.
Write a tombstone/outbox event, remove cache/projections, then hard-delete after audit/
recovery retention. Checkout snapshots have their own legal/business TTL.

## 14. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client times out after commit | Retry same key returns committed response |
| Concurrent device update | One version wins; other receives 409/current cart |
| Cache fails or is stale | Read authoritative store; version blocks regression |
| Merge crashes | Atomic transaction or resumable freeze/copy saga preserves source |
| Catalog/pricing unavailable on cart read | Show saved SKUs/observed data as stale; cart still usable |
| Inventory unavailable at checkout | Do not promise order; retry/release prior reservations |
| Expiry event races update | Conditional state/version/expiry prevents deletion |
| Outbox consumer duplicates | Cart/version idempotency protects projections |
| Shard region fails | Promote fenced replica; reject split-brain cart writes |

## 15. Security and privacy

Authorize owner on every cart/snapshot; use high-entropy anonymous IDs plus signed,
short-lived, HttpOnly/SameSite tokens and rotate at login. Prevent cart fixation,
token enumeration, CSRF, SKU/quantity/promotion abuse, and price tampering. Encrypt
data, minimize address/payment data (these do not belong in cart), audit merges/
checkout/admin access, and apply retention, deletion, residency, legal hold, and
account closure to carts, snapshots, events, caches, analytics, and backups.

## 16. Observability

Track read/update/merge/snapshot latency/errors, version conflicts and retries,
idempotency replay/hash mismatch, cart/item sizes, hot shards, cache hit/version
regression, active/expired carts, expiry lag, merge caps/dropped items, decoration
failures, observed-to-checkout price/stock changes, snapshot-to-order conversion,
abandonment, outbox lag, and reconciliation divergence.

State-machine/property tests reorder duplicate updates, merge, expiry, and order
events and assert invariants. Load-test hot/bot carts and login bursts. Chaos tests
kill cache/store/merge/expiry/outbox dependencies; reconciliation checks item limits,
merged-cart links, snapshot immutability, and cache/store version consistency.

## 17. Implementation path

1. **MVP:** strongly consistent cart/items, set quantity, optimistic version,
   idempotency, owner/anonymous authorization, and authoritative checkout snapshot.
2. **Lifecycle:** guest merge, multi-device conflict UX, TTL index/tombstones, cache,
   catalog decoration, promotion references, outbox, and reconciliation.
3. **Scale:** logical sharding, hot-cart limits, regional routing, checkout pricing/
   inventory saga, analytics, and graceful dependency degradation.
4. **Hardening:** failover fencing, security/privacy lifecycle, load/chaos/property
   tests, restore drills, runbooks, and SLO dashboards.

## 18. Final design

Store each cart as an authoritative versioned aggregate and accept idempotent absolute
item mutations under optimistic concurrency. Deterministic guest merge preserves both
sources without duplicate effects. Immutable checkout snapshots cleanly separate a
mutable wish-to-buy list from authoritative pricing, promotions, inventory, and order
creation. Version-aware caches, conditional expiry, tombstones, and a recoverable
outbox preserve correctness across retries, devices, failures, and lifecycle events.
