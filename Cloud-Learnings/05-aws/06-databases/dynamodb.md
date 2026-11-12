← [Previous: Aurora](./aurora.md) | [Home](../../README.md) | [Next: ElastiCache →](./elasticache.md)

---

# Amazon DynamoDB

DynamoDB is a serverless, fully managed NoSQL database delivering single-digit millisecond performance at any scale. There are no servers to provision, no schemas to migrate, and capacity scales automatically.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Table** | The top-level resource — stores items |
| **Item** | A single record (equivalent to a row) — up to 400KB |
| **Attribute** | A field within an item — can be any type |
| **Partition key (PK)** | Required primary key — determines storage partition |
| **Sort key (SK)** | Optional — combined with PK forms a composite key |
| **GSI** | Global Secondary Index — different PK/SK, queries on any attribute |
| **LSI** | Local Secondary Index — same PK, different SK |
| **RCU** | Read Capacity Unit — 1 strongly consistent read of ≤4KB/s, or 2 eventually consistent |
| **WCU** | Write Capacity Unit — 1 write of ≤1KB/s |
| **DynamoDB Streams** | Change data capture — ordered record of every item change |
| **DAX** | DynamoDB Accelerator — in-memory cache, microsecond reads |

---

## Table Design — Single Table Pattern

DynamoDB works best with a single-table design where all entities share one table and are differentiated by their PK/SK values.

```
PK               SK                 Attributes
───────────────  ─────────────────  ──────────────────────────────
USER#alice        PROFILE            name, email, created_at
USER#alice        ORDER#2026-001     total, status, items
USER#alice        ORDER#2026-002     total, status, items
ORDER#2026-001   ITEM#1             product_id, qty, price
ORDER#2026-001   ITEM#2             product_id, qty, price
PRODUCT#prod-1   METADATA           name, description, price
```

Access patterns supported with the above design:
- Get user profile: `PK = USER#alice, SK = PROFILE`
- Get all orders for a user: `PK = USER#alice, SK begins_with ORDER#`
- Get order items: `PK = ORDER#2026-001, SK begins_with ITEM#`

---

## Creating a Table

```bash
# Create a table with on-demand capacity (pay-per-request)
TABLE_ARN=$(aws dynamodb create-table \
    --table-name MyAppTable \
    --attribute-definitions \
        AttributeName=PK,AttributeType=S \
        AttributeName=SK,AttributeType=S \
        AttributeName=GSI1PK,AttributeType=S \
        AttributeName=GSI1SK,AttributeType=S \
    --key-schema \
        AttributeName=PK,KeyType=HASH \
        AttributeName=SK,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --global-secondary-indexes '[
        {
            "IndexName": "GSI1",
            "KeySchema": [
                {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                {"AttributeName": "GSI1SK", "KeyType": "RANGE"}
            ],
            "Projection": {"ProjectionType": "ALL"}
        }
    ]' \
    --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
    --sse-specification Enabled=true,SSEType=KMS \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
    --deletion-protection-enabled \
    --tags Key=Environment,Value=production Key=Service,Value=my-app \
    --query 'TableDescription.TableArn' --output text)

echo "Table ARN: $TABLE_ARN"

# Wait until active
aws dynamodb wait table-exists --table-name MyAppTable

# Describe the table
aws dynamodb describe-table \
    --table-name MyAppTable \
    --query 'Table.{
        Name:TableName,
        Status:TableStatus,
        ItemCount:ItemCount,
        BillingMode:BillingModeSummary.BillingMode
    }'
```

---

## Reading and Writing Data

### CLI Operations

