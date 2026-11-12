← [Previous: Relational Databases](./relational.md) | [Home](../README.md) | [Next: Caching →](./caching.md)

---

# NoSQL Databases

NoSQL databases trade relational features (joins, strict schema, ACID everywhere) for scale, flexibility, or speed. Choose based on your access patterns, not popularity.

---

## Choosing a NoSQL Database

| Use case | Database | Reason |
|----------|---------|--------|
| Session store, rate limiting, ephemeral data | Redis | Sub-millisecond, TTL support |
| User profiles, product catalog (flexible schema) | DynamoDB / MongoDB | Schemaless, fast by primary key |
| Real-time sync (mobile/web) | Firestore | Live updates, offline support |
| Event sourcing, audit logs (append-heavy) | DynamoDB | Pay-per-request, infinite scale |
| Search + filtering | Elasticsearch / OpenSearch | Full-text, facets, geo |
| Time series (metrics, IoT) | TimescaleDB / InfluxDB | Optimized for time-series queries |
| Wide-column (write-heavy, high throughput) | Cassandra / Bigtable | Horizontal write scale |

---

## DynamoDB

### Data Modeling (Single-Table Design)

```python
# DynamoDB: access patterns drive the data model
# Design around: what queries do you need? Then model PK/SK accordingly.

# Entity types stored in one table:
# USER: PK=USER#<user_id>,  SK=PROFILE
# ORDER: PK=USER#<user_id>, SK=ORDER#<order_id>
# PRODUCT: PK=PRODUCT#<product_id>, SK=METADATA

import boto3
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("my-app-table")


def create_order(user_id: str, order_id: str, total_cents: int, items: list) -> dict:
    """Write an order record with idempotent put."""
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "PK": f"USER#{user_id}",
        "SK": f"ORDER#{order_id}",
        "GSI1PK": f"ORDER#{order_id}",  # GSI for direct order lookup
        "GSI1SK": f"USER#{user_id}",
        "entity_type": "ORDER",
        "order_id": order_id,
        "user_id": user_id,
        "status": "pending",
        "total_cents": total_cents,
        "items": items,
        "created_at": now,
        "updated_at": now,
    }
    logger.info("Creating order", extra={"user_id": user_id, "order_id": order_id})
    table.put_item(
        Item=item,
        ConditionExpression="attribute_not_exists(PK)",  # Idempotent — fail if already exists
    )
    return item


def get_user_orders(user_id: str, limit: int = 20, last_key: Optional[dict] = None) -> dict:
    """Get paginated orders for a user, newest first."""
    logger.info("Fetching user orders", extra={"user_id": user_id, "limit": limit})
    kwargs = {
        "KeyConditionExpression": "PK = :pk AND begins_with(SK, :prefix)",
        "ExpressionAttributeValues": {
            ":pk": f"USER#{user_id}",
            ":prefix": "ORDER#",
        },
        "ScanIndexForward": False,  # Newest first (SK is ORDER#timestamp)
        "Limit": limit,
    }
    if last_key:
        kwargs["ExclusiveStartKey"] = last_key

    from boto3.dynamodb.conditions import Key
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"USER#{user_id}") & Key("SK").begins_with("ORDER#"),
        ScanIndexForward=False,
        Limit=limit,
        **({"ExclusiveStartKey": last_key} if last_key else {}),
    )
    return {
        "items": response["Items"],
        "next_key": response.get("LastEvaluatedKey"),
    }


def update_order_status(
    user_id: str,
    order_id: str,
    new_status: str,
    expected_status: str,
) -> None:
    """Optimistic locking: only update if current status matches expected."""
    logger.info(
        "Updating order status",
        extra={"order_id": order_id, "from": expected_status, "to": new_status},
    )
    table.update_item(
        Key={"PK": f"USER#{user_id}", "SK": f"ORDER#{order_id}"},
        UpdateExpression="SET #status = :new_status, updated_at = :now",
        ConditionExpression="#status = :expected",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":new_status": new_status,
            ":expected": expected_status,
            ":now": datetime.now(timezone.utc).isoformat(),
        },
    )
```

