# Broken Scenario: Container Crash on Start

## Scenario

A container keeps restarting. Docker shows `Restarting (1) X seconds ago`.

```bash
docker ps
# CONTAINER ID  IMAGE    COMMAND              STATUS
# abc123        myapp    "python app.py"      Restarting (1) 3 seconds ago
```

## Your Task

1. Find out why the container is crashing
2. Identify the error from logs
3. Fix the issue

## Setup

```bash
# Create the broken app
mkdir -p /tmp/broken-app
cat > /tmp/broken-app/app.py << 'EOF'
import os
import sys

# This app requires a required environment variable
DB_URL = os.environ["DATABASE_URL"]  # Will fail if not set
print(f"Connecting to: {DB_URL}")

# If we get here, simulate running
import time
while True:
    print("App running...")
    time.sleep(10)
EOF

cat > /tmp/broken-app/Dockerfile << 'EOF'
FROM python:3.12-slim
WORKDIR /app
COPY app.py .
CMD ["python", "app.py"]
EOF

cd /tmp/broken-app
docker build -t broken-app .
docker run -d --name broken-app broken-app
# Container will restart
```

## Diagnose

```bash
docker ps -a | grep broken-app
docker logs broken-app
docker inspect broken-app | jq '.[0].State'
```

## Root Cause

The app requires `DATABASE_URL` environment variable but it's not provided.

Python raises `KeyError: 'DATABASE_URL'` which causes exit code 1.

## Fix

```bash
docker rm broken-app
docker run -d --name broken-app \
  -e DATABASE_URL="postgresql://labuser:labpassword123@localhost:5432/labdb" \
  broken-app
docker logs -f broken-app
```

## Cleanup

```bash
docker stop broken-app
docker rm broken-app
docker rmi broken-app
rm -rf /tmp/broken-app
```