```bash
TABLE="MyAppTable"

# PutItem — create or replace an item
aws dynamodb put-item \
    --table-name $TABLE \
    --item '{
        "PK":    {"S": "USER#alice"},
        "SK":    {"S": "PROFILE"},
        "name":  {"S": "Alice Smith"},
        "email": {"S": "alice@example.com"},
        "GSI1PK":{"S": "USER"},
        "GSI1SK":{"S": "alice@example.com"},
        "created_at": {"S": "2026-01-01T00:00:00Z"}
    }' \
    --condition-expression "attribute_not_exists(PK)"   # prevent overwrite

# GetItem — exact key lookup (fastest, cheapest)
aws dynamodb get-item \
    --table-name $TABLE \
    --key '{"PK": {"S": "USER#alice"}, "SK": {"S": "PROFILE"}}' \
    --consistent-read

# UpdateItem — atomic attribute update
aws dynamodb update-item \
    --table-name $TABLE \
    --key '{"PK": {"S": "USER#alice"}, "SK": {"S": "PROFILE"}}' \
    --update-expression "SET #n = :name, updated_at = :ts" \
    --condition-expression "attribute_exists(PK)" \
    --expression-attribute-names '{"#n": "name"}' \
    --expression-attribute-values '{":name": {"S": "Alice Johnson"}, ":ts": {"S": "2026-05-31T00:00:00Z"}}' \
    --return-values ALL_NEW

# DeleteItem
aws dynamodb delete-item \
    --table-name $TABLE \
    --key '{"PK": {"S": "USER#alice"}, "SK": {"S": "PROFILE"}}'

# Query — returns items matching PK (and optional SK condition)
aws dynamodb query \
    --table-name $TABLE \
    --key-condition-expression "PK = :pk AND begins_with(SK, :skPrefix)" \
    --expression-attribute-values '{
        ":pk":       {"S": "USER#alice"},
        ":skPrefix": {"S": "ORDER#"}
    }' \
    --scan-index-forward false \    # newest first
    --limit 20 \
    --query 'Items[*]'

# Query on GSI — find user by email
aws dynamodb query \
    --table-name $TABLE \
    --index-name GSI1 \
    --key-condition-expression "GSI1PK = :gsi1pk AND GSI1SK = :email" \
    --expression-attribute-values '{
        ":gsi1pk": {"S": "USER"},
        ":email":  {"S": "alice@example.com"}
    }'
```

### Python SDK Pattern

```python
import boto3
import logging
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Use resource API for cleaner syntax (no explicit type marshaling)
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("MyAppTable")


def get_user_profile(user_id: str) -> dict | None:
    """Fetch a user profile by user ID."""
    logger.info("Fetching user profile: user_id=%s", user_id)
    try:
        response = table.get_item(
            Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
            ConsistentRead=True,
        )
        item = response.get("Item")
        if item:
            logger.debug("User profile found: user_id=%s", user_id)
        else:
            logger.info("User profile not found: user_id=%s", user_id)
        return item
    except ClientError as e:
        logger.error("DynamoDB GetItem failed: user_id=%s error=%s", user_id, e.response["Error"]["Code"])
        raise


def get_user_orders(user_id: str, limit: int = 20) -> list:
    """Fetch recent orders for a user, newest first."""
    logger.info("Fetching user orders: user_id=%s limit=%d", user_id, limit)
    try:
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"USER#{user_id}") & Key("SK").begins_with("ORDER#"),
            ScanIndexForward=False,   # descending (newest first)
            Limit=limit,
        )
        items = response.get("Items", [])
        logger.info("Orders retrieved: user_id=%s count=%d", user_id, len(items))
        return items
    except ClientError as e:
        logger.error("DynamoDB Query failed: user_id=%s error=%s", user_id, e.response["Error"]["Code"])
        raise


def create_order(user_id: str, order_id: str, total: float, status: str) -> None:
    """Create an order atomically — fails if order already exists."""
    logger.info("Creating order: user_id=%s order_id=%s total=%.2f", user_id, order_id, total)
    try:
        table.put_item(
            Item={
                "PK": f"USER#{user_id}",
                "SK": f"ORDER#{order_id}",
                "GSI1PK": "ORDER",
                "GSI1SK": f"{status}#{order_id}",
                "total": str(total),
                "status": status,
            },
            ConditionExpression=Attr("PK").not_exists(),
        )
        logger.info("Order created: order_id=%s", order_id)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning("Order already exists: order_id=%s", order_id)
            raise ValueError(f"Order {order_id} already exists")
        logger.error("DynamoDB PutItem failed: order_id=%s error=%s", order_id, e.response["Error"]["Code"])
        raise
```

---

## Capacity Modes

### On-Demand (Pay-Per-Request)

```bash
# Switch to on-demand (no capacity planning, scales instantly)
aws dynamodb update-table \
    --table-name $TABLE \
    --billing-mode PAY_PER_REQUEST
```

