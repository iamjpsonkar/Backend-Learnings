# Microservices Platform — Advanced

**Difficulty**: Advanced
**Profile**: `core apps observability messaging data`
**Time estimate**: 3–5 hours

---

## Scenario

Design and deploy a small but complete microservices platform. Multiple services communicate via HTTP and messaging, share a database layer, and are observable end-to-end.

---

## Setup

```bash
./run.sh start core apps observability messaging data
./run.sh status  # all services healthy
```

---

## Architecture to build

```
Client (curl/browser)
  │
  ▼
Traefik (reverse proxy, port 80)
  │
  ├── /api/orders  → Order Service (sample-api)
  │                      │ async via RabbitMQ
  │                      ▼
  │               Inventory Worker (sample-worker)
  │                      │ reads/writes
  │                      ▼
  │               PostgreSQL (orders + inventory tables)
  │
  └── /         → Frontend (sample-frontend)
```

All services emit traces to Tempo and metrics to Prometheus.

---

## Tasks

### Task 1 — Map the existing services

Before building, inventory what's already running:
- What services exist and what do they do?
- What ports do they expose?
- How do they communicate currently?
- What observability data do they emit?

Draw or write a description of the current state.

### Task 2 — Extend the Order Service

Add a `POST /orders` endpoint to sample-api that:
1. Accepts JSON: `{"item": "laptop", "quantity": 2, "customer_id": "c001"}`
2. Saves to PostgreSQL orders table
3. Publishes `order.created` event to RabbitMQ `lab.events` exchange
4. Returns the created order with an `order_id`

Write the code, build a new Docker image, update the compose config.

### Task 3 — Extend the Worker

Modify sample-worker to consume `order.created` events and:
1. Log the order
2. Update the inventory table in PostgreSQL (decrement stock)
3. If insufficient stock, publish `order.rejected` to `lab.events`
4. If stock OK, publish `order.confirmed`

### Task 4 — Add distributed tracing

Ensure every request generates a trace that spans:
- HTTP request to Order Service
- Database write
- RabbitMQ publish
- Worker pickup
- Worker database write

View the complete trace in Grafana → Explore → Tempo.

### Task 5 — Build a status dashboard

In Grafana, create a dashboard showing:
- Orders created per minute
- Orders confirmed vs rejected ratio
- Worker queue depth (RabbitMQ messages pending)
- End-to-end order processing time (from HTTP to worker complete)
- Error rates for each service

### Task 6 — Inject a failure

Stop the worker while orders are being created:
```bash
docker stop cloud-learnings-lab-sample-worker-1
# Send 10 orders
# Then restart the worker
docker start cloud-learnings-lab-sample-worker-1
```

Verify:
- Orders are queued in RabbitMQ while worker is down
- All queued orders are processed after worker restarts
- The dashboard shows the gap and recovery

### Task 7 — Document the platform

Write a `PLATFORM.md` that documents:
- Architecture diagram (text/ASCII is fine)
- Service responsibilities
- Message flow
- How to add a new service
- How to debug a failed order

---

## Success criteria

- [ ] POST /orders endpoint working with DB persistence and RabbitMQ publish
- [ ] Worker processes events and updates inventory
- [ ] Distributed trace visible in Tempo spanning all services
- [ ] Grafana dashboard shows all 5 metrics
- [ ] Failure injection and recovery verified
- [ ] PLATFORM.md written
