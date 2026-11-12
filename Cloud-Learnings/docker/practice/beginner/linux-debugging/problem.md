# Linux Debugging — Beginner

**Difficulty**: Beginner
**Profile**: `core`
**Time estimate**: 30–45 minutes

---

## Scenario

A container is running but behaving unexpectedly. Your job is to investigate it using standard Linux tools — no restarting, no guessing.

---

## Setup

```bash
./run.sh start core
docker exec -it cloud-learnings-lab-nginx-1 sh
```

You are now inside a running Alpine Linux container.

---

## Tasks

### Task 1 — Who am I?

Find out:
- What user are you running as?
- What is the UID/GID?
- What groups do you belong to?

Commands to explore: `id`, `whoami`

### Task 2 — What is running?

Find all running processes inside the container.

Commands to explore: `ps aux`, `top`, `ps -ef`

### Task 3 — What ports are in use?

Find which ports the nginx process is listening on.

Commands to explore: `ss -tlnp`, `netstat -tlnp`

> Note: some tools may not be available in Alpine — work around it.

### Task 4 — Read the config

Find and display the nginx configuration file. Identify:
- The listening port
- The root directory
- Any custom headers

Commands to explore: `find`, `cat`, `grep`

### Task 5 — Check disk usage

Find how much space is available and which directories use the most space.

Commands to explore: `df -h`, `du -sh /*`

### Task 6 — Environment variables

List all environment variables set in the container. Find the `PATH` variable.

Commands to explore: `env`, `printenv`, `echo $PATH`

### Task 7 — File permissions

Find the nginx worker config. Check its permissions.

Who owns `/etc/nginx/nginx.conf`? Can the current user write to it?

Commands to explore: `ls -la`, `stat`

---

## Success criteria

You can answer all of the following without guessing:
- [ ] Container user and UID
- [ ] Number of running processes
- [ ] Port nginx is listening on
- [ ] Location of the nginx config file
- [ ] Available disk space (root partition)
- [ ] Value of the `NGINX_VERSION` env var (if set)
- [ ] Owner of `/etc/nginx/nginx.conf`
