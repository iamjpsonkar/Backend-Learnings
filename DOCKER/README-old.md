# Docker: Concepts, History, Architecture, and Components

> A practical foundation for understanding Docker, how containers work,
> how Docker differs from virtual machines, and the parts that make up
> the Docker ecosystem.

## 1. What is Docker?

**Docker is a platform and set of tools for building, packaging,
distributing, and running applications in containers.**

A container packages an application together with the files, libraries,
runtime, and configuration it needs. It runs as an isolated process on a
host operating system while sharing the host's kernel.

The key idea is **build once, run consistently**: the same image can be
used on a developer's laptop, a test environment, or a production
server, provided the target system supports the image's operating system
and CPU architecture.

### Why Docker exists

Without containerization, an application may work on one machine but
fail on another because of differences in:

-   Programming-language or runtime versions
-   System libraries and dependencies
-   Operating-system packages
-   Environment variables and configuration
-   Filesystem layout and startup commands

Docker helps make these dependencies explicit and reproducible. It also
makes it easier to start, stop, replace, scale, and distribute
application instances.

### Docker is not a virtual machine

Docker containers are not miniature virtual machines. A typical Linux
container is an isolated group of processes that shares the host's Linux
kernel. A virtual machine runs a guest operating system on virtualized
hardware.

Docker is also more than the `docker` command. The ecosystem includes
image formats, a build system, a client, an API, a daemon or other
runtime components, registries, and integrations with lower-level
container runtimes.

## 2. A short history of Docker and containers

Containerization did not begin with Docker. Docker made an existing set
of operating-system isolation ideas easier for application developers to
use and distribute.

  ------------------------------------------------------------------------
  Period                  Development             Why it matters
  ----------------------- ----------------------- ------------------------
  1979                    Unix `chroot` was       It changed a process's
                          introduced in Version 7 apparent root directory,
                          Unix                    providing an early form
                                                  of filesystem isolation.

  2000                    FreeBSD Jails           Extended isolation to
                                                  processes, filesystems,
                                                  users, and networking.

  2001                    Linux VServer           Provided
                                                  operating-system-level
                                                  virtualization for
                                                  Linux.

  2004                    Solaris Containers      Combined resource
                                                  controls and zones for
                                                  isolated environments.

  2006--2008              Process containers,     Enabled accounting for
                          later cgroups,          and limiting groups of
                          developed in the Linux  processes' resource
                          kernel                  usage.

  2008                    Linux Containers (LXC)  Combined Linux kernel
                                                  features to create
                                                  system containers.

  2013                    Docker was publicly     Made container-based
                          introduced by dotCloud  application packaging
                                                  and workflows accessible
                                                  to a much wider
                                                  developer audience.

  2013 onward             Docker images,          Encouraged portable
                          registries, and         application packaging
                          developer tooling       and image sharing.
                          gained adoption         

  2015                    Open Container          Began standardizing
                          Initiative (OCI) was    container image formats
                          launched                and runtime behavior
                                                  across implementations.

  2016 onward             Container               Made it practical to
                          orchestration,          manage containerized
                          including Kubernetes,   applications across
                          became widely adopted   clusters of machines.
  ------------------------------------------------------------------------

### Important historical distinction

Docker did not invent containers, namespaces, or cgroups. Its major
contribution was to make container workflows approachable: package an
application into an image, share that image, and run it in a predictable
environment.

For historical details and current terminology, see the references at
the end.

## 3. How Docker works: the mental model

Think of Docker as a pipeline:

1.  **Describe** the environment and startup instructions in a
    `Dockerfile`.
2.  **Build** the `Dockerfile` into an image.
3.  **Store or share** the image locally or in a registry.
4.  **Create and start** a container from the image.
5.  **Connect** the container to networks and attach persistent storage
    when required.
6.  **Observe and manage** the running container through Docker tools
    and APIs.

``` text
                 Dockerfile
                     |
                     | docker build
                     v
                Docker Image
                     |
          +----------+----------+
          |                     |
          | docker run          | push / pull
          v                     v
      Container             Registry
          ^                     |
          |                     | pull
          +---------------------+
```

An image is the packaged template. A container is a runnable instance
created from that template. One image can be used to create many
containers.

## 4. How a Linux container works under the hood

Containers are enabled primarily by Linux kernel features. Docker
provides the user-facing workflow and coordinates the components that
use those features.

### 4.1 Namespaces: isolation

Linux namespaces give processes different views of selected system
resources. A container can therefore see its own process list, network
interfaces, hostname, and mount layout rather than the host's full view.

Common namespace types include:

  -----------------------------------------------------------------------
  Namespace                           What it isolates
  ----------------------------------- -----------------------------------
  PID                                 Process ID view. A process in a PID
                                      namespace can see its own process
                                      tree.

  Network                             Network devices, routes, IP
                                      addresses, ports, and
                                      network-related state.

  Mount                               Filesystem mount points and mount
                                      layout.

  UTS                                 Hostname and domain name.

  IPC                                 Inter-process communication
                                      resources.

  User                                User and group ID mappings,
                                      allowing a process to be root
                                      inside a user namespace without
                                      necessarily being host root.

  Cgroup                              A view of control-group hierarchy,
                                      where supported by the kernel.
  -----------------------------------------------------------------------

Namespaces provide separation of views; they do not by themselves impose
CPU or memory limits.

### 4.2 cgroups: resource accounting and limits

**Control groups (cgroups)** let the kernel organize processes and
account for or limit resources.

Depending on the host configuration and cgroup version, controls can
include:

-   CPU time and CPU shares/weights
-   Memory usage and memory limits
-   Process counts
-   Block I/O usage and throttling

For example, a container can be configured with a memory limit so that
it cannot consume unlimited host memory. Exact behavior when a limit is
reached depends on the resource and kernel configuration.

### 4.3 Filesystem layers: image and container storage

Container images are generally composed of read-only filesystem layers.
When a container is created, the container runtime adds a writable layer
on top.

``` text
        Container filesystem view
       +---------------------------+
       | Writable container layer  |  <- changes made while running
       +---------------------------+
       | Image layer 3             |
       +---------------------------+
       | Image layer 2             |  <- read-only image layers
       +---------------------------+
       | Image layer 1             |
       +---------------------------+
       | Base image layer          |
       +---------------------------+
```

Layers can be reused across images when they are identical, which can
reduce storage and transfer costs. The exact storage driver and
implementation depend on the Docker installation.

**Important:** Data written only to a container's writable layer is tied
to that container's lifecycle. Removing the container normally removes
that writable layer. Use volumes or bind mounts for data that must
persist.

### 4.4 Union filesystems and copy-on-write

Layered filesystems present multiple layers as one filesystem view. With
copy-on-write behavior, a file from a lower read-only layer can be
copied into the writable layer when modified. The container then sees
the modified version while the image remains unchanged.

The implementation is storage-driver and platform dependent; do not
assume every Docker environment uses the same filesystem driver.

### 4.5 Container isolation is not a separate kernel

On a Linux host, containers share the host kernel. They are isolated
processes, not separate operating-system installations.

This is efficient, but it also means the kernel is part of the shared
security boundary. Containers should not automatically be treated as
equivalent to a strongly isolated VM. Use least privilege, avoid
unnecessary capabilities, keep hosts patched, and apply appropriate
security controls.

## 5. Docker architecture and components

A common Docker Engine setup uses a client-server architecture.

``` text
      Developer / CI pipeline
                |
                | docker CLI commands
                v
          Docker Client
                |
                | Docker Engine API
                v
          Docker Daemon (dockerd)
             /      |       \
            /       |        \
       Images    Containers   Networks / Volumes
            \       |        /
             \      |       /
              containerd
                  |
               runc
                  |
          Linux kernel features
       (namespaces, cgroups, etc.)

        Docker Registry
          ^         |
          | push    | pull
          +---------+
```

The exact internal arrangement varies by Docker version, operating
system, and installation. The diagram represents a common high-level
flow, not every implementation detail.

### 5.1 Docker Client (`docker` CLI)

