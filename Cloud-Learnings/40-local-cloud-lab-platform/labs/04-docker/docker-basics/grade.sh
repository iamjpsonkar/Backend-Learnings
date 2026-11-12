#!/usr/bin/env bash
# Grade lab: docker-basics
# Outputs JSON: {"score": N, "max_score": M, "feedback": [...]}
set -euo pipefail

SCORE=0
MAX_SCORE=100
FEEDBACK=()

# Check 1: nginx:alpine image exists (25 pts)
if docker image inspect nginx:alpine &>/dev/null; then
    SCORE=$((SCORE + 25))
    FEEDBACK+=("Image pull: nginx:alpine image is present")
else
    FEEDBACK+=("Image pull: nginx:alpine not found - run: docker pull nginx:alpine")
fi

# Check 2: Container was stopped/removed (25 pts)
if ! docker ps -a --filter "name=^lab-nginx$" --format "{{.Names}}" | grep -q "lab-nginx"; then
    SCORE=$((SCORE + 25))
    FEEDBACK+=("Cleanup: lab-nginx container removed correctly")
else
    FEEDBACK+=("Cleanup: lab-nginx container still exists — run: docker rm -f lab-nginx")
fi

# Check 3: Docker can run containers (25 pts)
if docker run --rm alpine:latest echo "ok" &>/dev/null; then
    SCORE=$((SCORE + 25))
    FEEDBACK+=("Docker runtime: containers can be created and run")
    docker rmi alpine:latest &>/dev/null || true
else
    FEEDBACK+=("Docker runtime: failed to run a test container")
fi

# Check 4: At least one image from the lab exists (25 pts)
if docker images | grep -qE "nginx|alpine"; then
    SCORE=$((SCORE + 25))
    FEEDBACK+=("Image management: Docker images are being managed correctly")
else
    FEEDBACK+=("Image management: no relevant images found")
fi

PASSED=false
if [ "$SCORE" -ge 70 ]; then
    PASSED=true
fi

# Output JSON
python3 -c "
import json
print(json.dumps({
    'score': $SCORE,
    'max_score': $MAX_SCORE,
    'percentage': round($SCORE/$MAX_SCORE*100, 1),
    'passed': $PASSED,
    'feedback': $(python3 -c "import json; print(json.dumps($(echo "${FEEDBACK[@]}" | python3 -c "import sys,json; lines=sys.stdin.read().split('\n'); print(json.dumps([l for l in lines if l]))")))")
}))
" 2>/dev/null || echo "{\"score\": $SCORE, \"max_score\": $MAX_SCORE, \"passed\": $PASSED, \"feedback\": []}"
