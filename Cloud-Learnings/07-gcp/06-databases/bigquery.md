← [Previous: Memorystore](./memorystore.md) | [Home](../../README.md) | [Next: GCP Containers →](../07-containers/README.md)

---

# BigQuery

BigQuery is GCP's serverless, fully managed data warehouse. It scales to petabytes, supports standard SQL, and charges per query (bytes scanned) or flat-rate reservations.

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Dataset** | Container for tables and views (like a schema/database) |
| **Table** | Columnar storage — native, external, or materialized view |
| **Partition** | Split a table by date/column for cost-efficient queries |
| **Cluster** | Sort data within partitions for further pruning |
| **Slot** | Unit of BigQuery compute (1 slot = 0.5 vCPU) |
| **Job** | Asynchronous operation: query, load, export, copy |

---

## Dataset and Table Management

```bash
PROJECT="my-app-prod-123456"
DATASET="my_app_analytics"
LOCATION="US"

# Create a dataset
bq mk \
    --project_id=$PROJECT \
    --dataset \
    --location=$LOCATION \
    --description="Analytics data for my-app" \
    --default_table_expiration=0 \
    $PROJECT:$DATASET

# Create a partitioned + clustered table
bq mk \
    --project_id=$PROJECT \
    --table \
    --time_partitioning_type=DAY \
    --time_partitioning_field=event_timestamp \
    --clustering_fields=user_id,event_type \
    --description="App events" \
    $PROJECT:$DATASET.events \
    event_timestamp:TIMESTAMP,user_id:STRING,event_type:STRING,properties:JSON,session_id:STRING

# Load data from GCS (JSON)
bq load \
    --project_id=$PROJECT \
    --source_format=NEWLINE_DELIMITED_JSON \
    --autodetect \
    $PROJECT:$DATASET.events \
    gs://my-app-prod-data/events/2024-06-15/*.json

# Load from GCS (Parquet — most efficient)
bq load \
    --project_id=$PROJECT \
    --source_format=PARQUET \
    $PROJECT:$DATASET.events \
    "gs://my-app-prod-data/events/dt=2024-06-15/*.parquet"

# List tables
bq ls --project_id=$PROJECT $PROJECT:$DATASET

# Show table schema
bq show --format=prettyjson $PROJECT:$DATASET.events | jq '.schema'

# Delete a table
bq rm --project_id=$PROJECT --table $PROJECT:$DATASET.old_table
```

---

## Querying

```bash
# Run a query from CLI
bq query \
    --project_id=$PROJECT \
    --use_legacy_sql=false \
    --nouse_cache \
    "SELECT event_type, COUNT(*) as cnt
     FROM \`$PROJECT.$DATASET.events\`
     WHERE DATE(event_timestamp) = CURRENT_DATE()
     GROUP BY 1 ORDER BY 2 DESC LIMIT 10"

# Dry run — estimate bytes scanned (cost estimate)
bq query \
    --project_id=$PROJECT \
    --use_legacy_sql=false \
    --dry_run \
    "SELECT * FROM \`$PROJECT.$DATASET.events\` WHERE DATE(event_timestamp) = '2024-06-15'"
# Output: Query successfully validated. Bytes processed: 1234567890

# Write query results to a table
bq query \
    --project_id=$PROJECT \
    --use_legacy_sql=false \
    --destination_table=$PROJECT:$DATASET.daily_summary \
    --replace \
    "SELECT DATE(event_timestamp) as date, event_type, COUNT(*) as cnt
     FROM \`$PROJECT.$DATASET.events\`
     GROUP BY 1, 2"
```

---

## Useful SQL Patterns

