# Platform Architecture

---

## High-Level Design

```
┌──────────────────────────────────────────────────────────────┐
│                   Local Cloud Lab Platform                   │
│                                                              │
│  ┌────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  React UI  │    │  FastAPI API │    │   Lab Runner     │  │
│  │  (Vite)   │◄───│  (Python)    │◄───│  runner.py       │  │
│  │  :3001     │    │  :4567       │    │                  │  │
│  └────────────┘    └──────┬───────┘    └────────┬─────────┘  │
│                           │                     │            │
│                    ┌──────┴──────┐    ┌──────────┴────────┐  │
│                    │   SQLite    │    │  labs/**/*.yaml    │  │
│                    │  progress   │    │  validate.sh       │  │
│                    │  metadata   │    │  grade.sh          │  │
│                    └─────────────┘    └───────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │           Docker Compose Profiles                     │   │
│  │                                                       │   │
│  │  core          │ MinIO, Traefik, API, UI              │   │
│  │  observability │ Prometheus, Grafana, Loki, Jaeger    │   │
│  │  security      │ Vault, Keycloak                      │   │
│  │  cicd          │ Gitea, Woodpecker CI                 │   │
│  │  data          │ PostgreSQL, MongoDB, Redis, Redpanda │   │
│  │  aws-local     │ LocalStack                           │   │
│  │  azure-local   │ Azurite                              │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Details

### React UI (`ui/`)

- **Framework**: React 18 + Vite
- **Served by**: Nginx in Docker (production build)
- **Port**: 3001
- **Responsibilities**:
  - Display lab catalog (fetched from API)
  - Show lab details, prerequisites, tasks, hints
  - Track progress (persisted via API → SQLite)
  - Show service health status
  - Provide quick-start buttons for Docker profiles
- **Key files**:
  - `ui/src/App.jsx` — root component, routing
  - `ui/src/components/LabCard.jsx` — lab display
  - `ui/src/components/ServiceStatus.jsx` — Docker health panel
  - `ui/src/api/client.js` — API client

### FastAPI Backend (`api/`)

- **Framework**: FastAPI (Python 3.11+)
- **Database**: SQLite (`api/lab_platform.db`)
- **Port**: 4567
- **Responsibilities**:
  - Serve lab catalog from `labs/` YAML files
  - Track lab progress (started, completed, score)
  - Trigger lab runner and return results
  - Report Docker service health
  - Serve lab assets (instructions, hints)
- **Key files**:
  - `api/app/main.py` — FastAPI entry point, router registration
  - `api/app/routers/labs.py` — lab catalog and progress endpoints
  - `api/app/routers/runner.py` — lab execution endpoints
  - `api/app/routers/health.py` — health and Docker status endpoints
  - `api/app/models.py` — SQLAlchemy models
  - `api/app/schemas.py` — Pydantic schemas
  - `api/app/db.py` — SQLite connection and session management
  - `api/app/lab_loader.py` — YAML lab definition parser + validator

### Lab Runner (`lab-runner/`)

- **Language**: Python 3.11+
- **Responsibilities**:
  - Load and parse `lab.yaml` definition files
  - Execute `validate.sh` scripts to check task completion
  - Execute `grade.sh` scripts to calculate scores
  - Return structured JSON results to the API
  - Support `--verbose` mode for debugging
- **Key files**:
  - `lab-runner/runner.py` — CLI entry point and orchestrator
  - `lab-runner/validators/` — reusable validation helpers (Docker, K8s, files, HTTP)
  - `lab-runner/graders/` — scoring logic
  - `lab-runner/schemas/lab_schema.yaml` — JSON Schema for lab.yaml validation

### Labs (`labs/`)

Each lab lives in `labs/<category>/<lab-slug>/`:

```
labs/
  04-docker/
    docker-basics/
      lab.yaml         # lab definition (metadata, tasks, grading rules)
      README.md        # lab instructions (rendered in UI and terminal)
      validate.sh      # checks if the user completed each task
      grade.sh         # calculates score (optional, falls back to validate.sh)
      setup.sh         # pre-lab setup (optional)
      cleanup.sh       # post-lab cleanup (optional)
      solution/        # reference solution (hidden from UI, for grading reference)
      assets/          # lab-specific files (configs, manifests, etc.)
