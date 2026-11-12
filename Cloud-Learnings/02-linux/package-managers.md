← [Previous: Processes & Services](./processes-services.md) | [Home](../README.md) | [Next: Shell Scripting →](./shell-scripting.md)

---

# Linux Package Managers

## Overview

Package managers install, update, and remove software while handling dependencies automatically. The package manager you use depends on your Linux distribution.

| Distribution | Package manager | Package format | Config |
|-------------|----------------|---------------|--------|
| Ubuntu / Debian | `apt` (frontend), `dpkg` (backend) | `.deb` | `/etc/apt/` |
| Amazon Linux 2023 / RHEL 8+ | `dnf` | `.rpm` | `/etc/dnf/` |
| Amazon Linux 2 / CentOS 7 | `yum` | `.rpm` | `/etc/yum.conf` |
| Alpine Linux | `apk` | `.apk` | `/etc/apk/` |
| Arch Linux | `pacman` | `.pkg.tar.zst` | `/etc/pacman.conf` |

---

## apt — Debian / Ubuntu

`apt` is the high-level interface. `apt-get` is the older, more scriptable version used in automation. `dpkg` is the low-level backend.

### Essential apt Commands

```bash
# Update package index (always do this first)
sudo apt update

# Upgrade installed packages
sudo apt upgrade                          # upgrade packages (ask confirmation)
sudo apt upgrade -y                       # non-interactive
sudo apt full-upgrade                     # upgrade + remove obsolete packages
sudo apt dist-upgrade                     # like full-upgrade (older alias)

# Install packages
sudo apt install nginx
sudo apt install -y nginx curl git        # multiple packages, no confirmation
sudo apt install -y --no-install-recommends nginx   # skip recommended packages (useful in containers)

# Remove packages
sudo apt remove nginx                     # remove but keep config files
sudo apt purge nginx                      # remove including config files
sudo apt autoremove                       # remove unused dependency packages
sudo apt clean                            # remove downloaded .deb files from cache

# Search and info
apt search nginx
apt show nginx                            # detailed package information
apt list --installed                      # all installed packages
apt list --installed | grep nginx         # check if nginx is installed
apt list --upgradable                     # packages with available updates
dpkg -l nginx                             # dpkg view of package status

# Single-file queries
dpkg -L nginx                             # list files installed by a package
dpkg -S /usr/sbin/nginx                   # which package owns this file
dpkg --get-selections                     # all installed packages
```

### apt Sources

Package sources are defined in:
- `/etc/apt/sources.list` — main sources list
- `/etc/apt/sources.list.d/` — drop-in files (added by `add-apt-repository` or third-party tools)

```bash
# View current sources
cat /etc/apt/sources.list
ls /etc/apt/sources.list.d/

# Add a third-party repository (example: Docker)
# 1. Add GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 2. Add repository
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list

# 3. Update and install
sudo apt update
sudo apt install docker-ce
```

### Unattended Upgrades (Auto Security Patching)

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades   # configure interactively

# Config: /etc/apt/apt.conf.d/50unattended-upgrades
# Enabled by default on Ubuntu 20.04+ for security updates only
sudo systemctl status unattended-upgrades
cat /var/log/unattended-upgrades/unattended-upgrades.log
```

---

## dnf — Amazon Linux 2023 / RHEL 8+ / Fedora

`dnf` replaced `yum` as the default package manager in RHEL 8 and Amazon Linux 2023. It is mostly backward-compatible with `yum` commands.

### Essential dnf Commands

```bash
# Update package index and upgrade
sudo dnf check-update               # check for updates (non-interactive)
sudo dnf update                     # update all packages
sudo dnf update -y                  # non-interactive

# Install packages
sudo dnf install nginx
sudo dnf install -y nginx curl git
sudo dnf install -y --setopt=install_weak_deps=False nginx  # skip weak deps

# Remove packages
sudo dnf remove nginx
sudo dnf autoremove                  # remove unused dependencies
sudo dnf clean all                   # clean cache

# Search and info
dnf search nginx
dnf info nginx
dnf list installed
dnf list installed | grep nginx
dnf list available

# Querying files
rpm -ql nginx                        # files installed by nginx package
rpm -qf /usr/sbin/nginx              # which package owns this file
rpm -qa                              # all installed packages
rpm -qi nginx                        # package information
```

### dnf Groups

```bash
dnf group list                       # available package groups
sudo dnf group install "Development Tools"
sudo dnf group remove "Development Tools"
```

### dnf Repositories

```bash
dnf repolist                         # enabled repositories
dnf repolist all                     # all repositories (enabled and disabled)
sudo dnf config-manager --enable powertools   # enable a disabled repo

