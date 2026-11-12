# Troubleshooting — Databases

## PostgreSQL: FATAL: password authentication failed

Use the correct credentials from `.env`:
- User: `labuser`
- Password: `labpassword123`
- Database: `labdb`

```bash
docker exec -it cloud-learnings-postgres psql -U labuser -d labdb
# (no password prompt — inside container uses peer auth)
```

## MySQL: Access denied for user

```bash
# Connect as root to diagnose
docker exec -it cloud-learnings-mysql mysql -u root -prootpassword123

# Check grants
SHOW GRANTS FOR 'labuser'@'%';
```

## MongoDB: Authentication failed

Check you're using the admin database for authentication:
```bash
mongosh mongodb://admin:adminpassword123@localhost:27017/?authSource=admin
```

## Redis: NOAUTH Authentication required

Always pass the password:
```bash
redis-cli -a redispassword123 ping
```

Or authenticate after connecting:
```
AUTH redispassword123
```

## Container not running

```bash
# Check status
docker ps | grep -E "postgres|mysql|mongo|redis"

# Start data profile
./run.sh start data

# Check logs for errors
docker logs cloud-learnings-postgres --tail=20
```

## pg_dump fails: not found

The `pg_dump` command runs inside the container:
```bash
# Correct:
docker exec cloud-learnings-postgres pg_dump -U labuser labdb > backup.sql

# Wrong (pg_dump is in the container, not on your host):
# pg_dump -h localhost -U labuser labdb > backup.sql  # Only works if pg_dump installed on host
```
