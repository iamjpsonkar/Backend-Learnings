← [Previous: Cloud SQL](./cloud-sql.md) | [Home](../../README.md) | [Next: Memorystore →](./memorystore.md)

---

# Cloud Firestore

Firestore is a serverless, horizontally scaling NoSQL document database. It supports real-time listeners, ACID transactions, and strong consistency. The native mode is the recommended offering.

---

## Firestore vs Datastore vs Firebase Realtime DB

| Feature | Firestore (Native) | Datastore | Firebase RT DB |
|---------|-------------------|-----------|---------------|
| Data model | Documents/Collections | Entities/Kinds | JSON tree |
| Real-time listeners | Yes | No | Yes |
| Transactions | Yes (multi-document) | Yes | Limited |
| Offline support | Yes (mobile) | No | Yes |
| Pricing | Per document op | Per entity op | Per GB |

---

## Data Model

```
Collection: orders
  Document: order_12345
    Fields:
      customerId: "cust_001"
      total: 99.99
      status: "pending"
      items: [...]             ← array
      address: {city: "NY"}   ← map
      createdAt: Timestamp
  Document: order_12346
    ...
  SubCollection: items
    Document: item_001
      ...
```

---

## Creating a Database

```bash
PROJECT="my-app-prod-123456"

# Create Firestore database (one per project in native mode)
gcloud firestore databases create \
    --project=$PROJECT \
    --location=us-central \
    --type=firestore-native \
    --delete-protection=true

# List databases
gcloud firestore databases list --project=$PROJECT

# Create a named database (for multiple databases per project — GA)
gcloud firestore databases create \
    --project=$PROJECT \
    --database=analytics \
    --location=us-central \
    --type=firestore-native
```

---

## Python SDK — CRUD Operations

```python
import os
import logging
from datetime import datetime, UTC
from typing import Optional
from google.cloud import firestore
from google.api_core.exceptions import NotFound, AlreadyExists

logger = logging.getLogger(__name__)

PROJECT = os.environ["GCP_PROJECT"]

# Client uses ADC automatically (Workload Identity on GKE, SA key locally)
db = firestore.AsyncClient(project=PROJECT)


async def create_order(order_id: str, order: dict) -> dict:
    """Create an order document."""
    doc_ref = db.collection("orders").document(order_id)
    order["createdAt"] = firestore.SERVER_TIMESTAMP
    order["updatedAt"] = firestore.SERVER_TIMESTAMP

    logger.info("Creating order", extra={"order_id": order_id})
    await doc_ref.set(order)
    logger.info("Order created", extra={"order_id": order_id})
    return {"id": order_id, **order}


async def get_order(order_id: str) -> Optional[dict]:
    """Get an order by ID."""
    doc_ref = db.collection("orders").document(order_id)
    logger.debug("Fetching order", extra={"order_id": order_id})

    doc = await doc_ref.get()
    if not doc.exists:
        logger.warning("Order not found", extra={"order_id": order_id})
        return None

    return {"id": doc.id, **doc.to_dict()}


async def update_order_status(order_id: str, status: str) -> None:
    """Update order status field only."""
    doc_ref = db.collection("orders").document(order_id)
    logger.info("Updating order status", extra={"order_id": order_id, "status": status})
    await doc_ref.update({
        "status": status,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })


async def delete_order(order_id: str) -> None:
    """Delete an order document."""
    logger.info("Deleting order", extra={"order_id": order_id})
    await db.collection("orders").document(order_id).delete()


async def query_orders(customer_id: str, status: Optional[str] = None, limit: int = 20) -> list[dict]:
    """Query orders for a customer, optionally filtered by status."""
    query = (
        db.collection("orders")
          .where("customerId", "==", customer_id)
          .order_by("createdAt", direction=firestore.Query.DESCENDING)
          .limit(limit)
    )

    if status:
        query = query.where("status", "==", status)

    logger.info("Querying orders", extra={"customer_id": customer_id, "status": status, "limit": limit})
    docs = await query.get()
    results = [{"id": doc.id, **doc.to_dict()} for doc in docs]
    logger.info("Orders query complete", extra={"customer_id": customer_id, "count": len(results)})
    return results


async def batch_create_orders(orders: list[dict]) -> None:
    """Create multiple orders in a single batch (atomic, up to 500 ops)."""
    batch = db.batch()
    for order in orders:
        order_id = order["orderId"]
        doc_ref = db.collection("orders").document(order_id)
        batch.set(doc_ref, {**order, "createdAt": firestore.SERVER_TIMESTAMP})

    logger.info("Committing batch write", extra={"count": len(orders)})
    await batch.commit()
    logger.info("Batch write complete", extra={"count": len(orders)})


async def transfer_funds(from_account: str, to_account: str, amount: float) -> None:
    """Atomic multi-document transaction (debit + credit)."""
    from_ref = db.collection("accounts").document(from_account)
    to_ref = db.collection("accounts").document(to_account)

    logger.info("Starting funds transfer", extra={"from": from_account, "to": to_account, "amount": amount})

    @firestore.async_transactional
    async def run_transaction(transaction, from_ref, to_ref, amount):
        from_snap = await transaction.get(from_ref)
        to_snap = await transaction.get(to_ref)

        from_balance = from_snap.get("balance")
        if from_balance < amount:
            raise ValueError(f"Insufficient funds: {from_balance} < {amount}")

        transaction.update(from_ref, {"balance": firestore.Increment(-amount)})
        transaction.update(to_ref, {"balance": firestore.Increment(amount)})

    transaction = db.transaction()
    await run_transaction(transaction, from_ref, to_ref, amount)
    logger.info("Transfer complete", extra={"from": from_account, "to": to_account, "amount": amount})
```

---

## Indexes

Firestore automatically creates single-field indexes. Composite indexes must be created manually.

```bash
# Create a composite index (required for multi-field queries)
gcloud firestore indexes composite create \
    --project=$PROJECT \
    --collection-group=orders \
    --query-scope=COLLECTION \
    --field-config=field-path=customerId,order=ASCENDING \
    --field-config=field-path=createdAt,order=DESCENDING

# List indexes
gcloud firestore indexes composite list \
    --project=$PROJECT

# Deploy indexes from firestore.indexes.json (Terraform/Firebase approach)
# firebase deploy --only firestore:indexes
```

---

## Security Rules (Firebase-managed)

```
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /orders/{orderId} {
      allow read: if request.auth != null
                   && request.auth.uid == resource.data.customerId;
      allow create: if request.auth != null
                    && request.resource.data.customerId == request.auth.uid;
      allow update: if request.auth != null
                    && resource.data.customerId == request.auth.uid
                    && !request.resource.data.diff(resource.data).affectedKeys()
                       .hasAny(['createdAt', 'customerId']);
      allow delete: if false;  // Never delete orders
    }
  }
}
```

---

## References

- [Firestore documentation](https://cloud.google.com/firestore/docs)
- [Data model](https://cloud.google.com/firestore/docs/data-model)
- [Python client library](https://cloud.google.com/python/docs/reference/firestore/latest)
- [Transactions](https://cloud.google.com/firestore/docs/transaction-data-contention)

---

← [Previous: Cloud SQL](./cloud-sql.md) | [Home](../../README.md) | [Next: Memorystore →](./memorystore.md)
