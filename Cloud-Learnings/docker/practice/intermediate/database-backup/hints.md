# Hints — Database Backup and Restore

---

## Hint 1 — PostgreSQL backup

```bash
# Plain SQL dump (human-readable)
docker exec cloud-learnings-lab-postgres-1 \
  pg_dump -U appuser -d appdb > backups/appdb.sql

# Compressed custom format (faster restore)
docker exec cloud-learnings-lab-postgres-1 \
  pg_dump -U appuser -d appdb -Fc > backups/appdb.dump

# Directory format (parallel)
docker exec cloud-learnings-lab-postgres-1 \
  pg_dump -U appuser -d appdb -Fd -f /tmp/appdb_dir
docker cp cloud-learnings-lab-postgres-1:/tmp/appdb_dir ./backups/
```

---

## Hint 2 — PostgreSQL restore

```bash
# Create target database first
docker exec cloud-learnings-lab-postgres-1 \
  psql -U postgres -c "CREATE DATABASE appdb_restored;"

# Restore from SQL
docker exec -i cloud-learnings-lab-postgres-1 \
  psql -U appuser -d appdb_restored < backups/appdb.sql

# Restore from custom format
docker exec cloud-learnings-lab-postgres-1 \
  pg_restore -U appuser -d appdb_restored /tmp/appdb.dump
```

---

## Hint 3 — MySQL backup/restore

```bash
# Backup single table
docker exec cloud-learnings-lab-mysql-1 \
  mysqldump -u appuser -papppassword appdb products > backups/products.sql

# Full database backup
docker exec cloud-learnings-lab-mysql-1 \
  mysqldump -u appuser -papppassword appdb > backups/appdb.sql

# Restore
docker exec cloud-learnings-lab-mysql-1 \
  mysql -u root -prootpassword -e "CREATE DATABASE appdb_restored;"
docker exec -i cloud-learnings-lab-mysql-1 \
  mysql -u appuser -papppassword appdb_restored < backups/appdb.sql
```

---

## Hint 4 — MongoDB backup/restore

```bash
# Backup
docker exec cloud-learnings-lab-mongodb-1 \
  mongodump --db appdb --out /tmp/mongodump
docker cp cloud-learnings-lab-mongodb-1:/tmp/mongodump ./backups/

# Drop collection
docker exec cloud-learnings-lab-mongodb-1 \
  mongosh appdb --eval "db.users.drop()"

# Restore
docker cp ./backups/mongodump cloud-learnings-lab-mongodb-1:/tmp/
docker exec cloud-learnings-lab-mongodb-1 \
  mongorestore --db appdb /tmp/mongodump/appdb
```

---

## Hint 5 — Script template

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="./backups/$(date +%Y-%m-%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
ERRORS=0

log() { echo "[$(date +%H:%M:%S)] $*"; }

# PostgreSQL
log "Backing up PostgreSQL..."
if docker exec cloud-learnings-lab-postgres-1 \
    pg_dump -U appuser -d appdb -Fc > "$BACKUP_DIR/postgres.dump"; then
  log "PostgreSQL backup complete"
else
  log "ERROR: PostgreSQL backup failed"
  ERRORS=$((ERRORS + 1))
fi

# ... (repeat for MySQL and MongoDB)

exit $ERRORS
```