```sql
-- Cost optimization: always filter on partition column first
SELECT user_id, event_type, COUNT(*) as events
FROM `my-app-prod-123456.my_app_analytics.events`
WHERE DATE(event_timestamp) BETWEEN '2024-06-01' AND '2024-06-15'  -- Partition pruning
  AND event_type IN ('purchase', 'add_to_cart')                     -- Cluster pruning
GROUP BY 1, 2;

-- Session analysis with window functions
SELECT
  user_id,
  session_id,
  MIN(event_timestamp) AS session_start,
  MAX(event_timestamp) AS session_end,
  TIMESTAMP_DIFF(MAX(event_timestamp), MIN(event_timestamp), SECOND) AS duration_secs,
  COUNT(*) AS event_count,
  COUNTIF(event_type = 'purchase') AS purchases
FROM `my-app-prod-123456.my_app_analytics.events`
WHERE DATE(event_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY 1, 2;

-- Funnel analysis
WITH funnel AS (
  SELECT
    user_id,
    COUNTIF(event_type = 'page_view') > 0 AS viewed,
    COUNTIF(event_type = 'add_to_cart') > 0 AS added,
    COUNTIF(event_type = 'checkout') > 0 AS checked_out,
    COUNTIF(event_type = 'purchase') > 0 AS purchased
  FROM `my-app-prod-123456.my_app_analytics.events`
  WHERE DATE(event_timestamp) = CURRENT_DATE()
  GROUP BY 1
)
SELECT
  COUNTIF(viewed) AS viewed,
  COUNTIF(added) AS added,
  COUNTIF(checked_out) AS checked_out,
  COUNTIF(purchased) AS purchased,
  ROUND(100.0 * COUNTIF(purchased) / NULLIF(COUNTIF(viewed), 0), 2) AS conversion_rate
FROM funnel;

-- Unnest JSON fields
SELECT
  user_id,
  JSON_VALUE(properties, '$.page') AS page,
  JSON_VALUE(properties, '$.referrer') AS referrer
FROM `my-app-prod-123456.my_app_analytics.events`
WHERE event_type = 'page_view'
  AND DATE(event_timestamp) = CURRENT_DATE();
```

---

## Python SDK

```python
import os
import logging
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

logger = logging.getLogger(__name__)

PROJECT = os.environ["GCP_PROJECT"]
DATASET = os.environ["BQ_DATASET"]

client = bigquery.Client(project=PROJECT)


def run_query(sql: str, job_config: bigquery.QueryJobConfig | None = None) -> list[dict]:
    """Execute a BigQuery SQL query and return results as dicts."""
    logger.info("Running BigQuery query", extra={"bytes_estimate": "pending"})
    job = client.query(sql, job_config=job_config)
    logger.info("Query job submitted", extra={"job_id": job.job_id})

    try:
        results = job.result(timeout=300)
        rows = [dict(row) for row in results]
        logger.info(
            "Query complete",
            extra={"job_id": job.job_id, "rows": len(rows), "bytes_processed": job.total_bytes_processed},
        )
        return rows
    except GoogleAPIError as exc:
        logger.error("Query failed", extra={"job_id": job.job_id, "error": str(exc)})
        raise


def stream_insert(table_id: str, rows: list[dict]) -> None:
    """Stream rows into BigQuery (for real-time ingestion, small batches)."""
    table_ref = f"{PROJECT}.{DATASET}.{table_id}"
    logger.info("Streaming insert", extra={"table": table_ref, "rows": len(rows)})

    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        logger.error("Stream insert errors", extra={"table": table_ref, "errors": errors})
        raise RuntimeError(f"BigQuery insert errors: {errors}")

    logger.info("Stream insert complete", extra={"table": table_ref, "rows": len(rows)})


def load_from_gcs(gcs_uri: str, table_id: str, schema: list[bigquery.SchemaField] | None = None) -> None:
    """Load data from GCS into BigQuery."""
    table_ref = f"{PROJECT}.{DATASET}.{table_id}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=schema is None,
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        time_partitioning=bigquery.TimePartitioning(field="event_timestamp"),
    )

    logger.info("Loading from GCS to BigQuery", extra={"source": gcs_uri, "table": table_ref})
    job = client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
    job.result(timeout=600)

    table = client.get_table(table_ref)
    logger.info("Load complete", extra={"table": table_ref, "rows": table.num_rows})
```

---

## Scheduled Queries

```bash
# Create a scheduled query (runs daily at 02:00 UTC)
bq mk \
    --project_id=$PROJECT \
    --transfer_config \
    --data_source=scheduled_query \
    --display_name="daily-summary" \
    --target_dataset=$DATASET \
    --schedule="every day 02:00" \
    --params='{
        "destination_table_name_template": "daily_summary_{run_date}",
        "write_disposition": "WRITE_TRUNCATE",
        "query": "SELECT DATE(event_timestamp) as date, COUNT(*) as events FROM `'"$PROJECT.$DATASET"'.events` WHERE DATE(event_timestamp) = @run_date GROUP BY 1"
    }'
```

---

## References

- [BigQuery documentation](https://cloud.google.com/bigquery/docs)
- [SQL reference](https://cloud.google.com/bigquery/docs/reference/standard-sql/introduction)
- [Python client library](https://cloud.google.com/python/docs/reference/bigquery/latest)
- [Best practices for cost](https://cloud.google.com/bigquery/docs/best-practices-costs)

---

← [Previous: Memorystore](./memorystore.md) | [Home](../../README.md) | [Next: GCP Containers →](../07-containers/README.md)
