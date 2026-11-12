# Database Backup and Restore — Intermediate

**Difficulty**: Intermediate
**Profile**: `data`
**Time estimate**: 60–90 minutes

---

## Scenario

The data team needs a backup/restore runbook for all three databases: PostgreSQL, MySQL, and MongoDB. Your job: write and test the procedures.

---

## Setup

```bash
./run.sh start data

# Verify all three databases are running
docker ps --filter "label=com.cloudlearnings.project=cloud-learnings-lab"
```

---

## Tasks

### Task 1 — Explore the existing data

```bash
# PostgreSQL
docker exec -it cloud-learnings-lab-postgres-1 psql -U appuser -d appdb \
  -c "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM orders;"

# MySQL
docker exec -it cloud-learnings-lab-mysql-1 mysql -u appuser -papppassword appdb \
  -e "SELECT COUNT(*) FROM products;"

# MongoDB
docker exec -it cloud-learnings-lab-mongodb-1 mongosh appdb \
  --eval "db.users.countDocuments({})"
```

Verify each database has data (initialized from init scripts).

### Task 2 — PostgreSQL backup and restore

```bash
# 2a. Create a full backup (pg_dump)
# 2b. Restore to a new database (appdb_restored)
# 2c. Verify row counts match
# 2d. Create a compressed backup
# 2e. Create a directory-format backup (for parallel restore)
```

### Task 3 — MySQL backup and restore

```bash
# 3a. Backup single table
# 3b. Backup full database
# 3c. Restore to a new database
# 3d. Verify data integrity
```

### Task 4 — MongoDB backup and restore

```bash
# 4a. Backup with mongodump
# 4b. Drop the users collection
# 4c. Restore with mongorestore
# 4d. Verify data is back
```

### Task 5 — Automate with a script

Write a `backup.sh` script that:
1. Backs up all three databases to `./backups/YYYY-MM-DD/`
2. Uses timestamps in filenames
3. Logs each step
4. Returns exit code 1 if any backup fails

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="./backups/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Your code here
```

### Task 6 — Disaster recovery drill

1. Run your `backup.sh`
2. Delete all data from PostgreSQL: `DROP TABLE users CASCADE;`
3. Restore from your backup
4. Verify data is back

---

## Success criteria

- [ ] Row counts confirmed in all three databases
- [ ] PostgreSQL pg_dump and psql restore working
- [ ] MySQL mysqldump restore working
- [ ] MongoDB mongodump/mongorestore working
- [ ] backup.sh script written and tested
- [ ] Full DR drill completed: delete + restore + verify
