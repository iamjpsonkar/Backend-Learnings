← [Previous: Kubernetes App](./kubernetes-app.md) | [Home](../README.md) | [Next: Multi-Tier App →](./multi-tier-app.md)

---

# Project: Streaming Data Pipeline

Build a real-time data pipeline: events flow from an API into Kinesis, get enriched by Lambda, land in S3 (data lake), get cataloged by Glue, and become queryable via Athena — all without managing any servers.

**Estimated cost:** ~$20–40/month (Kinesis + Lambda + S3 + Glue + Athena)
**Time to complete:** 3–4 hours

---

## Architecture

```
Client events (clickstream / orders / IoT)
  │  HTTPS POST /events
  ▼
API Gateway (HTTP API)
  │
  ▼
Kinesis Data Streams (2 shards)
  │  real-time consumer
  ▼
Lambda (enrichment + transform)
  ├── Add geo-IP lookup
  ├── Validate schema
  ├── Convert to Parquet (via pyarrow)
  └── Write to S3 (partitioned by date/hour)
        │
        s3://data-lake/events/
        └── year=2024/month=01/day=15/hour=14/
              ├── part-0001.parquet
              └── part-0002.parquet
                    │
                    ▼
              Glue Data Catalog (auto-crawled nightly)
                    │
                    ▼
              Athena (SQL queries over S3)
                    │
                    ▼
              QuickSight / Grafana CloudWatch plugin
```

---

## Step 1: Kinesis Data Stream

```bash
export APP="data-pipeline"
export REGION="us-east-1"

# Create stream (2 shards = 2 MB/s ingest, 4 MB/s read)
aws kinesis create-stream \
    --stream-name "${APP}-events" \
    --shard-count 2 \
    --region $REGION

# Wait for active
aws kinesis wait stream-exists \
    --stream-name "${APP}-events" \
    --region $REGION

# Enable server-side encryption
aws kinesis start-stream-encryption \
    --stream-name "${APP}-events" \
    --encryption-type KMS \
    --key-id alias/aws/kinesis \
    --region $REGION

# Get stream ARN
STREAM_ARN=$(aws kinesis describe-stream-summary \
    --stream-name "${APP}-events" \
    --query 'StreamDescriptionSummary.StreamARN' --output text)

echo "Stream ARN: $STREAM_ARN"
```

---

## Step 2: S3 Data Lake

```bash
BUCKET="${APP}-data-lake-$(aws sts get-caller-identity --query Account --output text)"

# Create bucket
aws s3api create-bucket --bucket $BUCKET --region $REGION

# Block public access
aws s3api put-public-access-block \
    --bucket $BUCKET \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,\
BlockPublicPolicy=true,RestrictPublicBuckets=true

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket $BUCKET \
    --versioning-configuration Status=Enabled

# Lifecycle policy: move to Intelligent-Tiering after 30 days
aws s3api put-bucket-lifecycle-configuration \
    --bucket $BUCKET \
    --lifecycle-configuration '{
        "Rules": [{
            "ID": "archive-old-data",
            "Status": "Enabled",
            "Filter": {"Prefix": "events/"},
            "Transitions": [
                {"Days": 30, "StorageClass": "INTELLIGENT_TIERING"}
            ],
            "Expiration": {"Days": 365}
        }]
    }'

echo "Data lake bucket: s3://$BUCKET"
```

---

## Step 3: Lambda Enrichment Function