**Pricing (us-east-1):** $1.25 per million WRUs, $0.25 per million RRUs.

### Provisioned (with Auto Scaling)

```bash
# Switch to provisioned with auto scaling
aws dynamodb update-table \
    --table-name $TABLE \
    --billing-mode PROVISIONED \
    --provisioned-throughput ReadCapacityUnits=100,WriteCapacityUnits=50

# Enable auto scaling for reads
aws application-autoscaling register-scalable-target \
    --service-namespace dynamodb \
    --resource-id "table/$TABLE" \
    --scalable-dimension dynamodb:table:ReadCapacityUnits \
    --min-capacity 5 \
    --max-capacity 1000

aws application-autoscaling put-scaling-policy \
    --service-namespace dynamodb \
    --resource-id "table/$TABLE" \
    --scalable-dimension dynamodb:table:ReadCapacityUnits \
    --policy-name my-table-read-scaling \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration \
        TargetValue=70.0,PredefinedMetricSpecification={PredefinedMetricType=DynamoDBReadCapacityUtilization}
```

---

## DynamoDB Streams + Lambda

Streams capture every item-level change (INSERT, MODIFY, REMOVE) for change data capture, replication, and triggering downstream processing.

```bash
# Enable streams on an existing table
aws dynamodb update-table \
    --table-name $TABLE \
    --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES

# Get the stream ARN
STREAM_ARN=$(aws dynamodb describe-table \
    --table-name $TABLE \
    --query 'Table.LatestStreamArn' --output text)

# Connect a Lambda function to process the stream
aws lambda create-event-source-mapping \
    --event-source-arn $STREAM_ARN \
    --function-name my-stream-processor \
    --starting-position TRIM_HORIZON \
    --batch-size 100 \
    --bisect-batch-on-function-error \
    --maximum-retry-attempts 3 \
    --destination-config '{
        "OnFailure": {
            "Destination": "arn:aws:sqs:us-east-1:123456789012:dynamodb-dlq"
        }
    }'
```

---

## Global Tables (Multi-Region Active-Active)

```bash
# Create a global table (replicates across regions)
aws dynamodb create-table \
    --table-name MyGlobalTable \
    --attribute-definitions AttributeName=PK,AttributeType=S AttributeName=SK,AttributeType=S \
    --key-schema AttributeName=PK,KeyType=HASH AttributeName=SK,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
    --replicas '[
        {"RegionName": "us-east-1"},
        {"RegionName": "eu-west-1"}
    ]'

# Add a new replica region to an existing global table
aws dynamodb update-table \
    --table-name MyGlobalTable \
    --replica-updates '[{"Create": {"RegionName": "ap-southeast-1"}}]'
```

---

## TTL (Time To Live)

TTL automatically deletes expired items, reducing storage costs for temporary data like sessions, caches, and rate-limiting counters.

```bash
# Enable TTL on a Unix timestamp attribute
aws dynamodb update-time-to-live \
    --table-name $TABLE \
    --time-to-live-specification Enabled=true,AttributeName=expires_at

# When writing items, set expires_at to a Unix epoch timestamp
# Python example:
import time
expires_in_1_hour = int(time.time()) + 3600
table.put_item(Item={"PK": "SESSION#abc", "SK": "DATA", "data": "...", "expires_at": expires_in_1_hour})
```

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using Scan instead of Query | Design access patterns first; use GSIs to avoid scans |
| Hot partition key (e.g., `date` or single user ID) | Add a random suffix to the PK; use write sharding |
| Storing large items (>400KB) | Store binary in S3; save S3 key in DynamoDB |
| Ignoring eventually consistent reads | Use strongly consistent reads for critical lookups |
| No TTL on temporary data | Set TTL on sessions, tokens, rate-limit counters |
| Using multiple tables | Use single-table design to enable complex access patterns |

---

## References

- [DynamoDB documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/)
- [Single-table design guide](https://www.alexdebrie.com/posts/dynamodb-single-table/)
- [DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/)
- [DAX (DynamoDB Accelerator)](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.html)
---

← [Previous: Aurora](./aurora.md) | [Home](../../README.md) | [Next: ElastiCache →](./elasticache.md)
