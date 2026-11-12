# Lab Runner

The lab execution engine for the Local Cloud Lab Platform.

## Usage

```bash
# List all labs
python3 runner.py list

# Get lab info
python3 runner.py info --lab=04-docker/docker-basics

# Run a lab interactively
python3 runner.py run --lab=04-docker/docker-basics

# Just validate (check tasks are done)
python3 runner.py validate --lab=04-docker/docker-basics

# Grade and get JSON output (used by API)
python3 runner.py grade --lab=04-docker/docker-basics --output-json

# Validate all lab.yaml files
python3 runner.py validate-all

# Show progress
python3 runner.py progress

# Generate report
python3 runner.py report --output=reports/progress.json
```

## Lab Structure

Each lab lives in `labs/<category>/<lab-slug>/`:

```
lab.yaml        — required: lab metadata, tasks, grading rules
README.md       — required: instructions (shown in terminal and UI)
validate.sh     — optional: checks if tasks are done
grade.sh        — optional: calculates score (outputs JSON)
setup.sh        — optional: pre-lab setup
cleanup.sh      — optional: post-lab cleanup
```

## validate.sh Output Format

Scripts should print `PASS:` or `FAIL:` prefixed lines for structured output:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Check: nginx image pulled
if docker image inspect nginx:alpine &>/dev/null; then
    echo "PASS: nginx:alpine image exists"
else
    echo "FAIL: nginx:alpine image not found"
fi

# Exit 0 if all passed, 1 if any failed
```

## grade.sh Output Format

Must output JSON to stdout:

```json
{
  "score": 80,
  "max_score": 100,
  "feedback": ["Great work!", "Task 2 needs improvement"]
}
```

## Validators

Reusable validation helpers in `validators/`:

| Module | Purpose |
|--------|---------|
| `docker_validator.py` | Container, image, volume, network checks |
| `http_validator.py` | HTTP endpoint, status code, body checks |
| `k8s_validator.py` | Pod, Deployment, Service, PVC checks |

Use from `validate.sh`:
```bash
python3 /path/to/validators/docker_validator.py container-running nginx
python3 /path/to/validators/http_validator.py status http://localhost:8080 200
python3 /path/to/validators/k8s_validator.py deployment-ready myapp default
```
