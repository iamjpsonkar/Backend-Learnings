← [Previous: Filestore](../05-storage/filestore.md) | [Home](../../README.md) | [Next: Cloud SQL →](./cloud-sql.md)

---

# GCP Databases

---

## Service Selection

| Service | AWS Equivalent | Use Case |
|---------|----------------|---------|
| **Cloud SQL** | RDS | Managed MySQL, PostgreSQL, SQL Server |
| **AlloyDB** | Aurora PostgreSQL | Fully managed PostgreSQL — 4x faster for analytics |
| **Cloud Spanner** | Aurora (global) | Globally distributed, strongly consistent relational |
| **Firestore** | DynamoDB | Serverless document database — NoSQL |
| **Bigtable** | DynamoDB (high-throughput) | Wide-column, petabyte-scale, time-series / IoT |
| **Memorystore for Redis** | ElastiCache for Redis | Managed Redis — cache, sessions, rate limiting |
| **Memorystore for Memcached** | ElastiCache for Memcached | Managed Memcached |
| **BigQuery** | Redshift | Serverless data warehouse — analytical queries |

---

## Cloud SQL (PostgreSQL)

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"
ZONE="us-central1-a"

# Create a Cloud SQL PostgreSQL instance (HA — primary + standby in another zone)
gcloud sql instances create pg-my-app-prod \
    --project=$PROJECT_ID \
    --database-version=POSTGRES_16 \
    --tier=db-n1-standard-4 \
    --region=$REGION \
    --availability-type=REGIONAL \
    --no-assign-ip \
    --network=projects/$PROJECT_ID/global/networks/vpc-my-app-prod \
    --retained-backups-count=7 \
    --enable-bin-log \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04 \
    --database-flags=max_connections=200,log_min_duration_statement=1000 \
    --storage-size=100GB \
    --storage-type=SSD \
    --storage-auto-increase \
    --deletion-protection \
    --labels=environment=production,service=my-app

# Create a database
gcloud sql databases create myapp \
    --project=$PROJECT_ID \
    --instance=pg-my-app-prod

# Create a user
gcloud sql users create myapp_user \
    --project=$PROJECT_ID \
    --instance=pg-my-app-prod \
    --password="$(openssl rand -base64 32)"

# Create a read replica in another region
gcloud sql instances create pg-my-app-prod-replica-us-east1 \
    --project=$PROJECT_ID \
    --master-instance-name=pg-my-app-prod \
    --region=us-east1 \
    --database-version=POSTGRES_16 \
    --tier=db-n1-standard-2 \
    --no-assign-ip \
    --network=projects/$PROJECT_ID/global/networks/vpc-my-app-prod

# Point-in-time recovery (restore to specific timestamp)
gcloud sql instances clone pg-my-app-prod pg-my-app-restored \
    --project=$PROJECT_ID \
    --point-in-time="2024-06-01T12:00:00.000Z"

# Connection string for Cloud SQL Auth Proxy (recommended approach)
# The Auth Proxy handles IAM auth and TLS without managing IP allowlists
# Run proxy locally: cloud-sql-proxy my-app-production:us-central1:pg-my-app-prod
# Connect: psql "host=127.0.0.1 port=5432 dbname=myapp user=myapp_user"

# Connect directly from a VM (using Private IP via VPC)
gcloud sql instances describe pg-my-app-prod \
    --project=$PROJECT_ID \
    --format="value(ipAddresses[0].ipAddress)"
```

### Cloud SQL Auth Proxy (Application Connection Pattern)

```python
# requirements: google-cloud-sqlconnector sqlalchemy pg8000
import logging
import os
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy

logger = logging.getLogger(__name__)

_connector = Connector()


def get_engine() -> sqlalchemy.engine.Engine:
    """Create a SQLAlchemy engine using Cloud SQL Python Connector (IAM auth, no keys)."""
    instance_connection_name = os.environ["CLOUD_SQL_INSTANCE"]  # project:region:instance
    db_user = os.environ["DB_USER"]
    db_name = os.environ["DB_NAME"]

    logger.info("Creating Cloud SQL engine: instance=%s db=%s", instance_connection_name, db_name)

    def getconn():
        conn = _connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_user,
            db=db_name,
            ip_type=IPTypes.PRIVATE,
            enable_iam_auth=True,  # Authenticate via IAM — no password needed
        )
        return conn

    engine = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    logger.info("Cloud SQL engine created successfully: instance=%s", instance_connection_name)
    return engine
```

---

## Firestore

Firestore is a serverless, NoSQL document database — scales to zero when idle.

```bash
# Create a Firestore database (native mode — default for new projects)
gcloud firestore databases create \
    --project=$PROJECT_ID \
    --location=$REGION \
    --type=firestore-native

# Create a composite index (required for multi-field queries)
gcloud firestore indexes composite create \
    --project=$PROJECT_ID \
    --collection-group=orders \
    --query-scope=COLLECTION \
    --field-config=field-path=customerId,order=ASCENDING \
    --field-config=field-path=createdAt,order=DESCENDING

# Export data to Cloud Storage (backup)
gcloud firestore export gs://${PROJECT_ID}-backups/firestore-$(date +%Y%m%d) \
    --project=$PROJECT_ID
```

### Python SDK — Firestore

```python
import logging
import os
from google.cloud import firestore
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_db = firestore.Client(project=os.environ["GCP_PROJECT_ID"])


