#!/usr/bin/env bash
# Validate lab: prometheus-basics
set -euo pipefail

PROMETHEUS="http://localhost:9090"
GRAFANA="http://localhost:3000"

# Check Prometheus is up
if curl -sf "$PROMETHEUS/-/ready" &>/dev/null; then
    echo "PASS: Prometheus is ready at $PROMETHEUS"
else
    echo "FAIL: Prometheus not ready — run: make start-observability"
fi

# Check targets API
TARGETS=$(curl -sf "$PROMETHEUS/api/v1/targets" 2>/dev/null || echo "{}")
if echo "$TARGETS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
targets = d.get('data', {}).get('activeTargets', [])
up = [t for t in targets if t.get('health') == 'up']
print(f'Active targets: {len(targets)}, UP: {len(up)}')
exit(0 if len(up) > 0 else 1)
" 2>/dev/null; then
    echo "PASS: Prometheus has active UP targets"
else
    echo "FAIL: No active UP targets in Prometheus"
fi

# Check PromQL query works
QUERY_RESULT=$(curl -sf "$PROMETHEUS/api/v1/query?query=up" 2>/dev/null || echo "{}")
if echo "$QUERY_RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
exit(0 if d.get('status') == 'success' else 1)
" 2>/dev/null; then
    echo "PASS: PromQL query 'up' returns results"
else
    echo "FAIL: PromQL query failed"
fi

# Check Grafana
if curl -sf "$GRAFANA/api/health" | python3 -c "
import sys, json
d = json.load(sys.stdin)
exit(0 if d.get('database') == 'ok' else 1)
" 2>/dev/null; then
    echo "PASS: Grafana is healthy at $GRAFANA"
else
    echo "FAIL: Grafana not healthy — run: make start-observability"
fi

# Check Prometheus datasource in Grafana
DS_RESULT=$(curl -sf -u "admin:adminpassword123" "$GRAFANA/api/datasources" 2>/dev/null || echo "[]")
if echo "$DS_RESULT" | python3 -c "
import sys, json
ds = json.load(sys.stdin)
prom = [d for d in ds if d.get('type') == 'prometheus']
exit(0 if prom else 1)
" 2>/dev/null; then
    echo "PASS: Prometheus datasource configured in Grafana"
else
    echo "FAIL: Prometheus datasource not found in Grafana"
fi
