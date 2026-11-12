#!/usr/bin/env bash
# Validate lab: grafana-dashboards
set -euo pipefail

GRAFANA="http://localhost:3000"
PROMETHEUS="http://localhost:9090"
GRAFANA_CREDS="admin:adminpassword123"

echo "=== Grafana Dashboards Lab Validation ==="

# Check Grafana is up
if curl -sf "$GRAFANA/api/health" 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
exit(0 if d.get('database') == 'ok' else 1)
" 2>/dev/null; then
    echo "PASS: Grafana is healthy at $GRAFANA"
else
    echo "FAIL: Grafana not healthy — run: make start-observability"
    exit 1
fi

# Check Prometheus datasource
if curl -sf -u "$GRAFANA_CREDS" "$GRAFANA/api/datasources" 2>/dev/null | python3 -c "
import sys, json
ds = json.load(sys.stdin)
prom = [d for d in ds if d.get('type') == 'prometheus']
print(f'Prometheus datasources: {len(prom)}')
exit(0 if prom else 1)
" 2>/dev/null; then
    echo "PASS: Prometheus datasource is configured in Grafana"
else
    echo "FAIL: Prometheus datasource not found in Grafana"
fi

# Check Prometheus is running
if curl -sf "$PROMETHEUS/-/ready" &>/dev/null; then
    echo "PASS: Prometheus is ready at $PROMETHEUS"
else
    echo "WARN: Prometheus not running — run: make start-observability"
fi

# Check dashboards exist
DASHBOARD_COUNT=$(curl -sf -u "$GRAFANA_CREDS" "$GRAFANA/api/search?type=dash-db" 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(len(d))
" 2>/dev/null || echo "0")

if [ "$DASHBOARD_COUNT" -gt 0 ]; then
    echo "PASS: $DASHBOARD_COUNT dashboard(s) found in Grafana"
    # List dashboard titles
    curl -sf -u "$GRAFANA_CREDS" "$GRAFANA/api/search?type=dash-db" 2>/dev/null | python3 -c "
import sys, json
dashboards = json.load(sys.stdin)
for d in dashboards:
    print(f'  - {d[\"title\"]} (uid: {d.get(\"uid\",\"\")})')
" 2>/dev/null || true
else
    echo "WARN: No dashboards found — create at least one in the Grafana UI"
fi

# Check Loki datasource (bonus)
if curl -sf -u "$GRAFANA_CREDS" "$GRAFANA/api/datasources" 2>/dev/null | python3 -c "
import sys, json
ds = json.load(sys.stdin)
loki = [d for d in ds if d.get('type') == 'loki']
exit(0 if loki else 1)
" 2>/dev/null; then
    echo "PASS: Loki datasource is also configured (bonus)"
fi

# Check Jaeger datasource (bonus)
if curl -sf -u "$GRAFANA_CREDS" "$GRAFANA/api/datasources" 2>/dev/null | python3 -c "
import sys, json
ds = json.load(sys.stdin)
jaeger = [d for d in ds if d.get('type') == 'jaeger']
exit(0 if jaeger else 1)
" 2>/dev/null; then
    echo "PASS: Jaeger datasource is also configured (bonus)"
fi

echo ""
echo "=== Validation complete ==="
