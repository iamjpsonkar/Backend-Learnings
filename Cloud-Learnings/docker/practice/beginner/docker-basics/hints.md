# Hints — Docker Basics

Read hints one at a time. Only move to the next hint if still stuck.

---

## Hint 1 — Python HTTP Server

Python has a built-in HTTP server. Use `http.server.BaseHTTPRequestHandler`:

```python
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # self.path contains the URL path
        # self.send_response(200) sends status
        # self.send_header("Content-Type", "application/json") sends header
        # self.end_headers() ends headers
        # self.wfile.write(b"content") sends body
        pass
```

---

## Hint 2 — Non-root User in Dockerfile

```dockerfile
RUN useradd -m -u 1001 appuser
USER appuser
```

The `useradd` must happen before `USER` instruction.

---

## Hint 3 — HEALTHCHECK Instruction

```dockerfile
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1
```

---

## Hint 4 — Keeping Image Small

Order matters in Dockerfile:
1. FROM python:3.12-slim  (not python:3.12 or python:latest)
2. WORKDIR /app
3. COPY server.py .
4. (no pip install needed — no packages)

---

## Hint 5 — Port in Python

```python
server = HTTPServer(("0.0.0.0", 8080), Handler)
server.serve_forever()
```

Must bind to `0.0.0.0`, not `127.0.0.1`, for Docker port mapping to work.