```python
# src/pipeline/handler.py
import base64
import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import boto3
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
BUCKET = os.environ["DATA_LAKE_BUCKET"]
STREAM_NAME = os.environ["STREAM_NAME"]


# ─── Schema ───────────────────────────────────────────────────────────────────

EVENT_SCHEMA = pa.schema([
    pa.field("event_id", pa.string()),
    pa.field("event_type", pa.string()),
    pa.field("user_id", pa.string()),
    pa.field("session_id", pa.string()),
    pa.field("timestamp", pa.timestamp("ms", tz="UTC")),
    pa.field("properties", pa.string()),   # JSON blob
    pa.field("ingested_at", pa.timestamp("ms", tz="UTC")),
    pa.field("source_shard", pa.string()),
])


def handler(event: dict, context) -> dict:
    """
    Process a batch of Kinesis records:
    1. Decode base64 payload
    2. Validate and enrich
    3. Write batch as Parquet to S3 (partitioned by date/hour)
    """
    request_id = context.aws_request_id
    records = event.get("Records", [])

    logger.info("Processing Kinesis batch", extra={
        "request_id": request_id,
        "record_count": len(records),
    })

    rows: list[dict] = []
    parse_errors = 0

    for record in records:
        try:
            payload = base64.b64decode(record["kinesis"]["data"]).decode("utf-8")
            data = json.loads(payload)
            enriched = _enrich(data, record["kinesis"]["sequenceNumber"], record["kinesis"]["partitionKey"])
            rows.append(enriched)
        except Exception as exc:
            parse_errors += 1
            logger.warning("Failed to parse record", extra={
                "request_id": request_id,
                "sequence_number": record["kinesis"].get("sequenceNumber"),
                "error": str(exc),
            })

    if rows:
        _write_parquet(rows, request_id)

    logger.info("Batch complete", extra={
        "request_id": request_id,
        "processed": len(rows),
        "errors": parse_errors,
    })

    # Return batch item failures to retry only failed records (partial batch response)
    return {"batchItemFailures": []}


def _enrich(data: dict, sequence_number: str, partition_key: str) -> dict:
    """Add metadata and validate required fields."""
    required = {"event_id", "event_type", "user_id", "timestamp"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    return {
        "event_id": data["event_id"],
        "event_type": data["event_type"],
        "user_id": data["user_id"],
        "session_id": data.get("session_id", ""),
        "timestamp": datetime.fromisoformat(data["timestamp"]),
        "properties": json.dumps(data.get("properties", {})),
        "ingested_at": datetime.now(timezone.utc),
        "source_shard": partition_key,
    }


def _write_parquet(rows: list[dict], request_id: str) -> None:
    """Write rows as a Parquet file to S3, partitioned by date/hour."""
    now = rows[0]["timestamp"]  # Use first record's timestamp for partition
    s3_key = (
        f"events/year={now.year:04d}/month={now.month:02d}/"
        f"day={now.day:02d}/hour={now.hour:02d}/{request_id}.parquet"
    )

    # Build PyArrow table
    table = pa.Table.from_pylist(rows, schema=EVENT_SCHEMA)

    # Write to in-memory buffer then S3
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    buf.seek(0)

    s3.put_object(
        Bucket=BUCKET,
        Key=s3_key,
        Body=buf.read(),
        ContentType="application/octet-stream",
    )

    logger.info("Parquet file written", extra={
        "request_id": request_id,
        "s3_key": s3_key,
        "row_count": len(rows),
        "size_bytes": buf.tell(),
    })
```

---

## Step 4: Connect Lambda to Kinesis

```bash
# Create Lambda function
LAMBDA_ARN=$(aws lambda create-function \
    --function-name "${APP}-processor" \
    --runtime python3.12 \
    --handler handler.handler \
    --role arn:aws:iam::$ACCOUNT_ID:role/lambda-kinesis-role \
    --zip-file fileb://function.zip \
    --environment "Variables={DATA_LAKE_BUCKET=$BUCKET,STREAM_NAME=${APP}-events}" \
    --timeout 300 \
    --memory-size 512 \
    --query 'FunctionArn' --output text)

# Create Kinesis event source mapping
aws lambda create-event-source-mapping \
    --function-name "${APP}-processor" \
    --event-source-arn $STREAM_ARN \
    --batch-size 100 \
    --starting-position TRIM_HORIZON \
    --maximum-batching-window-in-seconds 5 \
    --bisect-batch-on-function-error \
    --function-response-types ReportBatchItemFailures \
    --destination-config '{
        "OnFailure": {
            "Destination": "arn:aws:sqs:us-east-1:'"$ACCOUNT_ID"':'"${APP}-dlq"'"
        }
    }'
```

