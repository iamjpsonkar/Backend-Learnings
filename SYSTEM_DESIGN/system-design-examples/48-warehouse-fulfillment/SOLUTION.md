# Complete Solution: Warehouse Fulfillment

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Accept fulfillment orders, choose warehouse/inventory, allocate units, plan pick waves,
lease work to authorized people/robots, verify item/location/container scans, handle
short/damaged substitutions, consolidate, pack, weigh, label, stage, hand off to carrier,
and publish shipment/inventory events. A warehouse keeps operating during WAN outages.

Targets: accepted order-to-allocation p99 below seconds, device scan response below
200 ms on warehouse LAN, tasks visible below one second, 99.99% local operations,
inventory/custody accuracy above 99.99%, and no task executed by two valid assignees.
Control is strongly consistent inside one warehouse; enterprise views are eventual.

## 2. Capacity estimation

Assume 100 warehouses, each handling up to one million item units/day, 250,000 orders/
day, ten scan/events/unit, 5x shift peaks, and 5,000 concurrent devices/site.

- Global peak can exceed 5,800 units/s and roughly 58,000 scan events/s, but warehouse-
  local cells divide it.
- A large site averages 12 units/s, peaks above 60/s and produces hundreds of events/s;
  automation can raise this substantially.
- At 500 bytes/event, 100 million item units/day × ten events is 500 GB/day globally
  before replication/audit/archive.
- Task/container/current inventory remains modest; immutable movement history dominates.
- WAN backlog must hold hours/days of outbound events and inbound order buffer without
  blocking local scans.

## 3. APIs and device protocol

```text
POST /v1/fulfillment-orders               Idempotency-Key
POST /v1/fulfillment-orders/{id}/cancel   Idempotency-Key
GET  /v1/fulfillment-orders/{id}
POST /v1/waves                            Idempotency-Key
POST /v1/tasks/{id}/claim                 Idempotency-Key
POST /v1/tasks/{id}/heartbeat             {leaseEpoch}
POST /v1/tasks/{id}/complete              {leaseEpoch, result} Idempotency-Key
POST /v1/scans/batches                     {deviceSession, events[]}
POST /v1/containers/{id}/seal              Idempotency-Key
POST /v1/shipments/{id}/label              Idempotency-Key
POST /v1/shipments/{id}/handoff            Idempotency-Key
```

Each scan includes stable scan ID, device session/sequence, worker, warehouse, station,
task/lease epoch, barcode type/value, container, quantity, event time and server receive
time. Bound batch/quantity/task lease/offline age and require online confirmation for
high-risk actions such as shipment/controlled inventory.

## 4. State and custody model

```text
FulfillmentOrder: RECEIVED -> ALLOCATED -> RELEASED -> PICKING -> PACKING
                  -> READY_TO_SHIP -> SHIPPED
                  -> CANCELLED | EXCEPTION; may be PARTIALLY_SHIPPED
Task: PENDING -> LEASED -> IN_PROGRESS -> COMPLETED
      LEASED/IN_PROGRESS -> EXPIRED/BLOCKED/CANCELLED
InventoryUnit/quantity: AVAILABLE -> ALLOCATED -> PICKED -> PACKED -> SHIPPED
                                  \-> EXCEPTION/QUARANTINED
Container: EMPTY -> OPEN -> PICKING_COMPLETE -> AT_PACK -> SEALED -> STAGED -> HANDED_OFF
```

Invariants:

- quantities in mutually exclusive custody states conserve physical stock;
- a unit/quantity belongs to at most one active allocation/task/container position;
- task completion is accepted only from current unexpired lease epoch;
- every movement has source/destination, actor/device, reason and unique event ID;
- a sealed package's item manifest, weight, label generation and tracking reference are
  immutable; corrections create a new generation/void prior label.

## 5. Data model

```text
FulfillmentOrder(id, external_order_id, warehouse_id, priority, ship_by,
                 state, version, destination_snapshot, service_requirements)
OrderLine(id, order_id, sku, requested_qty, allocated_qty, picked_qty,
          packed_qty, shipped_qty, cancelled_qty, version)
InventoryBalance(warehouse_id, sku, location_id, lot, disposition,
                 on_hand, allocated, picked, version)
Allocation(id, order_line_id, sku, location_id, lot, quantity, state, version)
Wave(id, warehouse_id, zone, strategy, cutoff, state, planner_version)
Task(id, wave_id, order_id, type, source_location, destination,
     sku, quantity, state, assignee, lease_epoch, lease_until, priority, version)
Container(id, warehouse_id, barcode, type, current_location, state, version)
ContainerItem(container_id, allocation_id, sku, lot, quantity, state)
ScanEvent(id, device_session, sequence, task_id, lease_epoch, type,
          barcode_refs, quantity, event_time, receive_time, result)
Package(id, order_id, container_id, manifest_hash, weight, dimensions,
        label_generation, carrier, tracking_ref, state, version)
Outbox(id, aggregate_id, version, event_type, payload, published_at)
```

