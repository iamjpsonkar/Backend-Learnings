# System Requirements

## Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| Disk (free) | 20 GB | 40 GB |
| Docker | 24.0+ | Latest |
| Docker Compose | v2.20+ | Latest |
| Python | 3.11+ | 3.12 |

**RAM by profile:**

| Profile | Approximate RAM |
|---------|----------------|
| core (MinIO + Traefik + API + UI) | ~512 MB |
| observability | ~1.5 GB |
| security | ~1 GB |
| cicd | ~1.5 GB |
| data | ~2 GB |
| aws-local | ~512 MB |
| azure-local | ~256 MB |
| all profiles | ~8 GB |

---

## macOS

### Tested On
- macOS 13 (Ventura) or later
- Intel and Apple Silicon (M1/M2/M3/M4)

### Install Docker Desktop
```bash
# Via Homebrew (recommended)
brew install --cask docker

# Or download from: https://www.docker.com/products/docker-desktop/
```

### Configure Docker Desktop for macOS
1. Open Docker Desktop > Settings > Resources
2. Set Memory: at least 8 GB (16 GB recommended for all profiles)
3. Set CPUs: at least 4
4. Set Disk image size: at least 40 GB

### Apple Silicon Notes
- Most containers run natively on ARM64
- LocalStack and a few others use `linux/amd64` via Rosetta — Docker Desktop handles this automatically
- If you see `exec format error`, a specific container needs `platform: linux/amd64`

### Install Other Tools
```bash
# Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Required
brew install python@3.12 make

# Kubernetes tools (for kubernetes labs)
brew install kubectl kind helm k9s

# IaC tools (for terraform labs)
brew install terraform opentofu

# Security scanning (for security labs)
brew install trivy checkov

# Utilities
brew install jq yq curl wget
```

---

## Linux (Ubuntu/Debian)

### Install Docker Engine
```bash
# Remove old versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine + Compose
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to docker group (log out and back in after this)
sudo usermod -aG docker $USER
```

### Install Other Tools (Linux)
```bash
# Python 3.12
sudo apt-get install -y python3.12 python3.12-venv python3-pip make curl wget jq

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.23.0/kind-linux-amd64
chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# OpenTofu
curl --proto '=https' --tlsv1.2 -fsSL https://get.opentofu.org/install-opentofu.sh | sh

# Trivy
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy
```

---

## Windows (WSL2)

WSL2 is required. Native Windows Docker without WSL2 is not supported.

### Setup WSL2
```powershell
# In PowerShell as Administrator
wsl --install
wsl --set-default-version 2
```

Install Ubuntu 22.04 from the Microsoft Store.

### Install Docker Desktop for Windows
1. Download Docker Desktop for Windows
2. In Settings > General: enable "Use the WSL 2 based engine"
3. In Settings > Resources > WSL Integration: enable for Ubuntu-22.04
4. Set Memory to at least 8 GB

### Inside WSL2 Ubuntu
Follow the Linux instructions above inside your WSL2 terminal.

### Windows-Specific Notes
- Always run commands from within WSL2, not from PowerShell/CMD
- File paths must use Linux paths (`/home/user/...`) not Windows paths
- Port forwarding from WSL2 to Windows is automatic in Docker Desktop
- If ports aren't accessible from Windows, restart Docker Desktop

---

## Tool Version Reference

| Tool | Minimum Version | Check Command |
|------|----------------|---------------|
| Docker Engine | 24.0 | `docker --version` |
| Docker Compose | 2.20 | `docker compose version` |
| Python | 3.11 | `python3 --version` |
| kubectl | 1.28 | `kubectl version --client` |
| kind | 0.20 | `kind --version` |
| Helm | 3.13 | `helm version` |
| Terraform | 1.6 | `terraform --version` |
| OpenTofu | 1.6 | `tofu --version` |
| Trivy | 0.48 | `trivy --version` |

---

## Ports That Must Be Free

Before starting, ensure these ports are not in use:

```bash
# Check for port conflicts
make check-ports

# Or manually:
lsof -i :3001 -i :4567 -i :8080 -i :9000 -i :9001 -i :9090 -i :3000
```

If a port is in use, edit `.env` to change the port mapping.

---

## Disk Space Requirements

| Profile | Approximate Images Size |
|---------|------------------------|
| core | ~1 GB |
| observability | ~2 GB |
| security | ~2 GB |
| cicd | ~2.5 GB |
| data | ~3 GB |
| aws-local | ~1.5 GB |
| all | ~10 GB |

Docker images are cached — starting profiles again after first pull is instant.
