← [Previous: GCP Databases](./README.md) | [Home](../../README.md) | [Next: Firestore →](./firestore.md)

---

# Cloud SQL

Cloud SQL is a fully managed relational database service supporting PostgreSQL, MySQL, and SQL Server. It handles replication, failover, backups, and patching.

---

## Instance Creation — PostgreSQL

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"

# Create a PostgreSQL 16 instance with HA and private IP
gcloud sql instances create psql-my-app-prod \
    --project=$PROJECT \
    --database-version=POSTGRES_16 \
    --tier=db-n1-standard-4 \
    --region=$REGION \
    --availability-type=REGIONAL \
    --enable-bin-log \
    --backup \
    --backup-start-time=02:00 \
    --retained-backups-count=14 \
    --retained-transaction-log-days=7 \
    --no-assign-ip \
    --network=projects/$PROJECT/global/networks/vpc-my-app-prod \
    --allocated-ip-range-name=cloud-sql-peering-range \
    --storage-type=SSD \
    --storage-size=100GB \
    --storage-auto-increase \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=4 \
    --database-flags=max_connections=500,log_min_duration_statement=1000 \
    --labels=environment=production,service=my-app

# Create database
gcloud sql databases create myappdb \
    --instance=psql-my-app-prod \
    --project=$PROJECT

# Create a user (use Secret Manager for the password)
DB_PASS=$(openssl rand -base64 24)
gcloud sql users create appuser \
    --instance=psql-my-app-prod \
    --project=$PROJECT \
    --password=$DB_PASS
# Store $DB_PASS in Secret Manager immediately

# Get the private IP
gcloud sql instances describe psql-my-app-prod \
    --project=$PROJECT \
    --format="value(ipAddresses.ipAddress)"
```

---

## Private IP Setup

Cloud SQL private IP uses VPC peering. You must allocate an IP range for it.

```bash
# Allocate IP range for Cloud SQL in your VPC
gcloud compute addresses create cloud-sql-peering-range \
    --project=$PROJECT \
    --global \
    --purpose=VPC_PEERING \
    --addresses=10.0.200.0 \
    --prefix-length=24 \
    --network=vpc-my-app-prod

# Enable private services access (Cloud SQL VPC peering)
gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --network=vpc-my-app-prod \
    --ranges=cloud-sql-peering-range \
    --project=$PROJECT
```

---

## Read Replicas

```bash
# Create a read replica (same region)
gcloud sql instances create psql-my-app-replica \
    --project=$PROJECT \
    --master-instance-name=psql-my-app-prod \
    --region=$REGION \
    --tier=db-n1-standard-2 \
    --no-assign-ip \
    --network=projects/$PROJECT/global/networks/vpc-my-app-prod

# Create a cross-region read replica (for DR reads)
gcloud sql instances create psql-my-app-replica-us-east \
    --project=$PROJECT \
    --master-instance-name=psql-my-app-prod \
    --region=us-east1 \
    --tier=db-n1-standard-2

# Promote replica to standalone (failover)
gcloud sql instances promote-replica psql-my-app-replica \
    --project=$PROJECT
```

---

## Point-in-Time Recovery

```bash
# Restore to a specific point in time (creates new instance)
gcloud sql instances clone psql-my-app-prod psql-my-app-restored \
    --project=$PROJECT \
    --point-in-time="2024-06-15T10:00:00Z"

# List available backups
gcloud sql backups list \
    --instance=psql-my-app-prod \
    --project=$PROJECT \
    --format="table(id,windowStartTime,status)"

# Restore from backup to existing instance (overwrites data!)
gcloud sql backups restore BACKUP_ID \
    --restore-instance=psql-my-app-prod \
    --backup-instance=psql-my-app-prod \
    --project=$PROJECT
```

---

## Cloud SQL Python Connector

The Cloud SQL Python Connector handles authentication and SSL without VPN or Cloud SQL proxy.

```python
import os
import logging
from contextlib import asynccontextmanager
import asyncpg
from google.cloud.sql.connector import AsyncConnector, IPTypes

logger = logging.getLogger(__name__)

INSTANCE_CONNECTION_NAME = os.environ["CLOUD_SQL_INSTANCE"]
# Format: project:region:instance  e.g. my-app-prod-123456:us-central1:psql-my-app-prod
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASS = os.environ.get("DB_PASS")  # None when using IAM auth


async def get_pool() -> asyncpg.Pool:
    """Create an asyncpg connection pool via Cloud SQL Python Connector."""
    connector = AsyncConnector()

    async def get_conn() -> asyncpg.Connection:
        logger.debug("Creating Cloud SQL connection", extra={"instance": INSTANCE_CONNECTION_NAME})
        conn = await connector.connect_async(
            INSTANCE_CONNECTION_NAME,
            "asyncpg",
            user=DB_USER,
            password=DB_PASS,  # None for IAM auth
            db=DB_NAME,
            ip_type=IPTypes.PRIVATE,  # Use private IP
        )
        return conn

    pool = await asyncpg.create_pool(
        dsn=None,
        connect=get_conn,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    logger.info("Cloud SQL connection pool created", extra={"instance": INSTANCE_CONNECTION_NAME, "db": DB_NAME})
    return pool


# IAM database authentication (no password — uses ADC token)
# Grant IAM user database access:
# gcloud sql users create DB_USER_EMAIL --instance=psql-my-app-prod --type=cloud_iam_service_account
```

---

## Instance Management

```bash
# Stop instance (saves compute cost — storage still billed)
gcloud sql instances patch psql-my-app-prod \
    --activation-policy=NEVER \
    --project=$PROJECT

# Start instance
gcloud sql instances patch psql-my-app-prod \
    --activation-policy=ALWAYS \
    --project=$PROJECT

# Resize
gcloud sql instances patch psql-my-app-prod \
    --tier=db-n1-standard-8 \
    --project=$PROJECT

# Show instance status
gcloud sql instances describe psql-my-app-prod \
    --project=$PROJECT \
    --format="table(name,state,databaseVersion,settings.tier,ipAddresses)"
```

---

## References

- [Cloud SQL documentation](https://cloud.google.com/sql/docs)
- [Cloud SQL Python Connector](https://github.com/GoogleCloudPlatform/cloud-sql-python-connector)
- [IAM database authentication](https://cloud.google.com/sql/docs/postgres/iam-logins)
- [High availability](https://cloud.google.com/sql/docs/postgres/high-availability)

---

← [Previous: GCP Databases](./README.md) | [Home](../../README.md) | [Next: Firestore →](./firestore.md)
