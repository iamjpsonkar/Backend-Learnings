# Practice Scenarios

Unguided practice environments for real-world skills.

## Categories

### Broken Labs (`broken-labs/`)

Pre-broken environments that you must diagnose and fix. No hints — just logs, symptoms, and your toolkit.

- `broken-k8s-deployment/` — A Kubernetes app that won't start
- `broken-cicd-pipeline/` — A CI/CD pipeline that silently fails
- `broken-database/` — PostgreSQL with corrupted replication
- `broken-nginx/` — Nginx returning 502 for all requests
- `broken-terraform/` — IaC state that's drifted from reality

### Interview Scenarios (`interview-scenarios/`)

Timed challenges modeled on real SRE/DevOps interview scenarios:

- `incident-30min/` — Production is down. You have 30 minutes.
- `debug-live-system/` — Find the bug in a running system
- `design-scalable-api/` — Design and implement a scalable API
- `optimize-slow-query/` — Find and fix a slow database query

## Usage

```bash
# Start a broken lab scenario
cd practice/broken-labs/broken-k8s-deployment/
bash setup.sh       # sets up the broken environment
bash check.sh       # check if you've fixed it
bash solution.sh    # reveal the solution (spoiler!)

# Start an interview scenario (timed)
cd practice/interview-scenarios/incident-30min/
bash start.sh       # starts the timer and breaks the environment
bash submit.sh      # submit your fix and see score
```

## Philosophy

These scenarios have no walkthroughs. Use your documentation, man pages, and instincts.
The goal is to build confidence with real ambiguity — the same ambiguity you'll face on the job.
