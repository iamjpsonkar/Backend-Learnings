#!/usr/bin/env bash
#
# Download every image referenced by Markdown files under KUBERNETES/
# into KUBERNETES/assets/ using the exact basename referenced by Markdown.
#
# Usage:
#   chmod +x KUBERNETES/download-assets.sh
#   ./KUBERNETES/download-assets.sh
#
# Optional:
#   ./KUBERNETES/download-assets.sh --force
#   ASSET_DIR=/custom/path ./KUBERNETES/download-assets.sh
#
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ASSET_DIR="${ASSET_DIR:-${SCRIPT_DIR}/assets}"
FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

mkdir -p "$ASSET_DIR"

for command in curl grep sed awk; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'ERROR: required command not found: %s\n' "$command" >&2
    exit 1
  }
done

# Resolve raw image URLs to the exact Markdown image filename.
# Add new entries here when a Markdown image points to a non-raw source.
resolve_url() {
  local url="$1"
  case "$url" in
    https://github.com/*/blob/*)
      printf '%s\n' "$url" | sed -E 's#https://github.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)#https://raw.githubusercontent.com/\1/\2/\3/\4#'
      ;;
    *)
      printf '%s\n' "$url"
      ;;
  esac
}

declare -A IMAGE_URLS=()
declare -A IMAGE_FILES=()

# Match standard Markdown image syntax: ![alt](path-or-url "optional title")
while IFS= read -r -d '' md_file; do
  while IFS= read -r line; do
    # Extract each image destination. This intentionally supports simple
    # Markdown image links; paths with parentheses should be URL-encoded.
    while IFS= read -r target; do
      [[ -z "$target" ]] && continue
      case "$target" in
        http://*|https://*)
          url="$target"
          name="$(basename "${url%%\?*}")"
          ;;
        *)
          # Existing local assets are already in place; do not download them.
          continue
          ;;
      esac

      [[ "$name" == *.* ]] || {
        printf 'WARN: image URL has no file extension, skipping: %s\n' "$url" >&2
        continue
      }

      IMAGE_URLS["$name"]="$(resolve_url "$url")"
      IMAGE_FILES["$name"]=1
    done < <(printf '%s\n' "$line" | grep -oE '!\[[^]]*\]\([^ )]+' | sed -E 's/^!\[[^]]*\]\(//')
  done < "$md_file"
done < <(find "$SCRIPT_DIR" -type f \( -iname '*.md' -o -iname '*.markdown' \) -print0)

if (( ${#IMAGE_URLS[@]} == 0 )); then
  echo "No remote Markdown images found. Existing relative images need no download."
  exit 0
fi

downloaded=0
skipped=0
failed=0

for name in "${!IMAGE_URLS[@]}"; do
  url="${IMAGE_URLS[$name]}"
  destination="$ASSET_DIR/$name"
  temp_file="$(mktemp "${ASSET_DIR}/.${name}.XXXXXX")"

  if [[ -s "$destination" && "$FORCE" -ne 1 ]]; then
    printf 'SKIP  %s (already exists; use --force to replace)\n' "$name"
    ((skipped+=1))
    continue
  fi

  printf 'GET   %s\n' "$url"
  if curl --fail --location --silent --show-error \
      --retry 3 --retry-delay 1 --connect-timeout 15 --max-time 120 \
      --user-agent "Learnings-Kubernetes-asset-downloader/1.0" \
      "$url" --output "$temp_file"; then

    # Reject empty responses and common HTML error pages saved as image files.
    if [[ ! -s "$temp_file" ]] || grep -aqiE '<!doctype html|<html[ >]' "$temp_file"; then
      printf 'FAIL  %s (empty response or HTML instead of an image)\n' "$name" >&2
      rm -f "$temp_file"
      ((failed+=1))
      continue
    fi

    mv -f "$temp_file" "$destination"
    printf 'OK    %s (%s bytes)\n' "$name" "$(wc -c < "$destination" | tr -d ' ')"
    ((downloaded+=1))
  else
    printf 'FAIL  %s\n' "$name" >&2
    rm -f "$temp_file"
    ((failed+=1))
  fi
done

printf '\nSummary: %d downloaded, %d skipped, %d failed.\n' "$downloaded" "$skipped" "$failed"
printf 'Asset directory: %s\n' "$ASSET_DIR"

(( failed == 0 )) || exit 1
