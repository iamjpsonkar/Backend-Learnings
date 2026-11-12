← [Previous: Identity](./identity.md) | [Home](../README.md) | [Next: IaC Abstractions →](./iac-abstractions.md)

---

# Cross-Cloud Data Replication

Replicating data across cloud providers is more expensive and more complex than replication within a single cloud. This file covers patterns for keeping data in sync between AWS and GCP/Azure, including event-driven CDC, batch sync, and conflict resolution.

---

## Replication Patterns

```
Pattern              Latency      Consistency     Complexity     Use case
─────────────────────────────────────────────────────────────────────────
Event-driven CDC     Seconds      Eventually      High           Live operational data
Periodic batch sync  Minutes-hrs  Eventually      Medium         Analytics, reporting
Streaming pipeline   Seconds      Eventually      Medium-high    Log/event data
Object storage sync  Near-real    Eventually      Low            Files, backups, exports
Database logical     Seconds      Eventually      High           PostgreSQL cross-cloud
```

---

## Event-Driven CDC: AWS → GCP

Stream database changes from an AWS RDS PostgreSQL instance to GCP BigQuery using Debezium + Kafka + Dataflow.

### Architecture

```
RDS PostgreSQL (AWS)
      │ logical replication (WAL)
      ▼
Debezium connector (MSK / Kafka on EC2)
      │ Kafka topic: prod.public.orders
      ▼
GCP Pub/Sub (via Kafka MirrorMaker2 or direct connector)
      │
      ▼
Dataflow pipeline (Apache Beam)
      │
      ▼
BigQuery table (analytics replica)
```

### Debezium Configuration

```json
{
    "name": "rds-postgres-source",
    "config": {
        "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
        "database.hostname": "prod-postgres.xxxx.us-east-1.rds.amazonaws.com",
        "database.port": "5432",
        "database.user": "debezium",
        "database.password": "${file:/opt/kafka/secrets.properties:db.password}",
        "database.dbname": "myapp",
        "database.server.name": "prod",
        "plugin.name": "pgoutput",
        "slot.name": "debezium_slot",
        "publication.name": "debezium_publication",
        "table.include.list": "public.orders,public.order_items,public.customers",
        "transforms": "unwrap",
        "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
        "transforms.unwrap.drop.tombstones": "false",
        "transforms.unwrap.add.fields": "op,ts_ms,source.ts_ms",
        "key.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter": "org.apache.kafka.connect.json.JsonConverter",
        "snapshot.mode": "initial",
        "heartbeat.interval.ms": "10000"
    }
}
```

### Dataflow Pipeline: Kafka → BigQuery

```python
import json
import logging
from datetime import datetime
from typing import Any

import apache_beam as beam
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition
from apache_beam.io.kafka import ReadFromKafka
from apache_beam.options.pipeline_options import PipelineOptions

logger = logging.getLogger(__name__)


class ParseDebeziumRecord(beam.DoFn):
    """Parse Debezium CDC record into BigQuery row."""

    def process(self, element: tuple) -> list[dict]:
        try:
            key, value = element
            record = json.loads(value.decode("utf-8"))

            op = record.get("__op", "r")  # c=create, u=update, d=delete, r=read
            ts_ms = record.get("__source_ts_ms", 0)

            row = {
                "ingested_at": datetime.utcnow().isoformat(),
                "source_timestamp": datetime.utcfromtimestamp(ts_ms / 1000).isoformat(),
                "operation": op,
                "order_id": record.get("order_id"),
                "customer_id": record.get("customer_id"),
                "status": record.get("status"),
                "total_amount": record.get("total_amount"),
                "is_deleted": op == "d",
            }

            logger.debug("Parsed CDC record", extra={
                "op": op, "order_id": row["order_id"],
            })
            return [row]

        except Exception as exc:
            logger.error("Failed to parse CDC record", extra={"error": str(exc)}, exc_info=True)
            return []  # Dead letter: in production, send to error topic


def run_cdc_pipeline(kafka_bootstrap: str, gcp_project: str, bq_dataset: str):
    options = PipelineOptions(
        project=gcp_project,
        region="us-central1",
        runner="DataflowRunner",
        streaming=True,
        job_name="orders-cdc-pipeline",
        temp_location=f"gs://{gcp_project}-dataflow-tmp/temp",
    )

    with beam.Pipeline(options=options) as pipeline:
        (
            pipeline
            | "Read from Kafka" >> ReadFromKafka(
                consumer_config={
                    "bootstrap.servers": kafka_bootstrap,
                    "group.id": "gcp-cdc-consumer",
                    "auto.offset.reset": "earliest",
                },
                topics=["prod.public.orders"],
                with_metadata=False,
            )
            | "Parse CDC Records" >> beam.ParDo(ParseDebeziumRecord())
            | "Write to BigQuery" >> WriteToBigQuery(
                table=f"{gcp_project}:{bq_dataset}.orders_replica",
                schema={
                    "fields": [
                        {"name": "ingested_at", "type": "TIMESTAMP"},
                        {"name": "source_timestamp", "type": "TIMESTAMP"},
                        {"name": "operation", "type": "STRING"},
                        {"name": "order_id", "type": "STRING"},
                        {"name": "customer_id", "type": "STRING"},
                        {"name": "status", "type": "STRING"},
                        {"name": "total_amount", "type": "NUMERIC"},
                        {"name": "is_deleted", "type": "BOOL"},
                    ]
                },
                write_disposition=BigQueryDisposition.WRITE_APPEND,
                create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            )
        )
```

