# Reverse Proxy — Intermediate

**Difficulty**: Intermediate
**Profile**: `core apps`
**Time estimate**: 60–90 minutes

---

## Scenario

Traefik is running as the platform reverse proxy. Your job: configure routing rules, TLS, and middleware for the sample API.

---

## Setup

```bash
./run.sh start core apps

# Traefik dashboard: http://localhost:8080
# Sample API direct: http://localhost:8000
# Via Traefik: http://localhost (port 80)
```

---

## Tasks

### Task 1 — Explore Traefik dashboard

Open http://localhost:8080

Find:
- How many services are registered?
- What routers exist?
- What middleware is configured?
- How does Traefik discover Docker services (check providers)?

### Task 2 — Add a custom router

In docker-compose.yml (or a new compose override), add Traefik labels to sample-api:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.api.rule=Host(`api.localhost`)"
  - "traefik.http.routers.api.entrypoints=web"
  - "traefik.http.services.api.loadbalancer.server.port=8000"
```

Test with:
```bash
curl -H "Host: api.localhost" http://localhost/health
```

### Task 3 — Path-based routing

Add a second router that routes `/v1/` prefix to the same backend:

```yaml
- "traefik.http.routers.api-v1.rule=PathPrefix(`/v1/`)"
- "traefik.http.middlewares.strip-v1.stripprefix.prefixes=/v1"
- "traefik.http.routers.api-v1.middlewares=strip-v1"
```

Test:
```bash
curl http://localhost/v1/health
# Should return same as curl http://localhost/health
```

### Task 4 — Rate limiting middleware

Add a rate limit of 10 requests per second:

```yaml
- "traefik.http.middlewares.ratelimit.ratelimit.average=10"
- "traefik.http.middlewares.ratelimit.ratelimit.burst=20"
- "traefik.http.routers.api.middlewares=ratelimit"
```

Test with a burst of requests. What happens at the limit?

### Task 5 — Basic auth middleware

Protect the Traefik dashboard with basic auth.

Generate a hash:
```bash
htpasswd -nb admin secret123
# admin:$2y$...
```

Add to Traefik static config or dynamic config:
```yaml
http:
  middlewares:
    dashboard-auth:
      basicAuth:
        users:
          - "admin:$2y$..."
```

### Task 6 — Health check in Traefik

Add a health check for the backend:

```yaml
- "traefik.http.services.api.loadbalancer.healthcheck.path=/health"
- "traefik.http.services.api.loadbalancer.healthcheck.interval=10s"
```

Verify in the Traefik dashboard that the service shows as healthy.

---

## Success criteria

- [ ] Traefik dashboard explored and services counted
- [ ] Host-based routing working via `api.localhost`
- [ ] Path-based routing with prefix stripping working
- [ ] Rate limiting configured and tested
- [ ] Basic auth added to at least one route
- [ ] Health check visible in Traefik dashboard