```

### Docker Compose Files (`docker-compose.*.yml`)

The platform uses a modular compose structure:

```
docker-compose.yml           # base: core services (MinIO, Traefik, API, UI)
docker-compose.observability.yml
docker-compose.security.yml
docker-compose.cicd.yml
docker-compose.data.yml
docker-compose.aws-local.yml
docker-compose.azure-local.yml
```

All services share a single `cloud-lab-network` Docker network so they can communicate by service name.

All resources are labelled `com.cloudlabs.project=local-cloud-lab` for safe cleanup.

---

## Network Architecture

```
cloud-lab-network (Docker bridge, 172.20.0.0/16)
│
├── traefik          (172.20.0.2) — reverse proxy, routes by domain/path
├── minio            (172.20.0.3) — S3-compatible object storage
├── api              (172.20.0.4) — FastAPI backend
├── ui               (172.20.0.5) — React dashboard
├── prometheus       (172.20.0.10) — metrics collection
├── grafana          (172.20.0.11) — metrics dashboards
├── loki             (172.20.0.12) — log aggregation
├── promtail         (172.20.0.13) — log shipping
├── jaeger           (172.20.0.14) — distributed tracing
├── otel-collector   (172.20.0.15) — OpenTelemetry collector
├── vault            (172.20.0.20) — secrets management
├── keycloak         (172.20.0.21) — identity/IAM
├── gitea            (172.20.0.30) — Git server
├── woodpecker       (172.20.0.31) — CI/CD
├── postgres         (172.20.0.40) — SQL database
├── mysql            (172.20.0.41) — SQL database (alternative)
├── mongodb          (172.20.0.42) — document database
├── redis            (172.20.0.43) — cache/queue
├── redpanda         (172.20.0.44) — Kafka-compatible streaming
├── rabbitmq         (172.20.0.45) — message broker
├── localstack       (172.20.0.50) — AWS services emulator
└── azurite          (172.20.0.51) — Azure storage emulator
```

---

## Data Flow: Running a Lab

```
User types: make run-lab LAB=04-docker/docker-basics
        │
        ▼
Makefile → python3 lab-runner/runner.py run --lab=04-docker/docker-basics
        │
        ▼
runner.py loads labs/04-docker/docker-basics/lab.yaml
        │
        ├── validates schema
        ├── checks docker_profiles are running
        └── prints lab brief + tasks to terminal
        │
        ▼
User completes tasks (types "done")
        │
        ▼
runner.py executes validate.sh
        │
        ├── validate.sh checks Docker containers, files, HTTP endpoints
        └── returns exit 0 (pass) or exit 1 (fail) per check
        │
        ▼
runner.py executes grade.sh → returns JSON {score, max_score, feedback[]}
        │
        ▼
runner.py prints results + posts to API: POST /api/v1/progress
        │
        ▼
API stores in SQLite → UI progress updates
```

---

## Lab YAML Schema

See [lab-runner/schemas/lab_schema.yaml](lab-runner/schemas/lab_schema.yaml) for the full schema.

Key fields:

```yaml
id: docker-basics
title: "Docker Basics: Run, Build, Push"
difficulty: beginner            # beginner | intermediate | advanced
estimated_time: "45 minutes"
category: docker
docker_profiles: [core]         # which compose profiles must be running
tasks:
  - id: pull-image
    description: "Pull the nginx:alpine image"
    hints:
      - "Use the docker pull command"
grading_rules:
  - check: "docker image inspect nginx:alpine"
    points: 10
