← [Previous: Multi-Cloud Overview](./README.md) | [Home](../README.md) | [Next: Networking →](./networking.md)

---

# Multi-Cloud Strategy

A multi-cloud strategy starts with a clear answer to: **which workloads belong on which cloud and why?** Without that answer, you get accidental complexity instead of intentional architecture.

---

## Workload Placement Framework

### Placement Decision Matrix

```
                    │  AWS Advantage     │  GCP Advantage    │  Azure Advantage
────────────────────┼────────────────────┼───────────────────┼──────────────────
Compute (general)   │  ✓ Widest choice   │  ✓ Good           │  ✓ Good
ML / AI             │  ✓ SageMaker       │  ✓✓ Best (TPUs)   │  ✓ OpenAI partner
Analytics / DWH     │  ✓ Redshift        │  ✓✓ BigQuery      │  ✓ Synapse
Kubernetes          │  ✓ EKS             │  ✓✓ GKE (orig.)   │  ✓ AKS
Enterprise identity │  ✓ Cognito         │  ✓ IAP            │  ✓✓ Entra ID
SAP workloads       │  ✓                 │  –                │  ✓✓ Certified
Serverless          │  ✓✓ Lambda         │  ✓ Cloud Run       │  ✓ Functions
CDN / Edge          │  ✓ CloudFront      │  ✓ Cloud CDN       │  ✓ Front Door
Hybrid (on-prem)    │  ✓ Outposts        │  ✓ Distributed     │  ✓✓ Arc
```

### Workload Classification

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CloudProvider(str, Enum):
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "Azure"
    HYBRID = "Hybrid"


@dataclass
class WorkloadRequirements:
    name: str
    primary_use_case: str        # "ml", "analytics", "compute", "identity", "sap"
    existing_aws_deps: bool      # heavy dependency on existing AWS services
    azure_ad_required: bool      # requires Azure Entra ID / Active Directory
    ml_training_needed: bool     # large-scale ML training workloads
    bigquery_analytics: bool     # BI/analytics that benefits from BigQuery
    on_prem_connectivity: bool   # needs ExpressRoute / Direct Connect to on-prem
    regulatory_region: Optional[str] = None  # specific region requirement


def recommend_cloud(req: WorkloadRequirements) -> tuple[CloudProvider, str]:
    """
    Return (recommended_cloud, rationale).
    Override with engineering judgment — this is a starting point.
    """
    if req.existing_aws_deps:
        return CloudProvider.AWS, "Existing AWS service dependencies reduce migration cost"

    if req.azure_ad_required:
        return CloudProvider.AZURE, "Azure Entra ID integration required for enterprise identity"

    if req.ml_training_needed:
        return CloudProvider.GCP, "GCP TPUs and Vertex AI provide best ML training economics"

    if req.bigquery_analytics:
        return CloudProvider.GCP, "BigQuery serverless analytics with no cluster management"

    if req.on_prem_connectivity and req.existing_aws_deps:
        return CloudProvider.HYBRID, "On-prem + AWS with Direct Connect"

    # Default: AWS for broadest service coverage
    return CloudProvider.AWS, "Default: widest service selection and ecosystem"


# Example classification
workloads = [
    WorkloadRequirements("order-api", "compute", True, False, False, False, False),
    WorkloadRequirements("fraud-detection-model", "ml", False, False, True, False, False),
    WorkloadRequirements("bi-reporting", "analytics", False, False, False, True, False),
    WorkloadRequirements("employee-portal", "identity", False, True, False, False, True),
]

for w in workloads:
    cloud, reason = recommend_cloud(w)
    print(f"{w.name:30s} → {cloud.value:6s} ({reason})")
```

---

## Vendor Lock-In Analysis

### Lock-In Risk by Service Category

```
High lock-in risk (avoid or abstract):
  ├── Proprietary message queues     (SQS/SNS vs Pub/Sub vs Service Bus)
  ├── Managed Kubernetes add-ons     (EKS addons, GKE Autopilot features)
  ├── Provider-specific DBaaS        (DynamoDB, Firestore, CosmosDB)
  ├── Serverless functions           (Lambda, Cloud Functions, Azure Functions)
  └── ML platform features           (SageMaker Pipelines, Vertex AI)

Medium lock-in risk (use with awareness):
  ├── Managed Kubernetes (EKS/GKE/AKS)  — cluster stays portable
  ├── Managed RDS (PostgreSQL)           — engine is open-source
  ├── Object storage (S3/GCS/Azure Blob) — APIs differ but tools bridge them
  └── Container registries               — images are portable

