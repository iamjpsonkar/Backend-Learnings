# Troubleshooting — AWS with LocalStack

## LocalStack not responding

```bash
# Check if container is running
docker ps | grep localstack

# Check logs
docker logs cloud-learnings-localstack --tail=50

# Check health
curl http://localhost:4566/_localstack/health
```

Wait up to 60 seconds on first start for service initialization.

## Error: Could not connect to the endpoint URL

Make sure you always pass `--endpoint-url=http://localhost:4566`:

```bash
# Wrong:
aws s3 ls

# Correct:
aws --endpoint-url=http://localhost:4566 s3 ls
```

Or set as environment variable:
```bash
export AWS_ENDPOINT_URL=http://localhost:4566
```

## Error: InvalidClientTokenId

Use fake credentials for LocalStack:
```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
```

## Lambda function not found

Free tier LocalStack has limited Lambda support.
Lambda requires the `local` executor mode.
Check `LAMBDA_EXECUTOR=local` in docker-compose.yml environment section.

## Bucket already exists

LocalStack persists between restarts using the volume. If a bucket already exists:

```bash
# List and delete
aws --endpoint-url=http://localhost:4566 s3 rb s3://my-practice-bucket --force
```

## Reset LocalStack to clean state

```bash
# Stop and remove the container + volume
docker stop cloud-learnings-localstack
docker volume rm cloud-learnings-localstack-data
./run.sh start aws
```
