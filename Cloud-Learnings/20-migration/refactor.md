← [Previous: Replatform](./replatform.md) | [Home](../README.md) | [Next: Data Migration →](./data-migration.md)

---

# Refactor (Re-architect)

Refactoring redesigns an application to be cloud-native. It requires the most effort but delivers the most long-term value: independent scaling, faster deployments, and elimination of shared mutable state. The two foundational patterns are **strangler fig** (incremental) and **microservices decomposition** (structural).

---

## Strangler Fig Pattern

The strangler fig grows around a tree until the tree is replaced. Applied to software: incrementally route traffic away from the monolith to new services until the monolith is gone. No big-bang rewrite required.

```
Phase 1: Proxy in front        Phase 2: Route feature A        Phase 3: Retire monolith
                                to new service
  Client                          Client                           Client
    │                               │                               │
    ▼                               ▼                               ▼
  Proxy (façade)                  Proxy                           Proxy
    │                             ├── /orders → Orders Service     ├── /orders → Orders Svc
    ▼                             └── /* → Monolith                ├── /users → Users Svc
  Monolith                                                         └── /* → remaining monolith
```

### API Gateway as Strangler Façade

```bash
# Create API Gateway as the entry point in front of the monolith

# Create HTTP API
API_ID=$(aws apigatewayv2 create-api \
    --name prod-facade \
    --protocol-type HTTP \
    --query 'ApiId' --output text)

# Default route → monolith (existing VPC link or ALB)
aws apigatewayv2 create-integration \
    --api-id $API_ID \
    --integration-type HTTP_PROXY \
    --integration-uri "http://internal-monolith-alb.us-east-1.elb.amazonaws.com/{proxy}" \
    --integration-method ANY \
    --payload-format-version "1.0"

MONOLITH_INTEGRATION_ID=$(aws apigatewayv2 get-integrations \
    --api-id $API_ID \
    --query 'Items[0].IntegrationId' --output text)

aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key "ANY /{proxy+}" \
    --target "integrations/$MONOLITH_INTEGRATION_ID"

# Later: add new service integration for extracted route
NEW_SVC_INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id $API_ID \
    --integration-type HTTP_PROXY \
    --integration-uri "http://orders-svc-alb.us-east-1.elb.amazonaws.com/{proxy}" \
    --integration-method ANY \
    --payload-format-version "1.0" \
    --query 'IntegrationId' --output text)

# Route /orders to the new service (overrides the catch-all)
aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key "ANY /orders/{proxy+}" \
    --target "integrations/$NEW_SVC_INTEGRATION_ID"

aws apigatewayv2 create-deployment --api-id $API_ID
```

### Incremental Extraction Process

```python
"""
Strangler fig extraction workflow:
1. Identify bounded context to extract
2. Create new service (same behavior, new deployment)
3. Deploy behind feature flag (dark launch)
4. Verify parity with monolith (shadow mode)
5. Cut over traffic (0% → 1% → 10% → 100%)
6. Remove code from monolith
"""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlags:
    orders_service_enabled: bool = False
    orders_service_traffic_pct: int = 0  # 0-100


class OrdersRouter:
    """
    Shadow/canary router for strangler fig extraction.
    Routes to new service while optionally comparing results.
    """

    def __init__(self, flags: FeatureFlags, monolith_url: str, new_svc_url: str):
        self.flags = flags
        self.monolith_url = monolith_url
        self.new_svc_url = new_svc_url
        self._client = httpx.AsyncClient(timeout=10.0)

    async def get_order(self, order_id: str, request_id: str) -> dict:
        pct = self.flags.orders_service_traffic_pct
        use_new = self.flags.orders_service_enabled and _should_route_to_new(order_id, pct)

        logger.info("Order routing decision", extra={
            "order_id": order_id,
            "request_id": request_id,
            "use_new_service": use_new,
            "traffic_pct": pct,
        })

        if use_new:
            try:
                resp = await self._client.get(f"{self.new_svc_url}/orders/{order_id}")
                resp.raise_for_status()
                result = resp.json()
                logger.info("New service responded", extra={
                    "order_id": order_id, "request_id": request_id,
                    "status": resp.status_code,
                })
                return result
            except Exception as exc:
                # Fallback to monolith on any new service error
                logger.warning("New service failed, falling back to monolith", extra={
                    "order_id": order_id, "request_id": request_id,
                    "error": str(exc),
                })

        # Default: monolith
        resp = await self._client.get(f"{self.monolith_url}/orders/{order_id}")
        resp.raise_for_status()
        return resp.json()


def _should_route_to_new(order_id: str, traffic_pct: int) -> bool:
    """Deterministic hash-based routing for consistent user experience."""
    return (int(order_id[-4:], 16) % 100) < traffic_pct
```

