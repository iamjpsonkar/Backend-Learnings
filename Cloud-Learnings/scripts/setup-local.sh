#!/usr/bin/env bash
# setup-local.sh — Install all local tooling dependencies for Cloud-Learnings
#
# Usage:
#   ./scripts/setup-local.sh
#
# Supports: macOS (Homebrew) and Debian/Ubuntu Linux

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

log_info()    { echo "[INFO]    $*"; }
log_success() { echo "[OK]      $*"; }
log_warn()    { echo "[WARN]    $*"; }
log_error()   { echo "[ERROR]   $*" >&2; }

# ---------------------------------------------------------------------------
# Detect platform
# ---------------------------------------------------------------------------
detect_platform() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    else
        echo "unknown"
    fi
}

PLATFORM="$(detect_platform)"
log_info "Detected platform: $PLATFORM"
log_info "Repo root: $REPO_ROOT"

# ---------------------------------------------------------------------------
# Check/install Homebrew (macOS only)
# ---------------------------------------------------------------------------
ensure_brew() {
    if [[ "$PLATFORM" != "macos" ]]; then
        return 0
    fi
    if command -v brew &>/dev/null; then
        log_success "Homebrew already installed: $(brew --version | head -1)"
        return 0
    fi
    log_info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    log_success "Homebrew installed"
}

# ---------------------------------------------------------------------------
# Ensure a binary is available; install if missing
# ---------------------------------------------------------------------------
ensure_binary() {
    local binary="$1"
    local install_cmd_macos="$2"
    local install_cmd_debian="${3:-}"

    if command -v "$binary" &>/dev/null; then
        log_success "$binary already available: $("$binary" --version 2>/dev/null | head -1 || echo 'ok')"
        return 0
    fi

    log_info "Installing $binary..."
    case "$PLATFORM" in
        macos)
            eval "$install_cmd_macos"
            ;;
        debian)
            if [[ -n "$install_cmd_debian" ]]; then
                eval "$install_cmd_debian"
            else
                log_warn "No Debian install command for $binary — install manually."
                return 1
            fi
            ;;
        *)
            log_warn "Unknown platform — cannot auto-install $binary. Install it manually."
            return 1
            ;;
    esac
    log_success "$binary installed"
}

# ---------------------------------------------------------------------------
# Ensure an npm global package is available
# ---------------------------------------------------------------------------
ensure_npm_global() {
    local package="$1"
    local binary="${2:-$1}"

    if command -v "$binary" &>/dev/null; then
        log_success "npm:$package already installed"
        return 0
    fi

    log_info "Installing npm package: $package..."
    npm install -g "$package"
    log_success "npm:$package installed"
}

# ---------------------------------------------------------------------------
# Main installation sequence
# ---------------------------------------------------------------------------
main() {
    log_info "=== Cloud-Learnings local setup ==="

    ensure_brew

    # Python 3
    ensure_binary "python3" \
        "brew install python3" \
        "sudo apt-get install -y python3 python3-pip"

    # Node.js (needed for npm tools)
    ensure_binary "node" \
        "brew install node" \
        "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs"

    # pngquant for image optimization
    ensure_binary "pngquant" \
        "brew install pngquant" \
        "sudo apt-get install -y pngquant"

    # markdownlint-cli
    ensure_npm_global "markdownlint-cli" "markdownlint"

    # markdown-link-check
    ensure_npm_global "markdown-link-check"

    # Mermaid CLI for diagram generation
    ensure_npm_global "@mermaid-js/mermaid-cli" "mmdc"

    log_info ""
    log_success "=== Setup complete ==="
    log_info "Run the following to validate the repository:"
    log_info "  ./scripts/validate-repo.sh"
}

main "$@"
