# Object Storage — Beginner

**Difficulty**: Beginner
**Profile**: `aws` (or `data` for MinIO)
**Time estimate**: 45–60 minutes

---

## Scenario

Object storage (S3, MinIO, Azure Blob, GCS) is the most-used cloud service. Master the patterns: upload, download, signed URLs, versioning, lifecycle rules.

---

## Setup

```bash
./run.sh start aws

# Configure CLI for LocalStack
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

---

## Tasks

### Task 1 — Bucket setup

```bash
# Create a versioned bucket
# Enable versioning on it
# Confirm versioning is enabled
```

Expected: `aws s3api get-bucket-versioning` returns `Status: Enabled`

### Task 2 — Upload and version

```bash
# Upload a file called "config.json" with content {"version": 1}
# Upload the same key again with content {"version": 2}
# List all versions of the object
# Download version 1 (the old one)
```

### Task 3 — Bucket policy (public read)

Write a bucket policy that allows anyone to read objects.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::YOUR_BUCKET/*"
  }]
}
```

Apply it and verify.

### Task 4 — Presigned URLs

Generate a presigned URL for an object that expires in 60 seconds.

```bash
aws s3 presign s3://YOUR_BUCKET/config.json --expires-in 60
```

Test it with `curl`. Does it work? Does it expire?

### Task 5 — Lifecycle rules

Set a lifecycle rule that:
- Moves objects to `STANDARD_IA` after 30 days
- Deletes objects after 90 days

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket YOUR_BUCKET \
  --lifecycle-configuration file://lifecycle.json
```

Write the `lifecycle.json` file first.

### Task 6 — Server-side copy

Copy an object to a different key (without downloading):

```bash
aws s3 cp s3://YOUR_BUCKET/config.json s3://YOUR_BUCKET/backup/config.json
```

### Task 7 — Sync a directory

Create a local directory with 3 files. Sync it to S3:

```bash
aws s3 sync ./local-dir/ s3://YOUR_BUCKET/uploads/
```

Then sync again after adding a file. Only the new file should be uploaded.

---

## Success criteria

- [ ] Versioning enabled and old version retrieved
- [ ] Bucket policy applied
- [ ] Presigned URL generated and tested with curl
- [ ] Lifecycle rule JSON written and applied
- [ ] Cross-key copy performed without local download
- [ ] Directory sync with incremental upload
