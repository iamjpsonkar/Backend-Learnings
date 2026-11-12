# OpenTofu — LocalStack Infrastructure

Same as `../terraform/` but uses OpenTofu CLI instead of Terraform.

OpenTofu is the open-source fork of Terraform (fully compatible with HCL syntax).

---

## Running

```bash
# Start the platform with aws + iac profiles
./run.sh start aws iac

# Run OpenTofu via Docker
docker run --rm -it \
  --network cloud-learnings-lab_cloud_net \
  -v "$(pwd)/infrastructure/opentofu:/workspace" \
  ghcr.io/opentofu/opentofu:latest \
  -chdir=/workspace init

docker run --rm -it \
  --network cloud-learnings-lab_cloud_net \
  -v "$(pwd)/infrastructure/opentofu:/workspace" \
  ghcr.io/opentofu/opentofu:latest \
  -chdir=/workspace apply -auto-approve
```

Or via the `opentofu` service if you added it to docker-compose:
```bash
docker compose --project-name cloud-learnings-lab run --rm opentofu \
  -chdir=/workspace apply -auto-approve
```

---

## What Gets Created

| Resource | Name | Type |
|---|---|---|
| S3 | cloudlab-app-data | Versioned bucket |
| S3 | cloudlab-backups | Backup bucket |
| SQS | cloudlab-orders | Queue with DLQ |
| SQS | cloudlab-dlq | Dead-letter queue |
| SNS | cloudlab-events | Topic (→SQS subscription) |
| DynamoDB | cloudlab-sessions | Single-key with TTL |
| DynamoDB | cloudlab-inventory | Composite key with GSI |

All resources go to LocalStack — no real AWS charges.

---

## Differences from Terraform

- `tofu` command instead of `terraform`
- Supports state encryption natively (OpenTofu 1.7+)
- May support experimental features before official Terraform

For practice purposes the HCL is identical — switch CLI freely.