### DynamoDB Table + GSI (Terraform)

```hcl
resource "aws_dynamodb_table" "main" {
  name         = "my-app-table"
  billing_mode = "PAY_PER_REQUEST"   # On-demand; use PROVISIONED for predictable traffic
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }
  attribute {
    name = "GSI1PK"
    type = "S"
  }
  attribute {
    name = "GSI1SK"
    type = "S"
  }

  # GSI: look up orders directly by order ID
  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb.arn
  }

  tags = {
    service     = "my-app"
    environment = "production"
  }
}
```

---

## MongoDB (Atlas)

```python
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

MONGO_URI = os.environ["MONGODB_URI"]  # mongodb+srv://...

client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client.get_database("my_app")
products_collection = db.get_collection("products")


async def get_product(product_id: str) -> Optional[dict]:
    """Fetch a single product by ID with read preference from secondary."""
    logger.debug("Fetching product", extra={"product_id": product_id})
    doc = await products_collection.find_one(
        {"_id": product_id},
        {"_id": 1, "name": 1, "price_cents": 1, "category": 1, "in_stock": 1},
    )
    if doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


async def search_products(
    category: str,
    max_price_cents: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Paginated product search with optional price filter."""
    query: dict = {"category": category, "in_stock": True}
    if max_price_cents is not None:
        query["price_cents"] = {"$lte": max_price_cents}

    skip = (page - 1) * page_size
    logger.debug("Searching products", extra={"category": category, "page": page})

    cursor = products_collection.find(query).sort("price_cents", 1).skip(skip).limit(page_size)
    items = await cursor.to_list(length=page_size)
    total = await products_collection.count_documents(query)

    return {
        "items": [{**doc, "id": str(doc.pop("_id"))} for doc in items],
        "total": total,
        "page": page,
        "pages": (total + page_size - 1) // page_size,
    }
```

### MongoDB Index Creation

```javascript
// Run in mongo shell or via mongosh
use my_app

// Compound index for product search
db.products.createIndex(
  { category: 1, price_cents: 1, in_stock: 1 },
  { name: "category_price_stock", background: true }
)

// Text index for search
db.products.createIndex(
  { name: "text", description: "text" },
  { name: "text_search", weights: { name: 10, description: 1 } }
)

// TTL index for expiring sessions
db.sessions.createIndex(
  { created_at: 1 },
  { expireAfterSeconds: 86400, name: "session_ttl" }
)

// Explain a query
db.products.find({ category: "electronics", price_cents: { $lte: 10000 } })
  .explain("executionStats")
```

---

## DynamoDB vs MongoDB vs PostgreSQL

| Factor | DynamoDB | MongoDB | PostgreSQL |
|--------|---------|---------|-----------|
| **Schema** | Schemaless | Schemaless | Strict schema |
| **Queries** | By PK only (GSI for more) | Rich queries, aggregations | Full SQL + JOINs |
| **Scale** | Infinite (horizontal) | Horizontal (sharding) | Vertical (read replicas) |
| **Transactions** | Up to 25 items | Multi-document ACID | Full ACID |
| **Ops overhead** | Zero (serverless) | Moderate (Atlas) | High (self-managed) |
| **Cost model** | Per request | Instance + storage | Instance + storage |
| **Best for** | High-scale, simple lookups | Flexible documents, search | Complex queries, reporting |

---

## References

- [DynamoDB Developer Guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/)
- [DynamoDB Single-Table Design](https://www.alexdebrie.com/posts/dynamodb-single-table/)
- [MongoDB documentation](https://www.mongodb.com/docs/)
- [Firestore documentation](https://cloud.google.com/firestore/docs)

---

← [Previous: Relational Databases](./relational.md) | [Home](../README.md) | [Next: Caching →](./caching.md)
