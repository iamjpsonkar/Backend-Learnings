# 60 System Design Examples

A practice catalog spanning infrastructure, consumer products, commerce,
real-time systems, data platforms, and security. Each prompt identifies a useful
scope, its core design problem, and a failure or scaling question worth exploring.

Use the [system design interview template](../docs/system-design-interview-template.md)
to turn any row into a complete design. Start with the stated scope, quantify the
load, define APIs and data ownership, draw the critical path, and then answer the
failure question.

## Solution index

Each numbered directory contains a design brief and a dedicated `SOLUTION.md`
with concrete components, capacity calculations, request flows, and recovery.

### Core infrastructure

- [URL Shortener](01-url-shortener/)
- [Paste Service](02-paste-service/)
- [Distributed Rate Limiter](03-distributed-rate-limiter/)
- [Unique ID Generator](04-unique-id-generator/)
- [Distributed Cache](05-distributed-cache/)
- [Layer 7 Load Balancer](06-layer-7-load-balancer/)
- [Service Discovery](07-service-discovery/)
- [Configuration Service](08-configuration-service/)
- [Distributed Task Scheduler](09-distributed-task-scheduler/)
- [API Gateway](10-api-gateway/)

### Communication and collaboration

- [One-to-One Chat](11-one-to-one-chat/)
- [Group Chat](12-group-chat/)
- [Presence Service](13-presence-service/)
- [Push Notification Platform](14-push-notification-platform/)
- [Email Delivery Service](15-email-delivery-service/)
- [Video Conferencing](16-video-conferencing/)
- [Collaborative Text Editor](17-collaborative-text-editor/)
- [Shared Whiteboard](18-shared-whiteboard/)
- [Calendar Service](19-calendar-service/)
- [Webhook Delivery Platform](20-webhook-delivery-platform/)

### Social, content, and discovery

- [Social News Feed](21-social-news-feed/)
- [Photo-Sharing Platform](22-photo-sharing-platform/)
- [Video-on-Demand Platform](23-video-on-demand-platform/)
- [Live-Streaming Platform](24-live-streaming-platform/)
- [Podcast Platform](25-podcast-platform/)
- [Comment System](26-comment-system/)
- [Search Autocomplete](27-search-autocomplete/)
- [Web Search Engine](28-web-search-engine/)
- [Web Crawler](29-web-crawler/)
- [Recommendation Service](30-recommendation-service/)

### Commerce, finance, and reservations

- [Shopping Cart](31-shopping-cart/)
- [Product Catalog](32-product-catalog/)
- [Inventory Service](33-inventory-service/)
- [Order Management System](34-order-management-system/)
- [Payment Gateway](35-payment-gateway/)
- [Double-Entry Ledger](36-double-entry-ledger/)
- [Digital Wallet](37-digital-wallet/)
- [Ticket Booking](38-ticket-booking/)
- [Hotel Reservation](39-hotel-reservation/)
- [Online Auction](40-online-auction/)

### Mobility, logistics, and location

- [Ride-Hailing Service](41-ride-hailing-service/)
- [Food-Delivery Service](42-food-delivery-service/)
- [Maps and Routing](43-maps-and-routing/)
- [Live Location Sharing](44-live-location-sharing/)
- [Nearby-Place Search](45-nearby-place-search/)
- [Fleet Tracking](46-fleet-tracking/)
- [Package Tracking](47-package-tracking/)
- [Warehouse Fulfillment](48-warehouse-fulfillment/)
- [Navigation ETA Service](49-navigation-eta-service/)
- [Geofencing Platform](50-geofencing-platform/)

### Data and observability

- [Distributed Message Queue](51-distributed-message-queue/)
- [Publish-Subscribe Service](52-publish-subscribe-service/)
- [Stream-Processing Engine](53-stream-processing-engine/)
- [Log Aggregation Platform](54-log-aggregation-platform/)
- [Metrics Platform](55-metrics-platform/)
- [Distributed Tracing Platform](56-distributed-tracing-platform/)
- [Alerting System](57-alerting-system/)
- [Real-Time Analytics Dashboard](58-real-time-analytics-dashboard/)
- [Feature Flag Platform](59-feature-flag-platform/)
- [Experimentation Platform](60-experimentation-platform/)

