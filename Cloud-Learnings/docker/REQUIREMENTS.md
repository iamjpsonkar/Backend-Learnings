# Requirements

## System Requirements

### Minimum (core profile only)

| Resource | Minimum |
|---|---|
| RAM | 4 GB free |
| CPU | 2 cores |
| Disk | 10 GB free |
| Docker | 24.x+ |
| Docker Compose | v2.20+ |

### Recommended (multiple profiles)

| Resource | Recommended |
|---|---|
| RAM | 8 GB free |
| CPU | 4 cores |
| Disk | 30 GB free |

### For heavy profiles (observability, security, cicd, all)

| Resource | Heavy |
|---|---|
| RAM | 16 GB free |
| CPU | 6+ cores |
| Disk | 50 GB free |

---

## Software Requirements

### Required

- **Docker Desktop 4.x+** (macOS, Windows) or **Docker Engine 24.x+** (Linux)
- **Docker Compose v2** — comes bundled with Docker Desktop; for Linux install separately
- **Bash 4.x+** — macOS ships with bash 3.2 (POSIX-compatible run.sh is provided); install bash 5 via Homebrew for best experience

Check versions:

```bash
docker --version
docker compose version
bash --version
```

### Optional (for kubernetes labs)

- **kind** — `brew install kind` (macOS) or install binary
- **k3d** — `brew install k3d` (macOS) or install binary
- **kubectl** — `brew install kubectl` (macOS)
- **helm** — `brew install helm` (macOS)

run.sh will check for these and warn if missing when you try to use kubernetes labs.

### Optional (for shell tooling)

- **jq** — JSON parsing: `brew install jq`
- **yq** — YAML parsing: `brew install yq`
- **curl** — HTTP testing (usually pre-installed)
- **openssl** — TLS/cert generation (usually pre-installed)

---

## Platform Support

### macOS

Fully supported. Tested on macOS 13+ (Ventura) and 14+ (Sonoma) with Docker Desktop.

```bash
# Install Docker Desktop
brew install --cask docker

# Install optional tools
brew install kind k3d kubectl helm jq yq
```

### Linux (Ubuntu/Debian)

Fully supported. Tested on Ubuntu 22.04 LTS.

```bash
# Install Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose v2
sudo apt install docker-compose-plugin

# Install optional tools
sudo apt install jq
```

### Windows (WSL2)

Supported via WSL2. Run everything inside a WSL2 Ubuntu terminal.

1. Install Docker Desktop for Windows
2. Enable WSL2 integration in Docker Desktop settings
3. Open WSL2 Ubuntu terminal
4. Clone the repo inside WSL2 filesystem (not /mnt/c/)
5. Run all commands from WSL2 terminal

**Do not run from PowerShell or CMD directly.**

---

## Docker Desktop Settings (macOS)

For heavy profiles, increase Docker Desktop resource limits:

1. Open Docker Desktop
2. Settings → Resources
3. Set Memory: 8-16 GB (depending on profiles you use)
4. Set CPUs: 4-8
5. Set Disk: 60+ GB
6. Apply and Restart

---

## Network Requirements

- Ports 80, 443, 3000-9999 range must be available on localhost
- No firewall blocking Docker bridge networks
- Internet access required for first run (image pulls only)
- After images are pulled, everything works fully offline

---

## Port Availability

Before starting, check for port conflicts:

```bash
./run.sh doctor
```

Or manually:

```bash
# macOS/Linux
lsof -i :80
lsof -i :3000
lsof -i :8080
```

If ports are in use, edit `.env` to remap them.

---

## Disk Space Estimates

| Profile | Approximate image size |
|---|---|
| core | ~500 MB |
| data | ~2 GB |
| aws (LocalStack) | ~1.5 GB |
| azure (Azurite) | ~800 MB |
| gcp emulators | ~2 GB |
| observability | ~3 GB |
| security | ~3 GB |
| cicd | ~3 GB |
| all profiles | ~15 GB |

Images are pulled once and cached. Volumes add additional disk usage.

---

## Credential Requirements

**None.** All credentials are fake and local-only. See [SECURITY.md](SECURITY.md).

Real cloud credentials (AWS, Azure, GCP) are **never required** and **never used** in default mode.
