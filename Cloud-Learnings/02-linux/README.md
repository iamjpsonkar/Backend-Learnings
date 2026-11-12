← [Previous: Cross-Cloud Comparison](../01-cloud-fundamentals/cross-cloud-comparison.md) | [Home](../README.md) | [Next: Filesystem →](./filesystem.md)

---

# Linux for Cloud Engineers

Linux is the dominant OS in cloud computing. Every EC2 instance, GCE VM, AKS node, and containerized workload you run will likely be Linux. This section covers what you need to operate, automate, and troubleshoot Linux systems in a cloud context.

## Topics

| File | Description |
|------|-------------|
| [filesystem.md](./filesystem.md) | FHS hierarchy, important directories, permissions, disk usage, mounts |
| [users-groups-permissions.md](./users-groups-permissions.md) | Users, groups, chmod, chown, sudo, sudoers, special permission bits |
| [processes-services.md](./processes-services.md) | Process management, systemd, journald, signals, job control |
| [package-managers.md](./package-managers.md) | apt/dpkg, yum/dnf, managing packages and security updates |
| [shell-scripting.md](./shell-scripting.md) | Bash scripting for cloud automation — variables, loops, functions, error handling |
| [ssh-scp-rsync.md](./ssh-scp-rsync.md) | SSH keys, config, jump hosts, tunnels, SCP, rsync, EC2 patterns |
| [cron-scheduling.md](./cron-scheduling.md) | Cron syntax, crontab, /etc/cron.d/, systemd timers, cloud alternatives |
| [troubleshooting.md](./troubleshooting.md) | Disk full, high CPU/memory, network issues, service failures, log analysis |

## Distributions You'll Encounter in Cloud

| Distro | Package manager | Init system | Common use |
|--------|----------------|------------|-----------|
| Ubuntu 22.04 / 24.04 LTS | apt | systemd | Default for most cloud workloads, containers |
| Amazon Linux 2023 | dnf | systemd | AWS-optimized, includes SSM agent pre-installed |
| Amazon Linux 2 | yum | systemd | Older AWS standard, still widely deployed |
| RHEL / CentOS Stream | dnf | systemd | Enterprise, regulated environments |
| Debian 12 | apt | systemd | Minimal, stable, common in containers |
| Alpine Linux | apk | OpenRC | Minimal container base image (~5MB) |

## Minimum Linux Competency for Cloud Work

You should be comfortable with:

- Navigating the filesystem and finding files (`ls`, `cd`, `find`, `locate`)
- Reading and editing files (`cat`, `less`, `vim`/`nano`, `grep`, `awk`, `sed`)
- Managing permissions and understanding who owns what
- Starting, stopping, and troubleshooting services (`systemctl`, `journalctl`)
- SSH into remote instances and managing keys
- Writing basic shell scripts for automation
- Diagnosing disk, CPU, and memory issues
- Reading package manager output and applying security updates
---

← [Previous: Cross-Cloud Comparison](../01-cloud-fundamentals/cross-cloud-comparison.md) | [Home](../README.md) | [Next: Filesystem →](./filesystem.md)
