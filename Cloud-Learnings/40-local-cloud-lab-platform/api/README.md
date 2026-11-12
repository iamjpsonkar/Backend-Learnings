# Lab Platform API

FastAPI backend for the Local Cloud Lab Platform.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/labs` | List all labs (supports `?category=` and `?difficulty=` filters) |
| GET | `/api/v1/labs/{id}` | Get lab details |
| GET | `/api/v1/progress` | Get all progress (supports `?lab_id=` filter) |
| POST | `/api/v1/progress` | Record lab progress |
| DELETE | `/api/v1/progress/{lab_id}` | Reset progress for a lab |
| POST | `/api/v1/runner/run` | Trigger lab validation/grading |
| GET | `/api/v1/services` | Get Docker service statuses |
| GET | `/api/v1/services/profiles` | Get active Docker Compose profiles |

Interactive docs: `http://localhost:4567/docs`

## Development

```bash
cd api

# Create venv
python3 -m venv .venv && source .venv/bin/activate

# Install deps
pip install -r requirements.txt

# Run dev server (with auto-reload)
RELOAD=true python3 -m app.main

# Run tests
pytest tests/ -v
```

## Architecture

- `app/main.py` — FastAPI app factory, middleware, lifespan
- `app/settings.py` — Environment-based configuration
- `app/db.py` — SQLAlchemy async engine + session
- `app/models.py` — ORM models (Lab, LabProgress, LabRun)
- `app/schemas.py` — Pydantic request/response schemas
- `app/lab_loader.py` — Lab YAML scanner and validator
- `app/routers/` — Router modules per domain

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level |
| `LABS_DIR` | `/labs` | Path to labs directory |
| `DB_PATH` | `/app/data/lab_platform.db` | SQLite database path |
| `LAB_RUNNER_TIMEOUT` | `300` | Runner subprocess timeout (seconds) |