---

## Microservices Decomposition

### Domain-Driven Design Boundaries

```
Monolith domains → Services

  E-commerce monolith
  ├── User management     → users-service (Cognito-backed or custom)
  ├── Product catalog     → catalog-service (DynamoDB + ElasticSearch)
  ├── Order processing    → orders-service (PostgreSQL/RDS)
  ├── Inventory           → inventory-service (DynamoDB with atomic counters)
  ├── Payment             → payments-service (PCI scope, separate AWS account)
  ├── Notifications       → notifications-service (SES + SNS + SQS)
  └── Search              → search-service (OpenSearch Service)

Communication patterns:
  Synchronous (request/response): REST / gRPC via API Gateway or service mesh
  Asynchronous (event-driven):    Amazon EventBridge or SQS/SNS
```

### Event-Driven Decomposition with EventBridge

```python
# Replace direct function calls between modules with events

import boto3
import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)
events = boto3.client("events")

EVENT_BUS_NAME = "prod-app-events"


def publish_event(
    source: str,
    detail_type: str,
    detail: dict[str, Any],
    request_id: str,
) -> str:
    """Publish a domain event to EventBridge."""
    entry = {
        "Source": source,
        "DetailType": detail_type,
        "Detail": json.dumps({**detail, "timestamp": datetime.utcnow().isoformat()}),
        "EventBusName": EVENT_BUS_NAME,
    }

    logger.info("Publishing domain event", extra={
        "source": source,
        "detail_type": detail_type,
        "request_id": request_id,
    })

    response = events.put_events(Entries=[entry])

    if response["FailedEntryCount"] > 0:
        logger.error("Event publish failed", extra={
            "failed_entries": response["Entries"],
            "request_id": request_id,
        })
        raise RuntimeError(f"EventBridge publish failed: {response['Entries']}")

    event_id = response["Entries"][0]["EventId"]
    logger.info("Domain event published", extra={
        "event_id": event_id,
        "source": source,
        "detail_type": detail_type,
        "request_id": request_id,
    })
    return event_id


# Orders service: emit event instead of calling inventory directly
def place_order(order_data: dict, request_id: str) -> dict:
    logger.info("Placing order", extra={
        "order_id": order_data.get("order_id"),
        "request_id": request_id,
    })

    # Save order to database
    order = _save_order(order_data)

    # Emit event — inventory service subscribes and handles stock reservation
    publish_event(
        source="orders-service",
        detail_type="OrderPlaced",
        detail={
            "order_id": order["order_id"],
            "items": order["items"],
            "customer_id": order["customer_id"],
        },
        request_id=request_id,
    )

    logger.info("Order placed and event emitted", extra={
        "order_id": order["order_id"],
        "request_id": request_id,
    })
    return order
```

```bash
# Create EventBridge event bus
aws events create-event-bus \
    --name prod-app-events

# Create rule: OrderPlaced → inventory-service Lambda
aws events put-rule \
    --name route-order-placed \
    --event-bus-name prod-app-events \
    --event-pattern '{
        "source": ["orders-service"],
        "detail-type": ["OrderPlaced"]
    }' \
    --state ENABLED

aws events put-targets \
    --rule route-order-placed \
    --event-bus-name prod-app-events \
    --targets '[{
        "Id": "inventory-service",
        "Arn": "arn:aws:lambda:us-east-1:123456789012:function:inventory-reserve-stock"
    }]'

# Create rule: OrderPlaced → notifications-service SQS queue
aws events put-targets \
    --rule route-order-placed \
    --event-bus-name prod-app-events \
    --targets '[{
        "Id": "notifications-queue",
        "Arn": "arn:aws:sqs:us-east-1:123456789012:notifications-queue"
    }]'
```

### Service Mesh with AWS App Mesh

```yaml
# app-mesh-virtual-service.yaml (deployed via Kubernetes or ECS)
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualService
metadata:
  name: orders-service
  namespace: prod
spec:
  awsName: orders-service.prod.svc.cluster.local
  provider:
    virtualRouter:
      virtualRouterRef:
        name: orders-router

---
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: orders-router
  namespace: prod
spec:
  listeners:
    - portMapping:
        port: 8080
        protocol: http
  routes:
    - name: orders-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: orders-v2
              weight: 10    # 10% to new version
            - virtualNodeRef:
                name: orders-v1
              weight: 90
        retryPolicy:
          httpRetryEvents:
            - server-error
          maxRetries: 3
          perRetryTimeout:
            unit: ms
            value: 2000
```

