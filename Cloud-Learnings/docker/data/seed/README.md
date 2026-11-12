# Seed Data

Sample data files for populating databases during lab exercises.

---

## Files

| File | Purpose | Rows |
|---|---|---|
| `users.json` | Sample user accounts (5 users, 3 tiers) | 5 |
| `products.json` | Sample product catalog (electronics + furniture) | 7 |

---

## Usage

### Load into PostgreSQL
```bash
# Using psql COPY from JSON (requires pg_read_file or stdin)
cat data/seed/users.json | docker exec -i cloud-learnings-lab-postgres-1 \
  psql -U appuser -d appdb -c "COPY users FROM STDIN WITH (FORMAT json)"

# Or using a Python script
python3 scripts/load-seed.py --db postgres --file data/seed/users.json
```

### Load into MongoDB
```bash
docker exec -i cloud-learnings-lab-mongodb-1 \
  mongoimport --db appdb --collection users \
  --file /dev/stdin --jsonArray < data/seed/users.json
```

### Load into Redis (as hash set)
```bash
cat data/seed/users.json | python3 -c "
import json, sys, subprocess
for u in json.load(sys.stdin):
    key = f'user:{u[\"user_id\"]}'
    for k, v in u.items():
        if isinstance(v, dict):
            continue  # skip nested objects
        subprocess.run(['docker', 'exec', 'cloud-learnings-lab-redis-1',
                       'redis-cli', 'hset', key, k, str(v)])
"
```

---

## Data schema

### users
- `user_id` — string, unique key
- `name` — full name
- `email` — local domain (@example.local, not real)
- `tier` — standard | premium | enterprise
- `created_at` — ISO 8601 timestamp
- `address` — nested object (city, country)

### products
- `product_id` — string, unique key
- `name` — product display name
- `category` — electronics | furniture
- `price` — float, USD
- `stock` — integer, available quantity
- `sku` — stock keeping unit
- `weight_kg` — float
