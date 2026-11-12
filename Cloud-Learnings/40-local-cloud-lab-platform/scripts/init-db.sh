#!/usr/bin/env bash
# scripts/init-db.sh — Initialize the lab platform SQLite database
# Called by setup.sh and reset-db target

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/utils/common.sh"
load_env

DB_PATH="${DB_PATH:-$PLATFORM_ROOT/api/data/lab_platform.db}"
DB_DIR="$(dirname "$DB_PATH")"

log_info "Initializing database at $DB_PATH"
mkdir -p "$DB_DIR"

VENV_PYTHON="$PLATFORM_ROOT/.venv/bin/python3"
if [[ ! -f "$VENV_PYTHON" ]]; then
    VENV_PYTHON="python3"
fi

"$VENV_PYTHON" << 'EOF'
import os
import sqlite3
import sys

db_path = os.environ.get("DB_PATH", "api/data/lab_platform.db")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Labs catalog cache
cur.execute("""
CREATE TABLE IF NOT EXISTS labs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK(difficulty IN ('beginner','intermediate','advanced')),
    estimated_time TEXT,
    yaml_path TEXT NOT NULL,
    last_loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# User progress
cur.execute("""
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'not_started'
        CHECK(status IN ('not_started','in_progress','completed','failed')),
    score INTEGER DEFAULT 0,
    max_score INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    attempts INTEGER DEFAULT 0,
    last_feedback TEXT,
    FOREIGN KEY (lab_id) REFERENCES labs(id)
)
""")

# Lab run history
cur.execute("""
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_id TEXT NOT NULL,
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score INTEGER,
    max_score INTEGER,
    duration_seconds INTEGER,
    validation_output TEXT,
    grade_output TEXT,
    FOREIGN KEY (lab_id) REFERENCES labs(id)
)
""")

# Settings / platform metadata
cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Insert default settings
cur.execute("""
INSERT OR IGNORE INTO settings (key, value) VALUES
    ('schema_version', '1'),
    ('initialized_at', datetime('now')),
    ('platform_version', '1.0.0')
""")

conn.commit()
conn.close()
print(f"Database initialized: {db_path}")
EOF

log_ok "Database initialized at $DB_PATH"
