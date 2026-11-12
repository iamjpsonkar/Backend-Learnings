#!/usr/bin/env bash
# generate-diagrams.sh — Render Mermaid .mmd sources to SVG
#
# Usage:
#   ./scripts/generate-diagrams.sh              # render all .mmd files
#   ./scripts/generate-diagrams.sh path/to.mmd  # render a single file
#
# Output: SVG files are written to assets/diagrams/svg/
# Requires: @mermaid-js/mermaid-cli (mmdc) — install via setup-local.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MERMAID_SRC="$REPO_ROOT/assets/diagrams/mermaid"
SVG_OUT="$REPO_ROOT/assets/diagrams/svg"

log_info()    { echo "[INFO]    $*"; }
log_success() { echo "[OK]      $*"; }
log_error()   { echo "[ERROR]   $*" >&2; }

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
check_deps() {
    if ! command -v mmdc &>/dev/null; then
        log_error "mmdc (Mermaid CLI) not found."
        log_error "Install it with: npm install -g @mermaid-js/mermaid-cli"
        log_error "Or run: ./scripts/setup-local.sh"
        exit 1
    fi
    log_info "Using mmdc: $(mmdc --version 2>/dev/null | head -1)"
}

# ---------------------------------------------------------------------------
# Render a single .mmd file to SVG
# ---------------------------------------------------------------------------
render_file() {
    local src="$1"
    local basename
    basename="$(basename "$src" .mmd)"
    local out="$SVG_OUT/${basename}.svg"

    log_info "Rendering: $src → $out"

    mmdc \
        --input "$src" \
        --output "$out" \
        --theme neutral \
        --backgroundColor transparent \
        --quiet

    if [[ -f "$out" ]]; then
        local size_kb
        size_kb="$(du -k "$out" | cut -f1)"
        log_success "Generated: $out (${size_kb}KB)"
    else
        log_error "Failed to generate: $out"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Render all .mmd files in mermaid/ directory
# ---------------------------------------------------------------------------
render_all() {
    local count=0
    local failed=0

    while IFS= read -r file; do
        if render_file "$file"; then
            ((count++))
        else
            ((failed++))
        fi
    done < <(find "$MERMAID_SRC" -name "*.mmd" -type f | sort)

    echo ""
    log_info "Rendered: $count file(s)"
    if [[ "$failed" -gt 0 ]]; then
        log_error "Failed: $failed file(s)"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
main() {
    check_deps
    mkdir -p "$SVG_OUT"

    if [[ "$#" -gt 0 ]]; then
        # Render specific file(s) passed as arguments
        for src in "$@"; do
            if [[ ! -f "$src" ]]; then
                log_error "File not found: $src"
                exit 1
            fi
            render_file "$src"
        done
    else
        # Render all
        local total
        total="$(find "$MERMAID_SRC" -name "*.mmd" -type f | wc -l | tr -d ' ')"
        log_info "Found $total .mmd file(s) in $MERMAID_SRC"

        if [[ "$total" -eq 0 ]]; then
            log_info "No .mmd files found. Add Mermaid diagrams to $MERMAID_SRC"
            exit 0
        fi

        render_all
    fi

    log_success "Done. SVGs written to: $SVG_OUT"
}

main "$@"
