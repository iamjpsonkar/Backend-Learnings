# Hints — Reverse Proxy

---

## Hint 1 — How Traefik Docker labels work

Traefik reads Docker labels from running containers. The label format:
```
traefik.http.routers.<ROUTER_NAME>.rule=<RULE>
traefik.http.services.<SERVICE_NAME>.loadbalancer.server.port=<PORT>
```

Router names and service names are arbitrary but must be consistent within a container's labels.

---

## Hint 2 — Testing with custom Host headers

When using `Host()` rules, you must send the Host header:
```bash
curl -H "Host: api.localhost" http://localhost/health
```

Or add to /etc/hosts for convenience:
```
127.0.0.1 api.localhost
```
Then: `curl http://api.localhost/health`

---

## Hint 3 — Strip prefix pattern

The strip prefix middleware removes the prefix before forwarding:
```
Request:  GET /v1/health
After strip: GET /health  ← forwarded to backend
```

```yaml
labels:
  - "traefik.http.routers.api-v1.rule=PathPrefix(`/v1/`)"
  - "traefik.http.routers.api-v1.middlewares=strip-v1@docker"
  - "traefik.http.middlewares.strip-v1.stripprefix.prefixes=/v1"
```

---

## Hint 4 — Middleware chaining

Apply multiple middlewares to a router (comma-separated):
```yaml
- "traefik.http.routers.api.middlewares=ratelimit@docker,auth@docker"
```

---

## Hint 5 — Dynamic config file

Instead of labels, you can use a `dynamic.yaml` config file mounted in Traefik:
```yaml
# docker/configs/traefik/dynamic.yaml
http:
  middlewares:
    my-auth:
      basicAuth:
        users:
          - "admin:$2y$05$..."
  routers:
    dashboard:
      rule: "Host(`traefik.localhost`)"
      service: api@internal
      middlewares:
        - my-auth
```

Traefik hot-reloads dynamic config — no restart needed.
