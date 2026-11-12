# Adding New Labs

Complete guide for contributing new labs to the platform.

## Quick Start

```bash
# 1. Create the lab directory
mkdir -p labs/<category>/<lab-slug>/

# 2. Create required files
touch labs/<category>/<lab-slug>/lab.yaml
touch labs/<category>/<lab-slug>/README.md
touch labs/<category>/<lab-slug>/validate.sh

# 3. Validate your YAML
make validate-labs

# 4. Test the lab
make run-lab LAB=<category>/<lab-slug>
```

## Required Files

### lab.yaml

The lab definition file. Full schema: [lab-runner/schemas/lab_schema.yaml](../lab-runner/schemas/lab_schema.yaml)

Minimum required fields:
```yaml
id: my-new-lab
title: "My New Lab: What You'll Learn"
description: >
  A clear description of what this lab covers and
  what the learner will accomplish.
difficulty: beginner    # beginner | intermediate | advanced
category: docker        # your lab's category
tasks:
  - description: "First task the user must complete"
```

### README.md

Lab instructions in Markdown. Should include:
- Overview
- Prerequisites
- Step-by-step task instructions with example commands
- Expected output
- Key concepts table
- Cleanup steps
- Links to related labs and documentation

### validate.sh (optional but strongly recommended)

Shell script that checks if the user completed the tasks.

Output format (one line per check):
```bash
echo "PASS: <description>"   # task passed
echo "FAIL: <description>"   # task failed
```

Exit code: 0 = all passed, 1 = some failed (overall)

```bash
#!/usr/bin/env bash
set -euo pipefail

if docker image inspect nginx:alpine &>/dev/null; then
    echo "PASS: nginx:alpine image exists"
else
    echo "FAIL: nginx:alpine image not found"
fi
```

### grade.sh (optional)

Script that calculates a score. Must output JSON to stdout:

```bash
#!/usr/bin/env bash
SCORE=0
# ... checks ...
echo "{\"score\": $SCORE, \"max_score\": 100, \"feedback\": [\"Well done!\"]}"
```

## Categories

Match the category to an existing one:

| Category | Labs Dir |
|----------|---------|
| foundations | `00-foundations/` |
| linux | `01-linux/` |
| networking | `02-networking/` |
| docker | `04-docker/` |
| kubernetes | `05-kubernetes/` |
| terraform | `06-terraform-opentofu/` |
| ansible | `07-ansible/` |
| aws-local | `08-aws-local/` |
| azure-local | `09-azure-local/` |
| security | `11-security/` |
| observability | `12-observability/` |
| cicd | `13-cicd/` |
| databases | `14-databases/` |
| storage | `15-storage/` |
| sre | `17-sre/` |

## Validator Helpers

Use the built-in validators in your validate.sh:

```bash
# Docker checks
python3 /path/to/lab-runner/validators/docker_validator.py container-running nginx
python3 /path/to/lab-runner/validators/docker_validator.py image-exists nginx:alpine

# HTTP checks
python3 /path/to/lab-runner/validators/http_validator.py status http://localhost:8080 200
python3 /path/to/lab-runner/validators/http_validator.py body-contains http://localhost/health ok

# Kubernetes checks
python3 /path/to/lab-runner/validators/k8s_validator.py deployment-ready myapp default
python3 /path/to/lab-runner/validators/k8s_validator.py pod-running myapp default
```

## Testing Your Lab

```bash
# Validate YAML schema
make validate-labs

# View lab info
make lab-info LAB=<category>/<lab-slug>

# Run the lab interactively
make run-lab LAB=<category>/<lab-slug>

# Run validation only
make validate-lab LAB=<category>/<lab-slug>
```

## Checklist Before Submitting

- [ ] lab.yaml validates without errors: `make validate-labs`
- [ ] README.md has clear task instructions with example commands
- [ ] validate.sh tests are accurate and not trivially bypassable
- [ ] cleanup_steps in lab.yaml remove all lab resources
- [ ] Lab was tested end-to-end with `make run-lab`
- [ ] related_docs links are correct relative paths
- [ ] safety_warning is set if the lab is destructive
- [ ] Lab runs in < 2x the estimated_time on a typical machine
