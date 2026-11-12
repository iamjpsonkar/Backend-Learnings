# Broken Scenario: DNS Resolution Failure

## Scenario

A containerized application cannot reach its database. The error log shows:

```
ERROR: Could not connect to database: Name or service not known
Connection string: postgresql://labuser:labpassword123@db.internal:5432/labdb
```

The application and database are both running. They worked yesterday.

## Your Task

1. Diagnose why DNS resolution is failing
2. Identify the root cause
3. Fix the issue without recreating containers

## Setup

```bash
# This creates the broken scenario
docker network create broken-net
docker run -d --name broken-db --network broken-net postgres:16-alpine \
  -e POSTGRES_PASSWORD=labpassword123

docker run -d --name broken-app --network broken-net alpine \
  sh -c "while true; do nslookup db.internal; sleep 5; done"
```

## Hints (read if stuck)

1. What is the hostname the app is trying to resolve?
2. What is the actual container name?
3. How does Docker DNS work with custom networks?

## Solution

The app is trying to resolve `db.internal` but the container is named `broken-db`.
Docker DNS resolves container names, not custom hostnames (unless you use `--hostname` or `--network-alias`).

Fix:
```bash
# Option 1: Use correct container name in connection string
# Change "db.internal" to "broken-db"

# Option 2: Add a network alias
docker network connect --alias db.internal broken-net broken-db

# Option 3: Use --hostname when creating the DB container
docker run -d --name broken-db --hostname db.internal --network broken-net postgres:16-alpine -e POSTGRES_PASSWORD=labpassword123
```

## Cleanup

```bash
docker stop broken-app broken-db
docker rm broken-app broken-db
docker network rm broken-net
```
