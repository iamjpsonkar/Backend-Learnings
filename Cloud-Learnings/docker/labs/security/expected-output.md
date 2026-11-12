# Expected Output — Security

## Vault KV Get

```
======== Secret Path ========
secret/data/myapp/config

======= Metadata =======
created_time          2024-01-01T12:00:00Z
current_version       1

====== Data ======
Key             Value
---             -----
api_key         abc123
db_password     mysecretpassword
```

## Trivy Image Scan

```
nginx:alpine (alpine 3.19.0)
=========================
Total: 3 (UNKNOWN: 0, LOW: 1, MEDIUM: 1, HIGH: 1, CRITICAL: 0)
```

## Checkov Scan

```
Passed checks: 10, Failed checks: 3, Skipped checks: 0

Check: CKV_AWS_18: "Ensure the S3 bucket has access logging enabled"
  FAILED for resource: aws_s3_bucket.example
```

## Hadolint Output

```
/workspace/sample-api/Dockerfile:3 DL3008 warning: Pin versions in apt get install. Instead of `apt-get install <package>` use `apt-get install <package>=<version>`
/workspace/sample-api/Dockerfile:5 DL3015 info: Avoid additional packages by specifying `--no-install-recommends`
```