The Docker client is the command-line interface most developers use.

Examples:

``` bash
docker build -t my-app:1.0 .
docker run --name my-app my-app:1.0
docker ps
docker logs my-app
docker stop my-app
```

The CLI sends requests to the Docker Engine API. The client and daemon
may run on the same machine or communicate remotely.

### 5.2 Docker Daemon (`dockerd`)

The Docker daemon is a background service responsible for managing
Docker objects and coordinating operations such as:

-   Building and managing images
-   Creating and managing containers
-   Managing networks and volumes
-   Communicating with registries
-   Exposing the Docker Engine API

On many Linux installations, `dockerd` runs as a system service. Docker
Desktop uses a different host integration architecture on macOS and
Windows.

### 5.3 Docker Engine API

The Engine API is the interface through which clients and other tools
request Docker operations. The CLI is one client; other programs can use
the API through supported libraries or HTTP endpoints.

Access to the Docker daemon is highly privileged. On many Linux systems,
membership in the `docker` group effectively grants root-level
capabilities. Protect the daemon socket and remote API.

### 5.4 containerd

`containerd` is a container runtime component responsible for core
container lifecycle operations, including image transfer and storage,
container execution management, and supervision of running containers.

Docker Engine commonly uses containerd rather than implementing every
low-level lifecycle function directly in `dockerd`.

### 5.5 runc

`runc` is a low-level OCI runtime. It creates and runs containers
according to an OCI runtime specification, using operating-system
facilities such as namespaces and cgroups.

A simplified relationship is:

-   Docker CLI: accepts user commands.
-   `dockerd`: manages Docker Engine objects and API requests.
-   `containerd`: manages container lifecycle tasks.
-   `runc`: performs low-level container creation and execution.

### 5.6 Docker Images

An image is a read-only, layered template used to create containers. It
includes application files, dependencies, metadata, and configuration
such as the default command.

Images are commonly identified by repository and tag, for example:

``` text
nginx:1.27
python:3.12-slim
my-company/payment-api:1.4.2
```

A tag is a movable name, not a guarantee of immutable content. For
repeatable deployments, consider pinning images by digest.

### 5.7 Docker Containers

A container is an instance of an image with its own runtime
configuration and writable layer.

A container can be:

-   Created
-   Started
-   Paused
-   Stopped
-   Restarted
-   Removed

A stopped container still exists until it is removed. A container is not
the same thing as an image.

### 5.8 Dockerfile

A `Dockerfile` is a text file containing instructions for building an
image.

Example:

``` dockerfile
# Choose a base image
FROM python:3.12-slim

# Set the working directory inside the image
WORKDIR /app

# Copy dependency definitions first to improve build caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Document the port the application listens on
EXPOSE 8000

# Default process when a container starts
CMD ["python", "app.py"]
```

Common instructions:

  -----------------------------------------------------------------------
  Instruction                         Purpose
  ----------------------------------- -----------------------------------
  `FROM`                              Selects a base image and begins a
                                      build stage.

  `WORKDIR`                           Sets the working directory for
                                      later instructions.

  `COPY`                              Copies files from the build context
                                      into the image.

  `ADD`                               Copies files and supports
                                      additional source handling; prefer
                                      `COPY` for ordinary file copying.

  `RUN`                               Executes a command during image
                                      build.

  `ENV`                               Sets environment variables in the
                                      image.

  `ARG`                               Defines build-time variables.

  `EXPOSE`                            Documents a port the application is
                                      expected to listen on; it does not
                                      publish the port.

  `USER`                              Sets the user for subsequent build
                                      steps and the default runtime user.

  `ENTRYPOINT`                        Defines the main executable for the
                                      container.

  `CMD`                               Supplies default command or
                                      arguments; interaction with
                                      `ENTRYPOINT` depends on the form
                                      used.

  `VOLUME`                            Declares a mount point intended for
                                      persistent or externally managed
                                      data.
  -----------------------------------------------------------------------

### 5.9 Docker Registry

A registry stores and distributes images. Developers and CI systems can
push images to a registry and servers can pull them.

Examples include Docker Hub and private registries provided by cloud
platforms or organizations.

Typical workflow:

``` bash
# Authenticate (if required)
docker login

# Tag a local image for a registry
docker tag my-app:1.0 username/my-app:1.0

# Upload the image
docker push username/my-app:1.0

# Download an image
docker pull username/my-app:1.0
```

### 5.10 Docker Volumes and Bind Mounts

Containers are replaceable. Persistent data should live outside the
container's writable layer.

**Volume:** Managed by Docker and stored in Docker-managed storage.

``` bash
docker volume create app-data

docker run -d \
  --name database \
  -v app-data:/var/lib/postgresql/data \
  postgres
```

**Bind mount:** Maps a specific host path into the container.

``` bash
docker run --rm \
  -v "$PWD:/app" \
  -w /app \
  python:3.12-slim \
  python app.py
```

Use volumes for Docker-managed persistent data. Bind mounts are useful
for development workflows and when a container must access a specific
host directory. Be mindful of permissions and host-path access.

### 5.11 Docker Networking

Docker networks allow containers to communicate with one another and
with external systems.

Common network drivers include:

-   **bridge:** Common default for containers on a single Docker host.
-   **host:** Shares the host network namespace on supported Linux
    setups.
-   **none:** Disables normal container networking.
-   **overlay:** Connects containers across multiple Docker hosts in
    supported swarm configurations.

Example:

``` bash
docker network create app-network

docker run -d \
  --name redis \
  --network app-network \
  redis

docker run --rm \
  --name api \
  --network app-network \
  my-api:1.0
```

Containers on a user-defined bridge network can generally reach each
other by container name. Publishing a port with `-p` makes a container
port reachable through a host port:

``` bash
docker run -d -p 8080:80 nginx
```

This maps host port `8080` to container port `80`.

### 5.12 Docker Compose

Docker Compose is a tool for defining and running multi-container
applications using a YAML file.

For example, an application may consist of:

-   API service
-   Database
-   Redis cache
-   Background worker

A simplified `compose.yaml`:

``` yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://app:secret@db:5432/app
    depends_on:
      - db
      - redis

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: app
    volumes:
      - postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7

volumes:
  postgres-data:
```

Start the application:

``` bash
docker compose up -d
```

Stop and remove its containers and network:

``` bash
docker compose down
```

The named volume remains unless explicitly removed (for example, with
`docker compose down -v`). The example is for learning; do not commit
real production passwords to source control. Use secrets or a secure
configuration mechanism.

## 6. Docker containers vs Virtual Machines

Both containers and virtual machines provide isolation, but they do it
at different layers.

### 6.1 Architecture comparison

**Virtual machine architecture**

``` text
+----------------------+  +----------------------+
| Application          |  | Application          |
| Libraries / Runtime  |  | Libraries / Runtime  |
| Guest OS             |  | Guest OS             |
+----------------------+  +----------------------+
|          Hypervisor                         |
+---------------------------------------------+
|          Host OS / Hardware                 |
+---------------------------------------------+
```

Each VM typically includes its own guest operating system and kernel.

**Container architecture**

``` text
+----------------------+  +----------------------+
| Application          |  | Application          |
| Libraries / Runtime  |  | Libraries / Runtime  |
| Container isolation  |  | Container isolation  |
+----------------------+  +----------------------+
|       Shared Host Operating-System Kernel   |
+---------------------------------------------+
|                 Hardware                    |
+---------------------------------------------+
```

Containers isolate processes while sharing the host kernel. On macOS and
Windows, Docker Desktop typically runs Linux containers inside a
lightweight Linux virtual machine because the host operating system does
not provide a Linux kernel directly.