## Difficulty guide

- **Starter**: one dominant request path and a small number of storage choices.
- **Intermediate**: asynchronous workflows, partitioning, or consistency trade-offs.
- **Advanced**: multi-region state, ordering, isolation, or specialized algorithms.

## Core infrastructure

| # | Example | Level | Scope and design focus | Failure or scaling question |
| ---: | --- | --- | --- | --- |
| 1 | URL shortener | Starter | Create aliases, redirect quickly, support expiration and custom keys; compare random IDs, hashing, and counters. | How do you prevent hot aliases and redirect loops? |
| 2 | Paste service | Starter | Store immutable text, optional expiration, visibility controls, and syntax metadata. | How are abusive content and oversized pastes isolated? |
| 3 | Distributed rate limiter | Intermediate | Enforce per-user, tenant, and endpoint quotas with token bucket or sliding windows. | What happens when the shared counter store is unavailable or regions disagree? |
| 4 | Unique ID generator | Intermediate | Produce sortable, collision-free IDs across workers and regions without a central bottleneck. | How does the design handle clock rollback and exhausted worker IDs? |
| 5 | Distributed cache | Advanced | Support partitioning, replication, TTL, eviction, and cache-aside operations. | How do rebalancing and node failure avoid a cache stampede? |
| 6 | Layer 7 load balancer | Advanced | Route HTTP traffic using health, locality, weights, retries, and connection reuse. | When can retries amplify an outage or duplicate a request? |
| 7 | Service discovery | Intermediate | Register instances, publish health, resolve services, and remove stale endpoints. | How quickly should a partitioned instance disappear from discovery? |
| 8 | Configuration service | Intermediate | Version, validate, audit, and distribute dynamic configuration to large fleets. | How do clients remain safe during a bad rollout or control-plane outage? |
| 9 | Distributed task scheduler | Advanced | Schedule one-time and recurring jobs with leases, retries, priorities, and idempotency. | How do you prevent duplicate execution after a worker or coordinator crash? |
| 10 | API gateway | Intermediate | Centralize routing, authentication, quotas, transformations, and request observability. | How do you keep the gateway from becoming a latency and availability bottleneck? |

## Communication and collaboration

| # | Example | Level | Scope and design focus | Failure or scaling question |
| ---: | --- | --- | --- | --- |
| 11 | One-to-one chat | Intermediate | Deliver messages across devices with history, offline sync, receipts, and ordering per conversation. | Can a retry create duplicates or reorder messages? |
| 12 | Group chat | Advanced | Add membership history, fan-out, mentions, moderation, and large public groups. | When should delivery fan out on write versus on read? |
| 13 | Presence service | Intermediate | Track online, idle, and last-seen state using heartbeats and expiring sessions. | How do network partitions affect the meaning of "online"? |
| 14 | Push notification platform | Intermediate | Accept events, apply preferences, select providers, retry, and record outcomes. | How are provider throttling and duplicate delivery contained? |
| 15 | Email delivery service | Advanced | Queue transactional mail, manage templates, reputation, bounces, suppression, and callbacks. | How do you preserve tenant isolation when one sender is abusive? |
| 16 | Video conferencing | Advanced | Establish rooms, signal peers, route media through SFUs, and adapt bitrate. | How does a regional media-node failure affect an active meeting? |
| 17 | Collaborative text editor | Advanced | Synchronize concurrent edits with operational transformation or CRDTs and retain versions. | How do offline clients merge without losing intent? |
| 18 | Shared whiteboard | Advanced | Synchronize strokes, objects, cursors, layers, and snapshots for many participants. | How do you bound replay time for a long-lived board? |
| 19 | Calendar service | Intermediate | Manage recurring events, attendees, time zones, reminders, and availability queries. | How are series edits and daylight-saving changes represented? |
| 20 | Webhook delivery platform | Intermediate | Sign, queue, retry, rate-limit, and audit outbound tenant callbacks. | How do slow or failing destinations avoid blocking healthy tenants? |

## Social, content, and discovery

