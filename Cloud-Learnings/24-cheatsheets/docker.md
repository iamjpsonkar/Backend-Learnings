← [Previous: Terraform](./terraform.md) | [Home](../README.md) | [Next: Linux →](./linux.md)

---

# Docker Cheatsheet

```bash
# ── BUILD ──────────────────────────────────────────────────────────────────────
docker build -t myapp:latest .                     # build from Dockerfile in current dir
docker build -t myapp:v1.2.3 -f Dockerfile.prod .  # specific Dockerfile
docker build --no-cache -t myapp:latest .          # bypass layer cache
docker build --build-arg ENV=prod -t myapp:latest . # pass build arg
docker build --platform linux/amd64 -t myapp:latest .  # force platform (M1/M2 Mac)

# Multi-stage: target specific stage
docker build --target builder -t myapp:build .

# ── RUN ────────────────────────────────────────────────────────────────────────
docker run myapp:latest                            # run (blocking)
docker run -d myapp:latest                         # detached (background)
docker run -it myapp:latest /bin/sh                # interactive shell
docker run --rm myapp:latest                       # auto-remove on exit

docker run -p 8080:8080 myapp:latest               # port mapping (host:container)
docker run -v $(pwd)/data:/app/data myapp:latest   # bind mount
docker run -v myapp-data:/app/data myapp:latest    # named volume

docker run -e DB_HOST=localhost -e DB_PORT=5432 myapp:latest  # env vars
docker run --env-file .env myapp:latest            # env file

docker run --name my-container myapp:latest        # named container
docker run --network my-network myapp:latest       # specific network
docker run --memory=512m --cpus=0.5 myapp:latest   # resource limits

# ── CONTAINERS ─────────────────────────────────────────────────────────────────
docker ps                                          # running containers
docker ps -a                                       # all (including stopped)
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"

docker stop my-container                           # graceful stop (SIGTERM)
docker kill my-container                           # force kill (SIGKILL)
docker rm my-container                             # remove stopped container
docker rm -f my-container                          # force remove (even if running)

docker logs my-container                           # all logs
docker logs my-container -f                        # follow
docker logs my-container --tail=50                 # last 50 lines
docker logs my-container --since=1h                # last 1 hour

docker exec -it my-container /bin/sh               # exec in running container
docker exec my-container env                       # print env vars
docker cp my-container:/app/logs/error.log ./      # copy file from container

docker stats                                       # live CPU/memory usage
docker inspect my-container                        # full JSON details
docker inspect my-container --format '{{.State.Status}}'

# ── IMAGES ─────────────────────────────────────────────────────────────────────
docker images                                      # list images
docker pull nginx:1.25                             # pull from registry
docker push myrepo/myapp:v1.2.3                   # push to registry
docker tag myapp:latest myrepo/myapp:v1.2.3       # add tag
docker rmi myapp:old                               # remove image
docker history myapp:latest                        # layer history
docker inspect myapp:latest                        # image details

# ECR authentication + push
aws ecr get-login-password --region us-east-1 \
    | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/order-api:latest

# ── VOLUMES ────────────────────────────────────────────────────────────────────
docker volume create myapp-data
docker volume ls
docker volume inspect myapp-data
docker volume rm myapp-data
docker volume prune                                # remove unused volumes

# ── NETWORKS ───────────────────────────────────────────────────────────────────
docker network create my-network
docker network ls
docker network inspect my-network
docker network connect my-network my-container
docker network disconnect my-network my-container

# ── DOCKER COMPOSE ─────────────────────────────────────────────────────────────
docker compose up                                  # start all services
docker compose up -d                               # detached
docker compose up --build                          # rebuild images
docker compose up api db                           # start specific services only

docker compose down                                # stop and remove containers
docker compose down -v                             # also remove volumes
docker compose down --rmi all                      # also remove images

docker compose ps                                  # service status
docker compose logs api -f                         # follow specific service logs
docker compose exec api /bin/sh                    # exec in service container
docker compose restart api                         # restart specific service

docker compose pull                                # pull latest images
docker compose build api                           # build specific service
docker compose config                              # validate and print resolved config

# Run one-off command
docker compose run --rm api python manage.py migrate

# ── CLEANUP ────────────────────────────────────────────────────────────────────
docker system prune                                # remove unused: containers, networks, images
docker system prune -a                             # also remove unused images
docker system prune -a --volumes                   # also remove volumes
docker builder prune                               # clean build cache
docker image prune                                 # remove dangling images only

# ── USEFUL PATTERNS ────────────────────────────────────────────────────────────
# Size analysis
docker image ls --format "{{.Repository}}:{{.Tag}}\t{{.Size}}" | sort -k2 -h

# Find large layers
docker history myapp:latest --human --no-trunc | sort -k4 -h | tail -10

# Run shell as root in non-root container (debugging)
docker exec -u root -it my-container /bin/sh

# Test Dockerfile entrypoint override
docker run --rm --entrypoint /bin/sh myapp:latest -c "env && ls -la /app"
```

---

← [Previous: Terraform](./terraform.md) | [Home](../README.md) | [Next: Linux →](./linux.md)