### 6.2 Side-by-side comparison

  ------------------------------------------------------------------------
  Feature                 Containers               Virtual Machines
  ----------------------- ------------------------ -----------------------
  Virtualization layer    Operating-system-level   Hardware virtualization
                          isolation                

  Kernel                  Shares the host kernel   Each VM has its own
                          (for Linux containers)   guest kernel

  Operating system        Packages application     Includes a full guest
                          dependencies, not a      OS
                          separate full guest OS   

  Startup                 Usually fast; often      Usually slower because
                          seconds or less,         a guest OS boots
                          depending on workload    

  Resource overhead       Generally lower          Generally higher due to
                                                   guest OS overhead

  Density                 Often more workloads per Usually fewer workloads
                          host                     per host at comparable
                                                   resource budgets

  Isolation boundary      Process and kernel       Separate guest kernel
                          isolation; depends on    and virtual hardware
                          configuration            boundary

  Portability             Image can run where      VM image depends on
                          compatible container     hypervisor and virtual
                          runtime and              hardware compatibility
                          kernel/architecture      
                          support exist            

  Best suited for         Microservices, CI jobs,  Different OS kernels,
                          application packaging,   strong workload
                          scalable services        separation, legacy OS
                                                   environments

  Typical tools           Docker, containerd,      KVM, Hyper-V, VMware,
                          Kubernetes               VirtualBox
  ------------------------------------------------------------------------

### 6.3 Which should you choose?

Choose **containers** when you want:

-   Consistent application packaging across environments
-   Fast startup and efficient resource usage
-   Many independently deployable services
-   Reproducible development and CI/CD environments

Choose **virtual machines** when you need:

-   A different guest operating system or kernel
-   A separate OS environment
-   A VM-level isolation boundary for a workload
-   To run legacy systems that need a full operating system

They are not mutually exclusive. A common production setup runs
containers inside virtual machines, combining VM-level infrastructure
isolation with container-level application packaging.

### 6.4 A crucial platform nuance

A Linux container needs a compatible Linux kernel. Docker Desktop on
macOS and Windows supplies a Linux environment using virtualization.
Therefore, saying "containers never use VMs" is incorrect: Linux
containers share a kernel, but that kernel may run inside a VM on a
non-Linux host.

## 7. Essential Docker commands

  -----------------------------------------------------------------------
  Command                             What it does
  ----------------------------------- -----------------------------------
  `docker version`                    Shows client and server versions.

  `docker info`                       Shows Docker Engine configuration
                                      and system information.

  `docker pull IMAGE`                 Downloads an image.

  `docker images`                     Lists local images.

  `docker build -t NAME:TAG .`        Builds an image from a build
                                      context.

  `docker run IMAGE`                  Creates and starts a container.

  `docker ps`                         Lists running containers.

  `docker ps -a`                      Lists all containers, including
                                      stopped ones.

  `docker logs CONTAINER`             Displays container logs.

  `docker exec -it CONTAINER sh`      Opens a shell in a running
                                      container, if available.

  `docker inspect CONTAINER`          Displays detailed object
                                      configuration.

  `docker stop CONTAINER`             Stops a running container.

  `docker rm CONTAINER`               Removes a container.

  `docker rmi IMAGE`                  Removes an image.

  `docker volume ls`                  Lists volumes.

  `docker network ls`                 Lists networks.

  `docker compose up -d`              Starts a Compose application in the
                                      background.

  `docker compose down`               Stops and removes Compose-managed
                                      containers and network.
  -----------------------------------------------------------------------

## 8. Important concepts to understand next

After understanding the fundamentals, study these topics in roughly this
order:

1.  **Image layers and build cache** --- how Docker builds images
    efficiently.
2.  **Dockerfile best practices** --- small images, multi-stage builds,
    non-root users, and reproducible builds.
3.  **Container lifecycle** --- create, start, stop, restart, inspect,
    and remove.
4.  **Networking** --- bridge networks, DNS, port publishing, and
    service discovery.
5.  **Storage** --- writable layers, volumes, bind mounts, and backup
    strategy.
6.  **Compose** --- running an API, database, cache, and worker
    together.
7.  **Security** --- least privilege, capabilities, secrets, image
    scanning, and daemon access.
8.  **Resource constraints** --- CPU, memory, process, and I/O limits.
9.  **Registries** --- tags, digests, authentication, and image
    distribution.
10. **Orchestration** --- Kubernetes or Docker Swarm for managing
    workloads across multiple machines.

## 9. Common misconceptions

-   **"A container is a lightweight VM."** Not exactly. A Linux
    container is an isolated process environment sharing the host
    kernel.
-   **"An image and a container are the same."** An image is a template;
    a container is an instance created from it.
-   **"`EXPOSE` publishes a port."** It documents a port. Use `-p` or
    Compose `ports` to publish a host port.
-   **"Container data is automatically persistent."** Data in the
    writable layer is normally removed with the container. Use volumes
    or bind mounts for persistence.
-   **"Docker guarantees identical behavior everywhere."** It improves
    consistency, but CPU architecture, kernel features, host
    configuration, external services, and environment-specific settings
    still matter.
-   **"Containers are automatically secure."** Security depends on image
    provenance, privileges, kernel configuration, daemon access, and
    runtime controls.
-   **"Docker and Kubernetes are alternatives."** Docker is a container
    platform/tooling ecosystem; Kubernetes is a container orchestration
    system. They address different layers of the problem.

## 10. References and further reading

Prefer official documentation for commands and implementation details
because Docker's architecture and defaults can evolve.

