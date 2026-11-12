#!/usr/bin/env bash
# scripts/k8s-dashboard.sh — Start the Kubernetes dashboard for the lab cluster
# Run: make k8s-dashboard

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

CLUSTER_CONTEXT="kind-cloud-lab"

log_step "Kubernetes Dashboard"

require_command kubectl
require_command helm

# Check cluster exists
if ! kubectl cluster-info --context "$CLUSTER_CONTEXT" &>/dev/null; then
    log_error "Cluster '$CLUSTER_CONTEXT' is not running"
    echo "Create it with: make k8s-create-cluster"
    exit 1
fi

# Install dashboard if not present
if ! kubectl get deployment kubernetes-dashboard -n kubernetes-dashboard &>/dev/null 2>&1; then
    log_info "Installing Kubernetes Dashboard..."
    helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/ 2>/dev/null || true
    helm repo update
    helm upgrade --install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard \
        --create-namespace \
        --namespace kubernetes-dashboard \
        --set=app.ingress.enabled=false \
        --kube-context "$CLUSTER_CONTEXT"

    # Create admin service account
    kubectl apply --context "$CLUSTER_CONTEXT" -f - << 'EOF'
apiVersion: v1
kind: ServiceAccount
metadata:
  name: lab-admin
  namespace: kubernetes-dashboard
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: lab-admin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: lab-admin
  namespace: kubernetes-dashboard
EOF
    log_ok "Dashboard installed"
fi

# Get token
log_info "Generating access token..."
TOKEN=$(kubectl create token lab-admin --namespace kubernetes-dashboard --context "$CLUSTER_CONTEXT" 2>/dev/null)

echo ""
echo -e "${BOLD}Kubernetes Dashboard${RESET}"
echo ""
echo "Starting kubectl proxy..."
echo "Dashboard URL: http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/"
echo ""
echo "Access token (copy this):"
echo ""
echo "$TOKEN"
echo ""
echo "Press Ctrl+C to stop the proxy"
echo ""

kubectl proxy --context "$CLUSTER_CONTEXT"