Immutable inventory movement/scan audit complements control balances. External order,
carrier and inventory command references are unique/idempotent.

## 6. Architecture

```text
enterprise orders/inventory -> warehouse sync gateway -> warehouse-local cell
                                                     /        |          \
                                              order/inventory planner   outbox spool
                                                       |       |
                                                wave/task queues
                                                       |
handheld/robot -> warehouse Wi-Fi/API -> scan/task state machine -> conveyor/WCS
                                                       |
                                      pack station -> label adapter -> carrier
                                                       |
                                           stage/handoff/shipment

local outbox -> enterprise event bus/order/inventory/tracking when WAN available
physical counts/sensor/container scans -> reconciliation/exception workbench
```

Each site has redundant local compute/database/message broker and identity/config cache.
Enterprise allocates work to site; site owns execution/custody until shipment. Warehouse
control system adapters are isolated from business state.

## 7. Step-by-step workflow

1. Enterprise allocator selects warehouse from available-to-promise, distance/SLA,
   capacity, cutoff, split cost and restrictions; sends stable fulfillment order.
2. Local transaction allocates exact SKU/location/lot quantities or creates shortage
   exception; allocation reduces locally available stock and commits event.
3. Wave planner selects releasable orders before cutoff, groups picks by zone/equipment/
   temperature/hazmat, sequences route and creates tasks/containers atomically.
4. Worker/device claims task lease. At source, scan location, item/lot and container;
   service validates expected task/epoch/quantity and atomically moves allocated stock
   to picked/container custody.
5. Zone picks route containers to consolidation/pack. Pack station scans items/order,
   verifies manifest, packaging rules and weight/dimensions, seals package.
6. Label workflow requests carrier service with stable package generation, stores
   tracking/label checksum, prints, verifies label scan and stages by route/trailer.
7. Handoff scans package plus trailer/carrier manifest, moves custody to SHIPPED once,
   consumes inventory, and publishes enterprise/tracking/billing events.
8. Short/damage/misroute/blocked-station events create explicit exception/reallocation/
   replenishment work; reconciliation compares physical and system custody.

## 8. Inventory allocation logic

```text
function allocateOrder(orderId):
    transaction in warehouse cell:
        order = orders.getForUpdate(orderId)
        require order.state == RECEIVED
        for line in order.lines sorted by sku:
            candidates = inventory.lockCandidateLocations(
                line.sku, disposition=SELLABLE,
                orderedBy=lotExpiryFEFOThenPickCost)
            remaining = line.requestedQty
            for stock in candidates:
                available = stock.onHand - stock.allocated - stock.picked
                qty = min(remaining, available)
                if qty > 0:
                    stock.allocated += qty; stock.version += 1
                    allocations.insert(line, stock.key, qty, ACTIVE)
                    remaining -= qty
                if remaining == 0: break
            if remaining > 0: fail transaction or apply explicit partial/backorder policy
        order.state = ALLOCATED; order.version += 1
        append inventory/order movements and outbox
```

All lines can be all-or-none when order contract requires; partial allocation is an
explicit state. Warehouse-level allocation must be reconciled with enterprise available-
to-promise but local physical/control row decides actual pickable stock.

## 9. Wave planning

Select orders by ship-by deadline, carrier cutoff, priority, aging and inventory
readiness. Enforce zone/equipment/skill/temperature/hazmat/weight/container constraints.
Large static waves minimize travel but delay urgent work; rolling waves every few
minutes adapt to demand and congestion.

```text
score(order) = latenessRisk(order.shipBy, predictedProcessing)
               + priority + aging
               - batchingAffinity(order.zoneSkuFootprint, currentWave)

while wave capacity remains:
    add highest feasible score order
route tasks using warehouse graph, one-way aisles, congestion and equipment
```

Exact vehicle-routing optimization is expensive; use cluster-by-zone/aisle followed by
nearest-neighbor/2-opt and continuous replanning for unclaimed tasks. Planner version/
inputs are recorded for analysis.

