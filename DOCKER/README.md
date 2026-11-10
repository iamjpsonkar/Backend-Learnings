# Docker Learning Notes

> A practical, hands-on guide to Docker fundamentals, installation,
> commands, images, containers, Dockerfiles, networking, storage,
> Compose, and a Flask + PostgreSQL project.

**Scope:** Linux containers and Docker Engine, with notes for Docker
Desktop on macOS and Windows.

------------------------------------------------------------------------

## Table of contents

1.  [What is Docker?](#1-what-is-docker)
2.  [A short history of containers](#2-a-short-history-of-containers)
3.  [How Docker works](#3-how-docker-works)
4.  [How Linux containers work
    internally](#4-how-linux-containers-work-internally)
5.  [Docker architecture and
    components](#5-docker-architecture-and-components)
6.  [Containers vs virtual machines](#6-containers-vs-virtual-machines)
7.  [Images, tags, registries, and Docker
    Hub](#7-images-tags-registries-and-docker-hub)
8.  [Essential Docker commands](#8-essential-docker-commands)
9.  [Dockerfile and image building](#9-dockerfile-and-image-building)
10. [Container storage](#10-container-storage)
11. [Docker networking](#11-docker-networking)
12. [Docker Compose](#12-docker-compose)
13. [Install Docker](#13-install-docker)
14. [Hands-on: package a Flask app](#14-hands-on-package-a-flask-app)
15. [Hands-on: Flask with
    PostgreSQL](#15-hands-on-flask-with-postgresql)
16. [Troubleshooting](#16-troubleshooting)
17. [Recommended learning path](#17-recommended-learning-path)
18. [References](#18-references)

------------------------------------------------------------------------

# 1. What is Docker?

**Docker is a platform and toolset for building, packaging,
distributing, and running applications in containers.**

A container packages an application with the files, libraries, runtime,
and configuration it needs. A Linux container runs as an isolated group
of processes while sharing the host's Linux kernel.

The central idea is:

> Build an image once, then run that image consistently in compatible
> environments.

The same image can be used on a developer's machine, in a test
environment, or on a production server, provided the target environment
supports the image's operating system and CPU architecture.

### Why Docker is useful

Without a reproducible runtime environment, an application may work on
one machine but fail on another because of differences in:

-   Programming-language or runtime versions.
-   System libraries and dependencies.
-   Operating-system packages.
-   Environment variables and configuration.
-   Filesystem layout and startup commands.

Docker makes these requirements explicit and makes it easier to start,
stop, replace, distribute, and scale application instances.

### Docker is not a virtual machine

A typical Linux container is not a miniature virtual machine. It is an
isolated process environment that shares the host's Linux kernel.

A virtual machine runs a guest operating system on virtualized hardware.
Docker is also more than the `docker` command: its ecosystem includes
image formats, build tooling, a client, an API, runtime components,
registries, networks, and storage.

------------------------------------------------------------------------

# 2. A short history of containers

Containerization predates Docker. Docker made container-based
application packaging and workflows much easier for developers to use.

  ------------------------------------------------------------------------
  Period                  Development             Why it matters
  ----------------------- ----------------------- ------------------------
  1979                    Unix `chroot`           Changed a process's
                                                  apparent root directory,
                                                  providing an early form
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
                          later cgroups           and limiting groups of
                                                  processes' resource
                                                  usage.

  2008                    Linux Containers (LXC)  Combined Linux kernel
                                                  features to create
                                                  system containers.

  2013                    Docker publicly         Made container-based
                          introduced              application packaging
                                                  and workflows accessible
                                                  to a wider developer
                                                  audience.

  2015                    Open Container          Began standardizing
                          Initiative (OCI)        container image formats
                          launched                and runtime behavior.

  2016 onward             Container               Made it practical to
                          orchestration,          manage containerized
                          including Kubernetes,   applications across
                          became widely adopted   clusters.
  ------------------------------------------------------------------------

### Important historical distinction

Docker did not invent containers, namespaces, or cgroups. Its major
contribution was making container workflows approachable: package an
application into an image, share that image, and run it in a predictable
environment.

------------------------------------------------------------------------

# 3. How Docker works

Think of Docker as a pipeline:

1.  **Describe** the application environment and startup instructions in
    a `Dockerfile`.
2.  **Build** the Dockerfile into an image.
3.  **Store or share** the image locally or in a registry.
4.  **Create and start** a container from the image.
5.  **Connect** the container to networks and attach persistent storage
    when needed.
6.  **Observe and manage** the container using Docker tools and APIs.

``` text
              Dockerfile
                  |
             docker build
                  |
                  v
             Docker Image
              /       \
     docker run       push
          |              \
          v               v
      Container        Registry
          ^               |
          |               | pull
          +---------------+
```

An **image** is the packaged template. A **container** is a runnable
instance created from that template. One image can be used to create
multiple containers.

------------------------------------------------------------------------

# 4. How Linux containers work internally

Containers are enabled primarily by Linux kernel features. Docker
provides the user-facing workflow and coordinates components that use
those features.

## 4.1 Namespaces: isolation

Linux namespaces give processes different views of selected system
resources. A container can therefore see its own process list, network
interfaces, hostname, and mount layout rather than the host's full view.

  -----------------------------------------------------------------------
  Namespace                           What it isolates
  ----------------------------------- -----------------------------------
  PID                                 Process ID view and process tree.

  Network                             Network devices, routes, IP
                                      addresses, ports, and related
                                      state.

  Mount                               Filesystem mount points and mount
                                      layout.

  UTS                                 Hostname and domain name.

  IPC                                 Inter-process communication
                                      resources.

  User                                User and group ID mappings. A
                                      process can be root inside a user
                                      namespace without necessarily being
                                      root on the host.

  Cgroup                              A view of the control-group
                                      hierarchy, where supported.
  -----------------------------------------------------------------------

Namespaces provide separation of views; they do not by themselves impose
CPU or memory limits.

## 4.2 cgroups: resource accounting and limits

**Control groups (cgroups)** let the kernel organize processes and
account for or limit resources.

Depending on the host configuration and cgroup version, controls can
include:

-   CPU time and CPU weights.
-   Memory usage and memory limits.
-   Process counts.
-   Block I/O usage and throttling.

A container can be configured with a memory limit so it cannot consume
unlimited host memory. The exact behavior when a limit is reached
depends on the resource and kernel configuration.

## 4.3 Filesystem layers

Container images are generally composed of read-only filesystem layers.
When a container is created, the runtime adds a writable layer on top.

``` text
       Container filesystem view
      +---------------------------+
      | Writable container layer  | <- runtime changes
      +---------------------------+
      | Image layer 3             |
      +---------------------------+
      | Image layer 2             | <- read-only image layers
      +---------------------------+
      | Image layer 1             |
      +---------------------------+
      | Base image layer          |
      +---------------------------+
```

Identical layers can be reused across images, reducing storage and
transfer costs. The exact storage driver and implementation depend on
the Docker installation.

**Important:** Data written only to a container's writable layer is tied
to that container's lifecycle. Removing the container normally removes
that writable layer. Use volumes or bind mounts for data that must
persist.

## 4.4 Copy-on-write

Layered filesystems present multiple layers as one filesystem view. With
copy-on-write behavior, a file from a lower read-only layer can be
copied into the writable layer when modified. The container sees the
modified version while the original image remains unchanged.

The implementation is storage-driver and platform dependent; do not
assume every Docker environment uses the same filesystem driver.

## 4.5 Containers share a kernel

On a Linux host, containers share the host kernel. They are isolated
processes, not separate operating-system installations.

This is efficient, but the kernel is part of the shared security
boundary. Containers should not automatically be treated as equivalent
to strongly isolated VMs. Use least privilege, avoid unnecessary
capabilities, keep hosts patched, and apply appropriate security
controls.

------------------------------------------------------------------------

# 5. Docker architecture and components

A common Docker Engine setup uses a client-server architecture.

``` text
       Developer / CI pipeline
                  |
             Docker CLI
                  |
           Docker Engine API
                  |
             dockerd
          /      |       \
       Images  Containers  Networks / Volumes
                  |
              containerd
                  |
                runc
                  |
            Linux kernel
       (namespaces, cgroups, etc.)

             Registry
          push ^   | pull
              +---+
```

The exact internal arrangement varies by Docker version, operating
system, and installation. This is a high-level view, not every
implementation detail.

## 5.1 Docker Client (`docker` CLI)

The Docker client is the command-line interface most developers use.

``` bash
docker build -t my-app:1.0 .
docker run --name my-app my-app:1.0
docker ps
docker logs my-app
docker stop my-app
```

The CLI sends requests to the Docker Engine API. The client and daemon
may run on the same machine or communicate remotely.

## 5.2 Docker Daemon (`dockerd`)

The Docker daemon is a background service responsible for managing
Docker objects and coordinating operations such as:

-   Building and managing images.
-   Creating and managing containers.
-   Managing networks and volumes.
-   Communicating with registries.
-   Exposing the Docker Engine API.

On many Linux installations, `dockerd` runs as a system service. Docker
Desktop uses a different host integration architecture on macOS and
Windows.

## 5.3 Docker Engine API

The Engine API is the interface through which clients and other tools
request Docker operations. The CLI is one client; other programs can use
the API through supported libraries or HTTP endpoints.

Access to the Docker daemon is highly privileged. On many Linux systems,
membership in the `docker` group effectively grants root-level
capabilities. Protect the daemon socket and remote API.

## 5.4 containerd

`containerd` is a container runtime component responsible for core
container lifecycle operations, including image transfer and storage,
container execution management, and supervision of running containers.

Docker Engine commonly uses containerd rather than implementing every
low-level lifecycle function directly in `dockerd`.

## 5.5 runc

`runc` is a low-level OCI runtime. It creates and runs containers
according to the OCI runtime specification, using operating-system
facilities such as namespaces and cgroups.

Simplified responsibilities:

-   Docker CLI: accepts user commands.
-   `dockerd`: manages Docker Engine objects and API requests.
-   `containerd`: manages container lifecycle tasks.
-   `runc`: performs low-level container creation and execution.

## 5.6 Docker images

An image is a read-only, layered template used to create containers. It
includes application files, dependencies, metadata, and configuration
such as the default command.

Examples:

``` text
nginx:1.27
python:3.12-slim
postgres:18-alpine
my-company/payment-api:1.4.2
```

A tag is a movable name, not a guarantee of immutable content. For
repeatable deployments, consider pinning images by digest.

## 5.7 Docker containers

A container is an instance of an image with its own runtime
configuration and writable layer.

A container can be created, started, paused, stopped, restarted, and
removed.

A stopped container still exists until it is removed. A container is not
the same thing as an image.

## 5.8 Dockerfile

A `Dockerfile` is a text file containing instructions for building an
image.

Example:

``` dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

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
                                      `COPY` for ordinary copying.

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

  `CMD`                               Supplies a default command or
                                      arguments; interaction with
                                      `ENTRYPOINT` depends on the form
                                      used.

  `VOLUME`                            Declares a mount point intended for
                                      persistent or externally managed
                                      data.
  -----------------------------------------------------------------------

## 5.9 Docker Registry

A registry stores and distributes images. Developers and CI systems can
push images to a registry and servers can pull them.

Examples include Docker Hub and private registries provided by cloud
platforms or organizations.

``` bash
# Authenticate, if required
docker login

# Tag a local image for a registry
docker tag my-app:1.0 username/my-app:1.0

# Upload the image
docker push username/my-app:1.0

# Download an image
docker pull username/my-app:1.0
```

## 5.10 Docker volumes and bind mounts

Containers are replaceable. Persistent data should live outside the
container's writable layer.

**Volume:** Managed by Docker and stored in Docker-managed storage.

``` bash
docker volume create app-data

docker run -d \
  --name database \
  -v app-data:/var/lib/postgresql/data \
  postgres:17
```

For PostgreSQL 18 and newer official images, use the image's documented
volume layout; the recommended mount point is `/var/lib/postgresql`. See
the PostgreSQL example later in this guide.

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

## 5.11 Docker networking

Docker networks allow containers to communicate with one another and
with external systems.

Common network drivers include:

-   **bridge:** Common default for containers on a single Docker host.
-   **host:** Shares the host network namespace on supported Linux
    setups.
-   **none:** Disables normal container networking.
-   **overlay:** Connects containers across multiple Docker hosts in
    supported Swarm configurations.

Example:

``` bash
docker network create app-network

docker run -d \
  --name redis \
  --network app-network \
  redis:7

docker run --rm \
  --name api \
  --network app-network \
  my-api:1.0
```

Containers on a user-defined bridge network can generally reach each
other by container name.

Publish a container port to a host port with `-p`:

``` bash
docker run -d -p 8080:80 nginx
```

This maps host port `8080` to container port `80`.

## 5.12 Docker Compose

Docker Compose defines and runs multi-container applications using a
YAML file.

A typical application may contain:

-   API service.
-   Database.
-   Redis cache.
-   Background worker.

Example:

``` yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://app:secret@db:5432/app
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:17
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: app
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      timeout: 5s
      retries: 10

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

The named volume remains unless explicitly removed, for example with
`docker compose down -v`.

The example is for learning; do not commit real production passwords to
source control. Use secrets or a secure configuration mechanism.

------------------------------------------------------------------------

# 6. Containers vs virtual machines

Both containers and virtual machines provide isolation, but they do it
at different layers.

## 6.1 Virtual machine architecture

``` text
+----------------------+  +----------------------+
| Application          |  | Application          |
| Libraries / Runtime  |  | Libraries / Runtime  |
| Guest OS             |  | Guest OS             |
+----------------------+  +----------------------+
|                  Hypervisor                     |
+-------------------------------------------------+
|                  Host hardware                  |
+-------------------------------------------------+
```

Each VM typically includes its own guest operating system and kernel.

## 6.2 Container architecture

``` text
+----------------------+  +----------------------+
| Application          |  | Application          |
| Libraries / Runtime  |  | Libraries / Runtime  |
| Container isolation  |  | Container isolation  |
+----------------------+  +----------------------+
|          Shared Host Operating-System Kernel    |
+-------------------------------------------------+
|                    Hardware                     |
+-------------------------------------------------+
```

Containers isolate processes while sharing the host kernel. On macOS and
Windows, Docker Desktop typically runs Linux containers inside a
lightweight Linux virtual machine because the host operating system does
not provide a Linux kernel directly.

## 6.3 Side-by-side comparison

  ------------------------------------------------------------------------
  Feature                 Containers               Virtual machines
  ----------------------- ------------------------ -----------------------
  Virtualization layer    Operating-system-level   Hardware virtualization
                          isolation                

  Kernel                  Shares the host kernel   Each VM has its own
                          for Linux containers     guest kernel

  Operating system        Packages application     Includes a full guest
                          dependencies, not a      OS
                          separate full guest OS   

  Startup                 Usually fast; depends on Usually slower because
                          workload                 a guest OS boots

  Resource overhead       Generally lower          Generally higher due to
                                                   guest OS overhead

  Density                 Often more workloads per Often fewer workloads
                          host                     at comparable resource
                                                   budgets

  Isolation boundary      Process and kernel       Separate guest kernel
                          isolation; depends on    and virtual hardware
                          configuration            boundary

  Best suited for         Application packaging,   Different OS kernels,
                          CI jobs, services        legacy OS environments,
                                                   VM-level separation

  Typical tools           Docker, containerd,      KVM, Hyper-V, VMware,
                          Kubernetes               VirtualBox
  ------------------------------------------------------------------------

## 6.4 Which should you choose?

Choose **containers** when you want:

-   Consistent application packaging across environments.
-   Fast startup and efficient resource usage.
-   Independently deployable services.
-   Reproducible development and CI/CD environments.

Choose **virtual machines** when you need:

-   A different guest operating system or kernel.
-   A separate OS environment.
-   A VM-level isolation boundary for a workload.
-   To run legacy systems that need a full operating system.

They are not mutually exclusive. A common production setup runs
containers inside virtual machines, combining VM-level infrastructure
isolation with container-level application packaging.

------------------------------------------------------------------------

# 7. Images, tags, registries, and Docker Hub

## 7.1 Image name format

A typical image reference has this structure:

``` text
[registry/] [namespace/] repository [:tag] [@digest]
```

Examples:

``` text
python:3.12-slim
postgres:18.6-alpine
docker.io/library/nginx:latest
ghcr.io/example/my-api:1.2.0
```

-   **Registry:** Where the image is stored, such as Docker Hub.
-   **Namespace:** User or organization.
-   **Repository:** Image name.
-   **Tag:** Human-readable version or variant label.
-   **Digest:** Content-addressed identifier for a specific image
    manifest.

`latest` is only a tag name. It does not necessarily mean the newest
stable version, and it is not automatically selected when a repository
has no `latest` tag.

## 7.2 Search repositories

``` bash
docker search nginx
```

`docker search` searches repositories. It does **not** list every tag or
version of an image.

To inspect available tags, use the repository's Docker Hub page:

-   [Docker Hub](https://hub.docker.com/)
-   [Official PostgreSQL image](https://hub.docker.com/_/postgres)
-   [Official Python image](https://hub.docker.com/_/python)

For example, Docker Hub's tags page for an image shows available
versions and variants.

## 7.3 Pull an image

``` bash
docker pull python:3.12-slim
docker pull postgres:18.6-alpine
```

If a tag is omitted, Docker normally uses `latest`.

## 7.4 List local images

``` bash
docker image ls
```

## 7.5 Inspect an image

``` bash
docker image inspect python:3.12-slim
```

## 7.6 Remove an image

``` bash
docker image rm python:3.12-slim
```

Docker will not remove an image if a container still depends on it
unless the relevant containers are removed first.

------------------------------------------------------------------------

# 8. Essential Docker commands

> Use `docker compose` (Compose V2) rather than the older standalone
> `docker-compose` command when possible.

## 8.1 Installation and daemon

``` bash
docker --version
docker version
docker info
docker context ls
```

-   `docker --version`: CLI version.
-   `docker version`: client and server versions.
-   `docker info`: Engine configuration and system information.
-   `docker context ls`: available Docker contexts.

## 8.2 Images

``` bash
docker pull nginx
docker image ls
docker image inspect nginx
docker image rm nginx
docker search nginx
```

## 8.3 Containers

``` bash
# Run a container in the foreground
docker run nginx

# Run in the background and assign a name
docker run -d --name web nginx

# Publish host port 8080 to container port 80
docker run -d --name web -p 8080:80 nginx

# List running containers
docker ps

# List all containers, including stopped ones
docker ps -a

# View logs
docker logs web

# Follow logs
docker logs -f web

# Execute a command in a running container
docker exec -it web sh

# Stop and start
docker stop web
docker start web

# Remove a stopped container
docker rm web

# Force-remove a container
docker rm -f web
```

`docker exec` works only while the target container is running.

## 8.4 Run a temporary interactive container

``` bash
docker run -it --rm python:3.12-slim python
```

-   `-i`: Keep standard input open.
-   `-t`: Allocate a terminal.
-   `--rm`: Remove the container when it exits.
-   `python:3.12-slim`: Image.
-   `python`: Command executed inside the container.

`--rm` removes the container, not the image.

## 8.5 Keep a container running for experiments

``` bash
docker run -dit \
  --name python-lab \
  python:3.12-slim \
  sleep infinity
```

Then:

``` bash
docker exec -it python-lab sh
docker exec -it python-lab python
```

Remove it when finished:

``` bash
docker rm -f python-lab
```

## 8.6 Copy files

``` bash
# Host to container
docker cp ./app.py web:/app/app.py

# Container to host
docker cp web:/app/logs ./logs
```

## 8.7 Pause and unpause

``` bash
docker pause web
docker unpause web
```

Pausing freezes the container's processes; it is not the same as
stopping the container.

## 8.8 Inspect resource usage

``` bash
docker stats
docker top web
docker inspect web
```

## 8.9 Remove unused resources carefully

``` bash
docker container prune
docker image prune
docker network prune
docker volume ls
```

Prune commands remove unused resources. Inspect what will be affected
before running them, especially for volumes containing data.

------------------------------------------------------------------------

# 9. Dockerfile and image building

A Dockerfile is the repeatable way to define how an application image is
built. Prefer it over manually configuring a container and committing
the result.

## 9.1 Build context

The final argument to `docker build` is the build context:

``` bash
docker build -t flask-app:1.0 .
```

The `.` means the current directory is sent as the build context. `COPY`
can only access files available inside that context.

Use `.dockerignore` to avoid sending unnecessary files:

``` text
.git
.venv
__pycache__
*.py[cod]
.pytest_cache
.mypy_cache
.env
.env.*
```

Do not exclude files that the image actually needs. Keep secrets such as
`.env` out of the image.

## 9.2 A basic Flask Dockerfile

Assume this project structure:

``` text
simple_app/
├── app.py
├── requirements.txt
├── Dockerfile
└── .dockerignore
```

`app.py`:

``` python
from flask import Flask

app = Flask(__name__)


@app.get("/")
def hello_world():
    return "<h1>Hello from Flask in Docker!</h1>"


if __name__ == "__main__":
    # 0.0.0.0 makes the server reachable outside the container.
    app.run(host="0.0.0.0", port=5000)
```

`requirements.txt`:

``` text
Flask==3.1.3
```

`Dockerfile`:

``` dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
```

### Why copy `requirements.txt` before the application?

Docker caches build layers. If the dependency file has not changed,
Docker can reuse the dependency-installation layer when application
source files change.

## 9.3 Build and run

``` bash
docker build -t flask-app:1.0 .
```

Run:

``` bash
docker run --rm \
  --name flask-app \
  -p 5000:5000 \
  flask-app:1.0
```

Open:

``` text
http://localhost:5000
```

The application must bind to `0.0.0.0` inside the container. Binding
only to `127.0.0.1` makes it reachable only from inside that container.

## 9.4 `EXPOSE` vs `-p`

`EXPOSE 5000` documents the port the application uses. It does not
publish that port to the host.

Publish it at runtime:

``` bash
docker run -p 5000:5000 flask-app:1.0
```

The format is:

``` text
HOST_PORT:CONTAINER_PORT
```

## 9.5 `CMD` vs `ENTRYPOINT`

-   `CMD` supplies the default command or arguments.
-   `ENTRYPOINT` defines the main executable.
-   They can be combined; the exact behavior depends on whether shell or
    exec form is used.

For a straightforward application, this is often enough:

``` dockerfile
CMD ["python", "app.py"]
```

Prefer exec form (JSON array) so the application receives signals
correctly.

## 9.6 Multi-stage builds

Multi-stage builds use multiple `FROM` instructions. Build tools can be
kept in an earlier stage while only the required runtime artifacts are
copied into the final image. This can reduce final image size and attack
surface.

------------------------------------------------------------------------

# 10. Container storage

## 10.1 Writable container layer

Changes made inside a container's writable layer are not part of the
original image. Removing the container normally removes those changes.

## 10.2 Named volumes

Create a volume:

``` bash
docker volume create app-data
```

Use it:

``` bash
docker run -d \
  --name database \
  -v app-data:/var/lib/app-data \
  nginx
```

List volumes:

``` bash
docker volume ls
docker volume inspect app-data
```

Remove a volume:

``` bash
docker volume rm app-data
```

A volume cannot normally be removed while it is still in use by a
container.

## 10.3 Bind mounts

Mount the current directory into a container:

``` bash
docker run --rm \
  -v "$PWD:/app" \
  -w /app \
  python:3.12-slim \
  python app.py
```

Bind mounts are useful for local development because source changes on
the host are visible inside the container.

## 10.4 Volume vs bind mount

  -----------------------------------------------------------------------
  Feature                 Named volume            Bind mount
  ----------------------- ----------------------- -----------------------
  Managed by              Docker                  Host filesystem

  Host path               Docker-managed          Explicit host path

  Common use              Database and persistent Source code and local
                          application data        development files

  Portability             Easier to manage        Depends on host path
                          through Docker          and permissions
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 11. Docker networking

## 11.1 Default bridge network

Docker creates a default bridge network. Containers on it can
communicate using network details, but for application stacks a
user-defined network is generally more convenient.

## 11.2 User-defined bridge network

``` bash
docker network create app-network

docker run -d \
  --name redis \
  --network app-network \
  redis:7-alpine

docker run --rm \
  --network app-network \
  alpine \
  ping -c 2 redis
```

Containers on a user-defined bridge network can use container names for
DNS-based discovery.

## 11.3 Port publishing

``` bash
docker run -d --name web -p 8080:80 nginx
```

-   Host: `localhost:8080`
-   Container: port `80`

Container-to-container traffic on the same Docker network generally uses
the container/service port directly; it does not need host port
publishing.

## 11.4 Common network drivers

  -----------------------------------------------------------------------
  Driver                              Typical use
  ----------------------------------- -----------------------------------
  `bridge`                            Containers on one Docker host.

  `host`                              Share the host network namespace on
                                      supported Linux configurations.

  `none`                              No normal container networking.

  `overlay`                           Multi-host networking in supported
                                      Swarm deployments.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 12. Docker Compose

Compose is useful when an application depends on multiple services, such
as a Flask API, PostgreSQL database, Redis, and a worker.

## 12.1 Important Compose concepts

-   A **service** defines how to run a container.
-   A **network** connects services.
-   A **volume** persists data.
-   `depends_on` controls startup ordering. With a health condition,
    Compose can wait for a dependency's health check before starting the
    dependent service.
-   Compose creates a default network if one is not explicitly defined.
-   Services can normally reach one another by service name.

## 12.2 Common commands

``` bash
# Start services and build images when needed
docker compose up --build

# Start in background
docker compose up -d --build

# List services and status
docker compose ps

# Follow all service logs
docker compose logs -f

# Follow one service
docker compose logs -f app

# Run a command in a running service
docker compose exec app sh

# Stop and remove containers and network
docker compose down

# Also remove named volumes (DESTRUCTIVE)
docker compose down -v
```

**Warning:** `docker compose down -v` removes Compose-managed named
volumes and therefore can delete database data.

------------------------------------------------------------------------

# 13. Install Docker

Docker installation differs by operating system:

-   **Linux:** Install Docker Engine directly, commonly from Docker's
    official repository.
-   **macOS:** Install Docker Desktop. It runs Linux containers inside a
    lightweight Linux VM.
-   **Windows:** Install Docker Desktop, normally using the WSL 2
    backend for Linux containers.

Docker Engine and Docker Desktop are related but different installation
choices. Docker Engine is the core container platform. Docker Desktop
bundles the engine with a desktop application and supporting tools.

> Follow the official documentation for your operating system. Supported
> versions and installation steps change over time.

## 13.1 Check your system

### Linux

``` bash
uname -m
cat /etc/os-release
```

Common architectures:

-   `x86_64`: 64-bit Intel/AMD.
-   `aarch64`: 64-bit ARM.

### macOS

``` bash
uname -m
sw_vers
```

-   `arm64`: Apple silicon.
-   `x86_64`: Intel Mac.

### Windows

Open PowerShell:

``` powershell
systeminfo
wsl --status
```

For Docker Desktop with the WSL 2 backend, use a supported Windows
version and ensure hardware virtualization is enabled in firmware/BIOS.

## 13.2 Install Docker Engine on Ubuntu

This is a common route for Ubuntu servers and systems where you want
Docker Engine without the Docker Desktop graphical application.

### Step 1: Remove conflicting packages, if installed

``` bash
sudo apt remove docker.io docker-doc docker-compose docker-compose-v2 \
  podman-docker containerd runc
```

If packages are not installed, `apt` may report that they could not be
found.

### Step 2: Install prerequisites

``` bash
sudo apt update
sudo apt install ca-certificates curl
```

### Step 3: Add Docker's official GPG key

``` bash
sudo install -m 0755 -d /etc/apt/keyrings

sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc

sudo chmod a+r /etc/apt/keyrings/docker.asc
```

### Step 4: Add Docker's official APT repository

``` bash
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

``` bash
sudo apt update
```

### Step 5: Install Docker Engine and plugins

``` bash
sudo apt install docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
```

  Package                   Purpose
  ------------------------- ----------------------------------------------------
  `docker-ce`               Docker Engine daemon.
  `docker-ce-cli`           Docker command-line client.
  `containerd.io`           Container runtime component used by Docker Engine.
  `docker-buildx-plugin`    Extended image-building functionality.
  `docker-compose-plugin`   Docker Compose V2 (`docker compose`).

### Step 6: Start and enable Docker

``` bash
sudo systemctl enable --now docker
sudo systemctl status docker
```

### Step 7: Verify

``` bash
sudo docker version
sudo docker info
sudo docker run hello-world
```

### Optional: run Docker without `sudo`

``` bash
sudo groupadd docker
sudo usermod -aG docker "$USER"
```

If the group already exists, the `groupadd` command may report that;
this is harmless.

Log out and log back in so the new group membership is applied. Or apply
it to a new shell:

``` bash
newgrp docker
docker run hello-world
```

**Security warning:** Membership in the `docker` group grants highly
privileged access and can effectively provide root-level control of the
host. Do not add untrusted users to this group. On shared or production
systems, consider using `sudo docker ...` or a properly configured
rootless Docker setup.

## 13.3 Install Docker Desktop on macOS

1.  Check your architecture with `uname -m`.
2.  Download the matching installer from [Docker Desktop for
    Mac](https://docs.docker.com/desktop/setup/install/mac-install/).
3.  Open the `.dmg` file.
4.  Drag Docker into Applications.
5.  Open Docker and complete the setup prompts.
6.  Wait until Docker Desktop reports that its engine is running.

Verify:

``` bash
docker --version
docker compose version
docker version
docker run hello-world
```

Notes:

-   Docker Desktop must be running before normal Docker CLI commands can
    communicate with its engine.
-   Docker Desktop manages the Linux VM; you generally do not need to
    create or manage that VM yourself.
-   File sharing and filesystem performance can differ from native
    Linux.
-   Docker Desktop licensing depends on the type and scale of use. Check
    current subscription terms.

## 13.4 Install Docker Desktop on Windows

For most developers who want Linux containers, Docker Desktop with the
WSL 2 backend is the recommended starting point.

### Step 1: Check Windows and virtualization

Open PowerShell:

``` powershell
winver
wsl --status
```

Ensure hardware virtualization is enabled in UEFI/BIOS. Check Docker
Desktop's current Windows edition, version, memory, and WSL
requirements.

### Step 2: Install or update WSL

Open PowerShell as Administrator:

``` powershell
wsl --install
```

Restart Windows if requested. Update WSL:

``` powershell
wsl --update
wsl --list --verbose
```

If a Linux distribution is using WSL 1 and should use WSL 2:

``` powershell
wsl --set-version Ubuntu 2
```

Replace `Ubuntu` with the exact distribution name shown by
`wsl --list --verbose`.

### Step 3: Install Docker Desktop

Follow the [official Windows installation
guide](https://docs.docker.com/desktop/setup/install/windows-install/),
download the installer, and run it.

### Step 4: Configure WSL integration

In Docker Desktop:

1.  Open **Settings**.
2.  Go to **Resources → WSL Integration** (the exact menu can vary).
3.  Enable integration for the Linux distribution you use.
4.  Apply changes and restart Docker Desktop if prompted.

### Step 5: Verify

From PowerShell or the integrated WSL terminal:

``` powershell
docker --version
docker compose version
docker version
docker run hello-world
```

If Docker works in PowerShell but not inside a WSL distribution, check
that WSL integration is enabled for that distribution.

## 13.5 First verification checklist

Run after installation:

``` bash
docker --version
docker version
docker info
docker compose version
docker run hello-world
docker ps
docker ps -a
docker image ls
```

Expected result: `docker run hello-world` prints a message confirming
Docker was able to download an image and run a container.

If `docker version` shows only Client information and reports a server
connection error, the Docker Engine may not be running or the CLI may be
using the wrong Docker context.

## 13.6 Run your first practical container

Start an NGINX web server:

``` bash
docker run -d \
  --name my-nginx \
  -p 8080:80 \
  nginx
```

  Option              Meaning
  ------------------- ----------------------------------------------
  `-d`                Run in the background (detached mode).
  `--name my-nginx`   Give the container a memorable name.
  `-p 8080:80`        Map host port 8080 to container port 80.
  `nginx`             Image to run; Docker downloads it if needed.

Open:

``` text
http://localhost:8080
```

Useful commands:

``` bash
docker ps
docker logs my-nginx
docker exec -it my-nginx sh
docker stop my-nginx
docker rm my-nginx
```

The NGINX image remains on your machine after the container is removed.
Remove the image separately if you no longer need it:

``` bash
docker image rm nginx
```

## 13.7 Common installation problems

  ---------------------------------------------------------------------------------------
  Problem                       Possible reason         What to check
  ----------------------------- ----------------------- ---------------------------------
  `docker: command not found`   CLI is not installed or Recheck installation and terminal
                                not on `PATH`.          `PATH`; reopen the terminal.

  Cannot connect to Docker      Engine is stopped or    On Linux, check
  daemon                        CLI targets the wrong   `sudo systemctl status docker`;
                                context.                on Desktop, start Docker Desktop.

  Permission denied on          Current Linux user      Use `sudo` or review Docker group
  `/var/run/docker.sock`        lacks socket            security implications.
                                permission.             

  WSL integration not working   WSL is outdated or      Run `wsl --update`, check
                                distribution is not     `wsl --list --verbose`, and
                                enabled in Desktop.     review Desktop integration
                                                        settings.

  Virtualization error          Hardware virtualization Check UEFI/BIOS virtualization
                                is disabled or          settings and platform
                                unavailable.            requirements.

  Port already allocated        Another process is      Choose another host port, such as
                                listening on the host   `-p 8081:80`.
                                port.                   

  Image pull fails              Network, DNS, proxy,    Check connectivity, proxy
                                registry                configuration, registry login,
                                authentication, or      and the error details.
                                rate-limit issue.       

  Container exits immediately   Main process completed  Run `docker ps -a` and inspect
                                or failed.              `docker logs CONTAINER`.
  ---------------------------------------------------------------------------------------

## 13.8 Official installation references

-   [Install Docker Engine](https://docs.docker.com/engine/install/)
-   [Install Docker Engine on
    Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
-   [Install Docker Desktop on
    macOS](https://docs.docker.com/desktop/setup/install/mac-install/)
-   [Install Docker Desktop on
    Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
-   [Install Docker Desktop on
    Ubuntu](https://docs.docker.com/desktop/setup/install/linux/ubuntu/)
-   [Docker post-installation steps for
    Linux](https://docs.docker.com/engine/install/linux-postinstall/)
-   [Microsoft: Install
    WSL](https://learn.microsoft.com/windows/wsl/install)
-   [Docker Desktop system
    requirements](https://docs.docker.com/desktop/setup/install/)

------------------------------------------------------------------------

# 14. Hands-on: package a Flask app

This section demonstrates two approaches:

1.  `docker commit` to understand how a container's filesystem changes
    can be captured.
2.  A Dockerfile to build a repeatable application image. This is the
    recommended approach.

## 14.1 Create a Flask application

Create the project:

``` bash
mkdir simple_app
cd simple_app
```

Create `app.py`:

``` python
from flask import Flask

app = Flask(__name__)


@app.get("/")
def hello_world():
    return "<h1>Hello, World!</h1>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

The `0.0.0.0` binding is important: it allows connections to the
application through the container's network interface.

## 14.2 Experiment with `docker commit`

> This is a learning exercise. For normal application development, use a
> Dockerfile (Section 14.3). A commit captures container filesystem
> changes and selected configuration; it does not save a running process
> or volume contents.

Start a container with a published port:

``` bash
docker run -dit \
  --name python-container \
  -p 5000:5000 \
  python:3.12-slim \
  sleep infinity
```

Install Flask inside it:

``` bash
docker exec -it python-container sh
```

Inside the container:

``` bash
pip install Flask==3.1.3
mkdir -p /app
exit
```

Copy the application file from the host:

``` bash
docker cp ./app.py python-container:/app/app.py
```

Start the Flask process inside the container:

``` bash
docker exec -d python-container python /app/app.py
```

Create a new image from the container:

``` bash
docker commit \
  --change='WORKDIR /app' \
  --change='EXPOSE 5000' \
  --change='CMD ["python", "app.py"]' \
  python-container \
  flask-app:commit-demo
```

Run a new container from the committed image:

``` bash
docker run --rm \
  --name flask-commit-demo \
  -p 5001:5000 \
  flask-app:commit-demo
```

Open:

``` text
http://localhost:5001
```

Clean up:

``` bash
docker rm -f python-container
```

### What `docker commit` does and does not do

-   Captures changes in the container's writable filesystem layer.
-   Can apply selected configuration changes using `--change`.
-   Does not capture the process state of a running application.
-   Does not include data stored in mounted volumes.
-   Is not a substitute for a reproducible Dockerfile.

## 14.3 Build the image with a Dockerfile (recommended)

Create a separate project:

``` bash
mkdir simple_app_v2
cd simple_app_v2
```

Project structure:

``` text
simple_app_v2/
├── app.py
├── requirements.txt
├── Dockerfile
└── .dockerignore
```

`app.py`:

``` python
from flask import Flask

app = Flask(__name__)


@app.get("/")
def hello_world():
    return "<h1>Hello from a Dockerfile-built image!</h1>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

`requirements.txt`:

``` text
Flask==3.1.3
```

`Dockerfile`:

``` dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
```

`.dockerignore`:

``` text
.git
.venv
__pycache__
*.py[cod]
.env
.pytest_cache
```

Build:

``` bash
docker build -t flask-app:v2.0 .
```

List images:

``` bash
docker image ls
```

Run:

``` bash
docker run --rm \
  --name flask-app-v2 \
  -p 5000:5000 \
  flask-app:v2.0
```

Open:

``` text
http://localhost:5000
```

### Why the Dockerfile approach is better

-   The build steps are documented and repeatable.
-   Dependencies are installed during the build.
-   Docker can reuse cached layers.
-   The image can be rebuilt by another developer or CI system.
-   Changes can be reviewed and version-controlled.

------------------------------------------------------------------------

# 15. Hands-on: Flask with PostgreSQL

This exercise combines Flask, Flask-SQLAlchemy, PostgreSQL, Psycopg,
Docker, and Docker Compose.

## 15.1 Architecture

``` text
Browser / API client
        |
        | http://localhost:5000
        v
+--------------------------+
| Flask container          |
|                          |
| Flask + SQLAlchemy       |
| Psycopg 3                |
+--------------------------+
        |
        | postgres:5432
        | Docker Compose network
        v
+--------------------------+
| PostgreSQL container     |
|                          |
| Database: student_db     |
| Named volume: postgres_data
+--------------------------+
```

Important networking rule:

-   Flask running directly on your host machine connects to PostgreSQL
    using `localhost:5432`.
-   Flask running inside Compose connects using the PostgreSQL **service
    name**, such as `postgres:5432`.
-   Inside a container, `localhost` refers to that same container, not
    another container.

## 15.2 Project structure

Create:

``` bash
mkdir web_app_v2
cd web_app_v2
```

Use this structure:

``` text
web_app_v2/
├── app.py
├── requirements.txt
├── Dockerfile
├── compose.yaml
├── .env
└── .dockerignore
```

## 15.3 Create the Flask application

Create `app.py`:

``` python
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, url_for
from flask.views import MethodView
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape
from sqlalchemy.exc import SQLAlchemyError


load_dotenv()

app = Flask(__name__)

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is not configured")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ------------------------------------------------------------
# Model
# ------------------------------------------------------------

class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
        }


# ------------------------------------------------------------
# Home
# ------------------------------------------------------------

class Home(MethodView):
    def get(self):
        return """
        <h1>Student Management System</h1>
        <ul>
            <li><a href="/students">List students</a></li>
            <li><a href="/students/new">Add a student</a></li>
        </ul>
        """


# ------------------------------------------------------------
# Student views
# ------------------------------------------------------------

class StudentView(MethodView):

    @staticmethod
    def wants_json():
        return (
            request.is_json
            or request.accept_mimetypes.best == "application/json"
        )

    @staticmethod
    def validate_data():
        if request.is_json:
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                return None, (jsonify(error="JSON body must be an object"), 400)
        else:
            payload = request.form

        name = payload.get("name")
        age = payload.get("age")

        if not isinstance(name, str) or not name.strip():
            return None, (jsonify(error="A valid name is required"), 400)

        try:
            age = int(age)
        except (TypeError, ValueError):
            return None, (jsonify(error="Age must be an integer"), 400)

        if not 10 <= age <= 25:
            return None, (jsonify(error="Age must be between 10 and 25"), 400)

        return (name.strip(), age), None

    def get(self, id=None, action=None):
        if action == "new":
            return self.student_form()

        if action == "edit":
            student = db.session.get(Student, id)
            if student is None:
                return "Student not found", 404
            return self.student_form(student)

        if id is None:
            return self.list_students()

        return self.get_student(id)

    def post(self, id=None, action=None):
        if action == "new":
            return self.create_student()

        if action == "edit":
            return self.update_student(id)

        if action == "delete":
            return self.delete_student(id)

        return jsonify(error="Invalid operation"), 400

    def put(self, id):
        return self.update_student(id, json_only=True)

    def delete(self, id):
        return self.delete_student(id, json_only=True)

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    def create_student(self):
        data, error = self.validate_data()
        if error:
            return error

        name, age = data

        try:
            student = Student(name=name, age=age)
            db.session.add(student)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Could not create student")
            return jsonify(error="Could not create student"), 500

        if request.is_json:
            return jsonify(
                message="Student created successfully",
                student=student.to_dict(),
            ), 201

        return redirect(url_for("student", id=student.id))

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def update_student(self, id, json_only=False):
        student = db.session.get(Student, id)
        if student is None:
            return jsonify(error="Student not found"), 404

        if json_only and not request.is_json:
            return jsonify(error="JSON body is required"), 400

        data, error = self.validate_data()
        if error:
            return error

        name, age = data

        try:
            student.name = name
            student.age = age
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Could not update student")
            return jsonify(error="Could not update student"), 500

        if request.is_json:
            return jsonify(
                message="Student updated successfully",
                student=student.to_dict(),
            )

        return redirect(url_for("student", id=id))

    # --------------------------------------------------------
    # Delete
    # --------------------------------------------------------

    def delete_student(self, id, json_only=False):
        student = db.session.get(Student, id)
        if student is None:
            return jsonify(error="Student not found"), 404

        if json_only and not request.is_json:
            return jsonify(error="JSON body is required"), 400

        try:
            db.session.delete(student)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Could not delete student")
            return jsonify(error="Could not delete student"), 500

        if json_only:
            return jsonify(
                message="Student deleted successfully",
                student_id=id,
            )

        return redirect(url_for("student"))

    # --------------------------------------------------------
    # HTML form
    # --------------------------------------------------------

    def student_form(self, student=None):
        editing = student is not None
        title = "Edit student" if editing else "Add student"

        name = escape(student.name) if editing else ""
        age = student.age if editing else ""

        action = (
            url_for("student", id=student.id, action="edit")
            if editing
            else url_for("student", action="new")
        )

        return f"""
        <h1>{title}</h1>
        <form method="POST" action="{action}">
            <label for="name">Name</label><br>
            <input id="name" name="name" value="{name}"
                   maxlength="100" required><br><br>

            <label for="age">Age</label><br>
            <input id="age" name="age" type="number"
                   value="{age}" min="10" max="25" required><br><br>

            <button type="submit">{"Update" if editing else "Create"}</button>
        </form>
        <p><a href="/students">Back to students</a></p>
        """

    # --------------------------------------------------------
    # Read all
    # --------------------------------------------------------

    def list_students(self):
        students = db.session.execute(
            db.select(Student).order_by(Student.id)
        ).scalars().all()

        if self.wants_json():
            return jsonify([student.to_dict() for student in students])

        rows = ""
        for student in students:
            rows += f"""
            <tr>
                <td>{student.id}</td>
                <td>{escape(student.name)}</td>
                <td>{student.age}</td>
                <td>
                    <a href="/students/{student.id}">View</a> |
                    <a href="/students/{student.id}/edit">Edit</a> |
                    <form method="POST"
                          action="/students/{student.id}/delete"
                          style="display:inline">
                        <button type="submit">Delete</button>
                    </form>
                </td>
            </tr>
            """

        return f"""
        <h1>All Students</h1>
        <p><a href="/students/new">Add student</a></p>
        <table border="1" cellpadding="8">
            <tr><th>ID</th><th>Name</th><th>Age</th><th>Actions</th></tr>
            {rows}
        </table>
        <p><a href="/">Home</a></p>
        """

    # --------------------------------------------------------
    # Read one
    # --------------------------------------------------------

    def get_student(self, id):
        student = db.session.get(Student, id)

        if student is None:
            return jsonify(error="Student not found"), 404

        if self.wants_json():
            return jsonify(student.to_dict())

        return f"""
        <h1>Student details</h1>
        <p>ID: {student.id}</p>
        <p>Name: {escape(student.name)}</p>
        <p>Age: {student.age}</p>
        <p><a href="/students/{id}/edit">Edit</a></p>
        <p><a href="/students">Back to students</a></p>
        """


# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------

app.add_url_rule(
    "/",
    view_func=Home.as_view("home"),
    methods=["GET"],
)

student_view = StudentView.as_view("student")

app.add_url_rule(
    "/students",
    view_func=student_view,
    methods=["GET"],
)

app.add_url_rule(
    "/students/new",
    view_func=student_view,
    defaults={"action": "new"},
    methods=["GET", "POST"],
)

app.add_url_rule(
    "/students/<int:id>",
    view_func=student_view,
    methods=["GET", "PUT", "DELETE"],
)

app.add_url_rule(
    "/students/<int:id>/edit",
    view_func=student_view,
    defaults={"action": "edit"},
    methods=["GET", "POST"],
)

app.add_url_rule(
    "/students/<int:id>/delete",
    view_func=student_view,
    defaults={"action": "delete"},
    methods=["POST"],
)


# ------------------------------------------------------------
# Development entry point
# ------------------------------------------------------------

if __name__ == "__main__":
    # Convenience for this learning project: creates missing tables.
    # It does not alter existing table schemas.
    with app.app_context():
        db.create_all()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
```

### Notes about the application

-   `Student` is both the SQLAlchemy model and the object used by the
    views. There is no separate in-memory dictionary.
-   `db.create_all()` creates missing tables, but does not add or alter
    columns in existing tables.
-   Flask-Migrate is installed for schema changes. Use migrations for
    ongoing schema evolution.
-   The age range of 10--25 is a validation rule for this example;
    change it to suit your application.
-   The built-in Flask development server is suitable for learning, not
    production deployment.

## 15.4 Create `requirements.txt`

``` text
Flask==3.1.3
Flask-Migrate==4.1.0
Flask-SQLAlchemy==3.1.1
psycopg[binary]==3.3.8
python-dotenv==1.2.4
```

**Important Psycopg detail:** Use `psycopg[binary]` when using the
SQLAlchemy URL `postgresql+psycopg://...` in this example. Installing
only `psycopg` may leave the container without a usable libpq
implementation, causing an error such as
`ImportError: no pq wrapper available`.

Install locally, if running Flask outside Docker:

``` bash
pip install -r requirements.txt
```

## 15.5 Configure environment variables

Create `.env`:

``` env
DATABASE_URL=postgresql+psycopg://admin:admin123@localhost:5432/student_db
FLASK_DEBUG=1
```

This URL is for Flask running directly on your host machine.

If Flask runs in Docker Compose, the hostname must be the PostgreSQL
service name. The Compose configuration below supplies the correct URL
to the app container.

Add `.env` to `.gitignore`:

``` text
.env
.venv/
__pycache__/
*.py[cod]
```

Do not commit real credentials to source control.

## 15.6 Start PostgreSQL as a standalone Docker container

Pull the image:

``` bash
docker pull postgres:18.6-alpine
```

Run it:

``` bash
docker run -d \
  --name postgres-db \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=admin123 \
  -e POSTGRES_DB=student_db \
  -p 5432:5432 \
  -v postgres-data:/var/lib/postgresql \
  postgres:18.6-alpine
```

**PostgreSQL 18 note:** The official PostgreSQL 18 image uses a
version-specific data directory below `/var/lib/postgresql/18/docker`.
Mounting the parent `/var/lib/postgresql` path is the recommended
approach for this image layout. PostgreSQL 17 and older commonly use
`/var/lib/postgresql/data`; do not blindly reuse the older mount path
for PostgreSQL 18.

Check the container:

``` bash
docker ps
docker logs postgres-db
```

Connect:

``` bash
docker exec -it postgres-db \
  psql -U admin -d student_db
```

Inside `psql`:

``` sql
SELECT current_database();
SELECT current_user;
\dt
\q
```

If the database is not ready immediately after starting, wait for it to
become ready before connecting.

## 15.7 Run Flask directly on the host

When PostgreSQL is in Docker but Flask runs on your host, use:

``` env
DATABASE_URL=postgresql+psycopg://admin:admin123@localhost:5432/student_db
```

Run:

``` bash
python -m app
```

The application creates missing tables when run through this entry point
because it calls `db.create_all()`.

## 15.8 Run Flask and PostgreSQL using Docker Compose

For a multi-container application, Compose is the recommended learning
workflow.

Create `Dockerfile`:

``` dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "-m", "app"]
```

Create `.dockerignore`:

``` text
.git
.venv
__pycache__
*.py[cod]
.pytest_cache
.env
.env.*
```

Create `.env` for Compose variable substitution:

``` env
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin123
POSTGRES_DB=student_db
FLASK_DEBUG=1
```

Create `compose.yaml`:

``` yaml
services:
  app:
    build: .
    container_name: web_app_v2
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-admin}:${POSTGRES_PASSWORD:-admin123}@postgres:5432/${POSTGRES_DB:-student_db}
      FLASK_DEBUG: ${FLASK_DEBUG:-1}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  postgres:
    image: postgres:18.6-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-admin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-admin123}
      POSTGRES_DB: ${POSTGRES_DB:-student_db}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql
    healthcheck:
      test:
        - CMD-SHELL
        - pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

volumes:
  postgres_data:
```

### Why this Compose file works

1.  Compose creates a network for the project automatically.
2.  The Flask service connects to PostgreSQL using the service hostname
    `postgres`.
3.  `depends_on` with `condition: service_healthy` waits for
    PostgreSQL's health check before starting Flask.
4.  The named volume keeps PostgreSQL data outside the container's
    writable layer.
5.  The app image installs `psycopg[binary]`, so the Psycopg 3 driver
    has its binary implementation available.
6.  The `version` field is intentionally omitted because modern Docker
    Compose uses the Compose Specification and treats the old top-level
    `version` field as obsolete.

### Start the application

``` bash
docker compose up --build
```

Or run it in the background:

``` bash
docker compose up -d --build
```

Check service status:

``` bash
docker compose ps
```

Follow application logs:

``` bash
docker compose logs -f app
```

Follow PostgreSQL logs:

``` bash
docker compose logs -f postgres
```

Connect to PostgreSQL:

``` bash
docker compose exec postgres \
  psql -U admin -d student_db
```

Open the application:

``` text
http://localhost:5000
```

### Stop the application

``` bash
docker compose down
```

This removes the Compose containers and network but keeps the named
database volume.

To remove the database volume as well:

``` bash
docker compose down -v
```

**Warning:** `down -v` deletes the PostgreSQL data stored in the Compose
volume. Use it only when you intentionally want to reset the database.

## 15.9 Database schema creation and migrations

For this learning application, `db.create_all()` runs when the app
starts through `python -m app`. It creates tables that do not exist.

However, `db.create_all()` does not alter existing tables when your
model changes.

For schema evolution, use Flask-Migrate:

Initialize migrations once:

``` bash
flask --app app db init
```

Generate a migration after changing models:

``` bash
flask --app app db migrate -m "Create students table"
```

Apply it:

``` bash
flask --app app db upgrade
```

When using Compose, commands can be run inside the app container:

``` bash
docker compose exec app flask --app app db migrate -m "Create students table"
docker compose exec app flask --app app db upgrade
```

Run `db init` only once, and only if the `migrations/` directory does
not already exist.

For a production deployment, apply migrations as a controlled deployment
step rather than automatically running `db.create_all()` at application
startup.

## 15.10 Test the CRUD API

  Operation         HTTP method   Endpoint
  ----------------- ------------- -----------------
  List students     GET           `/students`
  Get one student   GET           `/students/1`
  Create student    POST          `/students/new`
  Update student    PUT           `/students/1`
  Delete student    DELETE        `/students/1`

Create:

``` bash
curl -i -X POST http://localhost:5000/students/new \
  -H "Content-Type: application/json" \
  -d '{"name": "Amit", "age": 18}'
```

List:

``` bash
curl -i http://localhost:5000/students \
  -H "Accept: application/json"
```

Get one:

``` bash
curl -i http://localhost:5000/students/1 \
  -H "Accept: application/json"
```

Update:

``` bash
curl -i -X PUT http://localhost:5000/students/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Rahul", "age": 20}'
```

Delete:

``` bash
curl -i -X DELETE http://localhost:5000/students/1 \
  -H "Content-Type: application/json" \
  -d '{}'
```

The browser-based HTML forms are also available from the home page.

------------------------------------------------------------------------

# 16. Troubleshooting

## 16.1 `relation "students" does not exist`

**Meaning:** The application connected to PostgreSQL, but the table is
missing in the database/schema it queried.

For this learning app, start the app through its configured entry point
so `db.create_all()` runs:

``` bash
python -m app
```

Or create the tables explicitly:

``` bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

For a migration-managed schema, run:

``` bash
flask --app app db upgrade
```

Also verify that Flask is connected to the database you expect.

## 16.2 `ImportError: no pq wrapper available`

**Meaning:** Psycopg 3 is installed, but no usable implementation of its
PostgreSQL protocol layer is available in the Python environment.

Use this in `requirements.txt`:

``` text
psycopg[binary]==3.3.8
```

Then rebuild the app image:

``` bash
docker compose build --no-cache app
docker compose up
```

Do not assume that installing only `psycopg` provides the binary
implementation.

## 16.3 Flask container cannot connect to PostgreSQL

Check the URL.

When Flask runs on the host:

``` text
postgresql+psycopg://admin:admin123@localhost:5432/student_db
```

When Flask runs in Compose:

``` text
postgresql+psycopg://admin:admin123@postgres:5432/student_db
```

Inside a container, `localhost` means that same container. Use the
Compose service name to reach another service.

## 16.4 `Connection refused`

Possible causes:

-   PostgreSQL is not running.
-   PostgreSQL is still initializing.
-   The hostname or port is wrong.
-   The application is not on the same Docker network.
-   The database is listening on a different port.

Check:

``` bash
docker compose ps
docker compose logs postgres
docker compose logs app
```

## 16.5 Port already allocated

If host port `5432` or `5000` is already in use, change the host side of
the mapping.

For example:

``` yaml
ports:
  - "5433:5432"
```

The app container should still connect to `postgres:5432`; only host
access uses `localhost:5433`.

## 16.6 Flask returns 405 Method Not Allowed

A 405 response means the URL exists but does not accept the HTTP method
used.

Inspect routes:

``` bash
flask --app app routes
```

Make sure the route accepts the method and the `MethodView` has the
corresponding handler. For example, a browser form that submits to
`/students/new` requires POST to be registered for that route.

## 16.7 Container exits immediately

A container stays alive only while its main process is running.

Inspect:

``` bash
docker ps -a
docker logs CONTAINER_NAME
docker inspect CONTAINER_NAME
```

For a long-running application, use a foreground process as the
container's `CMD` or `ENTRYPOINT`. Do not start the main application as
an untracked background process.

## 16.8 Compose says `version` is obsolete

Remove the top-level field:

``` yaml
version: "1.0"
```

Modern Compose uses the Compose Specification and ignores the old
`version` field.

## 16.9 PostgreSQL data disappeared

Check whether the container was recreated without a persistent volume,
or whether the volume was removed.

``` bash
docker volume ls
docker volume inspect VOLUME_NAME
```

Avoid `docker compose down -v` unless you intentionally want to delete
the database volume.

## 16.10 PostgreSQL Alpine locale warning

A minimal Alpine image may log a warning such as:

``` text
sh: locale: not found
WARNING: no usable system locales were found
```

This warning during initialization is not necessarily a startup failure.
Check the later log lines for:

``` text
database system is ready to accept connections
```

------------------------------------------------------------------------

# 17. Recommended learning path

After understanding the fundamentals, study these topics in roughly this
order:

1.  **Images and layers** --- image layers, manifests, tags, digests,
    and build cache.
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

## Practical exercises

-   [ ] Run `hello-world` and inspect the exited container.
-   [ ] Pull two tags of the same image and compare them.
-   [ ] Run an interactive Python container.
-   [ ] Run NGINX and publish a host port.
-   [ ] Inspect a container using `docker inspect`.
-   [ ] View logs using `docker logs`.
-   [ ] Create a user-defined network and connect two containers.
-   [ ] Create a named volume and verify that data survives container
    replacement.
-   [ ] Build the Flask image using a Dockerfile.
-   [ ] Run Flask and PostgreSQL with Docker Compose.
-   [ ] Rebuild the Flask image after changing `requirements.txt`.
-   [ ] Practice database migrations.
-   [ ] Add a Redis service to the Compose project.
-   [ ] Add a health check to the Flask application.
-   [ ] Run the Flask application as a non-root user.

------------------------------------------------------------------------

# 18. References

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
-   [Docker Hub](https://hub.docker.com/) --- image repositories and
    tags.
-   [Official PostgreSQL image](https://hub.docker.com/_/postgres) ---
    supported image variants and usage.
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

# Quick recap

-   Docker helps build, package, distribute, and run applications in
    containers.
-   Linux containers use kernel features such as namespaces and cgroups.
-   Linux containers share the host kernel; VMs run separate guest
    operating systems.
-   Images are layered templates; containers are instances of images.
-   The Docker ecosystem includes the CLI, daemon, Engine API,
    containerd, runc, images, registries, networks, volumes, and
    Compose.
-   Use Dockerfiles for repeatable image builds.
-   Use volumes or bind mounts for data that must outlive a container.
-   Use Compose to define multi-container development environments.
-   In Compose, services reach each other using service names, not
    `localhost`.
-   Containers and VMs are complementary and are often used together.
