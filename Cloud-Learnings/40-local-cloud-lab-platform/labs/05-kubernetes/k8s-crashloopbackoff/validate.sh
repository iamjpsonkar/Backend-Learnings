#!/usr/bin/env bash
# Validate lab: k8s-crashloopbackoff
set -euo pipefail

CONTEXT="kind-cloud-lab"
NS="lab-debug"

check_k8s() {
    local desc="$1"
    shift
    if kubectl --context "$CONTEXT" "$@" &>/dev/null; then
        echo "PASS: $desc"
    else
        echo "FAIL: $desc"
    fi
}

# Check cluster is accessible
if ! kubectl --context "$CONTEXT" cluster-info &>/dev/null; then
    echo "FAIL: Kind cluster 'cloud-lab' not reachable. Run: make k8s-create-cluster"
    exit 1
fi

# Check namespace exists
check_k8s "Namespace lab-debug exists" get namespace "$NS"

# Check deployment exists
check_k8s "Deployment broken-app exists" get deployment broken-app -n "$NS"

# Check deployment is ready (this is the main success criteria)
if kubectl --context "$CONTEXT" rollout status deployment/broken-app -n "$NS" --timeout=30s &>/dev/null; then
    echo "PASS: Deployment broken-app is rolled out and ready"
else
    echo "FAIL: Deployment broken-app is not ready (pod may still be crashing)"
fi

# Check pod phase
POD_PHASE=$(kubectl --context "$CONTEXT" get pods -n "$NS" -l app=broken-app \
    -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "Unknown")
if [ "$POD_PHASE" = "Running" ]; then
    echo "PASS: Pod is in Running phase"
else
    echo "FAIL: Pod phase is '$POD_PHASE' (expected Running)"
fi

# Check restart count > 0 (confirms the bug was triggered at some point)
RESTARTS=$(kubectl --context "$CONTEXT" get pods -n "$NS" -l app=broken-app \
    -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}' 2>/dev/null || echo "0")
if [ "$RESTARTS" -ge 1 ]; then
    echo "PASS: Pod had $RESTARTS restart(s) — crash was triggered and recovered"
else
    echo "FAIL: Pod shows 0 restarts — the broken deployment may not have been applied"
fi
