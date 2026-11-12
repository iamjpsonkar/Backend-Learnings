# Complete Solution: Online Auction

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Sellers list an item with start/end, currency, opening price, increment schedule,
optional reserve and anti-sniping rules. Eligible users place direct or proxy maximum
bids, see authoritative current price/winner state, receive live updates, and settle
the winning bid. Support cancellation only under strict policy, disputes, bidder
deposits/limits, and an immutable audit trail.

Targets: accepted/rejected bid decision p99 below 300 ms for admitted bidders, live
update p99 below one second, 99.99% reads and 99.95% bid commands, and deterministic
winner/price under retry/failover. A bid counts only after the auction leader durably
commits it before authoritative end time. One fenced leader orders each auction.

## 2. Capacity estimation

Assume one million concurrent auctions, ten million active viewers, 100,000 aggregate
bids/s normally, and a celebrity auction receiving up to 100,000 attempted bids/s in
its closing seconds.

- Metadata/bid storage is manageable globally; one hot key's serialization/broadcast
  is the difficult dimension.
- At 500 bytes/bid, 100,000 committed bids/s is 50 MB/s before replication and event
  fan-out. Admission may intentionally accept far fewer under product capacity.
- Ten million WebSockets and viewer updates need regional gateways; gateways subscribe
  once per auction and fan out locally rather than one broker message/viewer.
- Retain complete bid/leader/close/settlement evidence for legal/business policy; tier
  closed-auction data to immutable archive.
- Read caches can be stale, but bid acceptance and close never consult them.

## 3. Auction rules and invariants

Rules are immutable after first accepted bid except narrowly authorized cancellation
or disclosed extension policy. Core invariants:

- an auction has one total order `(leader_epoch, sequence)` of committed commands;
- one client bid ID creates at most one bid/result;
- server commit/receipt time under documented rule, not device clock, decides timeliness;
- accepted proxy maxima remain immutable and hidden from other bidders;
- current winner/price are a deterministic fold of accepted bids and rule version;
- close is final only after the leader proves all pre-deadline committed bids applied;
- one winning bid creates at most one settlement/order/payment workflow.

State:

```text
DRAFT -> SCHEDULED -> LIVE -> CLOSING -> CLOSED -> SETTLING -> SETTLED
                    \-> CANCELLED; SETTLING -> PAYMENT_FAILED/DISPUTED
```

## 4. APIs

```text
POST /v1/auctions                         Idempotency-Key
POST /v1/auctions/{id}/publish            If-Match: version
GET  /v1/auctions/{id}
GET  /v1/auctions/{id}/bids?cursor=
POST /v1/auctions/{id}/bids               {maxAmount, clientBidId} Idempotency-Key
POST /v1/auctions/{id}/cancel             If-Match, Idempotency-Key
GET  /v1/auctions/{id}/stream-token
POST /v1/auctions/{id}/settlement-actions Idempotency-Key
```

Money is integer minor units and one auction currency. Return committed sequence,
current public price, whether the caller leads, authoritative end time, and rule
version. Never return other users' proxy maxima. Bound listings, bids/user, bid rate,
amount, increments, stream subscriptions, pagination, and retries.

## 5. Data model

```text
Auction(id, seller_id, item_snapshot_ref, state, currency, opening_amount,
        reserve_amount_ciphertext, increment_rule_version, start_at, end_at,
        extension_window, extension_duration, leader_epoch,
        last_sequence, applied_sequence, current_price, winner_id,
        winner_max, second_max, version)
Bid(id, auction_id, sequence, leader_epoch, bidder_id, max_amount,
    public_price_after, result, received_at, committed_at, client_bid_id,
    risk_decision_id)
BidderMaximum(auction_id, bidder_id, max_amount, first_attained_sequence, version)
AuctionCommand(auction_id, epoch, sequence, command_id, type, payload_hash, result)
Extension(auction_id, sequence, prior_end_at, new_end_at, rule_version)
Settlement(auction_id, winning_bid_id, winner_id, amount, state,
           order_id, payment_intent_id, version)
Inbox(source, external_event_id, payload_hash, processed_at)
Outbox(id, auction_id, sequence, event_type, payload, published_at)
```

Bid history is append-only. `BidderMaximum` and auction summary are synchronous
materialized state rebuildable by replay. Encrypt reserve/proxy maxima and restrict
access; public bid history uses masked identities and disclosed public price changes.