## 10. Leased task correctness

```text
function claimTask(worker, taskId, key):
    transaction:
        return prior if key exists
        task = tasks.getForUpdate(taskId)
        require task.state == PENDING or
                (task.state in [LEASED, IN_PROGRESS] and task.leaseUntil < now)
        require workerEligible(worker, task)
        task.leaseEpoch += 1
        task.assignee = worker.id
        task.state = LEASED
        task.leaseUntil = now + LEASE_TTL
        record event/idempotency
    return task with leaseEpoch

function acceptScan(worker, scan):
    transaction:
        if scans.exists(scan.id): return prior result
        task = tasks.getForUpdate(scan.taskId)
        require task.assignee == worker.id
        require task.leaseEpoch == scan.leaseEpoch and task.leaseUntil >= now
        validateExpectedLocationItemLotContainerQuantity(task, scan)
        applySingleCustodyMovement(task, scan)
        scans.insert(scan, ACCEPTED)
        task.progress += scan.quantity; task.version += 1
        if task.progress == task.quantity: task.state = COMPLETED
        append movement/outbox
```

Reassignment increments epoch; old device scans cannot mutate inventory. Heartbeat
extends only current epoch within maximum duration. A lost worker with physical goods
creates exception/count, not blind reissue of the same pick.

## 11. Offline handheld behavior

Device downloads bounded signed work manifest/barcode rules and queues scans with stable
IDs/session sequence/event time. Short Wi-Fi loss can allow only low-risk scans whose
task lease remains locally valid; UI marks them pending. Reconnect uploads in order.
Server deduplicates and verifies current lease/state—offline acceptance by device is not
final inventory truth.

If lease expired/reassigned, quarantine conflicting scan for supervisor physical
resolution rather than discard or double-pick. Packing, shipping, controlled goods,
large quantity adjustments and remote commands require online confirmation. Device
cache/config expires and lost devices revoke session.

## 12. Pick exceptions and replenishment

At source, worker can report short, wrong SKU/lot, damaged, inaccessible or blocked.
Command records evidence, quarantines/deducts observed stock through an adjustment,
releases remaining allocation and invokes alternate-location/warehouse/backorder/cancel
policy. Replenishment tasks move reserve stock to pick face with source/destination
scans and must not race picking beyond available control quantities.

Cycle count compares physical to control by location/SKU/lot. Variance creates audited
adjustment after approval thresholds; never overwrite on-hand silently.

## 13. Container custody and consolidation

Every pick scans destination tote/carton. `ContainerItem` binds allocation and quantity;
container current location changes only through paired scan/conveyor evidence. Zone
handoff/consolidation validates expected child containers/order before merge. Mixing
orders is allowed only with compartment/put-wall identity, never ambiguous loose custody.

Routing events from conveyors may duplicate/reorder; sensor event IDs and container
version conditionally advance. A missing/misrouted container becomes an alert/search
task while order remains blocked, not automatically repicked without count.

## 14. Pack and label logic

Pack station scans order/container and re-verifies expected picked items, lot/serial/
expiry, substitutions, inserts, dangerous/cold-chain rules. Select packaging using
dimensions/weight/protection/cost; measured weight tolerance detects missing/extra items.
Seal commits immutable manifest hash and package generation.

```text
function createLabel(packageId, generation):
    requestKey = "label:" + packageId + ":" + generation
    persist LABEL_REQUESTED with chosen carrier/service before network call
    result = carrier.createShipment(idempotency=requestKey, address, weight, dimensions)
    if definitive: store tracking ref, label bytes checksum, state LABEL_READY
    else: mark LABEL_UNKNOWN and query by requestKey before retry/new carrier
```

Reprint same generation does not create shipment. Address/service/weight change voids
old label where possible and creates next generation with audit.

## 15. Handoff and shipment

Stage location/trailer manifest has capacity, carrier, service and cutoff. Package scan
checks label/tracking/current state and atomically assigns stage/trailer. Carrier
handoff uses dock/trailer seal and package/manifests scans; unique handoff event moves
package/order line quantities `PACKED -> SHIPPED` and inventory `picked -> out` once.

Carrier API acknowledgement alone is not physical handoff; retain custody evidence.
Late carrier rejection/damage opens exception/claim and package tracking, not reversal
of immutable scan history.

## 16. Cancellation and changes

