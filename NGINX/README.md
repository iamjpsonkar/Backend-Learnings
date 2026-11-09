# NGINX with Docker and Node.js

Hands-on notes for learning NGINX as a static web server, reverse proxy, load balancer, and HTTPS/TLS termination point.

## Contents

1. [What is NGINX?](#1-what-is-nginx)
2. [Prerequisites](#2-prerequisites)
3. [Project structure](#3-project-structure)
4. [Serve static HTML](#4-serve-static-html)
5. [Reverse proxy to Node.js](#5-reverse-proxy-to-nodejs)
6. [Load balancing across Node.js containers](#6-load-balancing-across-nodejs-containers)
7. [HTTPS/TLS termination](#7-httpstls-termination)
8. [Useful commands and troubleshooting](#8-useful-commands-and-troubleshooting)
9. [Important concepts](#9-important-concepts)

---

## 1. What is NGINX?

NGINX is a web server that can also act as:

- A reverse proxy
- A load balancer
- An HTTP cache
- A TLS/SSL termination point
- A mail proxy

It uses an event-driven architecture and is commonly used to serve static files and route HTTP traffic to application servers.

### Common use cases

| Use case | Example |
|---|---|
| Static web server | Serve HTML, CSS, JavaScript, images |
| Reverse proxy | Forward requests to Node.js, Python, or Java services |
| Load balancer | Distribute requests across multiple backend instances |
| TLS termination | Handle HTTPS at the edge and proxy to an internal service |
| Caching | Cache eligible upstream responses |
| Rate limiting | Limit request rates to protect an application |

### Request flow

- **Static serving:** Browser → NGINX → static files
- **Reverse proxy:** Browser → NGINX → one backend
- **Load balancing:** Browser → NGINX → one of multiple backends
- **TLS termination:** Browser --HTTPS--> NGINX --HTTP--> backend

---

## 2. Prerequisites

Install or make sure you have:

- Docker Engine or Docker Desktop
- Docker Compose (optional)
- `curl`
- OpenSSL (needed for the self-signed certificate demo)

Check versions:

```bash
docker --version
docker compose version
curl --version
openssl version
```

**Where to run commands:** Unless a command says otherwise, run the Docker commands in this guide from the `NGINX/` directory (the directory containing `static-server-app/`, `reverse-proxy-app/`, and the other demo folders).

---

## 3. Project structure

The examples in this guide use this layout:

```text
NGINX/
├── README.md
├── static-server-app/
│   └── index.html
├── reverse-proxy-app/
│   ├── default.conf
│   └── server.js
├── load-balancer-app/
│   ├── default.conf
│   ├── server1.js
│   └── server2.js
└── ssl-tls-app/
    ├── certs/
    │   ├── nginx-selfsigned.crt
    │   └── nginx-selfsigned.key
    ├── default.conf
    └── server.js
```

The certificate files are generated locally in section 7. Do not commit private keys to Git.

---

## 4. Serve static HTML

NGINX can serve static files directly without a Node.js server.

### 4.1 Create the HTML page

`static-server-app/index.html`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NGINX Static Server</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      text-align: center;
      margin: 4rem auto;
    }
  </style>
</head>
<body>
  <h1>Hello, welcome to NGINX!</h1>
  <p>This HTML file is served directly by NGINX in Docker.</p>
</body>
</html>
```

### 4.2 Start NGINX and mount the local folder

Run from `NGINX/`:

```bash
docker run -d \
  --name static-nginx \
  -p 8080:80 \
  -v "$PWD/static-server-app:/usr/share/nginx/html:ro" \
  nginx:latest
```

The `:ro` suffix mounts the folder read-only inside the container. You can edit files locally; NGINX serves the updated files without rebuilding the image.

### 4.3 Test

```bash
curl -i http://localhost:8080
```

Open `http://localhost:8080` in your browser.

### 4.4 Clean up

```bash
docker rm -f static-nginx
```

---

## 5. Reverse proxy to Node.js

A reverse proxy receives a client request and forwards it to a backend service. The client communicates with NGINX rather than directly with Node.js.

### 5.1 Node.js application

`reverse-proxy-app/server.js`:

```javascript
const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello from the Node.js backend!');
});

server.listen(3000, '0.0.0.0', () => {
  console.log('Node.js server listening on port 3000');
});
```

The `0.0.0.0` bind address is important: it allows other containers on the Docker network to reach the server. Binding only to `127.0.0.1` would make it reachable only from inside its own container.

### 5.2 NGINX configuration

`reverse-proxy-app/default.conf`:

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://rp-node:3000;

        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

`rp-node` is the Node container name. Docker's user-defined bridge network provides DNS resolution for container names.

### 5.3 Create a network and start Node.js

Run from `NGINX/`:

```bash
docker network create reverse-proxy-network
```

```bash
docker run -d \
  --name rp-node \
  --network reverse-proxy-network \
  -v "$PWD/reverse-proxy-app:/app:ro" \
  -w /app \
  node:22-alpine \
  node server.js
```

The Node port is not published to the host. NGINX can still reach it over the shared Docker network.

### 5.4 Start NGINX

```bash
docker run -d \
  --name rp-nginx \
  --network reverse-proxy-network \
  -p 8080:80 \
  -v "$PWD/reverse-proxy-app/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:latest
```

### 5.5 Test

```bash
curl -i http://localhost:8080
```

Expected response body:

```text
Hello from the Node.js backend!
```

Check the NGINX configuration:

```bash
docker exec rp-nginx nginx -t
```

### 5.6 Clean up

```bash
docker rm -f rp-nginx rp-node
docker network rm reverse-proxy-network
```

---

## 6. Load balancing across Node.js containers

A load balancer distributes incoming requests across multiple backend instances. NGINX uses round-robin by default when multiple servers are listed in an `upstream` block.

For this demo, run each Node.js server in its own container. Both containers can listen on port `3000`; they have separate network namespaces.

### 6.1 Create the backend applications

`load-balancer-app/server1.js`:

```javascript
const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Welcome to Server 1');
});

server.listen(3000, '0.0.0.0', () => {
  console.log('Server 1 listening on port 3000');
});
```

`load-balancer-app/server2.js`:

```javascript
const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Welcome to Server 2');
});

server.listen(3000, '0.0.0.0', () => {
  console.log('Server 2 listening on port 3000');
});
```

### 6.2 Configure the NGINX upstream

`load-balancer-app/default.conf`:

```nginx
upstream node_backends {
    # Round-robin is the default method.
    server lb-server1:3000;
    server lb-server2:3000;
}

server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://node_backends;

        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6.3 Create a network

```bash
docker network create load-balancer-network
```

### 6.4 Start both backend containers

Run from `NGINX/`:

```bash
docker run -d \
  --name lb-server1 \
  --network load-balancer-network \
  -v "$PWD/load-balancer-app:/app:ro" \
  -w /app \
  node:22-alpine \
  node server1.js
```

```bash
docker run -d \
  --name lb-server2 \
  --network load-balancer-network \
  -v "$PWD/load-balancer-app:/app:ro" \
  -w /app \
  node:22-alpine \
  node server2.js
```

### 6.5 Start NGINX

```bash
docker run -d \
  --name lb-nginx \
  --network load-balancer-network \
  -p 8080:80 \
  -v "$PWD/load-balancer-app/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:latest
```

### 6.6 Test load balancing

```bash
for i in $(seq 1 10); do
  curl -s http://localhost:8080
  echo
done
```

You should see responses from both servers, typically alternating:

```text
Welcome to Server 1
Welcome to Server 2
Welcome to Server 1
Welcome to Server 2
```

Round-robin distributes requests in turn, but do not treat a particular response sequence as a guarantee under concurrent traffic or changing backend availability.

### 6.7 Try other load-balancing methods

**Least connections:**

```nginx
upstream node_backends {
    least_conn;
    server lb-server1:3000;
    server lb-server2:3000;
}
```

NGINX sends a new request to the server with the fewest active connections.

**IP hash:**

```nginx
upstream node_backends {
    ip_hash;
    server lb-server1:3000;
    server lb-server2:3000;
}
```

NGINX uses the client IP address to select a backend consistently, subject to backend membership and configuration.

After editing the mounted configuration, validate and reload NGINX:

```bash
docker exec lb-nginx nginx -t
docker exec lb-nginx nginx -s reload
```

### 6.8 Clean up

```bash
docker rm -f lb-nginx lb-server1 lb-server2
docker network rm load-balancer-network
```

---

## 7. HTTPS/TLS termination

TLS encrypts traffic between a client and a server. In this example, NGINX handles HTTPS and forwards the decrypted request to Node.js over HTTP. This is called **TLS termination**.

```text
Browser -- HTTPS --> NGINX -- HTTP --> Node.js
```

This demo uses a self-signed certificate. It is suitable for local development and testing, not for a public production website.

### 7.1 Create a self-signed certificate

Run from `NGINX/`:

```bash
mkdir -p ssl-tls-app/certs
```

Generate a certificate with Subject Alternative Names (SANs) for `localhost` and `127.0.0.1`:

```bash
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout ssl-tls-app/certs/nginx-selfsigned.key \
  -out ssl-tls-app/certs/nginx-selfsigned.crt \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

Files created:

- `ssl-tls-app/certs/nginx-selfsigned.crt`: certificate
- `ssl-tls-app/certs/nginx-selfsigned.key`: private key

Protect the private key and do not commit it to source control.

### 7.2 Node.js application

`ssl-tls-app/server.js`:

```javascript
const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello from Node.js Docker over the NGINX HTTPS proxy!');
});

server.listen(3000, '0.0.0.0', () => {
  console.log('Node.js server listening on port 3000');
});
```

Node.js uses HTTP in this demo. NGINX is responsible for HTTPS.

### 7.3 NGINX HTTPS configuration

`ssl-tls-app/default.conf`:

```nginx
server {
    listen 443 ssl;
    server_name localhost;

    ssl_certificate /etc/nginx/certs/nginx-selfsigned.crt;
    ssl_certificate_key /etc/nginx/certs/nginx-selfsigned.key;

    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://tls-node:3000;

        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name localhost;

    # Host port 8080 maps to container port 80.
    # Host port 8443 maps to container port 443.
    return 301 https://$host:8443$request_uri;
}
```

The certificate paths above are paths **inside the NGINX container**, not paths on the host.

### 7.4 Create a Docker network and start Node.js

```bash
docker network create ssl-tls-network
```

```bash
docker run -d \
  --name tls-node \
  --network ssl-tls-network \
  -v "$PWD/ssl-tls-app:/app:ro" \
  -w /app \
  node:22-alpine \
  node server.js
```

### 7.5 Start NGINX and mount the certificate files

```bash
docker run -d \
  --name tls-nginx \
  --network ssl-tls-network \
  -p 8080:80 \
  -p 8443:443 \
  -v "$PWD/ssl-tls-app/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$PWD/ssl-tls-app/certs:/etc/nginx/certs:ro" \
  nginx:latest
```

The port mappings are:

| Host port | Container port | Purpose |
|---:|---:|---|
| 8080 | 80 | HTTP; redirects to HTTPS |
| 8443 | 443 | HTTPS |

### 7.6 Test HTTP redirect and HTTPS

Check the redirect:

```bash
curl -I http://localhost:8080
```

Expected status and location:

```text
HTTP/1.1 301 Moved Permanently
Location: https://localhost:8443/
```

Test HTTPS:

```bash
curl -k https://localhost:8443
```

Expected response:

```text
Hello from Node.js Docker over the NGINX HTTPS proxy!
```

`-k` tells curl not to verify the self-signed certificate. Use it only for this local testing example. For a trusted certificate, configure the client to trust the issuing CA and omit `-k`.

Inspect the TLS handshake:

```bash
openssl s_client -connect localhost:8443 -servername localhost
```

### 7.7 Verify the NGINX configuration and certificate mount

```bash
docker exec tls-nginx nginx -t
docker exec tls-nginx ls -l /etc/nginx/certs/
docker logs tls-nginx
```

### 7.8 Clean up

```bash
docker rm -f tls-nginx tls-node
docker network rm ssl-tls-network
```

---

## 8. Useful commands and troubleshooting

### Docker commands

| Task | Command |
|---|---|
| List running containers | `docker ps` |
| List all containers | `docker ps -a` |
| Follow container logs | `docker logs -f <container>` |
| Inspect a container | `docker inspect <container>` |
| Execute a command in a container | `docker exec -it <container> sh` |
| List Docker networks | `docker network ls` |
| Inspect a network | `docker network inspect <network>` |
| Remove a container | `docker rm -f <container>` |
| Test NGINX configuration | `docker exec <nginx-container> nginx -t` |
| Reload NGINX | `docker exec <nginx-container> nginx -s reload` |

### Common problems

| Symptom | Likely cause | What to check |
|---|---|---|
| `502 Bad Gateway` | NGINX cannot reach the backend | Backend process, port, network, upstream name |
| `host not found in upstream` | Backend name cannot be resolved | Both containers must share a user-defined Docker network; check the upstream container name |
| `Connection refused` | Nothing is listening on the target port | Check the app process and listening port |
| `cannot load certificate` | Certificate path is wrong or file is not mounted | Check the host file and the container mount path |
| `mount ... not a directory` | Host source path is missing or has the wrong type | Check that a config-file mount points to a file and a directory mount points to a directory |
| `EADDRINUSE` | Two processes are trying to bind the same port in one network namespace | Use distinct ports, or run the apps in separate containers |
| Browser certificate warning | Self-signed certificate is not trusted | Expected for this demo; use a trusted CA for production |
| HTTP request to an HTTPS port fails | Protocol does not match the listener | Use `https://` for the TLS listener and `http://` for the plain HTTP listener |

### A useful debugging sequence

For a reverse proxy or load-balancer problem, debug from the backend outward:

1. Check that the backend container is running: `docker ps`.
2. Check backend logs: `docker logs <backend-container>`.
3. Test the backend from a temporary container on the same Docker network.
4. Check that NGINX and the backend share a network: `docker network inspect <network>`.
5. Validate NGINX: `docker exec <nginx-container> nginx -t`.
6. Inspect NGINX logs: `docker logs <nginx-container>`.
7. Test the public host port with `curl -i` or `curl -k`.

---

## 9. Important concepts

| Concept | Meaning |
|---|---|
| `listen` | Port and address on which NGINX accepts connections |
| `server` block | Virtual server configuration |
| `location` | Matches request URIs and defines handling |
| `root` | Builds a filesystem path by appending the URI |
| `alias` | Maps a location to a specified filesystem path |
| `proxy_pass` | Forwards a request to an upstream or backend |
| `upstream` | Defines a group of backend servers |
| `proxy_set_header` | Passes request metadata to the backend |
| Docker bind mount | Makes a host file or directory available inside a container |
| Docker user-defined bridge network | Provides container-to-container connectivity and name resolution |
| TLS termination | NGINX handles HTTPS and forwards traffic to the backend |

### `root` vs `alias`

With `root`, NGINX appends the request URI to the root path:

```nginx
location /static/ {
    root /data/www;
}
```

A request for `/static/image.png` maps to `/data/www/static/image.png`.

With `alias`, NGINX replaces the matching location prefix:

```nginx
location /static/ {
    alias /data/www/;
}
```

A request for `/static/image.png` maps to `/data/www/image.png`.

---

## Final checklist

- [ ] Serve local HTML files using an NGINX bind mount.
- [ ] Configure NGINX as a reverse proxy to Node.js.
- [ ] Connect NGINX and Node.js through a user-defined Docker network.
- [ ] Distribute requests across two Node.js containers.
- [ ] Configure NGINX to terminate HTTPS using a self-signed certificate.
- [ ] Verify redirects, backend responses, logs, and NGINX configuration.
- [ ] Keep private keys out of Git.

**Production note:** These examples are for learning. Production deployments also need appropriate certificate management, secrets handling, health checks, logging, monitoring, resource limits, and a deliberate network/security policy.