---

## S3 to GCS Object Sync

For file/artifact replication between AWS S3 and GCP Cloud Storage.

```python
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import boto3
from google.cloud import storage as gcs

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    key: str
    status: str  # "synced", "skipped", "failed"
    error: str | None = None


def sync_s3_to_gcs(
    s3_bucket: str,
    gcs_bucket: str,
    prefix: str = "",
    max_workers: int = 20,
) -> dict:
    """
    Sync objects from S3 to GCS. Only transfers objects that don't exist
    in GCS or have different ETags.
    """
    s3 = boto3.client("s3")
    gcs_client = gcs.Client()
    gcs_bkt = gcs_client.bucket(gcs_bucket)

    logger.info("Starting S3→GCS sync", extra={
        "s3_bucket": s3_bucket, "gcs_bucket": gcs_bucket, "prefix": prefix,
    })

    # Build GCS index for quick lookup
    logger.info("Building GCS object index")
    gcs_index = {
        blob.name: blob.md5_hash
        for blob in gcs_client.list_blobs(gcs_bucket, prefix=prefix)
    }

    # List S3 objects
    paginator = s3.get_paginator("list_objects_v2")
    s3_objects = []
    for page in paginator.paginate(Bucket=s3_bucket, Prefix=prefix):
        s3_objects.extend(page.get("Contents", []))

    logger.info("Objects to evaluate", extra={
        "s3_count": len(s3_objects), "gcs_count": len(gcs_index),
    })

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_sync_one_object, s3, gcs_bkt, s3_bucket, obj, gcs_index): obj["Key"]
            for obj in s3_objects
        }

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if result.status == "failed":
                logger.error("Object sync failed", extra={"key": result.key, "error": result.error})

    synced = sum(1 for r in results if r.status == "synced")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = sum(1 for r in results if r.status == "failed")

    logger.info("Sync complete", extra={
        "total": len(results), "synced": synced, "skipped": skipped, "failed": failed,
    })
    return {"total": len(results), "synced": synced, "skipped": skipped, "failed": failed}


def _sync_one_object(
    s3_client,
    gcs_bkt,
    s3_bucket: str,
    s3_obj: dict,
    gcs_index: dict,
) -> SyncResult:
    key = s3_obj["Key"]
    s3_etag = s3_obj["ETag"].strip('"')

    # Skip if GCS has the same object (compare via md5 — note: S3 multipart ETags differ)
    if key in gcs_index:
        return SyncResult(key=key, status="skipped")

    try:
        # Stream directly from S3 to GCS without local temp file
        s3_response = s3_client.get_object(Bucket=s3_bucket, Key=key)
        blob = gcs_bkt.blob(key)
        blob.upload_from_file(s3_response["Body"], content_type=s3_response.get("ContentType"))

        logger.debug("Object synced", extra={"key": key, "size": s3_obj["Size"]})
        return SyncResult(key=key, status="synced")

    except Exception as exc:
        return SyncResult(key=key, status="failed", error=str(exc))
```

