# Scripts

Utility scripts for maintaining and validating the Cloud-Learnings repository.

## Scripts

| Script | Language | Purpose |
|--------|----------|---------|
| `setup-local.sh` | Bash | Install all local tooling dependencies |
| `validate-repo.sh` | Bash | Run all repository health checks |
| `generate-diagrams.sh` | Bash | Render Mermaid `.mmd` files to SVG |
| `optimize-images.sh` | Bash | Compress PNG images above size threshold |
| `check-missing-topics.py` | Python | Report folders missing expected files |

## Quick Start

```bash
# Install dependencies first
./scripts/setup-local.sh

# Then validate the repo
./scripts/validate-repo.sh
```

## Running Individual Scripts

```bash
# Validate only
./scripts/validate-repo.sh

# Validate portable LF endings for scripts and configuration
./scripts/validate-repo.sh --line-endings

# Check which topics are missing content
python3 ./scripts/check-missing-topics.py

# Generate SVGs from Mermaid sources
./scripts/generate-diagrams.sh

# Optimize large images
./scripts/optimize-images.sh
```

## Requirements

| Tool | Used by | Install |
|------|---------|---------|
| `bash` 4+ | All shell scripts | Pre-installed on Linux/macOS |
| `python3` 3.9+ | check-missing-topics.py | `brew install python` |
| `node` 18+ | generate-diagrams.sh | `brew install node` |
| `@mermaid-js/mermaid-cli` | generate-diagrams.sh | `npm install -g @mermaid-js/mermaid-cli` |
| `pngquant` | optimize-images.sh | `brew install pngquant` |
| `markdownlint-cli` | validate-repo.sh | `npm install -g markdownlint-cli` |

Run `./scripts/setup-local.sh` to install all of the above automatically.
