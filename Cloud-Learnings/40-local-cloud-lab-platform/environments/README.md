# Environments

Environment-specific configuration overrides for the lab platform.

## Usage

Override docker-compose settings for specific environments using override files:

```bash
# Low-memory mode (limits container resources)
docker compose -f docker-compose.yml -f environments/low-memory.yml --profile core up -d

# High-performance mode (increased resource limits)
docker compose -f docker-compose.yml -f environments/high-perf.yml --profile core up -d
```

## Available Environments

| File | Use Case | RAM |
|------|----------|-----|
| `low-memory.yml` | 8 GB RAM machines | Conservative limits |
| `high-perf.yml` | 32+ GB RAM machines | Increased limits |
| `ci.yml` | CI/CD environments | Minimal, fast startup |

## Customization

Copy and edit any override file for your specific needs:
```bash
cp environments/low-memory.yml environments/my-custom.yml
```
