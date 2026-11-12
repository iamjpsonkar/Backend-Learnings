#!/usr/bin/env bash
# optimize-images.sh — Compress PNG images that exceed the 500KB size limit
#
# Usage:
#   ./scripts/optimize-images.sh           # optimize all oversized PNGs in assets/
#   ./scripts/optimize-images.sh --dry-run # show what would be optimized, no changes
#   ./scripts/optimize-images.sh path/to/image.png  # optimize a single file
#
# Requires: pngquant — install via setup-local.sh
# Strategy: lossy compression (pngquant) targeting 65–80% quality range.
#           Originals are preserved with a .orig backup before replacement.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGES_DIR="$REPO_ROOT/assets/images"

LIMIT_BYTES=512000   # 500KB
QUALITY_RANGE="65-80"
DRY_RUN=false

log_info()    { echo "[INFO]    $*"; }
log_success() { echo "[OK]      $*"; }
log_skip()    { echo "[SKIP]    $*"; }
log_warn()    { echo "[WARN]    $*"; }
log_error()   { echo "[ERROR]   $*" >&2; }

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
check_deps() {
    if ! command -v pngquant &>/dev/null; then
        log_error "pngquant not found."
        log_error "Install it with: brew install pngquant  (macOS)"
        log_error "                 sudo apt-get install pngquant  (Debian/Ubuntu)"
        log_error "Or run: ./scripts/setup-local.sh"
        exit 1
    fi
    log_info "Using pngquant: $(pngquant --version 2>/dev/null | head -1)"
}

# ---------------------------------------------------------------------------
# Optimize a single PNG file
# ---------------------------------------------------------------------------
optimize_file() {
    local img="$1"
    local size
    size="$(wc -c <"$img" 2>/dev/null || echo 0)"
    local size_kb=$(( size / 1024 ))

    if [[ "$size" -le "$LIMIT_BYTES" ]]; then
        log_skip "Already within limit (${size_kb}KB): $img"
        return 0
    fi

    if [[ "$DRY_RUN" == true ]]; then
        log_warn "DRY RUN — would optimize (${size_kb}KB): $img"
        return 0
    fi

    log_info "Optimizing (${size_kb}KB): $img"

    # Backup original
    local backup="${img}.orig"
    cp "$img" "$backup"
    log_info "  Backup saved: $backup"

    # Run pngquant — output to a temp file then replace
    local tmp="${img}.tmp.png"
    if pngquant \
        --quality "$QUALITY_RANGE" \
        --skip-if-larger \
        --force \
        --output "$tmp" \
        "$img" 2>/dev/null; then

        local new_size
        new_size="$(wc -c <"$tmp" 2>/dev/null || echo 0)"
        local new_size_kb=$(( new_size / 1024 ))
        local saved_kb=$(( size_kb - new_size_kb ))

        mv "$tmp" "$img"
        log_success "Optimized: ${size_kb}KB → ${new_size_kb}KB (saved ${saved_kb}KB): $img"
    else
        # pngquant returned non-zero (e.g., --skip-if-larger triggered)
        rm -f "$tmp"
        log_warn "Could not reduce size further — keeping original: $img"
        rm -f "$backup"
    fi
}

# ---------------------------------------------------------------------------
# Scan and optimize all PNGs in assets/images/
# ---------------------------------------------------------------------------
optimize_all() {
    local total=0
    local optimized=0
    local skipped=0

    while IFS= read -r img; do
        ((total++))
        local size
        size="$(wc -c <"$img" 2>/dev/null || echo 0)"
        if [[ "$size" -gt "$LIMIT_BYTES" ]]; then
            optimize_file "$img"
            ((optimized++))
        else
            ((skipped++))
        fi
    done < <(find "$IMAGES_DIR" -type f -name "*.png" | sort)

    echo ""
    log_info "Scan complete — Total: $total, Optimized: $optimized, Skipped (within limit): $skipped"
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
main() {
    check_deps

    local targets=()

    for arg in "$@"; do
        case "$arg" in
            --dry-run) DRY_RUN=true ;;
            --help|-h)
                echo "Usage: $0 [--dry-run] [path/to/image.png ...]"
                exit 0
                ;;
            -*)
                log_error "Unknown flag: $arg"
                exit 1
                ;;
            *)
                targets+=("$arg")
                ;;
        esac
    done

    if [[ "$DRY_RUN" == true ]]; then
        log_info "Dry-run mode — no files will be modified"
    fi

    if [[ "${#targets[@]}" -gt 0 ]]; then
        for target in "${targets[@]}"; do
            if [[ ! -f "$target" ]]; then
                log_error "File not found: $target"
                exit 1
            fi
            optimize_file "$target"
        done
    else
        log_info "Scanning $IMAGES_DIR for PNG files exceeding ${LIMIT_BYTES} bytes (500KB)..."
        optimize_all
    fi
}

main "$@"
