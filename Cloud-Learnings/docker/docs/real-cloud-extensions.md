# Real Cloud Extensions

How to extend labs to use real AWS, Azure, or GCP.

**WARNING**: Real cloud usage costs money. Always set budget alerts before starting. See [COST-SAFETY.md](../COST-SAFETY.md).

---

## Real AWS

### Setup

1. Create an AWS account (or use a practice account)
2. Create an IAM user with limited permissions (never use root)
3. Get access key and secret key

```bash
# Add to .env (NEVER commit this file)
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_DEFAULT_REGION=us-east-1
AWS_ENDPOINT_URL=     # Leave empty to use real AWS
```

### Switching Between LocalStack and Real AWS

The `AWS_ENDPOINT_URL` environment variable controls which endpoint to use:

```bash
# Use LocalStack
export AWS_ENDPOINT_URL=http://localhost:4566
aws s3 ls

# Use real AWS (clear the variable)
unset AWS_ENDPOINT_URL
aws s3 ls
```

In Terraform:
```hcl
# Real AWS provider (no endpoint overrides)
provider "aws" {
  region = "us-east-1"
  # Credentials from environment or ~/.aws/credentials
}
```

### Recommended Permissions for Practice

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:*",
      "sqs:*",
      "sns:*",
      "dynamodb:*",
      "lambda:*",
      "iam:PassRole"
    ],
    "Resource": "*"
  }]
}
```

**Better**: Use separate IAM users per service to practice least-privilege.

---

## Real Azure

### Setup

1. Create an Azure account (or use a practice subscription)
2. Create a Service Principal for CLI access

```bash
# Login
az login

# Or use Service Principal
az login --service-principal \
  --username APP_ID \
  --password CLIENT_SECRET \
  --tenant TENANT_ID
```

### Switching Between Azurite and Real Azure

```bash
# Use Azurite
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;..."

# Use real Azure
unset AZURE_STORAGE_CONNECTION_STRING
az login
# Now az storage commands use real Azure
```

### Create a Practice Resource Group

```bash
az group create --name cloud-learnings-practice --location eastus
# Always delete when done:
az group delete --name cloud-learnings-practice --yes
```

---

## Real GCP

### Setup

1. Create a GCP project
2. Enable required APIs
3. Create a service account

```bash
# Authenticate
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Create service account
gcloud iam service-accounts create practice-sa \
  --display-name "Practice Service Account"
```

### Switching Between Emulator and Real GCP

```bash
# Use emulator
export PUBSUB_EMULATOR_HOST=localhost:8085

# Use real GCP
unset PUBSUB_EMULATOR_HOST
# Now Pub/Sub SDK uses real GCP
```

---

## Best Practices for Real Cloud Practice

1. **Always use a dedicated practice account** — never your personal/work production account

2. **Set budget alerts FIRST** — before starting any real cloud lab:
   ```bash
   # AWS: set $5 monthly budget alert
   # Azure: set $5 monthly budget alert
   # GCP: set $5 monthly budget alert
   ```

3. **Tag everything** with:
   - `project: cloud-learnings-practice`
   - `owner: your-name`
   - `expires: YYYY-MM-DD`

4. **Use scripts for cleanup** — have a destroy/cleanup script ready before you start

5. **Prefer IaC** — use Terraform so you can `terraform destroy` when done

6. **Time-box your sessions** — set a timer, clean up before the session ends

7. **Review costs daily** — check the billing console after each session

8. **Use free tier when possible** — but know the limits

---

## Hybrid Mode: Local + Real Cloud

You can run the local platform alongside real cloud usage:

```bash
# Local services for tooling
./run.sh start core observability

# Real AWS for the actual practice target
export AWS_DEFAULT_REGION=us-east-1
unset AWS_ENDPOINT_URL
aws s3 ls  # Lists real S3 buckets

# Local Grafana shows metrics from your apps
# Local Loki aggregates logs
# Real AWS S3/DynamoDB for storage
```

This is a realistic hybrid setup that mirrors how teams use cloud services.
