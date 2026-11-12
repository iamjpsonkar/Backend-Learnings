# Broken Scenario: Database Connection

**Difficulty**: Intermediate
**Profile**: `data apps`

---

## Scenario

The sample-api is returning 500 errors on all database-related endpoints. The container is running and healthy. Your job: find and fix the root cause.

---

## Setup

The issue is already present — just start the services:

```bash
./run.sh start data apps
```

Test that it is broken:
```bash
curl http://localhost:8000/items
# Expected: 500 Internal Server Error
```

---

## Constraints

- Do NOT restart the database container
- Do NOT modify the Python code
- You may modify environment variables and compose configuration
- The fix should be persistent (survives container restart)

---

## Clues

1. The `/health` endpoint returns 200 — but what does the response body say?
2. Check the application logs for the actual error message
3. Compare `DATABASE_URL` in the environment vs what the app expects
4. Check if the database is accepting connections

---

## Investigation commands

```bash
# Check container logs
docker logs cloud-learnings-lab-sample-api-1 --tail 50

# Check environment variables
docker exec cloud-learnings-lab-sample-api-1 env | grep -i db

# Test database connection manually
docker exec cloud-learnings-lab-postgres-1 \
  psql -U appuser -d appdb -c "SELECT 1"

# Check if DNS resolves inside the API container
docker exec cloud-learnings-lab-sample-api-1 \
  nslookup postgres
```

---

## What is broken?

The `DATABASE_URL` environment variable has an intentional bug. Find it.

---

## Solution validation

```bash
curl http://localhost:8000/items
# Must return: {"items": [...], "count": N}

curl http://localhost:8000/health
# Must return: {"status": "ok", "database": "connected"}
```
