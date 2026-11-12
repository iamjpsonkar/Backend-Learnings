# Multi-Cloud Local — Advanced

**Difficulty**: Advanced
**Profile**: `cloud observability`
**Time estimate**: 3–4 hours

---

## Scenario

Build a multi-cloud application that uses services from AWS (LocalStack), Azure (Azurite), and GCP emulators simultaneously. This mirrors real architectures that span multiple clouds.

---

## Setup

```bash
./run.sh start cloud observability
./run.sh status
```

---

## Architecture to build

```
Application
├── User data → PostgreSQL (local)
├── File uploads → MinIO / Azurite Blob Storage
├── Events → LocalStack SQS + SNS
├── State cache → Redis
├── Pub/Sub notifications → GCP Pub/Sub emulator
└── Metrics → Prometheus / Grafana
```

---

## Tasks

### Task 1 — Verify all cloud emulators

```bash
# AWS LocalStack
aws --endpoint-url http://localhost:4566 s3 ls

# Azure Azurite
az storage container list \
  --connection-string "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCD7P65AddFCfRZRjNRQDqVMWCjKBXpEkYnvGlW1CqNMpKrNsN0sKsQ==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"

# GCP Pub/Sub emulator
curl http://localhost:8085/v1/projects/local-project/topics
```

All should return without error.

### Task 2 — Multi-cloud file storage

Write a Python script `multi-cloud-upload.py` that:
1. Accepts a file path as argument
2. Uploads to LocalStack S3: `s3://files-aws/uploads/{filename}`
3. Uploads to Azurite: container `files-azure`, blob `{filename}`
4. Logs upload success/failure for each cloud with timing

```python
import boto3
from azure.storage.blob import BlobServiceClient
import logging
import time
import sys

logger = logging.getLogger(__name__)
```

### Task 3 — Event fan-out across clouds

Build an event pipeline:
1. Publish event to LocalStack SNS topic
2. SNS fan-out to SQS queue (AWS consumer)
3. SNS fan-out to HTTP endpoint that re-publishes to GCP Pub/Sub

Write both the publisher and the cross-cloud bridge.

### Task 4 — Cloud-agnostic abstraction

Create `storage.py` with a `CloudStorage` interface:

```python
from abc import ABC, abstractmethod

class CloudStorage(ABC):
    @abstractmethod
    def upload(self, key: str, data: bytes) -> str:
        """Upload data. Returns URL."""
        ...

    @abstractmethod
    def download(self, key: str) -> bytes:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...

class S3Storage(CloudStorage):
    # LocalStack implementation
    ...

class AzureBlobStorage(CloudStorage):
    # Azurite implementation
    ...
```

Write both implementations and a test that runs the same operations against both.

### Task 5 — Cost simulation

Using the sample bill data in `data/sample-bills/`, analyze:
- Which cloud service has the highest cost?
- Which resources are untagged (potential orphans)?
- Estimate monthly cost if usage doubles

Write your findings in `data/sample-bills/analysis.md`.

### Task 6 — Observability across clouds

All cloud operations should be traced. Configure:
- Each cloud SDK call emits an OTel span
- Spans include: cloud provider, service name, operation, latency, success/failure
- Traces visible in Tempo grouped by `cloud.provider`

---

## Success criteria

- [ ] All three cloud emulators verified working
- [ ] File uploaded to both S3 and Azurite successfully
- [ ] Event fan-out pipeline working end-to-end
- [ ] CloudStorage abstraction with both implementations passing same tests
- [ ] Cost analysis written from sample bills
- [ ] OTel traces showing spans for each cloud provider