Cancellation is stage-aware. Before release, release allocation. During picking, stop
unclaimed tasks and route picked items to putaway; do not decrement custody magically.
After pack, intercept/void label/unpack or return. After handoff, use carrier intercept/
return flow. Order changes normally create new version/tasks rather than mutate an
active pick manifest. Every compensation has stable ID and physical scan requirements.

## 17. Warehouse-local resilience

Local redundant SQL/consensus, broker, APIs, identity/config cache and adapter spool
continue when enterprise WAN fails. Site accepts only orders/config/inventory versions
already durably synchronized and buffers signed ordered outbox events. WAN recovery
exchanges high-watermarks, deduplicates and reconciles; enterprise must not reassign
the same order to another site without fenced transfer/cancel acknowledgment.

If local quorum fails, stop custody mutations and operate manual safety procedure;
split-brain warehouse inventory is worse than temporary downtime.

## 18. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Device repeats offline scan | Stable scan ID returns original result |
| Task reassigned during offline scan | Lease epoch rejects/quarantines old mutation |
| Worker disappears with items | Expire task but require container/count resolution |
| Conveyor event duplicates | Sensor event ID/container version applies once |
| Label request times out | Query stable provider key; do not create duplicate shipment |
| Pack station blocks | Reroute unsealed compatible containers/tasks |
| WAN to enterprise fails | Local cell continues and spools ordered outbox |
| Local leader partitions | Fencing/quorum rejects unsafe custody writes |
| Carrier handoff duplicates | Unique package/handoff transition ships once |

## 19. Security, safety, and compliance

Authenticate worker/device/robot/station with short sessions and warehouse/role/task
scope; use mTLS, signed config/firmware, encrypted PII/labels, key vault, anti-replay,
rate limits, tamper-evident audit, supervisor approval and field-masked tools. Prevent
barcode spoofing, task/lease theft, IDOR, inventory/label/address tampering, insider
theft, fake shorts/damage, printer rerouting, malicious USB/firmware, CSV injection,
carrier credential leaks and unauthorized remote equipment commands.

Enforce ergonomics/equipment certification, hazmat/cold-chain/lot/serial/expiry rules,
worker safety, privacy/retention/deletion/residency, customs/carrier evidence, legal hold
and incident response. Safety interlocks stay local and must not depend on cloud API.

## 20. Observability

Track orders/units by state and age, allocation success/shortage, wave size/release/
travel efficiency, tasks queued/leased/expired/reassigned/blocked, scans latency/
duplicate/offline/rejected by reason, pick/pack/ship throughput/error, inventory state
conservation/drift/adjustments, containers missing/misrouted/dwell, replenishment, station/
conveyor/printer health, package weight variance, label latency/unknown/void/reprint,
cutoff miss/handoff, WAN spool/enterprise lag, shard leader changes and reconciliation cases.

Property tests reorder duplicate scans, lease expiry/reassignment, cancellation and
handoff and assert quantity/custody invariants. Simulate wave routes/capacity. Load-test
shift start, hot SKU and offline reconnect. Chaos tests kill local API/database/broker/
stations/carrier/WAN at every boundary. Reconciliation counts physical locations/
containers/packages against allocations/tasks/movements and enterprise inventory/orders.

## 21. Implementation path

1. **MVP:** one warehouse, order/allocation, simple FIFO pick tasks, online location/
   item/container scans, pack manifest, one carrier label and handoff.
2. **Reliable operations:** leases/epochs, offline buffered scans/quarantine, outbox/
   dedupe, expiry/exception/replenishment, inventory movements/count reconciliation.
3. **Scale/automation:** rolling waves/routing, zones/put walls/conveyors/robots, pack
   optimization, multiple carriers, local WAN-independent cell and enterprise sync.
4. **Hardening:** worker/device/equipment/security/safety/compliance controls, property/
   simulation/shift-load/chaos tests, local/enterprise restore drills, runbooks and SLOs.

## 22. Final design

Let each warehouse cell own strongly consistent inventory custody and execution. Orders
allocate specific quantities, rolling waves turn them into constrained route-efficient
tasks, and leased epochs ensure only the current assignee can make scans authoritative.
Every item movement is idempotent and binds source, destination and container; offline
scans are verified on reconnect, not blindly trusted. Immutable pack manifests and
generation-based carrier labels lead to a one-time physical handoff, while local
redundancy/outbox spooling keeps the site safe through WAN loss and reconciliation ties
physical stock, tasks, packages, enterprise orders and carriers together.