-   [Docker documentation](https://docs.docker.com/) --- official guides
    and reference.
-   [Docker Engine overview](https://docs.docker.com/engine/) --- Docker
    Engine concepts and architecture.
-   [Docker Engine API](https://docs.docker.com/reference/api/engine/)
    --- API reference.
-   [Dockerfile
    reference](https://docs.docker.com/reference/dockerfile/) --- build
    instructions.
-   [Docker Compose documentation](https://docs.docker.com/compose/) ---
    multi-container applications.
-   [Docker storage
    documentation](https://docs.docker.com/engine/storage/) --- volumes
    and storage drivers.
-   [Docker networking
    documentation](https://docs.docker.com/engine/network/) --- network
    drivers and configuration.
-   [Linux kernel
    namespaces](https://man7.org/linux/man-pages/man7/namespaces.7.html)
    --- namespace behavior.
-   [Linux control
    groups](https://docs.kernel.org/admin-guide/cgroup-v2.html) ---
    cgroup v2 documentation.
-   [Open Container Initiative](https://opencontainers.org/) --- open
    container standards.
-   [OCI Runtime
    Specification](https://github.com/opencontainers/runtime-spec) ---
    runtime configuration and lifecycle specification.
-   [containerd documentation](https://containerd.io/) --- container
    runtime project.
-   [runc](https://github.com/opencontainers/runc) --- OCI runtime
    implementation.
-   [A Brief History of
    Containers](https://www.docker.com/blog/a-brief-history-of-containers/)
    --- Docker's historical overview.

------------------------------------------------------------------------

## Quick recap

-   Docker helps build, package, distribute, and run applications in
    containers.
-   Containers isolate processes using operating-system features such as
    namespaces and cgroups.
-   Linux containers share the host kernel; VMs run separate guest
    operating systems.
-   Images are layered templates; containers are running or stopped
    instances of images.
-   The main Docker ecosystem components include the CLI, daemon, Engine
    API, containerd, runc, images, registries, networks, volumes, and
    Compose.
-   Containers and VMs are complementary and are often used together.


# Docker Installation and Setup

Docker installation differs by operating system:

- **Linux:** You can install Docker Engine directly. On Ubuntu Server, this is usually the simplest option.
- **macOS:** Install Docker Desktop. It runs Linux containers inside a lightweight Linux virtual machine.
- **Windows:** Install Docker Desktop, normally using the WSL 2 backend for Linux containers.

> **Important:** Docker Engine and Docker Desktop are related but different installation choices. Docker Engine is the core container platform. Docker Desktop bundles the engine with a desktop application and supporting tools. Follow the official documentation for your OS because supported versions and installer details change over time.

## Before installing: check your system

### Linux

```bash
uname -m
cat /etc/os-release
```

`uname -m` reports the CPU architecture. Common values include `x86_64` (64-bit Intel/AMD) and `aarch64` (64-bit ARM).

### macOS

```bash
uname -m
sw_vers
```

- `arm64` generally means Apple silicon.
- `x86_64` means Intel.

### Windows

Open PowerShell:

```powershell
systeminfo
wsl --status
```

For Docker Desktop with the WSL 2 backend, use a supported Windows version and ensure hardware virtualization is enabled in firmware/BIOS. Follow Microsoft's WSL installation guidance if WSL is not installed.

---

## Install Docker Engine on Ubuntu

This is the recommended route for Ubuntu servers and Ubuntu systems where you want Docker Engine without the Docker Desktop graphical application.

### Step 1: Remove conflicting packages (if installed)

Docker's official packages can conflict with distribution-provided or older packages.

```bash
sudo apt remove docker.io docker-doc docker-compose docker-compose-v2 \
  podman-docker containerd runc
```

If some packages are not installed, `apt` may simply report that they could not be found.

### Step 2: Update package information and install prerequisites

```bash
sudo apt update
sudo apt install ca-certificates curl
```

### Step 3: Add Docker's official GPG key

```bash
sudo install -m 0755 -d /etc/apt/keyrings

sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc

sudo chmod a+r /etc/apt/keyrings/docker.asc
```

### Step 4: Add Docker's official APT repository

```bash
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

Update package information:

```bash
sudo apt update
```

### Step 5: Install Docker Engine and useful plugins

```bash
sudo apt install docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
```

These packages provide:

| Package | Purpose |
|---|---|
| `docker-ce` | Docker Engine daemon. |
| `docker-ce-cli` | Docker command-line client. |
| `containerd.io` | Container runtime component used by Docker Engine. |
| `docker-buildx-plugin` | Extended image-building functionality. |
| `docker-compose-plugin` | Docker Compose V2 (`docker compose`). |

### Step 6: Start and enable Docker

```bash
sudo systemctl enable --now docker
```

Check the service:

```bash
sudo systemctl status docker
```

### Step 7: Verify the installation

```bash
sudo docker version
sudo docker info
sudo docker run hello-world
```

The `hello-world` image is downloaded if needed, started as a container, prints a success message, and exits.

### Step 8: Run Docker without `sudo` (optional)

On many Linux installations, Docker's Unix socket is accessible to members of the `docker` group.

```bash
sudo groupadd docker
sudo usermod -aG docker "$USER"
```

Log out and log back in so the new group membership is applied. Then test:

```bash
docker run hello-world
```

If the `docker` group already exists, `groupadd` may report that; that is harmless. You can also run:

```bash
newgrp docker
```

**Security warning:** Membership in the `docker` group grants highly privileged access and can effectively provide root-level control of the host. Do not add untrusted users to this group. On shared or production systems, consider using `sudo docker ...` or a properly configured rootless Docker setup instead.

### Optional: install Docker Desktop on Ubuntu

Docker Desktop for Linux is a separate option for users who want a graphical interface. It runs a VM and has additional requirements, including KVM support. It is not necessary for a headless Ubuntu server.

Official instructions: [Install Docker Desktop on Ubuntu](https://docs.docker.com/desktop/setup/install/linux/ubuntu/).

---

## Install Docker on macOS

On macOS, the usual supported approach is **Docker Desktop**. Linux containers need a Linux kernel, so Docker Desktop runs them in a lightweight Linux VM.

### Step 1: Check your Mac architecture

Open Terminal:

```bash
uname -m
```

- `arm64`: Apple silicon (M-series).
- `x86_64`: Intel Mac.

Download the matching installer from:

[Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/)

### Step 2: Install Docker Desktop

1. Download the Docker Desktop `.dmg` for your processor.
2. Open the downloaded `.dmg` file.
3. Drag Docker into the Applications folder.
4. Open Docker from Applications.
5. Review and accept the Docker terms when prompted.
6. Complete any requested setup or permission steps.

### Step 3: Wait for Docker to start

The Docker menu-bar icon indicates Docker Desktop's status. Wait until Docker reports that its engine is running.

### Step 4: Verify from Terminal

```bash
docker --version
docker compose version
docker version
docker run hello-world
```

`docker version` should show both Client and Server information when the engine is available.

### Optional: install Rosetta 2 on Apple silicon

Rosetta 2 is not generally required for Docker Desktop itself, but some optional Intel-based command-line tools may need it.

```bash
softwareupdate --install-rosetta
```

### macOS notes

- Docker Desktop must be running before normal Docker CLI commands can communicate with its engine.
- Docker Desktop manages the Linux VM; you generally do not need to create or manage that VM yourself.
- File sharing and filesystem performance can differ from native Linux.
- Docker Desktop licensing depends on the type and scale of use. Check the current Docker subscription terms.

---

## Install Docker on Windows

For most developers who want to run Linux containers, the recommended setup is **Docker Desktop with the WSL 2 backend**.

### Step 1: Check Windows and virtualization support

Open PowerShell:

```powershell
winver
wsl --status
```

Make sure hardware virtualization is enabled in UEFI/BIOS. Docker Desktop has specific Windows edition, version, memory, and WSL requirements; check the current requirements before installation.

### Step 2: Install or update WSL

Open PowerShell as Administrator:

```powershell
wsl --install
```

Restart Windows if requested.

To update WSL:

```powershell
wsl --update
```

Check installed distributions:

```powershell
wsl --list --verbose
```

If a Linux distribution is using WSL 1 and you want it to use WSL 2:

```powershell
wsl --set-version Ubuntu 2
```

Replace `Ubuntu` with the exact distribution name shown by `wsl --list --verbose`.

### Step 3: Download Docker Desktop

Use the official page:

[Install Docker Desktop on Windows](https://docs.docker.com/desktop/setup/install/windows-install/)

Download the installer and run `Docker Desktop Installer.exe`.

### Step 4: Install Docker Desktop

1. Run the installer.
2. Select the WSL 2 backend when offered, unless you have a specific reason to use another supported backend.
3. Complete the installation.
4. Restart or sign out if the installer asks you to.
5. Start Docker Desktop.

### Step 5: Configure WSL integration

In Docker Desktop:

1. Open **Settings**.
2. Go to **Resources → WSL Integration** (the exact menu can vary by version).
3. Enable integration for the Linux distribution you use.
4. Apply the changes and restart Docker Desktop if prompted.

### Step 6: Verify from PowerShell or the integrated WSL terminal

```powershell
docker --version
docker compose version
docker version
docker run hello-world
```

If Docker works in PowerShell but not inside a WSL distribution, check that WSL integration is enabled for that distribution.

### Windows notes

- Docker Desktop normally uses WSL 2 for Linux containers.
- Windows containers are a different mode and have additional Windows edition and configuration requirements.
- Avoid installing a second, conflicting Docker Engine inside WSL when using Docker Desktop's WSL integration unless you intentionally want to maintain a separate engine.
- Docker Desktop licensing depends on the type and scale of use. Check the current Docker subscription terms.

---

## First verification checklist (all platforms)

Run these commands after installation:

```bash
# Docker CLI version
docker --version

# Client and server details
docker version

# Engine configuration
docker info

# Compose plugin version
docker compose version

# Download and run a test container
docker run hello-world

# List running containers
docker ps

# List all containers, including exited ones
docker ps -a

# List downloaded images
docker images
```

Expected result: `docker run hello-world` prints a message confirming that Docker was able to download an image and run a container.

If `docker version` shows only Client information and reports a server connection error, the Docker Engine may not be running or the CLI may be using the wrong Docker context.

---

## Run your first practical container

Start an NGINX web server:

```bash
docker run -d \
  --name my-nginx \
  -p 8080:80 \
  nginx
```

What the options mean:

| Option | Meaning |
|---|---|
| `-d` | Run in the background (detached mode). |
| `--name my-nginx` | Give the container a memorable name. |
| `-p 8080:80` | Map host port 8080 to container port 80. |
| `nginx` | Image to run; Docker downloads it if needed. |

Open this address in a browser:

```text
http://localhost:8080
```

Useful follow-up commands:

```bash
# Check the container
docker ps

# View its logs
docker logs my-nginx

# Open a shell inside it (if the image provides one)
docker exec -it my-nginx sh

# Stop it
docker stop my-nginx

# Remove the stopped container
docker rm my-nginx
```

The NGINX image remains on your machine after the container is removed. Remove the image separately if you no longer need it:

```bash
docker rmi nginx
```

---

## Common installation problems

| Problem | Possible reason | What to check |
|---|---|---|
| `docker: command not found` | CLI is not installed or not on `PATH`. | Recheck installation and terminal `PATH`; reopen the terminal. |
| Cannot connect to the Docker daemon | Engine is stopped or CLI targets the wrong context. | On Linux, run `sudo systemctl status docker`; on Desktop, start Docker Desktop. |
| Permission denied on `/var/run/docker.sock` | Current Linux user lacks socket permission. | Use `sudo` or review the security implications of Docker group membership. |
| WSL 2 integration not working | WSL is outdated or the distribution is not enabled in Desktop. | Run `wsl --update`, check `wsl --list --verbose`, and review Desktop integration settings. |
| Virtualization error | Hardware virtualization is disabled or unavailable. | Check UEFI/BIOS virtualization settings and platform requirements. |
| Port already allocated | Another process is listening on the host port. | Choose another host port, such as `-p 8081:80`. |
| Image pull fails | Network, DNS, proxy, registry authentication, or rate-limit issue. | Check connectivity, proxy configuration, registry login, and the error details. |
| Container exits immediately | Its main process completed or failed. | Run `docker ps -a` and inspect `docker logs CONTAINER`. |

---

## Installation choice summary

| Operating system | Recommended starting point | Where containers run |
|---|---|---|
| Ubuntu Server | Docker Engine from Docker's APT repository | Host Linux kernel |
| Ubuntu Desktop | Docker Engine for a lightweight native setup, or Docker Desktop for a GUI | Host kernel with Engine; Docker Desktop uses a VM |
| macOS | Docker Desktop | Linux VM |
| Windows | Docker Desktop with WSL 2 backend | Linux environment managed through WSL 2 |

## Official installation references

Always consult the official instructions for current requirements and installation changes:

- [Install Docker Engine](https://docs.docker.com/engine/install/)
- [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Install Docker Desktop on macOS](https://docs.docker.com/desktop/setup/install/mac-install/)
- [Install Docker Desktop on Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
- [Install Docker Desktop on Ubuntu](https://docs.docker.com/desktop/setup/install/linux/ubuntu/)
- [Docker post-installation steps for Linux](https://docs.docker.com/engine/install/linux-postinstall/)
- [Microsoft: Install WSL](https://learn.microsoft.com/windows/wsl/install)
- [Docker Desktop system requirements](https://docs.docker.com/desktop/setup/install/)


# Docker Commands

## Docker version check
```sh
docker --version
```
```txt
Docker version 29.9.2-2, build a82e528901260c8df6073311379eac65f92db204
```

## Docker Hello-World
```sh
docker run hello-world
```
```txt
Unable to find image 'hello-world:latest' locally
latest: Pulling from library/hello-world
4f55086f7dd0: Pull complete 
d5e71e642bf5: Download complete 
Digest: sha256:c567b231f65614688711a75f31518a064258a51d442117a3e771a3a8fdba78ef
Status: Downloaded newer image for hello-world:latest

Hello from Docker!
This message shows that your installation appears to be working correctly.

To generate this message, Docker took the following steps:
 1. The Docker client contacted the Docker daemon.
 2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
    (amd64)
 3. The Docker daemon created a new container from that image which runs the
    executable that produces the output you are currently reading.
 4. The Docker daemon streamed that output to the Docker client, which sent it
    to your terminal.

To try something more ambitious, you can run an Ubuntu container with:
 $ docker run -it ubuntu bash

Share images, automate workflows, and more with a free Docker ID:
 https://hub.docker.com/

For more examples and ideas, visit:
 https://docs.docker.com/get-started/
```

## Docker running container/all container
```sh
docker ps
```
```txt
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```
```sh
docker ps -a
```
```txt
CONTAINER ID   IMAGE         COMMAND    CREATED         STATUS                     PORTS     NAMES
7d0ab51aa472   hello-world   "/hello"   4 minutes ago   Exited (0) 4 minutes ago             wonderful_rubin
```

## Docker Pulled Images
```sh
docker images
```
```txt
          i Info →   U  In Use
IMAGE                ID             DISK USAGE   CONTENT SIZE   EXTRA
hello-world:latest   c567b231f656       25.9kB         9.49kB    U   
```

## Docker remove images
```sh
docker rmi c567b231f656
```

## Docker remove container
```sh
docker rm 7d0ab51aa472
```

## Docker running a command
```sh
docker exec 7d0ab51aa472 ls
```

## Docker container pause
```sh
docker pause 7d0ab51aa472
```
## Docker start 
```sh
docker start 7d0ab51aa472
```

## Docker stop
```sh
docker stop 7d0ab51aa472
```

## Docker cp
```sh
docker cp source container-name:destination
```

## Docker step by step

```sh
docker search <image-name>
# Prefer official [ok] images

docker pull <image-name>:<tag>
# default tag is latest, to find other tags search on https://hub.docker.com/

docker create <image-name>

docker start <container-id>

docker pause <container-id>

docker stop <container-id>

docker rm <container-id>

docker rmi <image-name>
```

# Docker packaging your app in a image Using Docker Commit

## Pull lightweight/slim python docker image
```sh
docker pull python:3.12-slim
```

## Create Simple Python Flask app

### Create directory `simple_app`
```sh
mkdir simple_app
```

### Create app.py inside `simple_app`
```sh
cd simple_app
touch app.py
```

### Add below code in `app.py`
```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
```

### Install flask
```sh
pip install flask
```

### Execute the app
```sh
python -m simple_app.app
```
```txt
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

## Run the python container and Copy your `simple_app` inside it

### Run the container for infinity to copy your app
```sh
docker run -dit --name python-container python:3.12-slim sleep infinity
```

### Install fask in it
```sh
docker exec -it python-container sh
```

```txt
# pip install flask
Collecting flask
  Downloading flask-3.1.3-py3-none-any.whl.metadata (3.2 kB)
Collecting blinker>=1.9.0 (from flask)
  Downloading blinker-1.9.0-py3-none-any.whl.metadata (1.6 kB)
Collecting click>=8.1.3 (from flask)
  Downloading click-8.5.1-py3-none-any.whl.metadata (2.6 kB)
Collecting itsdangerous>=2.2.0 (from flask)
  Downloading itsdangerous-2.2.0-py3-none-any.whl.metadata (1.9 kB)
Collecting jinja2>=3.1.2 (from flask)
  Downloading jinja2-3.1.6-py3-none-any.whl.metadata (2.9 kB)
Collecting markupsafe>=2.1.1 (from flask)
  Downloading markupsafe-3.0.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.7 kB)
Collecting werkzeug>=3.1.0 (from flask)
  Downloading werkzeug-3.1.9-py3-none-any.whl.metadata (4.1 kB)
Downloading flask-3.1.3-py3-none-any.whl (103 kB)
Downloading blinker-1.9.0-py3-none-any.whl (8.5 kB)
Downloading click-8.5.1-py3-none-any.whl (126 kB)
Downloading itsdangerous-2.2.0-py3-none-any.whl (16 kB)
Downloading jinja2-3.1.6-py3-none-any.whl (134 kB)
Downloading markupsafe-3.0.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (22 kB)
Downloading werkzeug-3.1.9-py3-none-any.whl (228 kB)
Installing collected packages: markupsafe, itsdangerous, click, blinker, werkzeug, jinja2, flask
Successfully installed blinker-1.9.0 click-8.5.1 flask-3.1.3 itsdangerous-2.2.0 jinja2-3.1.6 markupsafe-3.0.4 werkzeug-3.1.9
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
#
```

### Copy your code in the docker container
```sh
docker cp simple_app/ python-container:/usr/
```

### Verify Your app running
```sh
docker exec python-container python -m usr.simple_app.app
```

```txt
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

### Commit your docker image
```sh
docker commit --change='EXPOSE 5000' --change='CMD ["python", "-m", "usr.simple_app.app"]' python-container flask-app:v1.0
```

### verify your image
```sh
docker images
```
```txt
                                                                                                                                           i Info →   U  In Use
IMAGE              ID             DISK USAGE   CONTENT SIZE   EXTRA
flask-app:v1.0     b5c9488fb0ef        200MB         49.2MB    U   
python:3.12-slim   5e2bdb1b0d54        180MB         45.5MB    U  
```

### Run container using the new image
```sh
docker run -p 5000:5000 flask-app:v1.0
```

```txt
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://172.17.0.3:5000
Press CTRL+C to quit
```


# Docker packaging your app in a image Using Docker Build and Dockerfile

## Create `simple_app_v2`
```sh
mkdir simple_app_v2
cd simple_app_v2
```

## Create app file with below content
```sh
touch app.py
```

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
```

## Create requirements file with below content
```sh
touch requirements.txt
```

```txt
Flask==3.1.3
```

## Create Dockerfile with below content
```sh
touch Dockerfile
```

```Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python", "-m", "app"]
```

## Execute docker build
```sh
docker build -t flask-app:v2.0 .
```
```txt
[+] Building 16.8s (10/10) FINISHED                                                                                                             docker:default
 => [internal] load build definition from Dockerfile                                                                                                      0.1s
 => => transferring dockerfile: 201B                                                                                                                      0.0s
 => [internal] load metadata for docker.io/library/python:3.12-slim                                                                                       0.0s
 => [internal] load .dockerignore                                                                                                                         0.0s
 => => transferring context: 2B                                                                                                                           0.0s
 => [1/5] FROM docker.io/library/python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b                                 2.3s
 => => resolve docker.io/library/python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b                                 0.0s
 => => extracting sha256:37fb86c2a767b88d500c6872195f88078f64765fe0d2f9cc375cc2efbd4c0a41                                                                 1.2s
 => => extracting sha256:68bced9e0afa4479df17c3646e27c7c7e9ce9ba70c0e6c73b6826487b89037d9                                                                 0.1s
 => => extracting sha256:2dc99d2d0a39fce31e37615eb4c932e16dcc4c2b0ce9993714280081b5dbe085                                                                 0.9s
 => => extracting sha256:05e0eee5572e9c9f50408a2132590133b830a668a1cf2ff2b150f19c57707e2b                                                                 0.0s
 => [internal] load build context                                                                                                                         0.0s
 => => transferring context: 478B                                                                                                                         0.0s
 => [2/5] WORKDIR /app                                                                                                                                    2.9s
 => [3/5] COPY requirements.txt .                                                                                                                         0.0s
 => [4/5] RUN pip install --no-cache-dir -r requirements.txt                                                                                              9.9s
 => [5/5] COPY . .                                                                                                                                        0.1s 
 => exporting to image                                                                                                                                    1.2s 
 => => exporting layers                                                                                                                                   0.7s 
 => => exporting manifest sha256:0ab8b6c70578337deec367c1ebd3dd2bea6004c59d991cd6df6a22219c91c641                                                         0.0s 
 => => exporting config sha256:2e7304cc66bbfeb405657b62c2af5dd6a4f5d208cab8a7cdd01f681d921b56c5                                                           0.0s 
 => => exporting attestation manifest sha256:b2e5d53ca3632bad09e2a58c93763351e6ad084e5d190ff0e30bd1713192a767                                             0.0s 
 => => exporting manifest list sha256:ab02264e6d64e7d8ef1c1418a067eb0b925cd474f10dec7044986185f818bb0e                                                    0.0s
 => => naming to docker.io/library/flask-app:v2.0                                                                                                         0.0s
 => => unpacking to docker.io/library/flask-app:v2.0                                                                                                      0.4s
```

## Verify the image
```sh
docker images
```
```txt
                                                                                                                                                                                      i Info →   U  In Use
IMAGE              ID             DISK USAGE   CONTENT SIZE   EXTRA
flask-app:v1.0     b5c9488fb0ef        200MB         49.2MB        
flask-app:v2.0     38b1de1b4b82        198MB         48.4MB    U   
python:3.12-slim   5e2bdb1b0d54        180MB         45.5MB      
```

## Run the container
```sh
docker run -p 5000:5000 flask-app:v2.0
```
```txt
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://172.17.0.2:5000
Press CTRL+C to quit
```

# Web App with Database using postgress docker

## Create `web_app`
```sh
mkdir web_app
```

## Create `app.py` with below content
```sh
touch app.py
```
```python
import os

from flask import Flask, request, jsonify, redirect, url_for
from flask.views import MethodView
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from markupsafe import escape
from sqlalchemy.exc import SQLAlchemyError


# ============================================================
# Application Configuration
# ============================================================

load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured in .env")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ============================================================
# Student Model
# ============================================================

class Student(db.Model):

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age
        }

    def __repr__(self):
        return (
            f"<Student id={self.id} "
            f"name={self.name!r} age={self.age}>"
        )


# ============================================================
# Home View
# ============================================================

class Home(MethodView):

    def get(self):
        return """
        <h1>Welcome to Student Management System</h1>

        <h2>Available Functionalities</h2>

        <ul>
            <li><a href="/students">List All Students</a></li>
            <li><a href="/students/1">View Student ID 1</a></li>
            <li><a href="/students/new">Add New Student</a></li>
        </ul>
        """


# ============================================================
# Student View
# ============================================================

class StudentView(MethodView):

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    @staticmethod
    def wants_json():
        return (
            request.is_json
            or request.accept_mimetypes.best == "application/json"
        )

    def validate_student_data(self):
        """
        Returns:
            ((name, age), None) on success
            (None, (response, status_code)) on failure
        """

        if request.is_json:
            data = request.get_json(silent=True)

            if not isinstance(data, dict):
                return None, (
                    jsonify({"error": "JSON body must be an object"}),
                    400
                )
        else:
            data = request.form

        name = data.get("name")
        age = data.get("age")

        if not isinstance(name, str) or not name.strip():
            return None, (
                jsonify({"error": "Valid name is required"}),
                400
            )

        try:
            age = int(age)
        except (ValueError, TypeError):
            return None, (
                jsonify({"error": "Age must be an integer"}),
                400
            )

        if not 10 <= age <= 25:
            return None, (
                jsonify({"error": "Age must be between 10 and 25"}),
                400
            )

        return (name.strip(), age), None

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def get(self, id=None, action=None):

        if action == "new":
            return self.student_form()

        if action == "edit":
            student = db.session.get(Student, id)

            if student is None:
                return "Student not found", 404

            return self.student_form(student)

        if id is None:
            return self.fetch_all_students()

        return self.fetch_student(id)

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    def post(self, id=None, action=None):

        if action == "new" or id is None:
            return self.create_student()

        if action == "edit":
            return self.update_student(id)

        if action == "delete":
            return self.delete_student(id)

        return jsonify({"error": "Invalid operation"}), 400

    # --------------------------------------------------------
    # PUT
    # --------------------------------------------------------

    def put(self, id):
        return self.update_student(id, json_only=True)

    # --------------------------------------------------------
    # DELETE
    # --------------------------------------------------------

    def delete(self, id):
        return self.delete_student(id, json_only=True)

    # ========================================================
    # CREATE STUDENT
    # ========================================================

    def create_student(self):

        data, error = self.validate_student_data()

        if error:
            return error

        name, age = data

        try:
            student = Student(
                name=name,
                age=age
            )

            db.session.add(student)
            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Failed to create student")
            return jsonify({"error": "Could not create student"}), 500

        if request.is_json:
            return jsonify({
                "message": "Student created successfully",
                "student": student.to_dict()
            }), 201

        return redirect(url_for("student", id=student.id))

    # ========================================================
    # UPDATE STUDENT
    # ========================================================

    def update_student(self, id, json_only=False):

        student = db.session.get(Student, id)

        if student is None:
            return jsonify({"error": "Student not found"}), 404

        if json_only and not request.is_json:
            return jsonify({"error": "JSON body is required"}), 400

        data, error = self.validate_student_data()

        if error:
            return error

        name, age = data

        try:
            student.name = name
            student.age = age

            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Failed to update student")
            return jsonify({"error": "Could not update student"}), 500

        if request.is_json:
            return jsonify({
                "message": "Student updated successfully",
                "student": student.to_dict()
            }), 200

        return redirect(url_for("student", id=id))

    # ========================================================
    # DELETE STUDENT
    # ========================================================

    def delete_student(self, id, json_only=False):

        student = db.session.get(Student, id)

        if student is None:
            return jsonify({"error": "Student not found"}), 404

        if json_only and not request.is_json:
            return jsonify({"error": "JSON request expected"}), 400

        try:
            db.session.delete(student)
            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Failed to delete student")
            return jsonify({"error": "Could not delete student"}), 500

        if json_only:
            return jsonify({
                "message": "Student deleted successfully",
                "student_id": id
            }), 200

        return redirect(url_for("student"))

    # ========================================================
    # HTML FORMS
    # ========================================================

    def student_form(self, student=None):

        is_edit = student is not None

        title = "Update Student" if is_edit else "Add New Student"

        name = escape(student.name) if is_edit else ""
        age = student.age if is_edit else ""

        action = (
            url_for("student", id=student.id, action="edit")
            if is_edit
            else url_for("student", action="new")
        )

        return f"""
        <h1>{title}</h1>

        <form method="POST" action="{action}">

            <label for="name">Name:</label><br>

            <input
                type="text"
                id="name"
                name="name"
                value="{name}"
                maxlength="100"
                required
            >

            <br><br>

            <label for="age">Age:</label><br>

            <input
                type="number"
                id="age"
                name="age"
                value="{age}"
                min="10"
                max="25"
                required
            >

            <br><br>

            <button type="submit">
                {"Update" if is_edit else "Create"}
            </button>

        </form>

        <br>

        <a href="/students">Back to Students</a>
        """

    # ========================================================
    # FETCH ALL STUDENTS
    # ========================================================

    def fetch_all_students(self):

        students = db.session.execute(
            db.select(Student).order_by(Student.id)
        ).scalars().all()

        if self.wants_json():
            return jsonify([
                student.to_dict()
                for student in students
            ])

        html = """
        <h1>All Students</h1>

        <a href="/students/new">Add New Student</a>

        <br><br>

        <table border="1" cellpadding="8">

            <tr>
                <th>ID</th>
                <th>NAME</th>
                <th>AGE</th>
                <th>ACTIONS</th>
            </tr>
        """

        for student in students:

            html += f"""
            <tr>
                <td>{student.id}</td>
                <td>{escape(student.name)}</td>
                <td>{student.age}</td>

                <td>
                    <a href="/students/{student.id}">
                        View
                    </a>

                    |

                    <a href="/students/{student.id}/edit">
                        Edit
                    </a>

                    |

                    <form
                        method="POST"
                        action="/students/{student.id}/delete"
                        style="display:inline"
                    >
                        <button type="submit">Delete</button>
                    </form>
                </td>
            </tr>
            """

        html += """
        </table>

        <br>

        <a href="/">Back to Home</a>
        """

        return html

    # ========================================================
    # FETCH SINGLE STUDENT
    # ========================================================

    def fetch_student(self, id):

        student = db.session.get(Student, id)

        if student is None:
            return jsonify({"error": "Student not found"}), 404

        if self.wants_json():
            return jsonify(student.to_dict())

        return f"""
        <h1>Student Details</h1>

        <table border="1" cellpadding="8">

            <tr>
                <th>ID</th>
                <th>NAME</th>
                <th>AGE</th>
            </tr>

            <tr>
                <td>{student.id}</td>
                <td>{escape(student.name)}</td>
                <td>{student.age}</td>
            </tr>

        </table>

        <br>

        <a href="/students/{id}/edit">
            Update Student
        </a>

        <br><br>

        <a href="/students">
            Back to Students
        </a>
        """


# ============================================================
# Register Views and Routes
# ============================================================

home_view = Home.as_view("home")
student_view = StudentView.as_view("student")

app.add_url_rule(
    "/",
    view_func=home_view,
    methods=["GET"]
)

app.add_url_rule(
    "/students",
    view_func=student_view,
    methods=["GET"]
)

app.add_url_rule(
    "/students/new",
    view_func=student_view,
    defaults={"action": "new"},
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/students/<int:id>",
    view_func=student_view,
    methods=["GET", "PUT", "DELETE"]
)

app.add_url_rule(
    "/students/<int:id>/edit",
    view_func=student_view,
    defaults={"action": "edit"},
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/students/<int:id>/delete",
    view_func=student_view,
    defaults={"action": "delete"},
    methods=["POST"]
)


# ============================================================
# Application Entry Point
# ============================================================

if __name__ == "__main__":

    with app.app_context():
        db.create_all()
        print("Database tables verified/created successfully!")

    print("\nRegistered Routes:")

    for rule in app.url_map.iter_rules():
        print(rule, sorted(rule.methods))

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
```

## Install postgress in docker
```sh
docker pull postgres:18.6-alpine
docker run -d \
  --name postgres-db \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=admin123 \
  -e POSTGRES_DB=student_db \
  -p 5432:5432 \
  -v postgres-data:/var/lib/postgresql \
  postgres:18.6-alpine
```

## Verify postgress container
```sh
docker ps

docker exec -it postgres-db psql -U admin -d student_db
```

## Create `.env` file with below content
```sh
touch .env
```
```txt
DATABASE_URL=postgresql+psycopg://admin:admin123@localhost:5432/student_db
```

## Create `requirements.txt` file with below content
```sh
touch requirements.txt
```
```txt
Flask==3.1.3
Flask-Migrate==4.1.0
Flask-SQLAlchemy==3.1.1
psycopg==3.3.8
python-dotenv==1.2.4
```

## Install dependencies
```sh
pip install -r requirements.txt
```

## Execute the app
```sh
python -m app
```

# Web App v2 with Database using postgress by docker compose

## Create `web_app`
```sh
mkdir web_app_v2
```

## Create `app.py` with below content
```sh
touch app.py
```
```python
import os

from flask import Flask, request, jsonify, redirect, url_for
from flask.views import MethodView
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from markupsafe import escape
from sqlalchemy.exc import SQLAlchemyError


# ============================================================
# Application Configuration
# ============================================================

load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured in .env")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ============================================================
# Student Model
# ============================================================

class Student(db.Model):

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age
        }

    def __repr__(self):
        return (
            f"<Student id={self.id} "
            f"name={self.name!r} age={self.age}>"
        )


# ============================================================
# Home View
# ============================================================

class Home(MethodView):

    def get(self):
        return """
        <h1>Welcome to Student Management System</h1>

        <h2>Available Functionalities</h2>

        <ul>
            <li><a href="/students">List All Students</a></li>
            <li><a href="/students/1">View Student ID 1</a></li>
            <li><a href="/students/new">Add New Student</a></li>
        </ul>
        """


# ============================================================
# Student View
# ============================================================

class StudentView(MethodView):

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    @staticmethod
    def wants_json():
        return (
            request.is_json
            or request.accept_mimetypes.best == "application/json"
        )

    def validate_student_data(self):
        """
        Returns:
            ((name, age), None) on success
            (None, (response, status_code)) on failure
        """

        if request.is_json:
            data = request.get_json(silent=True)

            if not isinstance(data, dict):
                return None, (
                    jsonify({"error": "JSON body must be an object"}),
                    400
                )
        else:
            data = request.form

        name = data.get("name")
        age = data.get("age")

        if not isinstance(name, str) or not name.strip():
            return None, (
                jsonify({"error": "Valid name is required"}),
                400
            )

        try:
            age = int(age)
        except (ValueError, TypeError):
            return None, (
                jsonify({"error": "Age must be an integer"}),
                400
            )

        if not 10 <= age <= 25:
            return None, (
                jsonify({"error": "Age must be between 10 and 25"}),
                400
            )

        return (name.strip(), age), None

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def get(self, id=None, action=None):

        if action == "new":
            return self.student_form()

        if action == "edit":
            student = db.session.get(Student, id)

            if student is None:
                return "Student not found", 404

            return self.student_form(student)

        if id is None:
            return self.fetch_all_students()

        return self.fetch_student(id)

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    def post(self, id=None, action=None):

        if action == "new" or id is None:
            return self.create_student()

        if action == "edit":
            return self.update_student(id)

        if action == "delete":
            return self.delete_student(id)

        return jsonify({"error": "Invalid operation"}), 400

    # --------------------------------------------------------
    # PUT
    # --------------------------------------------------------

    def put(self, id):
        return self.update_student(id, json_only=True)

    # --------------------------------------------------------
    # DELETE
    # --------------------------------------------------------

    def delete(self, id):
        return self.delete_student(id, json_only=True)

    # ========================================================
    # CREATE STUDENT
    # ========================================================

    def create_student(self):

        data, error = self.validate_student_data()

        if error:
            return error

        name, age = data

        try:
            student = Student(
                name=name,
                age=age
            )

            db.session.add(student)
            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Failed to create student")
            return jsonify({"error": "Could not create student"}), 500

        if request.is_json:
            return jsonify({
                "message": "Student created successfully",
                "student": student.to_dict()
            }), 201

        return redirect(url_for("student", id=student.id))

    # ========================================================
    # UPDATE STUDENT
    # ========================================================

    def update_student(self, id, json_only=False):

        student = db.session.get(Student, id)

        if student is None:
            return jsonify({"error": "Student not found"}), 404

        if json_only and not request.is_json:
            return jsonify({"error": "JSON body is required"}), 400

        data, error = self.validate_student_data()

        if error:
            return error

        name, age = data

        try:
            student.name = name
            student.age = age

            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Failed to update student")
            return jsonify({"error": "Could not update student"}), 500

        if request.is_json:
            return jsonify({
                "message": "Student updated successfully",
                "student": student.to_dict()
            }), 200

        return redirect(url_for("student", id=id))

    # ========================================================
    # DELETE STUDENT
    # ========================================================

    def delete_student(self, id, json_only=False):

        student = db.session.get(Student, id)

        if student is None:
            return jsonify({"error": "Student not found"}), 404

        if json_only and not request.is_json:
            return jsonify({"error": "JSON request expected"}), 400

        try:
            db.session.delete(student)
            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Failed to delete student")
            return jsonify({"error": "Could not delete student"}), 500

        if json_only:
            return jsonify({
                "message": "Student deleted successfully",
                "student_id": id
            }), 200

        return redirect(url_for("student"))

    # ========================================================
    # HTML FORMS
    # ========================================================

    def student_form(self, student=None):

        is_edit = student is not None

        title = "Update Student" if is_edit else "Add New Student"

        name = escape(student.name) if is_edit else ""
        age = student.age if is_edit else ""

        action = (
            url_for("student", id=student.id, action="edit")
            if is_edit
            else url_for("student", action="new")
        )

        return f"""
        <h1>{title}</h1>

        <form method="POST" action="{action}">

            <label for="name">Name:</label><br>

            <input
                type="text"
                id="name"
                name="name"
                value="{name}"
                maxlength="100"
                required
            >

            <br><br>

            <label for="age">Age:</label><br>

            <input
                type="number"
                id="age"
                name="age"
                value="{age}"
                min="10"
                max="25"
                required
            >

            <br><br>

            <button type="submit">
                {"Update" if is_edit else "Create"}
            </button>

        </form>

        <br>

        <a href="/students">Back to Students</a>
        """

    # ========================================================
    # FETCH ALL STUDENTS
    # ========================================================

    def fetch_all_students(self):

        students = db.session.execute(
            db.select(Student).order_by(Student.id)
        ).scalars().all()

        if self.wants_json():
            return jsonify([
                student.to_dict()
                for student in students
            ])

        html = """
        <h1>All Students</h1>

        <a href="/students/new">Add New Student</a>

        <br><br>

        <table border="1" cellpadding="8">

            <tr>
                <th>ID</th>
                <th>NAME</th>
                <th>AGE</th>
                <th>ACTIONS</th>
            </tr>
        """

        for student in students:

            html += f"""
            <tr>
                <td>{student.id}</td>
                <td>{escape(student.name)}</td>
                <td>{student.age}</td>

                <td>
                    <a href="/students/{student.id}">
                        View
                    </a>

                    |

                    <a href="/students/{student.id}/edit">
                        Edit
                    </a>

                    |

                    <form
                        method="POST"
                        action="/students/{student.id}/delete"
                        style="display:inline"
                    >
                        <button type="submit">Delete</button>
                    </form>
                </td>
            </tr>
            """

        html += """
        </table>

        <br>

        <a href="/">Back to Home</a>
        """

        return html

    # ========================================================
    # FETCH SINGLE STUDENT
    # ========================================================

    def fetch_student(self, id):

        student = db.session.get(Student, id)

        if student is None:
            return jsonify({"error": "Student not found"}), 404

        if self.wants_json():
            return jsonify(student.to_dict())

        return f"""
        <h1>Student Details</h1>

        <table border="1" cellpadding="8">

            <tr>
                <th>ID</th>
                <th>NAME</th>
                <th>AGE</th>
            </tr>

            <tr>
                <td>{student.id}</td>
                <td>{escape(student.name)}</td>
                <td>{student.age}</td>
            </tr>

        </table>

        <br>

        <a href="/students/{id}/edit">
            Update Student
        </a>

        <br><br>

        <a href="/students">
            Back to Students
        </a>
        """


# ============================================================
# Register Views and Routes
# ============================================================

home_view = Home.as_view("home")
student_view = StudentView.as_view("student")

app.add_url_rule(
    "/",
    view_func=home_view,
    methods=["GET"]
)

app.add_url_rule(
    "/students",
    view_func=student_view,
    methods=["GET"]
)

app.add_url_rule(
    "/students/new",
    view_func=student_view,
    defaults={"action": "new"},
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/students/<int:id>",
    view_func=student_view,
    methods=["GET", "PUT", "DELETE"]
)

app.add_url_rule(
    "/students/<int:id>/edit",
    view_func=student_view,
    defaults={"action": "edit"},
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/students/<int:id>/delete",
    view_func=student_view,
    defaults={"action": "delete"},
    methods=["POST"]
)


# ============================================================
# Application Entry Point
# ============================================================

if __name__ == "__main__":

    with app.app_context():
        db.create_all()
        print("Database tables verified/created successfully!")

    print("\nRegistered Routes:")

    for rule in app.url_map.iter_rules():
        print(rule, sorted(rule.methods))

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
```

## Create `requirements.txt` file with below content
```sh
touch requirements.txt
```
```txt
Flask==3.1.3
Flask-Migrate==4.1.0
Flask-SQLAlchemy==3.1.1
psycopg==3.3.8
python-dotenv==1.2.4
psycopg[binary]==3.3.8
```

## Create `Dockerfile` with below content
```sh
touch Dockerfle
```
```Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python", "-m", "app"]
```

## Create `docker-compose` file with below content
```sh
touch docker-compose.yml
```
```yml
version: "1.0"

services:
  app:
    build: .
    container_name: web_app_v2
    ports:
      - "5000:5000"
    networks:
      - web_app_v2
    environment:
      DATABASE_URL: postgresql+psycopg://admin:admin123@postgres:5432/student_db
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  postgres:
    image: postgres:18.6-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: admin123
      POSTGRES_DB: student_db
    ports:
      - "5432:5432"
    networks:
      - web_app_v2
    volumes:
      - postgres_data:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin -d student_db"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

volumes:
  postgres_data:

networks:
  web_app_v2:
    driver: bridge
```

## Build the docker compose and run it
```sh
docker-compose up --build
```

## Down it with
```sh
docker-compose down
```