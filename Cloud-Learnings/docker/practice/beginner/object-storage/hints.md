# Hints — Object Storage

---

## Hint 1 — Enable versioning

```bash
aws s3api create-bucket --bucket my-versioned-bucket
aws s3api put-bucket-versioning \
  --bucket my-versioned-bucket \
  --versioning-configuration Status=Enabled
aws s3api get-bucket-versioning --bucket my-versioned-bucket
```

---

## Hint 2 — List versions

```bash
aws s3api list-object-versions --bucket my-versioned-bucket --prefix config.json
```

Output includes `Versions[]` (current + old) and `DeleteMarkers[]`.

To download a specific version:
```bash
aws s3api get-object \
  --bucket my-versioned-bucket \
  --key config.json \
  --version-id THE_VERSION_ID \
  config-v1.json
```

---

## Hint 3 — Lifecycle JSON

```json
{
  "Rules": [
    {
      "ID": "archive-and-expire",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        }
      ],
      "Expiration": {
        "Days": 90
      }
    }
  ]
}
```

> LocalStack does not enforce lifecycle rules in real-time, but accepts the configuration.

---

## Hint 4 — Presigned URL test

```bash
URL=$(aws s3 presign s3://my-versioned-bucket/config.json --expires-in 60)
curl -s "$URL"
# Returns the object content

sleep 65
curl -s "$URL"
# Returns AccessDenied (expired)
```

---

## Hint 5 — Sync behavior

`aws s3 sync` compares ETags and only uploads changed/new files.
Use `--delete` flag to remove remote objects that no longer exist locally:
```bash
aws s3 sync ./local-dir/ s3://my-bucket/uploads/ --delete
```
