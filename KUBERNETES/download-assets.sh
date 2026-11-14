#!/usr/bin/env bash
# Download remote images referenced in Markdown under KUBERNETES/ into assets/.
# Local relative assets are left untouched. Existing files are skipped unless --force.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ASSET_DIR="${ASSET_DIR:-${SCRIPT_DIR}/assets}"
FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

for cmd in curl find grep sed basename mktemp; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: required command not found: $cmd" >&2; exit 1; }
done
mkdir -p "$ASSET_DIR"

resolve_url() {
  local url="$1"
  if [[ "$url" =~ ^https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)$ ]]; then
    printf 'https://raw.githubusercontent.com/%s/%s/%s/%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}"
  else
    printf '%s\n' "$url"
  fi
}

declare -A URL_BY_NAME=()
while IFS= read -r -d '' md_file; do
  while IFS= read -r target; do
    [[ -z "$target" ]] && continue
    case "$target" in
      http://*|https://*)
        url="$(resolve_url "$target")"
        name="$(basename "${target%%\?*}")"
        [[ "$name" == *.* ]] || { echo "WARN: image URL has no extension: $target" >&2; continue; }
        URL_BY_NAME["$name"]="$url"
        ;;
      *) : ;;
    esac
  done < <(grep -oE '!\[[^]]*\]\([^ )]+' "$md_file" | sed -E 's/^!\[[^]]*\]\(//' || true)
done < <(find "$SCRIPT_DIR" -type f \( -iname '*.md' -o -iname '*.markdown' \) -print0)

if (( ${#URL_BY_NAME[@]} == 0 )); then
  echo "No remote Markdown image links found. Local asset references are not downloaded."
  exit 0
fi

downloaded=0
skipped=0
failed=0
for name in "${!URL_BY_NAME[@]}"; do
  url="${URL_BY_NAME[$name]}"
  destination="$ASSET_DIR/$name"
  if [[ -s "$destination" && "$FORCE" -ne 1 ]]; then
    printf 'SKIP  %s (already exists; use --force to replace)\n' "$name"
    ((skipped+=1))
    continue
  fi

  temp_file="$(mktemp "${ASSET_DIR}/.${name}.XXXXXX")"
  printf 'GET   %s\n' "$url"
  if curl --fail --location --silent --show-error \
      --retry 3 --retry-delay 1 --connect-timeout 15 --max-time 120 \
      --user-agent 'Learnings-Kubernetes-asset-downloader/1.0' \
      "$url" --output "$temp_file"; then
    if [[ ! -s "$temp_file" ]] || grep -aqiE '<!doctype html|<html[ >]' "$temp_file"; then
      printf 'FAIL  %s (empty response or HTML instead of image)\n' "$name" >&2
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
