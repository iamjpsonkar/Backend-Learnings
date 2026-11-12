#!/usr/bin/env bash
# Validate lab: slo-error-budget
set -euo pipefail

PROMETHEUS="http://localhost:9090"
GRAFANA="http://localhost:3000"

echo "=== SLO Error Budget Lab Validation ==="

# Check Prometheus
if curl -sf "$PROMETHEUS/-/ready" &>/dev/null; then
    echo "PASS: Prometheus is ready"
else
    echo "FAIL: Prometheus not running — run: make start-observability"
    exit 1
fi

# Check rules are loaded
RULES_RESPONSE=$(curl -sf "$PROMETHEUS/api/v1/rules" 2>/dev/null || echo "{}")
RULE_COUNT=$(echo "$RULES_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
groups = d.get('data', {}).get('groups', [])
rules = [r for g in groups for r in g.get('rules', [])]
print(len(rules))
" 2>/dev/null || echo "0")

if [ "$RULE_COUNT" -gt 0 ]; then
    echo "PASS: Prometheus has $RULE_COUNT rule(s) loaded"
else
    echo "WARN: No Prometheus rules found"
fi

# Check alert rules specifically
ALERT_COUNT=$(echo "$RULES_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
groups = d.get('data', {}).get('groups', [])
alerts = [r for g in groups for r in g.get('rules', []) if r.get('type') == 'alerting']
print(len(alerts))
" 2>/dev/null || echo "0")

if [ "$ALERT_COUNT" -gt 0 ]; then
    echo "PASS: $ALERT_COUNT alerting rule(s) found"
else
    echo "INFO: No alerting rules found — add burn rate alerts to rules file"
fi

# Check recording rules
RECORDING_COUNT=$(echo "$RULES_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
groups = d.get('data', {}).get('groups', [])
recordings = [r for g in groups for r in g.get('rules', []) if r.get('type') == 'recording']
for r in recordings[:3]:
    print(f'  recording: {r.get(\"name\",\"?\")}')
print(len(recordings))
" 2>/dev/null || echo "0")

if echo "$RECORDING_COUNT" | grep -qE '^[1-9]'; then
    echo "PASS: Recording rules found (SLI definitions)"
else
    echo "INFO: No recording rules found — define SLI recording rules"
fi

# Check if sli alert file exists
LAB_ROOT="$(dirname "$(dirname "$(dirname "$0")")")"
ALERT_FILE="$LAB_ROOT/configs/prometheus/rules/lab-alerts.yml"
if [ -f "$ALERT_FILE" ]; then
    echo "PASS: lab-alerts.yml exists"
    if grep -q "burn_rate\|slo\|SLO\|error_budget" "$ALERT_FILE" 2>/dev/null; then
        echo "PASS: Alert file contains SLO/burn rate rules"
    else
        echo "INFO: lab-alerts.yml exists but no SLO burn rate alerts found yet"
    fi
fi

# Check basic PromQL for error rate
if curl -sf "$PROMETHEUS/api/v1/query?query=1" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d['status']=='success' else 1)" 2>/dev/null; then
    echo "PASS: PromQL engine is functional"
fi

# Check Grafana
if curl -sf "$GRAFANA/api/health" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('database')=='ok' else 1)" 2>/dev/null; then
    echo "PASS: Grafana is healthy"
else
    echo "WARN: Grafana not running"
fi

echo ""
echo "=== Validation complete ==="