```

---

## Security Design

1. **Label-based isolation**: All platform resources labelled `com.cloudlabs.project=local-cloud-lab`
2. **Cleanup safety**: `cleanup.sh` only removes resources with that label
3. **Destructive operation guard**: `--confirm` flag required for reset/cleanup
4. **Fake credentials only**: All passwords/tokens in `.env.example` are fake dev values
5. **No external writes**: Platform writes only inside `40-local-cloud-lab-platform/`
6. **Real cloud guard**: Commands that touch real cloud marked `# [REAL CLOUD - OPTIONAL]`
7. **Script safety**: All shell scripts use `set -euo pipefail`
8. **Pre-flight checks**: Scripts verify required tools before doing anything

---

## Progress Storage (SQLite Schema)

```sql
-- Labs catalog cache
CREATE TABLE labs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    estimated_time TEXT,
    yaml_path TEXT NOT NULL,
    last_loaded_at TIMESTAMP
);

-- User progress
CREATE TABLE progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_id TEXT NOT NULL,
    status TEXT NOT NULL,       -- not_started | in_progress | completed | failed
    score INTEGER DEFAULT 0,
    max_score INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    attempts INTEGER DEFAULT 0,
    last_feedback TEXT,         -- JSON feedback from grade.sh
    FOREIGN KEY (lab_id) REFERENCES labs(id)
);

-- Lab run history
CREATE TABLE runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_id TEXT NOT NULL,
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score INTEGER,
    max_score INTEGER,
    duration_seconds INTEGER,
    validation_output TEXT,     -- JSON output from validate.sh
    grade_output TEXT           -- JSON output from grade.sh
);
```

---

## Adding a New Lab

1. Create `labs/<category>/<lab-slug>/`
2. Add `lab.yaml` using the schema
3. Write `README.md` with clear task instructions
4. Write `validate.sh` — each check exits 0 for pass, 1 for fail
5. Optionally write `grade.sh` — must output JSON: `{"score": N, "max_score": M, "feedback": []}`
6. Run `make validate-labs` to confirm the YAML is valid
7. The lab appears in the catalog immediately (no restart needed)

---

## Directory Structure

```
40-local-cloud-lab-platform/
├── README.md              # Platform overview
├── QUICKSTART.md          # 5-minute getting started
├── REQUIREMENTS.md        # System requirements
├── ARCHITECTURE.md        # This file
├── LAB_INDEX.md           # Full lab catalog
├── TROUBLESHOOTING.md     # Common issues
├── ROADMAP.md             # Future plans
├── Makefile               # All make commands
├── .env.example           # Environment variable template
├── .gitignore
│
├── docker-compose.yml                  # core profile
├── docker-compose.observability.yml
├── docker-compose.security.yml
├── docker-compose.cicd.yml
├── docker-compose.data.yml
├── docker-compose.aws-local.yml
├── docker-compose.azure-local.yml
│
├── scripts/               # Platform management scripts
│   ├── setup.sh
│   ├── doctor.sh
│   ├── health.sh
│   ├── cleanup.sh
│   ├── reset.sh
│   └── ...
│
├── api/                   # FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── ...
│   ├── Dockerfile
│   └── requirements.txt
│
├── ui/                    # React + Vite dashboard
│   ├── src/
│   ├── Dockerfile
│   └── package.json
│
├── lab-runner/            # Lab execution engine
│   ├── runner.py
│   ├── validators/
│   ├── graders/
│   └── schemas/
│
├── labs/                  # Lab definitions
│   ├── 00-foundations/
│   ├── 01-linux/
│   ├── 04-docker/
│   └── ...
│
├── projects/              # Larger multi-service projects
├── practice/              # Broken scenarios, interview prep
├── configs/               # Service configuration files
├── tools/                 # Tool-specific configs (Prometheus rules, etc.)
├── environments/          # Environment-specific overrides
├── infrastructure/        # Platform's own Terraform/Ansible
├── assets/                # Diagrams, screenshots
├── docs/                  # Extended documentation
├── tests/                 # Platform self-tests
└── reports/               # Lab run reports output directory
```