# Add EPEL (Extra Packages for Enterprise Linux)
sudo dnf install epel-release        # on RHEL/CentOS
sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm

# Amazon Linux Extras (Amazon Linux 2 only)
amazon-linux-extras list
sudo amazon-linux-extras install nginx1
```

---

## yum — Amazon Linux 2 / CentOS 7

`yum` is the predecessor to `dnf`. Commands are nearly identical:

```bash
sudo yum update -y
sudo yum install nginx -y
sudo yum remove nginx
sudo yum search nginx
sudo yum info nginx
yum list installed
rpm -qa | grep nginx
```

---

## apk — Alpine Linux

Alpine is common as a minimal Docker base image. Its package manager `apk` is fast and produces very small images.

```bash
# Update index and upgrade
apk update
apk upgrade

# Install
apk add nginx curl bash
apk add --no-cache nginx    # don't cache index/packages (recommended in Dockerfiles)

# Remove
apk del nginx

# Search
apk search nginx
apk info nginx
apk info -L nginx           # list files installed by package

# Query
apk info                    # all installed packages
```

**In Dockerfiles, always use `--no-cache`:**

```dockerfile
FROM alpine:3.19
RUN apk update && apk add --no-cache nginx curl && rm -rf /var/cache/apk/*
```

---

## Security Updates — Automation Patterns

### Ubuntu: Apply Only Security Updates

```bash
# List only security updates
sudo apt list --upgradable 2>/dev/null | grep -i security

# Apply only security updates (using unattended-upgrades manually)
sudo unattended-upgrade --dry-run     # preview
sudo unattended-upgrade               # apply

# Or via apt with pattern matching
sudo apt-get -y upgrade \
  --with-new-pkgs \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold"
```

### Amazon Linux / RHEL: Apply Security Updates

```bash
# List available security updates
sudo dnf updateinfo list security

# Apply only security updates
sudo dnf update --security -y

# Apply a specific advisory
sudo dnf update --advisory RHSA-2024:1234 -y
```

### Checking if a Reboot Is Needed

```bash
# Ubuntu/Debian
ls /var/run/reboot-required 2>/dev/null && echo "Reboot needed" || echo "No reboot needed"

# RHEL/Amazon Linux
sudo needs-restarting -r    # requires yum-utils / dnf-utils
```

---

## Installing Without a Package Manager

Sometimes a package isn't in the repository. Common approaches:

### Binary / Tarball

```bash
# Example: install a binary release
VERSION="1.2.3"
curl -LO "https://example.com/tool-${VERSION}-linux-amd64.tar.gz"
tar -xzf "tool-${VERSION}-linux-amd64.tar.gz"
sudo mv tool /usr/local/bin/
sudo chmod +x /usr/local/bin/tool
tool --version
```

### From Source

```bash
# Install build tools first
sudo apt install -y build-essential     # Ubuntu
sudo dnf install -y gcc make            # Amazon Linux

# Build and install
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install
```

### Snap (Ubuntu)

```bash
snap install code --classic       # VS Code
snap list
snap refresh code                 # update specific snap
snap remove code
```

---

## Cloud Engineering Patterns

### Idempotent Package Installation in User Data / Cloud-Init

```bash
#!/bin/bash
set -euo pipefail

# Ubuntu
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  --no-install-recommends \
  nginx \
  curl \
  jq \
  awscli

# Prevent interactive prompts on upgrade
export DEBIAN_FRONTEND=noninteractive
apt-get upgrade -y \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold"
```

### Pinning Package Versions (Reproducible Builds)

```bash
# apt — install specific version
apt-cache policy nginx              # show available versions
sudo apt install nginx=1.18.0-0ubuntu1.2

# dnf — install specific version
dnf list nginx --showduplicates
sudo dnf install nginx-1.20.1-1.el8.ngx

# Pin to prevent unintended upgrades
echo "nginx hold" | sudo dpkg --set-selections      # apt hold
sudo apt-mark hold nginx                             # apt mark (easier)
sudo apt-mark unhold nginx

# dnf exclude
echo "exclude=nginx" | sudo tee -a /etc/dnf/dnf.conf
```

---

## References

- [Ubuntu apt documentation](https://ubuntu.com/server/docs/package-management)
- [Amazon Linux 2023 package management](https://docs.aws.amazon.com/linux/al2023/ug/package-management.html)
- [dnf documentation](https://dnf.readthedocs.io/)
- [Alpine apk reference](https://wiki.alpinelinux.org/wiki/Alpine_Package_Keeper)
---

← [Previous: Processes & Services](./processes-services.md) | [Home](../README.md) | [Next: Shell Scripting →](./shell-scripting.md)
