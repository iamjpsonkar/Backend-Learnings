← [Previous: Cloud Scheduler](./cloud-scheduler.md) | [Home](../../README.md) | [Next: GCP Security →](../09-security/README.md)

---

# Cloud Tasks

Cloud Tasks manages the execution of distributed, asynchronous tasks. Use it for deferred work, rate-limited task dispatch, deduplication, and guaranteed delivery to HTTP endpoints.

---

## Queues and Tasks

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"
SERVICE_URL="https://my-app-worker-abc123-uc.a.run.app"

# Create a queue
gcloud tasks queues create email-queue \
    --project=$PROJECT \
    --location=$REGION \
    --max-dispatches-per-second=100 \
    --max-concurrent-dispatches=1000 \
    --max-attempts=5 \
    --min-backoff=10s \
    --max-backoff=3600s \
    --max-doublings=5

# List queues
gcloud tasks queues list \
    --project=$PROJECT \
    --location=$REGION

# Pause / resume a queue
gcloud tasks queues pause email-queue \
    --project=$PROJECT \
    --location=$REGION

gcloud tasks queues resume email-queue \
    --project=$PROJECT \
    --location=$REGION

# Purge all tasks from a queue
gcloud tasks queues purge email-queue \
    --project=$PROJECT \
    --location=$REGION

# Describe a queue (check backlog)
gcloud tasks queues describe email-queue \
    --project=$PROJECT \
    --location=$REGION
```

---

## Python SDK

```python
import json
import logging
import os
import hashlib
import datetime
from typing import Any
from google.cloud import tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2

logger = logging.getLogger(__name__)

PROJECT = os.environ["GCP_PROJECT"]
REGION = os.environ.get("TASKS_REGION", "us-central1")
QUEUE_NAME = os.environ["TASKS_QUEUE"]
WORKER_URL = os.environ["WORKER_URL"]
SERVICE_ACCOUNT_EMAIL = os.environ["TASKS_SA_EMAIL"]

client = tasks_v2.CloudTasksClient()
QUEUE_PATH = client.queue_path(PROJECT, REGION, QUEUE_NAME)


def enqueue_task(
    payload: dict[str, Any],
    *,
    task_id: str | None = None,
    delay_seconds: int = 0,
    deadline_seconds: int = 600,
) -> str:
    """Enqueue an HTTP task. Returns task name.

    Args:
        payload: JSON-serialisable task data.
        task_id: Deterministic ID for deduplication (optional). If a task with
                 the same ID was created in the last ~1 hour it will not be
                 re-created (idempotency).
        delay_seconds: Delay before the task becomes eligible for dispatch.
        deadline_seconds: Max time the worker has to finish processing.
    """
    logger.info(
        "Enqueueing task",
        extra={
            "queue": QUEUE_NAME,
            "task_id": task_id,
            "delay_seconds": delay_seconds,
            "payload_keys": list(payload.keys()),
        },
    )

    task: dict = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{WORKER_URL}/tasks/process",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode("utf-8"),
            "oidc_token": {
                "service_account_email": SERVICE_ACCOUNT_EMAIL,
                "audience": WORKER_URL,
            },
        },
    }

    # Optional deterministic task ID for deduplication
    if task_id:
        task["name"] = f"{QUEUE_PATH}/tasks/{task_id}"

    # Optional schedule time
    if delay_seconds > 0:
        schedule_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay_seconds)
        ts = timestamp_pb2.Timestamp()
        ts.FromDatetime(schedule_time)
        task["schedule_time"] = ts

    # Optional dispatch deadline
    deadline = duration_pb2.Duration()
    deadline.FromSeconds(deadline_seconds)
    task["dispatch_deadline"] = deadline

    response = client.create_task(
        request={"parent": QUEUE_PATH, "task": task}
    )

    task_name = response.name
    logger.info(
        "Task enqueued",
        extra={"task_name": task_name, "queue": QUEUE_NAME},
    )
    return task_name


def enqueue_with_deduplication(
    payload: dict[str, Any],
    idempotency_key: str,
    delay_seconds: int = 0,
) -> str:
    """Enqueue a task with content-based deduplication.

    The task_id is derived from the idempotency_key so the same logical
    operation will not be queued more than once within the dedup window.
    """
    safe_key = hashlib.sha256(idempotency_key.encode()).hexdigest()[:64]
    logger.info(
        "Enqueueing deduplicated task",
        extra={"idempotency_key": idempotency_key, "safe_key": safe_key},
    )
    return enqueue_task(payload, task_id=safe_key, delay_seconds=delay_seconds)
```

---

## Worker Endpoint

```python
import json
import logging
from flask import Flask, request, jsonify, Response

logger = logging.getLogger(__name__)
app = Flask(__name__)


@app.route("/tasks/process", methods=["POST"])
def process_task() -> Response:
    """Cloud Tasks worker endpoint."""
    task_name = request.headers.get("X-CloudTasks-TaskName", "unknown")
    retry_count = int(request.headers.get("X-CloudTasks-TaskRetryCount", "0"))
    queue_name = request.headers.get("X-CloudTasks-QueueName", "unknown")

    logger.info(
        "Task received",
        extra={
            "task_name": task_name,
            "retry_count": retry_count,
            "queue_name": queue_name,
        },
    )

    payload = request.get_json(force=True)
    if not payload:
        logger.warning("Empty task payload", extra={"task_name": task_name})
        return jsonify({"error": "empty payload"}), 400

    try:
        _handle_task(payload, task_name)
        logger.info("Task completed successfully", extra={"task_name": task_name})
        return jsonify({"status": "ok"}), 200
    except Exception as exc:
        logger.error(
            "Task processing failed",
            extra={"task_name": task_name, "retry_count": retry_count, "error": str(exc)},
        )
        # Return 5xx to trigger retry; return 2xx to ack without retry
        if retry_count >= 4:
            logger.error("Max retries reached, dropping task", extra={"task_name": task_name})
            return jsonify({"status": "dropped"}), 200  # Don't retry anymore
        return jsonify({"error": str(exc)}), 500


def _handle_task(payload: dict, task_name: str) -> None:
    """Business logic."""
    task_type = payload.get("type", "unknown")
    logger.info("Processing task", extra={"task_name": task_name, "task_type": task_type})
    # ... your logic here
```

---

## References

- [Cloud Tasks documentation](https://cloud.google.com/tasks/docs)
- [Python client library](https://cloud.google.com/python/docs/reference/cloudtasks/latest)
- [Creating HTTP tasks](https://cloud.google.com/tasks/docs/creating-http-target-tasks)
- [Task deduplication](https://cloud.google.com/tasks/docs/reference/rpc/google.cloud.tasks.v2#createtaskrequest)

---

← [Previous: Cloud Scheduler](./cloud-scheduler.md) | [Home](../../README.md) | [Next: GCP Security →](../09-security/README.md)
