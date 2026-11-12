#!/usr/bin/env bash

set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"

required_files=(
  README.md
  compose.yaml
  examples/nginx/.dockerignore
  examples/nginx/Dockerfile
  examples/nginx/index.html
)

for path in "${required_files[@]}"; do
  if [[ ! -s "$path" ]]; then
    printf 'error: required file is missing or empty: %s\n' "$path" >&2
    exit 1
  fi
done

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
fi

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck scripts/validate.sh
fi

if ! command -v docker >/dev/null 2>&1; then
  printf 'Docker is not installed; skipping Compose and image checks.\n'
  exit 0
fi

docker compose config --quiet

if ! docker info >/dev/null 2>&1; then
  printf 'Docker daemon is unavailable; skipping image checks.\n'
  exit 0
fi

docker build --check examples/nginx
docker build --tag docker-learning-nginx:validation examples/nginx

printf 'Repository validation passed.\n'
