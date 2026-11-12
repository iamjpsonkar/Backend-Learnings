#!/usr/bin/env bash
# Validate lab: gitea-cicd-pipeline
set -euo pipefail

GITEA="http://localhost:18080"
WOODPECKER="http://localhost:18081"
GITEA_CREDS="labadmin:labpassword123"

echo "=== Gitea + Woodpecker CI Lab Validation ==="

# Check Gitea is running
if curl -sf "$GITEA" 2>/dev/null | grep -qi "gitea\|sign in\|explore"; then
    echo "PASS: Gitea is accessible at $GITEA"
else
    echo "FAIL: Gitea not accessible — run: make start-cicd"
    exit 1
fi

# Check Gitea API version
if curl -sf "$GITEA/api/v1/version" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Gitea version: {d.get(\"version\",\"?\")}'); exit(0 if d.get('version') else 1)" 2>/dev/null; then
    echo "PASS: Gitea API is responding"
else
    echo "WARN: Gitea API not responding"
fi

# Check Woodpecker is running
if curl -sf "$WOODPECKER" 2>/dev/null | grep -qi "woodpecker\|sign\|login"; then
    echo "PASS: Woodpecker CI is accessible at $WOODPECKER"
else
    echo "WARN: Woodpecker CI not accessible — run: make start-cicd"
fi

# Check if lab-pipeline repo exists
if curl -sf -u "$GITEA_CREDS" "$GITEA/api/v1/repos/labadmin/lab-pipeline" 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Repository: {d.get(\"full_name\",\"?\")} ({d.get(\"private\",\"?\")} private)')
exit(0 if d.get('name') == 'lab-pipeline' else 1)
" 2>/dev/null; then
    echo "PASS: lab-pipeline repository exists in Gitea"
else
    echo "WARN: lab-pipeline repository not found"
    echo "      Create: curl -u $GITEA_CREDS -X POST $GITEA/api/v1/user/repos -H 'Content-Type: application/json' -d '{\"name\":\"lab-pipeline\"}'"
fi

# Check if .woodpecker.yml exists in repo
if curl -sf -u "$GITEA_CREDS" "$GITEA/api/v1/repos/labadmin/lab-pipeline/contents/.woodpecker.yml" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('name') else 1)" 2>/dev/null; then
    echo "PASS: .woodpecker.yml pipeline config exists in repo"
else
    echo "WARN: .woodpecker.yml not found in lab-pipeline repo"
fi

# Count repos in Gitea
REPO_COUNT=$(curl -sf -u "$GITEA_CREDS" "$GITEA/api/v1/repos/search?limit=50" 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
repos = [r['name'] for r in d.get('data', [])]
print(f'Repositories: {repos}')
print(len(repos))
" 2>/dev/null | tail -1 || echo "0")

if [ "$REPO_COUNT" -gt 0 ]; then
    echo "PASS: $REPO_COUNT repository/repositories in Gitea"
fi

echo ""
echo "=== Validation complete ==="
