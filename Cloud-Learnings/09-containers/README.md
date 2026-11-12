← [Previous: Cloudflare](../08-other-clouds/cloudflare.md) | [Home](../README.md) | [Next: Docker Basics →](./docker-basics.md)

---

# Containers

Containers package an application and its dependencies into a single, portable, reproducible unit that runs identically across environments.

---

## Core Concepts

| Concept | Description |
|---------|------------|
| **Image** | Read-only template — layers of filesystem changes built from a Dockerfile |
| **Container** | Running instance of an image — adds a writable layer on top |
| **Registry** | Repository for storing and distributing images (Docker Hub, ECR, Artifact Registry, ACR, GHCR) |
| **Volume** | Persistent storage mounted into a container — survives container restarts |
| **Network** | Virtual network connecting containers — bridge (default), host, overlay, none |
| **Dockerfile** | Instructions to build an image — each instruction creates a layer |
| **docker-compose** | Tool to define and run multi-container applications from a YAML file |

---

## Why Containers?

| Problem | Container Solution |
|---------|--------------------|
| "Works on my machine" | Image includes runtime + deps — identical everywhere |
| Dependency conflicts | Each container has its own isolated filesystem |
| Slow environment setup | `docker pull` or `docker run` — seconds not hours |
| Inconsistent deployments | Image digest is immutable — same bits every time |
| Resource waste | Containers share the host kernel — far lighter than VMs |

---

## Container vs VM

| Aspect | VM | Container |
|--------|-----|-----------|
| Isolation | Hardware-level (hypervisor) | OS-level (namespaces + cgroups) |
| Boot time | 30–120 seconds | Milliseconds |
| Size | GBs | MBs |
| OS | Full OS per VM | Shared host kernel |
| Security boundary | Strong | Weaker (kernel shared) — use rootless/gVisor for hardening |
| Density | 10–100 per host | 100–1000 per host |

---

## Section Index

| File | Content |
|------|---------|
| [docker-basics.md](docker-basics.md) | Images, containers, volumes, networks, runtime essentials |
| [dockerfile.md](dockerfile.md) | Writing efficient, secure, production-ready Dockerfiles |
| [docker-compose.md](docker-compose.md) | Multi-container local development and testing environments |
| [container-registries.md](container-registries.md) | Docker Hub, ECR, Artifact Registry, ACR, GHCR — push/pull/auth |

---

## Container Runtime Landscape

| Runtime | Description |
|---------|------------|
| **Docker** | Most widely used — daemon-based, full toolchain (CLI, build, compose) |
| **containerd** | Industry-standard runtime used by Kubernetes — Docker uses it internally |
| **Podman** | Daemonless, rootless — drop-in Docker replacement, better security |
| **nerdctl** | Docker-compatible CLI for containerd |
| **gVisor** | User-space kernel — stronger isolation for untrusted workloads |
| **Kata Containers** | VM-based containers — hardware isolation with container UX |

Kubernetes uses **containerd** (or CRI-O) directly — not the Docker daemon.
---

← [Previous: Cloudflare](../08-other-clouds/cloudflare.md) | [Home](../README.md) | [Next: Docker Basics →](./docker-basics.md)