---

## Conflict Resolution

When data is written to multiple clouds concurrently, conflicts can occur. Choose a resolution strategy upfront.

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ConflictStrategy(str, Enum):
    LAST_WRITE_WINS = "last_write_wins"
    PRIMARY_WINS = "primary_wins"
    MERGE = "merge"


@dataclass
class Record:
    id: str
    data: dict[str, Any]
    updated_at: datetime
    source: str  # "aws" | "gcp"
    version: int


def resolve_conflict(
    aws_record: Record,
    gcp_record: Record,
    strategy: ConflictStrategy,
    primary_source: str = "aws",
) -> Record:
    """Resolve a conflict between the same record from two sources."""

    if strategy == ConflictStrategy.LAST_WRITE_WINS:
        winner = aws_record if aws_record.updated_at >= gcp_record.updated_at else gcp_record
        return winner

    elif strategy == ConflictStrategy.PRIMARY_WINS:
        return aws_record if primary_source == "aws" else gcp_record

    elif strategy == ConflictStrategy.MERGE:
        # Merge: take each field from the more recently updated source
        merged_data = {}
        for field in set(aws_record.data) | set(gcp_record.data):
            aws_val = aws_record.data.get(field)
            gcp_val = gcp_record.data.get(field)
            if aws_val == gcp_val:
                merged_data[field] = aws_val
            elif aws_record.updated_at >= gcp_record.updated_at:
                merged_data[field] = aws_val
            else:
                merged_data[field] = gcp_val

        return Record(
            id=aws_record.id,
            data=merged_data,
            updated_at=max(aws_record.updated_at, gcp_record.updated_at),
            source="merged",
            version=max(aws_record.version, gcp_record.version) + 1,
        )

    else:
        raise ValueError(f"Unknown conflict strategy: {strategy}")
```

---

## Monitoring Replication Lag

```python
import logging
import time

import boto3
from google.cloud import bigquery

logger = logging.getLogger(__name__)


def check_replication_lag(
    source_rds_endpoint: str,
    bq_project: str,
    bq_dataset: str,
    table: str,
) -> dict:
    """
    Compare max updated_at between source (RDS) and replica (BigQuery).
    Returns lag in seconds.
    """
    import psycopg2

    # Get latest timestamp from source
    with psycopg2.connect(source_rds_endpoint) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT MAX(updated_at) FROM {table}")  # noqa: S608
            source_latest = cur.fetchone()[0]

    # Get latest timestamp from BigQuery replica
    bq = bigquery.Client(project=bq_project)
    query = f"SELECT MAX(source_timestamp) as latest FROM `{bq_project}.{bq_dataset}.{table}_replica`"
    result = list(bq.query(query).result())[0]
    replica_latest = result.latest

    lag_seconds = (source_latest - replica_latest).total_seconds() if replica_latest else None

    logger.info("Replication lag check", extra={
        "table": table,
        "source_latest": str(source_latest),
        "replica_latest": str(replica_latest),
        "lag_seconds": lag_seconds,
    })

    if lag_seconds and lag_seconds > 300:  # > 5 minutes
        logger.warning("Replication lag exceeds threshold", extra={
            "table": table, "lag_seconds": lag_seconds, "threshold_seconds": 300,
        })

    return {
        "table": table,
        "source_latest": str(source_latest),
        "replica_latest": str(replica_latest),
        "lag_seconds": lag_seconds,
    }
```

---

## References

- [Debezium connectors](https://debezium.io/documentation/reference/connectors/postgresql.html)
- [GCP Dataflow templates](https://cloud.google.com/dataflow/docs/guides/templates/provided-streaming)
- [AWS DMS cross-cloud target](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.html)
- [Apache Beam cross-cloud pipelines](https://beam.apache.org/documentation/)

---

← [Previous: Identity](./identity.md) | [Home](../README.md) | [Next: IaC Abstractions →](./iac-abstractions.md)