## 6. Architecture

```text
clients -> edge/risk/rate limit -> auction router -> partition leader
                                                   |       |
                                           replicated log  state store/outbox
                                                   |       |
                                       follower replicas   regional event bus
                                                               |
                                              WebSocket gateway groups -> viewers

time service -> durable close scheduler -> same leader command path
closed event -> settlement/order/payment/notification
fraud/identity/deposit services -> eligibility snapshots + post-event review
```

Many auctions share a partition leader normally; migrate/isolate a hot auction to a
dedicated partition before/while live under a fenced handoff protocol. Consensus term
is the leader epoch; quorum commit precedes acknowledgement.

## 7. Step-by-step workflow

1. Seller creates/publishes validated immutable listing/rules; scheduler records start
   and close tasks. Search/cache projects metadata.
2. Bidder authenticates, passes account/KYC/region/deposit/limit/risk checks, and sends
   stable client bid ID plus maximum willingness—not a client-calculated price.
3. Router sends to current auction leader. Leader assigns ordered sequence, rechecks
   LIVE/end/rules/eligibility/idempotency, folds bid into proxy state, and quorum-
   commits command plus result/current state.
4. Only after commit, return decision and publish sequence event. Regional gateways
   coalesce live updates; clients detect sequence gaps and fetch a snapshot/tail.
5. Accepted bid within extension window atomically changes end time according to
   prepublished rule and reschedules versioned close task.
6. Close command through the same ordered log checks end/version and commit watermark,
   computes winner/reserve, commits CLOSED, and emits one settlement request.
7. Settlement authorizes/captures winner, creates order/fulfillment, pays seller after
   policy, or follows explicit nonpayment/second-chance process without silently
   rewriting auction history.

## 8. Direct bidding logic

For a simple ascending auction without proxy maxima:

```text
function applyDirectBid(state, bidder, amount, command):
    require state.state == LIVE
    require command.serverReceivedAt < state.endAt
    minimum = state.hasBid ? state.currentPrice + increment(state.currentPrice)
                           : state.openingAmount
    require amount >= minimum
    state.currentPrice = amount
    state.winnerId = bidder.id
    state.winningBidId = command.bidId
    maybeExtend(state, command)
    return ACCEPTED
```

All bidders see exact amount. Ties cannot occur in committed order if new amount must
strictly exceed minimum. The remaining design uses proxy bidding, which has additional
tie/price semantics.

## 9. Proxy bidding algorithm

Each bidder submits/raises a hidden maximum. Current winner is highest maximum; equal
maximum ties go to the bidder whose maximum first reached that amount at lower sequence.
Public price is the smallest incremented price needed to beat the second-highest maximum,
capped at winner's maximum and never below opening price.

```text
function recomputeProxyState(allBidderMaxima, opening, incrementRule):
    ranked = sort maxima by (maxAmount DESC, firstAttainedSequence ASC, bidderId ASC)
    leader = ranked[0]
    runner = ranked[1] if exists else null

    if runner == null:
        publicPrice = opening
    else if runner.maxAmount == leader.maxAmount:
        publicPrice = leader.maxAmount
    else:
        publicPrice = min(leader.maxAmount,
                          runner.maxAmount + increment(runner.maxAmount, incrementRule))
    publicPrice = max(opening, publicPrice)
    return leader.bidderId, publicPrice, leader.maxAmount, runner?.maxAmount
```

```text
function applyProxyBid(state, bidder, submittedMax, sequence):
    own = maxima.get(bidder.id)
    if own exists:
        require submittedMax > own.maxAmount
    else:
        require submittedMax >= state.nextDisplayedMinimum

    maxima.upsert(bidder.id, submittedMax,
                  firstAttainedSequence=sequence)
    state.winner, state.currentPrice, state.winnerMax, state.secondMax =
        recomputeProxyState(maxima, state.openingAmount, state.incrementRule)
```

Define increment boundary/tie/reserve/display behavior precisely in product rules and
test it exhaustively. The bidder may lead while public price is below their max.

## 10. Core ordered bid command

