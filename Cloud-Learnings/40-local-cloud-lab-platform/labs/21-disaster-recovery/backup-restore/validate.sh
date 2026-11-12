#!/usr/bin/env bash
# Validate lab: postgres-backup-restore
set -euo pipefail

echo "=== PostgreSQL Backup and Restore Lab Validation ==="

# Check psql is available
if command -v psql &>/dev/null; then
    PSQL_VER=$(psql --version | awk '{print $3}')
    echo "PASS: psql $PSQL_VER installed"
else
    echo "WARN: psql not installed — install PostgreSQL client tools"
fi

# Check pg_dump is available
if command -v pg_dump &>/dev/null; then
    echo "PASS: pg_dump installed"
else
    echo "WARN: pg_dump not installed"
fi

# Check PostgreSQL is running
if PGPASSWORD=labpassword123 psql -h localhost -p 5432 -U labuser -d labdb -c 'SELECT 1' -q -t 2>/dev/null | grep -q 1; then
    echo "PASS: PostgreSQL is running and accessible on port 5432"
else
    echo "FAIL: PostgreSQL not accessible — run: make start-data"
    exit 1
fi

# Check tables exist
TABLE_COUNT=$(PGPASSWORD=labpassword123 psql -h localhost -p 5432 -U labuser -d labdb -c '\dt' 2>/dev/null | grep -c "table" || echo "0")
echo "INFO: Database has $TABLE_COUNT table(s)"

# Check orders table
if PGPASSWORD=labpassword123 psql -h localhost -p 5432 -U labuser -d labdb -c 'SELECT COUNT(*) FROM orders' -t 2>/dev/null | grep -qE '[0-9]+'; then
    ORDER_COUNT=$(PGPASSWORD=labpassword123 psql -h localhost -p 5432 -U labuser -d labdb -c 'SELECT COUNT(*) FROM orders' -t 2>/dev/null | tr -d ' ')
    echo "PASS: orders table exists with $ORDER_COUNT rows"
else
    echo "WARN: orders table not found (disaster simulation may be in progress)"
fi

# Check backup files exist
mkdir -p ~/backups

SQL_BACKUP=$(ls ~/backups/*.sql 2>/dev/null | head -1 || true)
DUMP_BACKUP=$(ls ~/backups/*.dump 2>/dev/null | head -1 || true)

if [ -n "$SQL_BACKUP" ]; then
    SQL_SIZE=$(wc -l < "$SQL_BACKUP")
    echo "PASS: SQL backup found at $SQL_BACKUP ($SQL_SIZE lines)"
else
    echo "WARN: No SQL backup found in ~/backups/"
    echo "      Create: PGPASSWORD=labpassword123 pg_dump -h localhost -p 5432 -U labuser -d labdb > ~/backups/labdb.sql"
fi

if [ -n "$DUMP_BACKUP" ]; then
    DUMP_SIZE=$(wc -c < "$DUMP_BACKUP")
    echo "PASS: Custom format backup found at $DUMP_BACKUP ($DUMP_SIZE bytes)"
else
    echo "WARN: No .dump backup found in ~/backups/"
    echo "      Create: PGPASSWORD=labpassword123 pg_dump -h localhost -p 5432 -U labuser -d labdb -Fc -f ~/backups/labdb.dump"
fi

# Check pg-restore container
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^pg-restore$"; then
    echo "PASS: pg-restore container is running (restore to new instance task done)"

    # Verify restored data
    if PGPASSWORD=labpassword123 psql -h localhost -p 5433 -U labuser -d restored_db -c '\dt' 2>/dev/null | grep -q "table\|products\|orders"; then
        echo "PASS: Restored database has tables on port 5433"
    fi
else
    echo "INFO: pg-restore container not running (optional final task)"
fi

echo ""
echo "=== Validation complete ==="
