#!/usr/bin/env bash
# Validate lab: k8s-deploy-first-app
set -euo pipefail

echo "=== Kubernetes: Deploy First App — Validation ==="
KUBE_CTX="kind-cloud-lab"

# Check kubectl is installed
if kubectl version --client &>/dev/null; then
    echo "PASS: kubectl is installed"
else
    echo "FAIL: kubectl not installed"
    exit 1
fi

# Check kind cluster is running
if kubectl get nodes --context "$KUBE_CTX" 2>/dev/null | grep -q Ready; then
    NODE_COUNT=$(kubectl get nodes --context "$KUBE_CTX" 2>/dev/null | grep -c Ready)
    echo "PASS: kind cluster has $NODE_COUNT Ready node(s)"
else
    echo "FAIL: kind cluster not running or not reachable"
    echo "      Run: make k8s-create"
    exit 1
fi

# Check for webapp deployment
if kubectl get deployment webapp --context "$KUBE_CTX" 2>/dev/null | grep -q webapp; then
    READY=$(kubectl get deployment webapp --context "$KUBE_CTX" -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
    DESIRED=$(kubectl get deployment webapp --context "$KUBE_CTX" -o jsonpath='{.spec.replicas}' 2>/dev/null)
    echo "PASS: webapp Deployment exists — $READY/$DESIRED replicas ready"
else
    echo "WARN: webapp Deployment not found (may have been cleaned up)"
    echo "      Create with: kubectl create deployment webapp --image=nginx:alpine --replicas=2"
fi

# Check for webapp service
if kubectl get service webapp --context "$KUBE_CTX" 2>/dev/null | grep -q webapp; then
    SVC_TYPE=$(kubectl get service webapp --context "$KUBE_CTX" -o jsonpath='{.spec.type}' 2>/dev/null)
    echo "PASS: webapp Service exists (type: $SVC_TYPE)"
else
    echo "WARN: webapp Service not found (may have been cleaned up)"
    echo "      Expose with: kubectl expose deployment webapp --port=80 --type=NodePort"
fi

# Check pod logs are accessible
POD=$(kubectl get pods -l app=webapp --context "$KUBE_CTX" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
if [ -n "$POD" ]; then
    if kubectl logs "$POD" --context "$KUBE_CTX" &>/dev/null; then
        echo "PASS: Pod logs are accessible for pod $POD"
    else
        echo "WARN: Could not retrieve pod logs"
    fi
else
    echo "INFO: No webapp pods running currently"
fi

echo ""
echo "=== Validation complete ==="
