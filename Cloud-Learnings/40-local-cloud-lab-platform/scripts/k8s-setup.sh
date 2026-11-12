#!/usr/bin/env bash
# scripts/k8s-setup.sh — Create or delete the kind cluster for Kubernetes labs
# Usage: bash k8s-setup.sh create | delete | status

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/utils/common.sh"
load_env

CLUSTER_NAME="cloud-lab"
KIND_CONFIG="$PLATFORM_ROOT/configs/kind-cluster.yaml"

ACTION="${1:-create}"

case "$ACTION" in
create)
    log_step "Creating kind cluster: $CLUSTER_NAME"

    require_command kind "brew install kind  OR  curl -Lo kind https://kind.sigs.k8s.io/dl/v0.23.0/kind-linux-amd64 && chmod +x kind && mv kind /usr/local/bin/"
    require_command kubectl "brew install kubectl"
    require_docker

    if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        log_warn "Cluster '$CLUSTER_NAME' already exists"
        log_info "To delete it: make k8s-delete-cluster"
        exit 0
    fi

    if [[ -f "$KIND_CONFIG" ]]; then
        log_info "Using kind config: $KIND_CONFIG"
        kind create cluster --name "$CLUSTER_NAME" --config "$KIND_CONFIG"
    else
        log_info "Using default kind config (single-node)"
        kind create cluster --name "$CLUSTER_NAME"
    fi

    log_ok "Cluster created: $CLUSTER_NAME"
    log_info "Exporting kubeconfig..."
    kind export kubeconfig --name "$CLUSTER_NAME"

    log_step "Installing essential cluster components"

    # Install metrics-server for HPA labs
    log_info "Installing metrics-server..."
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml 2>/dev/null || true
    kubectl patch deployment metrics-server -n kube-system \
        --type=json \
        -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' \
        2>/dev/null || true

    log_ok "Kind cluster ready"
    echo ""
    echo "Test with:"
    echo "  kubectl cluster-info --context kind-$CLUSTER_NAME"
    echo "  kubectl get nodes"
    ;;

delete)
    log_step "Deleting kind cluster: $CLUSTER_NAME"
    require_command kind

    if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        log_info "Cluster '$CLUSTER_NAME' does not exist"
        exit 0
    fi

    kind delete cluster --name "$CLUSTER_NAME"
    log_ok "Cluster deleted"
    ;;

status)
    if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        log_ok "Cluster '$CLUSTER_NAME' exists"
        kubectl cluster-info --context "kind-$CLUSTER_NAME" 2>/dev/null || true
        kubectl get nodes --context "kind-$CLUSTER_NAME" 2>/dev/null || true
    else
        log_warn "Cluster '$CLUSTER_NAME' does not exist"
        echo "Create it with: make k8s-create-cluster"
    fi
    ;;

*)
    log_error "Unknown action: $ACTION"
    echo "Usage: $0 create | delete | status"
    exit 1
    ;;
esac