Low lock-in risk (safe to use freely):
  ├── VMs / compute instances            — workloads are portable
  ├── Standard Kubernetes workloads      — Helm charts deploy anywhere
  ├── PostgreSQL / MySQL                 — open-source, provider-independent
  ├── Standard networking (VPC/subnets)  — concepts port across providers
  └── Containers (Docker OCI images)     — truly portable
```

### Portability Layer Pattern

```python
"""
Abstract cloud storage behind a common interface.
Concrete implementations for each cloud — swap by config.
"""

import logging
from abc import ABC, abstractmethod
from io import BytesIO

logger = logging.getLogger(__name__)


class ObjectStorage(ABC):
    """Cloud-agnostic object storage interface."""

    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload object. Returns URL or URI."""

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Download object."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete object."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if object exists."""


class S3Storage(ObjectStorage):
    """AWS S3 implementation."""

    def __init__(self, bucket: str):
        import boto3
        self._s3 = boto3.client("s3")
        self._bucket = bucket
        logger.info("S3Storage initialized", extra={"bucket": bucket})

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        logger.debug("S3 put complete", extra={"bucket": self._bucket, "key": key, "size": len(data)})
        return f"s3://{self._bucket}/{key}"

    async def get(self, key: str) -> bytes:
        response = self._s3.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    async def delete(self, key: str) -> None:
        self._s3.delete_object(Bucket=self._bucket, Key=key)

    async def exists(self, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=self._bucket, Key=key)
            return True
        except self._s3.exceptions.ClientError:
            return False


class GCSStorage(ObjectStorage):
    """GCP Cloud Storage implementation."""

    def __init__(self, bucket: str):
        from google.cloud import storage
        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket)
        logger.info("GCSStorage initialized", extra={"bucket": bucket})

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        blob = self._bucket.blob(key)
        blob.upload_from_string(data, content_type=content_type)
        logger.debug("GCS put complete", extra={"key": key, "size": len(data)})
        return f"gs://{self._bucket.name}/{key}"

    async def get(self, key: str) -> bytes:
        blob = self._bucket.blob(key)
        return blob.download_as_bytes()

    async def delete(self, key: str) -> None:
        blob = self._bucket.blob(key)
        blob.delete()

    async def exists(self, key: str) -> bool:
        blob = self._bucket.blob(key)
        return blob.exists()


def create_storage(provider: str, bucket: str) -> ObjectStorage:
    """Factory: create the right storage implementation from config."""
    providers = {"aws": S3Storage, "gcp": GCSStorage}
    cls = providers.get(provider.lower())
    if cls is None:
        raise ValueError(f"Unknown storage provider: {provider}. Supported: {list(providers)}")
    return cls(bucket)
```

---

## Cost Model

### Cross-Cloud Data Transfer Costs

```python
def estimate_cross_cloud_transfer_cost(
    monthly_gb: float,
    source_provider: str = "aws",
    dest_provider: str = "gcp",
) -> dict:
    """
    Rough estimate of cross-cloud data transfer costs.
    Prices vary by region and are updated frequently — verify at provider pricing pages.
    """
    # Egress costs (approximate, USD/GB, as of 2024)
    egress_rates = {
        "aws": 0.09,     # AWS internet egress after first 100 GB/month
        "gcp": 0.08,     # GCP egress to internet (US regions)
        "azure": 0.087,  # Azure egress (first 10 TB/month)
    }

    egress_rate = egress_rates.get(source_provider.lower(), 0.09)
    egress_cost = monthly_gb * egress_rate

    # Ingress is typically free (destination provider charges egress when data leaves)
    ingress_cost = 0.0

    return {
        "monthly_gb": monthly_gb,
        "egress_cost_usd": round(egress_cost, 2),
        "ingress_cost_usd": ingress_cost,
        "total_monthly_usd": round(egress_cost + ingress_cost, 2),
        "annual_usd": round((egress_cost + ingress_cost) * 12, 2),
        "note": "Verify current pricing — rates change and vary by region",
    }


# Example: streaming 500 GB/month from AWS to GCP for analytics
costs = estimate_cross_cloud_transfer_cost(500, "aws", "gcp")
print(f"Monthly transfer cost: ${costs['total_monthly_usd']:.2f}")
print(f"Annual transfer cost:  ${costs['annual_usd']:.2f}")
```

---

## References

- [AWS multi-cloud whitepaper](https://docs.aws.amazon.com/whitepapers/latest/aws-multi-cloud/)
- [FinOps Foundation — Multi-cloud cost management](https://www.finops.org/framework/)
- [Cloud Native Glossary — Multi-cloud](https://glossary.cncf.io/multicloud/)

---

← [Previous: Multi-Cloud Overview](./README.md) | [Home](../README.md) | [Next: Networking →](./networking.md)