| # | Example | Level | Scope and design focus | Failure or scaling question |
| ---: | --- | --- | --- | --- |
| 21 | Social news feed | Advanced | Rank posts from a follow graph with fan-out, pagination, freshness, and privacy filters. | How do celebrity accounts avoid write amplification? |
| 22 | Photo-sharing platform | Intermediate | Upload, transform, store, moderate, and serve photos through a CDN. | How is a privacy change enforced against cached media? |
| 23 | Video-on-demand platform | Advanced | Upload, scan, transcode, package, index, authorize, and stream adaptive video. | How do viral videos and failed transcodes affect cost and availability? |
| 24 | Live-streaming platform | Advanced | Ingest live media, transcode renditions, distribute segments, chat, and archive streams. | How do you reduce glass-to-glass latency without sacrificing reliability? |
| 25 | Podcast platform | Intermediate | Ingest feeds, store episodes, distribute audio, track progress, and create analytics. | How are feed polling spikes and duplicate episodes handled? |
| 26 | Comment system | Intermediate | Support threads, votes, moderation, ranking, edits, and cursor pagination. | How do hot threads avoid counter and fan-out bottlenecks? |
| 27 | Search autocomplete | Intermediate | Build prefix suggestions from query streams with ranking, personalization, and filtering. | How quickly can trends update without destabilizing results? |
| 28 | Web search engine | Advanced | Crawl, deduplicate, index, rank, shard, and serve documents at low latency. | How are recrawl freshness and unavailable index shards balanced? |
| 29 | Web crawler | Advanced | Maintain a polite URL frontier, fetch pages, canonicalize links, deduplicate, and retry. | How do traps, huge domains, and frequently changing pages affect scheduling? |
| 30 | Recommendation service | Advanced | Generate candidates, retrieve features, rank, experiment, and collect feedback. | How does the system respond to stale features or a failed model rollout? |

## Commerce, finance, and reservations

| # | Example | Level | Scope and design focus | Failure or scaling question |
| ---: | --- | --- | --- | --- |
| 31 | Shopping cart | Intermediate | Maintain anonymous and signed-in carts, merge sessions, price snapshots, and expiration. | How do concurrent device updates merge predictably? |
| 32 | Product catalog | Intermediate | Store product variants, attributes, media, categories, and seller updates for read-heavy traffic. | How is schema flexibility balanced with searchable, validated data? |
| 33 | Inventory service | Advanced | Track stock, reservations, warehouses, expiration, and reconciliation. | How do you prevent overselling during flash sales and retries? |
| 34 | Order management system | Advanced | Coordinate checkout, payment, inventory, fulfillment, cancellation, and returns as a saga. | How are partial failure and out-of-order events repaired? |
| 35 | Payment gateway | Advanced | Authorize, capture, refund, tokenize, route providers, and process callbacks idempotently. | What is the source of truth after an ambiguous provider timeout? |
| 36 | Double-entry ledger | Advanced | Record immutable balanced postings, account balances, reversals, and audit history. | How are concurrency and correction handled without mutating history? |
| 37 | Digital wallet | Advanced | Manage funding, transfers, limits, ledger entries, risk checks, and withdrawals. | How is exactly-once business behavior achieved over at-least-once delivery? |
| 38 | Ticket booking | Advanced | Search events, select seats, place expiring holds, pay, and issue tickets. | How do you serialize demand for the same seat without blocking the venue? |
| 39 | Hotel reservation | Advanced | Search availability and rates, hold inventory, book rooms, and ingest partner updates. | How do stale partner allocations avoid double booking? |
| 40 | Online auction | Advanced | Accept ordered bids, extend closing times, notify participants, and settle winners. | How do regional latency and simultaneous bids affect fairness? |

## Mobility, logistics, and location