def create_order(order_id: str, customer_id: str, items: list, total_usd: float) -> dict:
    """Write an order document to Firestore."""
    logger.info("Creating order: order_id=%s customer_id=%s total=%.2f", order_id, customer_id, total_usd)

    order_ref = _db.collection("orders").document(order_id)
    order = {
        "orderId": order_id,
        "customerId": customer_id,
        "items": items,
        "totalUsd": total_usd,
        "status": "created",
        "createdAt": datetime.now(timezone.utc),
    }
    order_ref.set(order)
    logger.info("Order created in Firestore: order_id=%s", order_id)
    return order


def get_orders_by_customer(customer_id: str, limit: int = 20) -> list:
    """Query orders for a customer, newest first."""
    logger.info("Fetching orders: customer_id=%s limit=%d", customer_id, limit)
    docs = (
        _db.collection("orders")
        .where("customerId", "==", customer_id)
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    orders = [doc.to_dict() for doc in docs]
    logger.debug("Orders fetched: customer_id=%s count=%d", customer_id, len(orders))
    return orders


def update_order_status(order_id: str, status: str) -> None:
    """Update the status of an existing order."""
    logger.info("Updating order status: order_id=%s status=%s", order_id, status)
    _db.collection("orders").document(order_id).update({
        "status": status,
        "updatedAt": datetime.now(timezone.utc),
    })
    logger.info("Order status updated: order_id=%s", order_id)
```

---

## Memorystore for Redis

```bash
# Create a Redis instance (Standard tier — HA with replica)
gcloud redis instances create redis-my-app-prod \
    --project=$PROJECT_ID \
    --region=$REGION \
    --tier=STANDARD \
    --size=5 \
    --redis-version=redis_7_0 \
    --network=projects/$PROJECT_ID/global/networks/vpc-my-app-prod \
    --connect-mode=PRIVATE_SERVICE_ACCESS \
    --enable-auth \
    --labels=environment=production

# Get host and port
gcloud redis instances describe redis-my-app-prod \
    --project=$PROJECT_ID \
    --region=$REGION \
    --format="value(host,port)"

# Redis AUTH password
AUTH_STRING=$(gcloud redis instances get-auth-string redis-my-app-prod \
    --project=$PROJECT_ID \
    --region=$REGION \
    --format="value(authString)")
```

### Python Redis Pattern

```python
import redis
import json
import logging
import os
from functools import wraps

logger = logging.getLogger(__name__)

_redis_client = redis.StrictRedis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ.get("REDIS_PORT", "6379")),
    password=os.environ["REDIS_AUTH"],
    ssl=True,
    decode_responses=True,
    socket_timeout=2,
    socket_connect_timeout=2,
)


def cache_aside(key_prefix: str, ttl_seconds: int = 300):
    """Cache-aside decorator — returns cached value or calls function and caches result."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{':'.join(str(a) for a in args)}"
            try:
                cached = _redis_client.get(cache_key)
                if cached:
                    logger.debug("Cache hit: key=%s", cache_key)
                    return json.loads(cached)
                logger.debug("Cache miss: key=%s", cache_key)
            except redis.RedisError as e:
                logger.warning("Redis read failed, bypassing cache: key=%s error=%s", cache_key, str(e))

            result = func(*args, **kwargs)

            try:
                _redis_client.setex(cache_key, ttl_seconds, json.dumps(result, default=str))
                logger.debug("Cached result: key=%s ttl=%d", cache_key, ttl_seconds)
            except redis.RedisError as e:
                logger.warning("Redis write failed: key=%s error=%s", cache_key, str(e))

            return result
        return wrapper
    return decorator
```

---

## BigQuery

BigQuery is a serverless, columnar data warehouse. Queries are billed per TB scanned (or flat-rate).

```bash
# Create a dataset
bq mk \
    --project_id=$PROJECT_ID \
    --location=$REGION \
    --dataset my_app_analytics

# Create a table from schema JSON
bq mk \
    --project_id=$PROJECT_ID \
    --table my_app_analytics.events \
    --schema event_id:STRING,user_id:STRING,event_type:STRING,timestamp:TIMESTAMP,properties:JSON \
    --time_partitioning_field timestamp \
    --time_partitioning_type DAY \
    --clustering_fields event_type,user_id \
    --require_partition_filter

# Run a query (CLI)
bq query --use_legacy_sql=false \
    --project_id=$PROJECT_ID \
    "SELECT
       event_type,
       COUNT(*) as count,
       APPROX_QUANTILES(PARSE_JSON(properties).value, 100)[OFFSET(99)] as p99_value
     FROM my_app_analytics.events
     WHERE DATE(timestamp) = CURRENT_DATE()
     GROUP BY 1
     ORDER BY 2 DESC
     LIMIT 20"

# Load data from Cloud Storage
bq load \
    --project_id=$PROJECT_ID \
    --source_format=NEWLINE_DELIMITED_JSON \
    my_app_analytics.events \
    gs://${PROJECT_ID}-exports/events/2024/06/*.json

# Export query results to GCS
bq extract \
    --project_id=$PROJECT_ID \
    --destination_format=CSV \
    my_app_analytics.events \
    gs://${PROJECT_ID}-exports/events_export.csv
```

---

## References

- [Cloud SQL documentation](https://cloud.google.com/sql/docs)
- [Cloud SQL Python Connector](https://cloud.google.com/sql/docs/postgres/connect-connectors)
- [Firestore documentation](https://cloud.google.com/firestore/docs)
- [Memorystore documentation](https://cloud.google.com/memorystore/docs)
- [BigQuery documentation](https://cloud.google.com/bigquery/docs)
---

← [Previous: Filestore](../05-storage/filestore.md) | [Home](../../README.md) | [Next: Cloud SQL →](./cloud-sql.md)