```text
function placeBid(actor, auctionId, command):
    requestHash = hash(command.clientBidId, command.maxAmount)
    leader.requireCurrentEpoch()

    within leader's serialized state machine:
        prior = commandLog.get(auctionId, actor.id, command.clientBidId)
        if prior exists:
            require prior.requestHash == requestHash
            return prior.result
        state = auctionState.current(auctionId)
        now = trustedTime.now()
        require state.state == LIVE and now < state.endAt
        require eligibilitySnapshotValid(actor, state)
        require validMoneyAndBidLimits(command, state)

        sequence = state.lastSequence + 1
        next = copy(state)
        result = applyProxyBid(next, actor, command.maxAmount, sequence)
        if result.accepted: maybeExtend(next, now, sequence)
        record = AuctionCommand(auctionId, epoch, sequence,
                                command.clientBidId, requestHash, result, next)
        consensusLog.appendAndWaitForQuorum(record)
        stateStore.apply(record)
        outbox.appendSameDurableBatch(record.publicEvent)
    return result with sequence/currentPrice/endAt
```

Implementation can use one serializable database row/transaction per auction at lower
scale or a replicated state-machine log at high scale. The correctness requirements
are identical: one order, durable before ACK, fenced ownership, deterministic fold.

## 11. Time and anti-sniping extension

Use synchronized server monotonic/wall time and define whether eligibility is leader
receipt or durable commit before `end_at`; durable commit is easiest to audit. Client
clock/network delay gives no authority. Display server time offset and encourage early bids.

```text
function maybeExtend(state, acceptedAt, sequence):
    if state.endAt - acceptedAt <= state.extensionWindow:
        newEnd = max(state.endAt, acceptedAt + state.extensionDuration)
        if newEnd > state.endAt:
            append Extension(sequence, state.endAt, newEnd)
            state.endAt = min(newEnd, state.maximumExtendedEnd)
            state.closeGeneration += 1
```

Every extension is committed with the bid. Old timer carries prior generation/end and
becomes a no-op. Rules can extend repeatedly or once but are fixed before bidding.

## 12. Correct close algorithm

```text
function closeAuction(auctionId, expectedGeneration, scheduledEnd):
    route command to current leader
    within ordered state machine:
        state = current(auctionId)
        if state.state != LIVE: return existing terminal result
        if state.closeGeneration != expectedGeneration or state.endAt != scheduledEnd:
            return STALE_TIMER
        if trustedTime.now() < state.endAt: reschedule and return
        require state.appliedSequence == consensusLog.committedSequence(auctionId)

        state.state = CLOSED
        if state.winnerId exists and state.winnerMax >= state.reserveAmount:
            state.result = SOLD
            settlement.insertUnique(auctionId, state.winningBidId, PENDING)
        else:
            state.result = RESERVE_NOT_MET
        append durable AuctionClosed and settlement outbox
```

Closing goes through the same log, after all earlier commands. Failover leader replays
to committed sequence before accepting close. A hidden reserve determines sale but
must not leak through error/timing behavior beyond published product semantics.

## 13. Hot-auction scaling

- Put bid writes through one ordered leader but batch log replication and state updates;
  proxy fold is O(log bidders) using top maxima, not full sort per bid.
- Use admission tokens/fair queue when attempted rate exceeds safely durable throughput;
  reject early with explicit overload rather than accepting uncommitted requests.
- Rate-limit bidder/account/device/network and collapse duplicate retries by client ID.
- Regional edges terminate connections and forward one stream subscription per auction;
  coalesce price updates while preserving latest sequence/end.
- Serve auction snapshot/read history from replicas/cache; never route reads through
  leader unnecessarily.
- Pre-isolate scheduled hot auctions and load-test worst closing burst/failover.

Single-auction ordering has a physical throughput limit. Multi-leader “accept now,
resolve later” changes fairness and must not be presented as the same auction contract.

## 14. Live updates and read consistency

Each public event contains auction ID, sequence, public price, masked leader/change,
end time, state, and version. Gateway maintains regional subscription groups and sends
coalesced snapshots with latest sequence. Client seeing a gap fetches `/auction` plus
event tail. WebSocket is advisory; bid response from leader is authoritative.

Bid history pagination uses committed sequence cursor and redacts hidden maxima,
private risk data, and identities per policy. Cache key includes auction version;
closing/removal policy is rechecked before response.

## 15. Settlement and nonpayment

Winner settlement has stable `(auction, winning_bid, generation)` order/payment IDs.
Depending category, preauthorize/deposit/verify payment before bidding, then capture
winning price plus disclosed fees after close. Timeouts remain unknown and reconcile.
Seller payout waits for payment/fulfillment/dispute policy; ledger records buyer,
seller payable, platform fees, tax, refunds, and payout as balanced immutable effects.