| # | Example | Level | Scope and design focus | Failure or scaling question |
| ---: | --- | --- | --- | --- |
| 41 | Ride-hailing service | Advanced | Match riders and drivers, stream locations, price trips, dispatch, and track lifecycle state. | How do you avoid double-dispatch and geographic hot spots? |
| 42 | Food-delivery service | Advanced | Coordinate menus, carts, restaurants, couriers, dispatch, ETA, and order tracking. | How are long-running workflows recovered when a participant goes offline? |
| 43 | Maps and routing | Advanced | Store a hierarchical road graph, ingest traffic, compute routes, and update ETAs. | How do closures invalidate cached paths without global recomputation? |
| 44 | Live location sharing | Intermediate | Ingest mobile updates, apply access rules, expire sessions, and fan out positions. | How do you trade battery life, freshness, precision, and privacy? |
| 45 | Nearby-place search | Advanced | Index geospatial entities, filter by attributes, rank, and paginate stable results. | How do dense city cells and moving entities affect partitioning? |
| 46 | Fleet tracking | Intermediate | Collect device telemetry, show current positions, retain trips, and detect geofence events. | What happens during delayed, duplicated, or out-of-order telemetry? |
| 47 | Package tracking | Intermediate | Ingest carrier scans, model shipment state, estimate delivery, and notify customers. | How do conflicting carrier events reconcile into one customer timeline? |
| 48 | Warehouse fulfillment | Advanced | Allocate stock, release pick waves, route workers, pack, and ship orders. | How is work reassigned after device, worker, or conveyor failure? |
| 49 | Navigation ETA service | Advanced | Combine route geometry, live speeds, incidents, and historical patterns into arrival estimates. | How do you measure and correct systematic ETA bias? |
| 50 | Geofencing platform | Intermediate | Register spatial rules, ingest positions, detect transitions, and deliver actions. | How are boundary jitter and repeated enter/exit notifications suppressed? |

## Data and observability platforms

| # | Example | Level | Scope and design focus | Failure or scaling question |
| ---: | --- | --- | --- | --- |
| 51 | Distributed message queue | Advanced | Partition logs, replicate records, track consumer offsets, retain data, and apply backpressure. | What ordering and durability guarantees survive leader failure? |
| 52 | Publish-subscribe service | Advanced | Match topics, fan out messages, isolate subscriptions, retry, and dead-letter failures. | How does one slow subscription avoid retaining unlimited data? |
| 53 | Stream-processing engine | Advanced | Execute stateful windows, checkpoints, watermarks, joins, and replayable jobs. | How are late events and recovery made deterministic? |
| 54 | Log aggregation platform | Advanced | Collect, buffer, parse, index, retain, search, and control high-cardinality logs. | How does ingestion degrade safely when storage falls behind? |
| 55 | Metrics platform | Advanced | Ingest time series, aggregate, retain, query, dashboard, and downsample metrics. | How do unbounded labels and hot tenants affect cost? |
| 56 | Distributed tracing platform | Advanced | Sample traces, propagate context, ingest spans, build indexes, and query waterfalls. | How do you keep useful rare errors while sampling aggressively? |
| 57 | Alerting system | Intermediate | Evaluate rules, group incidents, deduplicate, route notifications, and manage silences. | How do you prevent alert storms during a broad outage? |
| 58 | Real-time analytics dashboard | Advanced | Ingest events, aggregate dimensions, support fresh queries, and correct late data. | When should results be approximate versus strongly consistent? |
| 59 | Feature flag platform | Intermediate | Evaluate flags locally, distribute changes, target cohorts, audit, and run kill switches. | How do services behave when configuration is stale or unreachable? |
| 60 | Experimentation platform | Advanced | Assign subjects consistently, manage exposure, compute metrics, and guard statistical validity. | How are sample-ratio mismatches and cross-experiment interference detected? |

## Suggested progression

1. Complete examples 1, 2, and 31 to practice APIs, schemas, and basic scaling.
2. Complete examples 3, 11, 20, and 46 to practice distributed state and retries.
3. Complete examples 21, 33, 35, and 51 to practice partitioning and consistency.
4. Complete examples 17, 24, 43, and 53 to practice specialized algorithms and
   real-time architectures.
5. Revisit one design at 10x and 100x scale, changing only components justified by
   a measured bottleneck.

## Expected deliverable for each example

- Explicit scope, assumptions, functional requirements, and measurable SLOs.
- Traffic, storage, bandwidth, and concurrency estimates with units.
- APIs or events, core entities, indexes, ownership, and consistency boundaries.
- A high-level diagram plus one normal and one failure-path walkthrough.
- Partitioning, replication, caching, queuing, security, and observability choices.
- Two important trade-offs, the simplest viable first version, and the next likely
  bottleneck.
