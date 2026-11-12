# Solution — Databases

## PostgreSQL Transaction Example

```sql
BEGIN;

INSERT INTO app.users(username, email) VALUES('dave', 'dave@example.local');
INSERT INTO app.orders(user_id, amount, status)
  SELECT id, 49.99, 'pending' FROM app.users WHERE username='dave';

-- Check before committing
SELECT u.username, o.amount, o.status
FROM app.users u JOIN app.orders o ON u.id = o.user_id
WHERE u.username='dave';

COMMIT;
```

## PostgreSQL EXPLAIN ANALYZE

```sql
EXPLAIN ANALYZE SELECT * FROM app.users WHERE email='alice@example.local';

-- Expected output shows:
-- Index Scan using idx_users_email on users (cost=0.14..8.16 rows=1 width=...)
--   Actual time: 0.005..0.006 rows=1 loops=1
```

## MongoDB Aggregation Pipeline

```javascript
db.events.aggregate([
  // Stage 1: Filter unprocessed
  { $match: { processed: false } },
  // Stage 2: Group by type and count
  { $group: { _id: "$type", count: { $sum: 1 }, latest: { $max: "$timestamp" } } },
  // Stage 3: Sort by count
  { $sort: { count: -1 } }
])
```

## Redis Pub/Sub Example

```bash
# Terminal 1 (subscriber):
docker exec -it cloud-learnings-redis redis-cli -a redispassword123
SUBSCRIBE events

# Terminal 2 (publisher):
docker exec -it cloud-learnings-redis redis-cli -a redispassword123
PUBLISH events "order.created:ORD-001"
# Terminal 1 will show:
# 1) "message"
# 2) "events"
# 3) "order.created:ORD-001"
```

## Connection Error Reference

| Error | Cause | Fix |
|---|---|---|
| `FATAL: password authentication failed` | Wrong password | Use labpassword123 |
| `Connection refused` | Port wrong or service down | Check port, `./run.sh start data` |
| `FATAL: database does not exist` | Wrong database name | Use `labdb` |
| `role "username" does not exist` | Wrong username | Use `labuser` |
