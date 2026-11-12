# Tasks — Databases

## Task 1 — PostgreSQL

- [ ] Connect to PostgreSQL:
  ```bash
  docker exec -it cloud-learnings-postgres psql -U labuser -d labdb
  ```
- [ ] List tables: `\dt app.*`
- [ ] Query the users table: `SELECT * FROM app.users;`
- [ ] Insert a new user
- [ ] Update an existing user
- [ ] Use EXPLAIN ANALYZE on a query
- [ ] Create a new index
- [ ] Run a JOIN between users and orders
- [ ] Use a transaction (BEGIN / COMMIT / ROLLBACK)
- [ ] Connect via Adminer at http://localhost:8081

## Task 2 — MySQL

- [ ] Connect to MySQL:
  ```bash
  docker exec -it cloud-learnings-mysql mysql -u labuser -plabpassword123 labdb
  ```
- [ ] List tables: `SHOW TABLES;`
- [ ] Query products: `SELECT * FROM products;`
- [ ] Insert a new product
- [ ] View query execution plan: `EXPLAIN SELECT * FROM products WHERE category='widgets';`
- [ ] Create an index
- [ ] Check user privileges: `SHOW GRANTS FOR 'labuser'@'%';`

## Task 3 — MongoDB

- [ ] Connect to MongoDB:
  ```bash
  docker exec -it cloud-learnings-mongo mongosh -u admin -p adminpassword123 --authenticationDatabase admin
  ```
- [ ] Switch to labdb: `use labdb`
- [ ] List collections: `show collections`
- [ ] Find all users: `db.users.find()`
- [ ] Find with filter: `db.users.find({tags: "admin"})`
- [ ] Insert a document
- [ ] Update a document
- [ ] Run an aggregation pipeline
- [ ] Create an index: `db.users.createIndex({email: 1})`

## Task 4 — Redis

- [ ] Connect to Redis:
  ```bash
  docker exec -it cloud-learnings-redis redis-cli -a redispassword123
  ```
- [ ] Set a key: `SET mykey "hello"`
- [ ] Get a key: `GET mykey`
- [ ] Set with expiry: `SETEX tempkey 60 "expires-in-60s"`
- [ ] Check TTL: `TTL tempkey`
- [ ] Use a hash: `HSET user:1 name "Alice" age 30`
- [ ] Use a list: `LPUSH mylist a b c`; `LRANGE mylist 0 -1`
- [ ] Use a set: `SADD myset a b c a`; `SMEMBERS myset`
- [ ] Use pub/sub: open two terminals, subscribe and publish

## Task 5 — Backup

- [ ] Backup PostgreSQL:
  ```bash
  ./run.sh backup
  ```
- [ ] Manual PostgreSQL dump:
  ```bash
  docker exec cloud-learnings-postgres pg_dump -U labuser labdb > backup.sql
  ```
- [ ] Check the backup file size and content

## Task 6 — Restore

- [ ] Restore from backup:
  ```bash
  docker exec -i cloud-learnings-postgres psql -U labuser -d labdb < backup.sql
  ```

## Task 7 — Connection Troubleshooting

Try each broken connection and diagnose:
- Wrong password: `psql -h localhost -U labuser -d labdb` (enter wrong password)
- Wrong port: `psql -h localhost -p 5433 -U labuser -d labdb`
- Wrong database: `psql -h localhost -U labuser -d nonexistent`

What error message appears for each?