---

## Database Decomposition

When decomposing a monolith, each service should own its data store.

```
Monolith → single shared DB         After decomposition

  orders table                         Orders DB (RDS PostgreSQL)
  users table         →                Users DB (RDS PostgreSQL)
  products table                       Products DB (DynamoDB)
  inventory table                      Inventory DB (DynamoDB with atomic counters)
  sessions table                       Sessions (ElastiCache Redis)
```

```python
# Saga pattern for distributed transactions
# Problem: order placement needs inventory reservation + payment charge
# Solution: choreography-based saga with compensating transactions

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class OrderSagaState(str, Enum):
    INITIATED = "INITIATED"
    INVENTORY_RESERVED = "INVENTORY_RESERVED"
    PAYMENT_CHARGED = "PAYMENT_CHARGED"
    COMPLETED = "COMPLETED"
    COMPENSATING = "COMPENSATING"
    FAILED = "FAILED"


async def execute_order_saga(order_id: str, order_data: dict) -> dict:
    """
    Choreography saga:
    1. Reserve inventory  → success: emit InventoryReserved
                         → failure: emit OrderFailed (no compensation needed)
    2. Charge payment     → success: emit PaymentCharged
                         → failure: emit PaymentFailed → triggers inventory release
    3. Confirm order      → emit OrderCompleted
    """
    logger.info("Starting order saga", extra={"order_id": order_id})

    state = OrderSagaState.INITIATED
    compensation_actions = []

    try:
        # Step 1: Reserve inventory
        reservation_id = await _reserve_inventory(order_data["items"], order_id)
        compensation_actions.append(("release_inventory", reservation_id))
        state = OrderSagaState.INVENTORY_RESERVED
        logger.info("Inventory reserved", extra={"order_id": order_id, "reservation_id": reservation_id})

        # Step 2: Charge payment
        charge_id = await _charge_payment(order_data["payment"], order_id)
        compensation_actions.append(("refund_payment", charge_id))
        state = OrderSagaState.PAYMENT_CHARGED
        logger.info("Payment charged", extra={"order_id": order_id, "charge_id": charge_id})

        # Step 3: Confirm order
        await _confirm_order(order_id)
        state = OrderSagaState.COMPLETED
        logger.info("Order saga completed", extra={"order_id": order_id})

        return {"order_id": order_id, "state": state}

    except Exception as exc:
        logger.error("Order saga failed, compensating", extra={
            "order_id": order_id, "state": state, "error": str(exc),
        }, exc_info=True)

        state = OrderSagaState.COMPENSATING
        for action, action_id in reversed(compensation_actions):
            try:
                await _compensate(action, action_id, order_id)
                logger.info("Compensation applied", extra={
                    "order_id": order_id, "action": action, "action_id": action_id,
                })
            except Exception as comp_exc:
                logger.error("Compensation failed — requires manual intervention", extra={
                    "order_id": order_id, "action": action, "action_id": action_id,
                    "error": str(comp_exc),
                })

        return {"order_id": order_id, "state": OrderSagaState.FAILED, "error": str(exc)}
```

---

## Refactor Readiness Checklist

- [ ] Bounded contexts identified and agreed by domain experts
- [ ] API contracts defined (OpenAPI specs) before splitting
- [ ] Shared database tables identified and ownership assigned
- [ ] Event schema registry created (Avro/JSON Schema)
- [ ] Distributed tracing instrumented across all services
- [ ] Circuit breakers and retry policies defined
- [ ] Service discovery configured (Route 53 private hosted zone or service mesh)
- [ ] Each service has its own CI/CD pipeline and can deploy independently
- [ ] Rollback procedure tested for each service

---

## References

- [Strangler Fig pattern](https://martinfowler.com/bliki/StranglerFigApplication.html)
- [AWS EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/)
- [AWS App Mesh](https://docs.aws.amazon.com/app-mesh/latest/userguide/)
- [Saga pattern](https://microservices.io/patterns/data/saga.html)

---

← [Previous: Replatform](./replatform.md) | [Home](../README.md) | [Next: Data Migration →](./data-migration.md)
