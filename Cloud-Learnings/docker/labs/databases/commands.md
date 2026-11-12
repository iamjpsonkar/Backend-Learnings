# Commands — Databases

## PostgreSQL

```bash
# Connect
docker exec -it cloud-learnings-postgres psql -U labuser -d labdb

# psql commands
\dt app.*         # list tables in app schema
\d app.users      # describe table
\l                # list databases
\q                # quit

# SQL examples
SELECT * FROM app.users;
INSERT INTO app.users(username, email) VALUES ('dave', 'dave@example.local');
UPDATE app.users SET email='dave2@example.local' WHERE username='dave';
DELETE FROM app.users WHERE username='dave';
EXPLAIN ANALYZE SELECT * FROM app.users WHERE email='alice@example.local';

# Transaction
BEGIN;
INSERT INTO app.orders(user_id, amount) VALUES(1, 99.99);
ROLLBACK;  -- or COMMIT;

# Backup
docker exec cloud-learnings-postgres pg_dump -U labuser labdb > backup.sql

# Restore
docker exec -i cloud-learnings-postgres psql -U labuser -d labdb < backup.sql
```

## MySQL

```bash
# Connect
docker exec -it cloud-learnings-mysql mysql -u labuser -plabpassword123 labdb

# Commands
SHOW TABLES;
DESCRIBE products;
SELECT * FROM products;
INSERT INTO products(name, sku, price, category) VALUES('New Widget', 'WGT-999', 5.99, 'widgets');
EXPLAIN SELECT * FROM products WHERE category='widgets';
SHOW CREATE TABLE products\G

# Backup
docker exec cloud-learnings-mysql mysqldump -u labuser -plabpassword123 labdb > mysql-backup.sql
```

## MongoDB

```bash
# Connect
docker exec -it cloud-learnings-mongo mongosh -u admin -p adminpassword123 --authenticationDatabase admin

# Commands
use labdb
show collections
db.users.find().pretty()
db.users.find({tags: "admin"})
db.users.insertOne({username: "dave", email: "dave@example.local", tags: ["user"]})
db.users.updateOne({username: "dave"}, {$set: {email: "dave2@example.local"}})
db.users.deleteOne({username: "dave"})

# Aggregation
db.events.aggregate([
  {$match: {processed: false}},
  {$group: {_id: "$type", count: {$sum: 1}}}
])

# Backup
docker exec cloud-learnings-mongo mongodump -u admin -p adminpassword123 --authenticationDatabase admin --db labdb --out /tmp/backup
docker cp cloud-learnings-mongo:/tmp/backup ./mongo-backup
```

## Redis

```bash
# Connect
docker exec -it cloud-learnings-redis redis-cli -a redispassword123

# String
SET key "value"
GET key
SETEX tempkey 60 "value"
TTL tempkey
DEL key

# Hash
HSET user:1 name "Alice" age 30 email "alice@example.com"
HGET user:1 name
HGETALL user:1

# List
RPUSH mylist a b c
LRANGE mylist 0 -1
LPOP mylist

# Set
SADD myset a b c a
SMEMBERS myset
SCARD myset

# Sorted set
ZADD leaderboard 100 alice 200 bob 150 carol
ZRANGE leaderboard 0 -1 WITHSCORES
ZRANK leaderboard alice

# Pub/Sub (in two terminals)
# Terminal 1: SUBSCRIBE mychannel
# Terminal 2: PUBLISH mychannel "hello"

# Admin
INFO server
DBSIZE
FLUSHDB  # WARNING: clears current database
```