---

## Step 5: Glue Crawler + Athena

```bash
# Create Glue database
aws glue create-database \
    --database-input '{
        "Name": "data_lake",
        "Description": "S3 data lake — events"
    }' \
    --region $REGION

# Create Glue crawler
aws glue create-crawler \
    --name "${APP}-events-crawler" \
    --role arn:aws:iam::$ACCOUNT_ID:role/glue-crawler-role \
    --database-name data_lake \
    --targets '{
        "S3Targets": [{
            "Path": "s3://'"$BUCKET"'/events/",
            "Exclusions": ["**/_temporary/**"]
        }]
    }' \
    --schedule "cron(0 6 * * ? *)" \
    --recrawl-policy '{"RecrawlBehavior": "CRAWL_NEW_FOLDERS_ONLY"}' \
    --schema-change-policy '{
        "UpdateBehavior": "UPDATE_IN_DATABASE",
        "DeleteBehavior": "LOG"
    }'

# Run crawler now (first time)
aws glue start-crawler --name "${APP}-events-crawler"

# Wait for crawler
while [ "$(aws glue get-crawler --name "${APP}-events-crawler" --query 'Crawler.State' --output text)" = "RUNNING" ]; do
    echo "Crawler running..."
    sleep 10
done

# Query with Athena
ATHENA_OUTPUT="s3://$BUCKET/athena-results/"

QUERY_ID=$(aws athena start-query-execution \
    --query-string "
        SELECT
            event_type,
            COUNT(*) AS event_count,
            COUNT(DISTINCT user_id) AS unique_users
        FROM data_lake.events
        WHERE year = '$(date +%Y)'
          AND month = '$(date +%m)'
          AND day = '$(date +%d)'
        GROUP BY event_type
        ORDER BY event_count DESC
        LIMIT 20
    " \
    --query-execution-context Database=data_lake \
    --result-configuration "OutputLocation=$ATHENA_OUTPUT" \
    --query 'QueryExecutionId' --output text)

# Wait for results
aws athena wait query-succeeded --query-execution-id $QUERY_ID

# Get results
aws athena get-query-results \
    --query-execution-id $QUERY_ID \
    --query 'ResultSet.Rows[*].Data[*].VarCharValue' \
    --output table
```

---

## Step 6: Send Test Events

```python
# test_producer.py
import boto3
import json
import uuid
from datetime import datetime, timezone
import random

kinesis = boto3.client("kinesis", region_name="us-east-1")
STREAM = "data-pipeline-events"
EVENT_TYPES = ["page_view", "button_click", "order_placed", "checkout_started"]

def send_events(count: int = 100):
    records = [
        {
            "Data": json.dumps({
                "event_id": str(uuid.uuid4()),
                "event_type": random.choice(EVENT_TYPES),
                "user_id": f"user-{random.randint(1, 1000)}",
                "session_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "properties": {"page": "/products", "referrer": "google.com"},
            }),
            "PartitionKey": f"shard-{random.randint(0, 1)}",
        }
        for _ in range(count)
    ]

    response = kinesis.put_records(StreamName=STREAM, Records=records)
    print(f"Sent {count} records. Failed: {response['FailedRecordCount']}")

send_events(1000)
```

---

## Teardown

```bash
# Delete Lambda event source mapping
aws lambda delete-event-source-mapping --uuid $MAPPING_UUID

# Delete Kinesis stream
aws kinesis delete-stream --stream-name "${APP}-events"

# Delete Glue resources
aws glue delete-crawler --name "${APP}-events-crawler"
aws glue delete-database --name data_lake

# Empty and delete S3 bucket
aws s3 rm s3://$BUCKET --recursive
aws s3api delete-bucket --bucket $BUCKET
```

---

← [Previous: Kubernetes App](./kubernetes-app.md) | [Home](../README.md) | [Next: Multi-Tier App →](./multi-tier-app.md)