If winner fails, policy may cancel, offer to next eligible bidder at a defined amount,
or relist. This is a new audited settlement generation/offer with explicit consent,
not mutation declaring the second bidder was original winner. Release losing deposits/
authorizations idempotently.

## 16. Fraud, abuse, and moderation

Before bids, verify account/KYC/age/region/category eligibility, seller ownership/item
policy, deposits/payment capability, and account limits. Detect shill bidding, bid
shielding, collusive rings, self-bids/related accounts, bot bursts, account takeover,
proxy-limit probing, nonpayment history, seller manipulation, and suspicious cancels.

Risk may reject/challenge before commit or flag after, but removing an accepted bid
must follow published legal/product policy with immutable administrative event—never
silent deletion. Human review, appeals, seller/buyer protection, and evidence retention
are required. Reserve/proxy maxima are especially restricted data.

## 17. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client repeats bid | Client bid ID/hash returns original sequence/result |
| Leader dies before quorum commit | Bid was not acknowledged; retry to new leader |
| Leader dies after commit before response | Retry returns committed result by ID |
| Old leader remains reachable | Consensus epoch/fencing rejects its append |
| Close timer fires after extension | Generation/end mismatch makes it no-op |
| Close races bids | Same ordered log decides exact command order/time rule |
| WebSocket event is lost | Sequence gap reloads snapshot/tail; bid state unaffected |
| Payment times out | Settlement remains UNKNOWN; query/reconcile stable intent |
| Read cache is stale | Bid/close leader remains authoritative |

## 18. Security, privacy, and compliance

Use strong authentication/device risk/step-up, seller/bidder/support/finance roles,
mTLS/service identities, signed events/callbacks, HSM/KMS keys, encrypted proxy/reserve/
PII/payment tokens, nonce/timestamp replay protection, tamper-evident audit, and dual
control for cancellations/manual outcomes. Prevent IDOR, amount/currency overflow,
client-time spoofing, bid replay/enumeration, bot queue bypass, XSS, listing fraud,
credential stuffing, insider max disclosure, and settlement/refund abuse.

Apply auction/gambling/securities/category-specific law where relevant, consumer/resale/
tax/payment obligations, privacy minimization/retention/deletion, residency, sanctions,
legal hold, dispute evidence, incident response, and tested backup/key recovery.

## 19. Observability

Track bid arrival/admission/accept/reject latency, leader queue depth and quorum commit,
commands/auction, idempotency replay/hash mismatch, proxy price/winner invariant,
sequence gaps, hot-partition CPU/network, leader epochs/fencing, WebSocket fan-out lag/
drops/connections, extension count, close timer delay/stale timers, close-to-settlement,
payment unknown/nonpayment, seller payout, fraud/challenge/admin removals, and
reconciliation mismatches by count/value.

Property/model tests permute direct/proxy bids including equal maxima, increment
boundaries, retries, extensions, close races, and replay after leader failure, asserting
same winner/price. Load-test one hot auction plus millions of viewers. Chaos tests kill
leader/quorum/gateways/timers/payment at every boundary. Replay immutable bid log and
compare summary/settlement continuously.

## 20. Implementation path

1. **MVP:** one database/serialized transaction per auction, direct bids, server close
   time, immutable history, idempotency, simple reads, and manual settlement.
2. **Auction correctness:** proxy maxima/tie tests, durable close/extension timers,
   outbox/live sequences, payment/deposit settlement, fraud checks, and reconciliation.
3. **Scale:** replicated/fenced partition leaders, hot-auction isolation/admission,
   batched append, regional gateway fan-out, read replicas/cache, and archive.
4. **Hardening:** legal/security/privacy/fraud lifecycle, model/property/hot-load/chaos
   tests, failover/restore/key drills, runbooks, dashboards, and SLOs.

## 21. Final design

Assign each auction to one fenced, quorum-backed ordered state machine. A bid is
eligible only when the leader validates and durably sequences it before authoritative
end time; retries return the same result. Proxy bidding deterministically folds hidden
per-bidder maxima into winner/public price with explicit tie and increment rules.
Extensions and close are commands in the same log, so timer, bid, and failover races
have one outcome. Regional caches/WebSockets scale viewers, while admission protects
the single hot write key and verified settlement preserves the committed winner.
