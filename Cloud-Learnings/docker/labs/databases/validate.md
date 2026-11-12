# Validation — Databases

## Check PostgreSQL

```bash
docker exec cloud-learnings-postgres \
  psql -U labuser -d labdb -c "SELECT COUNT(*) FROM app.users;"
# Expected: count >= 3 (from init + your inserts)
```

## Check MySQL

```bash
docker exec cloud-learnings-mysql \
  mysql -u labuser -plabpassword123 labdb -e "SELECT COUNT(*) FROM products;"
# Expected: count >= 3
```

## Check MongoDB

```bash
docker exec cloud-learnings-mongo \
  mongosh -u admin -p adminpassword123 --authenticationDatabase admin \
  --eval "db.getSiblingDB('labdb').users.countDocuments()" --quiet
# Expected: count >= 2
```

## Check Redis

```bash
docker exec cloud-learnings-redis \
  redis-cli -a redispassword123 DBSIZE
# Expected: number >= 1 (from your SET commands)
```

## Check backup file

```bash
ls -la backup.sql 2>/dev/null && echo "PASS" || echo "FAIL: backup.sql not found"
```
