# ✅ What is NGINX?

**NGINX** is an open-source, high-performance web server that also functions as:
- A reverse proxy
- Load balancer
- HTTP cache
- Mail proxy

It is designed for high concurrency, performance, and low memory usage — making it ideal for modern DevOps and cloud environments.

---

## 📊 NGINX vs Apache (Why DevOps Prefer NGINX)

| Feature         | NGINX                          | Apache                      |
|-----------------|--------------------------------|-----------------------------|
| Architecture    | Event-driven (asynchronous)    | Process/thread-based        |
| Performance     | High concurrency, fast         | Slower with many connections|
| Memory usage    | Low                            | High                        |
| Static content  | Extremely fast                 | Good                        |
| Config format   | Simple, declarative            | More flexible but complex   |
| Use cases       | Web server, reverse proxy, LB  | Traditional web server      |

💡 **DevOps Engineers** often choose NGINX for its:
- Lightweight footprint
- Ease of automation
- Docker/Kubernetes friendliness

---


## 🧰 Common DevOps Use Cases for NGINX

| Use Case                              | Example                                                                 |
|--------------------------------------|-------------------------------------------------------------------------|
| Web server                           | Serving static React/Angular apps                                      |
| Reverse proxy                        | Forwarding requests to backend apps (Node.js, Python, Java)            |
| Load balancer                        | Distributing load between multiple backend servers                     |
| SSL termination                      | Handling HTTPS at the edge                                             |
| Caching                              | Reducing load on upstream services                                     |
| Ingress controller (Kubernetes)      | Managing traffic inside Kubernetes clusters                            |
| Rate limiting & security enforcement | Protecting APIs from abuse or bots                                     |

---

## 🛠️ Installing NGINX

### 🐧 On Ubuntu/Debian
```bash
sudo apt update
sudo apt install nginx -y
```

### 📦 On RHEL/CentOS
```bash
sudo yum install epel-release -y
sudo yum install nginx -y
```

### 🐳 Using Docker (Recommended for DevOps)
```bash
docker run --name nginx -p 8080:80 -d nginx
```

Visit: `http://localhost:8080`

--- 



## 📁 NGINX File Structure (Linux)

| File/Directory        | Purpose                                      |
|-----------------------|----------------------------------------------|
| `/etc/nginx/nginx.conf` | Main configuration file                     |
| `/etc/nginx/sites-available/` | Stores virtual host (server block) configs |
| `/etc/nginx/sites-enabled/`   | Symlinks to active site configs         |
| `/var/www/html`       | Default web root directory                   |
| `/var/log/nginx/`     | Contains access and error logs               |

---

## 🧪 Demo: Run NGINX Using Docker

### Step 1: Run container
```bash
docker run --name nginx-demo -p 8080:80 -d nginx
```

### Step 2: Test in browser
Visit: `http://localhost:8080`  
You should see the **Welcome to NGINX** page.

### Step 3: View Logs
```bash
docker logs nginx-demo
```

### Step 4: Clean up
```bash
docker stop nginx-demo
docker rm nginx-demo
```

---

## 🎯 Summary

- NGINX is a lightweight, high-performance web server and reverse proxy.
- Widely used in DevOps for load balancing, SSL termination, and as a reverse proxy.
- Easy to install via Linux package managers or Docker.
- Supports modular configuration — great for automation and CI/CD.

# 🌐 Section 2: NGINX as a Web Server

## 🚀 Goal

Learn how to use NGINX to serve static content such as HTML, CSS, JavaScript, and images — a foundational skill for DevOps and Cloud Engineers.

---

## 🧠 What is a Web Server?

A **web server** is software that serves static files (like `.html`, `.css`, `.js`, `.png`) over HTTP.  
When users visit your website, the web server responds with these files.

NGINX is one of the fastest and most popular web servers used for this purpose.

---

## 📁 Default Web Root in Linux

| Directory             | Purpose                          |
|-----------------------|----------------------------------|
| `/var/www/html`       | Default directory for static files |
| `/etc/nginx/sites-available/default` | Default config file pointing to the web root |

---

## 📝 Anatomy of a Basic `server` Block

```nginx
server {
    listen 80;
    server_name localhost;

    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

### Breakdown:
- `listen 80;` → Listens on HTTP port 80
- `server_name localhost;` → Domain or IP to respond to
- `root` → Path where NGINX looks for files
- `index` → Default file to serve (usually index.html)
- `location /` → URL path handling

---

## 🧪 Demo: Serve a Static Website Using NGINX

### 🔧 Option 1: Using Native Linux NGINX

1. Create an HTML file:
```bash
echo "<h1>Hello from NGINX Web Server</h1>" | sudo tee /var/www/html/index.html
```

2. Reload NGINX:
```bash
sudo systemctl reload nginx
```

3. Test:
Visit: `http://localhost` or your server’s IP in browser.

---

### 🐳 Option 2: Serve HTML from Docker

1. Create a project folder:
```bash
mkdir nginx-static && cd nginx-static
```

2. Add `index.html`:
```html
<!-- index.html -->
<h1>Hello from NGINX in Docker!</h1>
```

3. Run NGINX Docker container:

```bash
docker run --name web-nginx -v $PWD:/usr/share/nginx/html:ro -p 8080:80 -d nginx
```

4. Open in browser:
```
http://localhost:8080
```

---

## 🔄 Root vs Alias

These two directives behave differently inside `location` blocks.

### `root` example:
```nginx
location /static/ {
    root /data/www;
}
# /static/img.png → /data/www/static/img.png
```

### `alias` example:
```nginx
location /static/ {
    alias /data/www/;
}
# /static/img.png → /data/www/img.png
```

📌 Use `alias` when you want to replace the URI path.

---

## 🧯 Common Errors & Fixes

| Error                             | Solution                                 |
|----------------------------------|------------------------------------------|
| 403 Forbidden                    | Check file permissions (use `chmod`/`chown`) |
| 404 Not Found                    | Ensure correct `root` or `alias`         |
| NGINX not reloading changes     | Use `sudo nginx -s reload` or restart NGINX |
| Port already in use             | Use `sudo lsof -i :80` to identify process |

---


## NGINX and NODE using docker for `static-server`

- Create `static-server-app` directory in present working directory
```bash
mkdir static-server-app
```

- Create one `index.html` inside `static-server-app` and add below content
```html
<h1 style="text-align:centre;">Hii, Welcome to NGINX Server</h1>
<h2 style="text-align:centre;">We are testing html file serving through nginx</h2>
```

- Mount `static-server-app` to nginx and run the container
```bash
docker run --name web-nginx -v $PWD:/usr/share/nginx/html:ro -p 8080:80 -d nginx
```


## ✅ Summary

- NGINX can serve static files efficiently.
- The `root` and `index` directives define where and what to serve.
- Use Docker volumes to serve files without touching the host filesystem.
- Always reload NGINX after making config changes.

---
 
# 🔁 Section 3: NGINX as a Reverse Proxy (Ubuntu/Linux)

## 🧠 What is a Reverse Proxy?

A **reverse proxy** is a server that receives client requests and forwards them to backend servers, then sends the response back to the client.

NGINX is one of the most popular tools used as a reverse proxy in production.

---

## 🔄 Reverse Proxy vs Forward Proxy

| Feature         | Forward Proxy                       | Reverse Proxy                           |
|-----------------|--------------------------------------|------------------------------------------|
| Who configures it | Client                              | Server-side                              |
| Forwards requests to | External servers (internet)         | Internal backend servers (apps/services) |
| Use case         | Browsing anonymously, caching       | Load balancing, SSL termination, API gateway |
| Example          | Proxy server for office users       | NGINX between frontend and backend apps  |

---

## 📌 Why Use NGINX as a Reverse Proxy?

- Protect backend services from direct access
- Centralized SSL termination
- Load balancing backend apps
- Path-based routing (`/api` → backend1, `/app` → backend2)
- Easy caching and compression

---

## 📝 Reverse Proxy Configuration (Ubuntu/Linux)

### 🔧 File: `/etc/nginx/sites-available/default`

Update the existing `server` block or create a new one:

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Breakdown:
- `proxy_pass` → forwards requests to your backend app
- `proxy_set_header` → preserves original request metadata (like IP and host)

---

## 🧪 Demo: Reverse Proxy to a Node.js App

### Step 1: Install Node.js (optional if using your own backend)
```bash
sudo apt update
sudo apt install nodejs npm -y
```

### Step 2: Create a simple backend app
```bash
mkdir ~/node-backend && cd ~/node-backend
nano server.js
```

**Paste this:**
```js
const http = require('http');
http.createServer((req, res) => {
  res.end('Hello from Node.js backend!');
}).listen(3000);
```

Run it:
```bash
node server.js
```

> Your app is now running at `http://localhost:3000`

---

### Step 3: Configure NGINX as reverse proxy

Edit the NGINX default site:
```bash
sudo nano /etc/nginx/sites-available/default
```

Replace the `location / {}` block with:
```nginx
location / {
    proxy_pass http://localhost:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Step 4: Test and reload NGINX

Check config for syntax errors:
```bash
sudo nginx -t
```

Reload NGINX:
```bash
sudo systemctl reload nginx
```

### Step 5: Test in browser

Visit:
```
http://localhost
```

✅ You should see: `Hello from Node.js backend!`

---

## NGINX and NODE using docker for `reverser-proxy`

- Create `reverse-proxy-app` directory in present working directory
```bash
mkdir reverse-proxy-app
```

- Create one `server.js` inside `reverse-proxy-app` and add below content
```js
const http = require('http');

const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Hello from Node.js Docker!');
});

server.listen(3000, '0.0.0.0', () => {
    console.log('Server running on port 3000');
});
```

- Mount `reverse-proxy-app` to node and run `node` container
```bash
docker run -it -d --name node -p 3000:3000 -v "$(pwd):/reverse-proxy-app" -w /reverse-proxy-app node:22-alpine tail -f /dev/null
```

- Now exec to `node conatiner`
```bash
docker exec -it node sh
```

- Go inside `reverse-proxy-app` and execute below
```bash
cd /reverse-proxy-app
node server.js
```
to run in background
```bash
node server.js &
```

- Now server is running at port `3000`

- Now run NGINX from your local
```bash
docker run --name nginx -p 8080:80 -d nginx
```

- As nginx and node server need to communicate with each other, we will create `docker network`
```bash
docker network create reverse-proxy-network
```

- Connect node to the network
```bash
docker network connect reverse-proxy-network node
```

- Connect nginx to same network
```bash
docker network connect reverse-proxy-network nginx
```

- Create Nginx reverse proxy configuration
```bash
cd reverse-proxy-app
touch default.conf
```

add below content to it
```conf
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://node:3000;

        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
- Recreate Nginx with the configuration

```bash
docker rm -f nginx

docker run -d --name nginx --network reverse-proxy-network -p 8080:80 -v "$(pwd)/default.conf:/etc/nginx/conf.d/default.conf:ro" nginx:latest
```


## 📁 File Structure Recap (Ubuntu)

| Path                              | Purpose                                |
|-----------------------------------|----------------------------------------|
| `/etc/nginx/nginx.conf`           | Global NGINX settings                   |
| `/etc/nginx/sites-available/default` | Active site config for reverse proxy   |
| `/var/www/html`                   | Not used in reverse proxy               |
| `/var/log/nginx/access.log`       | Logs all requests                       |

---

## ✅ Summary

- NGINX can proxy traffic to backend apps using `proxy_pass`.
- Config changes go in `/etc/nginx/sites-available/default` (on Ubuntu).
- Always test config and reload NGINX after changes.
- Ideal for API gateways, internal routing, and SSL termination.

# ⚖️ Section 4: Load Balancing with NGINX (Ubuntu/Linux)

## 🎯 Goal

Use NGINX to distribute traffic across multiple backend servers — improving availability, reliability, and scalability of your applications.

---

## 🧠 What is Load Balancing?

**Load balancing** is the process of distributing incoming network traffic across multiple backend servers.

Benefits:
- Prevents server overload
- Increases availability and fault tolerance
- Enables horizontal scaling

NGINX supports multiple load balancing algorithms out of the box.

---

## 🧮 Load Balancing Algorithms in NGINX

| Algorithm         | Behavior                                                               |
|-------------------|-------------------------------------------------------------------------|
| `round-robin`     | Default — rotates through all backends equally                         |
| `least_conn`      | Sends traffic to the backend with the fewest active connections         |
| `ip_hash`         | Uses client IP to consistently route requests to the same backend       |

---

## 📝 Basic Load Balancer Configuration

Edit:
```bash
sudo nano /etc/nginx/sites-available/default
```

Replace contents with:

```nginx
upstream backend_app {
    server 127.0.0.1:3001;
    server 127.0.0.1:3002;
}

server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://backend_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🧪 Demo: Load Balance Two Local Backend Servers

### Step 1: Create Backend Servers

We'll run two simple HTTP servers using Node.js.

#### Create script:
```bash
mkdir ~/load-test && cd ~/load-test
```

**server1.js**
```js
require('http').createServer((req, res) => {
  res.end('Response from Server 1');
}).listen(3001);
```

**server2.js**
```js
require('http').createServer((req, res) => {
  res.end('Response from Server 2');
}).listen(3002);
```

### Step 2: Run both servers
```bash
node server1.js &
node server2.js &
```

---

### Step 3: Reload NGINX

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Step 4: Test the Load Balancer

Open a browser or use curl:

```bash
curl http://localhost
```

Run it multiple times — you should see the response alternate between:

```
Response from Server 1
Response from Server 2
```

✅ You’ve just created a working load balancer using NGINX!

---


## NGINX and NODE using docker for `load-balancer`

- Create `load-balancer-app` directory in present working directory
```bash
mkdir load-balancer-app
```

- Create one `server1.js` and `server2.js` inside `reverse-proxy-app` and add below content
```js
const http = require('http');

const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Welcome to Server 1');
});

server.listen(3001, '0.0.0.0', () => {
    console.log('Welcome to Server 1');
});
```

```js
const http = require('http');

const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Welcome to Server 2');
});

server.listen(3002, '0.0.0.0', () => {
    console.log('Welcome to Server 2');
});

```

- Mount `load-balancer-app` to node and run `node` container
```bash
docker run -it -d --name node -p 3000:3000 -v "$(pwd):/load-balancer-app" -w /load-balancer-app node:22-alpine tail -f /dev/null
```

- Now exec to `node conatiner`
```bash
docker exec -it node sh
```

- Go inside `load-balancer-app` and execute below

to run in background
```bash
node server1.js &
node server2.js &

wget -O- http://127.0.0.1:3001
wget -O- http://127.0.0.1:3002
```

- Now server is running at port `30001` and `3002`

- As nginx and node server need to communicate with each other, we will create `docker network`
```bash
docker network create load-balancer-network
```

- Connect node to the network
```bash
docker network connect load-balancer-network node
```

- Create Nginx reverse proxy configuration
```bash
cd load-balancer-app
mkdir default.conf
```

add below content to it
```conf
upstream load_balancer_app {
    server node:3001;
    server node:3002;
}

server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://load_balancer_app;

        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
- Create Nginx with the configuration

```bash
docker run -d --name nginx --network load-balancer-network -p 8080:80 -v "$(pwd)/default.conf:/etc/nginx/conf.d/default.conf:ro" nginx:latest
```

---

## 🔄 Switching Load Balancing Methods

### Use Least Connections
```nginx
upstream backend_app {
    least_conn;
    server 127.0.0.1:3001;
    server 127.0.0.1:3002;
}
```

### Use IP Hash
```nginx
upstream backend_app {
    ip_hash;
    server 127.0.0.1:3001;
    server 127.0.0.1:3002;
}
```

--- 

# 🔒 Section 5: SSL/TLS Setup in NGINX Using a Self-Signed Certificate (Ubuntu/Linux)

## 🎯 Goal

Secure your application with HTTPS using a **self-signed SSL certificate**.  
This is ideal for **local development**, **internal tools**, and **non-public test environments**.

---

## 🧠 Why Use HTTPS (Even in Dev)?

- Encrypts traffic between client and server
- Simulates production-like environment for testing
- Helps catch mixed-content issues early
- Required by modern frontend frameworks and APIs

---

## 🛠️ Step-by-Step: Create a Self-Signed Certificate

### Step 1: Generate SSL Certificate and Key

```bash
sudo openssl req -x509 -nodes -days 365 \
 -newkey rsa:2048 \
 -keyout /etc/ssl/private/nginx-selfsigned.key \
 -out /etc/ssl/certs/nginx-selfsigned.crt
```

When prompted:
- Common Name (CN): use `localhost` or your server’s IP

---

### Step 2: Update NGINX Configuration

Edit the default site config:
```bash
sudo nano /etc/nginx/sites-available/default
```

Replace with the following:

```nginx
server {
    listen 443 ssl;
    server_name localhost;

    ssl_certificate /etc/ssl/certs/nginx-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/nginx-selfsigned.key;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Optional: Redirect HTTP to HTTPS
server {
    listen 80;
    server_name localhost;
    return 301 https://$host$request_uri;
}
```

---

### Step 3: Reload NGINX

Check and reload configuration:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

### Step 4: Test HTTPS Locally

Open your browser and visit:

```
https://localhost
```

⚠️ You will see a warning:  
> "Your connection is not private"

✅ That’s expected with self-signed certs. Proceed anyway to view your site securely.

---

## 📁 SSL File Paths Recap

| Path                                         | Purpose               |
|----------------------------------------------|------------------------|
| `/etc/ssl/certs/nginx-selfsigned.crt`        | SSL certificate        |
| `/etc/ssl/private/nginx-selfsigned.key`      | Private key            |
| `/etc/nginx/sites-available/default`         | HTTPS proxy config     |

---

## 🧪 Bonus: Test Without Browser (curl)

```bash
curl -k https://localhost
```

> `-k` allows insecure (self-signed) HTTPS connections.

---


## NGINX and NODE using docker for `ssl/tls connection`

- Create `ssl-tls-app` directory in present working directory
```bash
mkdir ssl-tls-app
cd ssl-tls-app
```

- Create one `server.js` inside `ssl-tls-app` and add below content
```js
const http = require('http');

const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Hello from Node.js Docker!');
});

server.listen(3000, '0.0.0.0', () => {
    console.log('Server running on port 3000');
});
```

- Mount `ssl-tls-app` to node and run `node` container
```bash
docker run -it -d --name node -p 3000:3000 -v "$(pwd):/ssl-tls-app" -w /ssl-tls-app node:22-alpine tail -f /dev/null
```

- Now exec to `node conatiner`
```bash
docker exec -it node sh
```

- Go inside `ssl-tls-app` and execute below
```bash
cd /ssl-tls-app
node server.js
```
to run in background
```bash
node server.js &
```

- Now server is running at port `3000`

- As nginx and node server need to communicate with each other, we will create `docker network`
```bash
docker network create ssl-tls-app
```

- Connect node to the network
```bash
docker network connect ssl-tls-app node
```

- Generate SSL Certificate and Key
```sh
mkdir certs
```

```bash
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout ./certs/nginx-selfsigned.key \
  -out ./certs/nginx-selfsigned.crt \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

- Create Nginx reverse proxy configuration
```bash
touch default.conf
```

add below content to it
```conf
server {
    listen 443 ssl;
    server_name localhost;

    ssl_certificate /etc/ssl/certs/nginx-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/nginx-selfsigned.key;

    location / {
        proxy_pass http://node:3000;

        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Optional: Redirect HTTP to HTTPS
server {
    listen 80;
    server_name localhost;
    return 301 https://$host$request_uri;
}
```
- Create Nginx with the configuration

```bash
docker run -d --name nginx --network ssl-tls-app -p 8080:80 -p 8443:443 -v "$(pwd)/default.conf:/etc/nginx/conf.d/default.conf:ro" -v "$(pwd)/certs:/etc/nginx/certs:ro" nginx:latest
```
- Test using
```sh
curl -I http://localhost:8080
curl -I http://localhost:8443
```



## ✅ Summary

- Self-signed SSL is perfect for secure local development.
- Requires only OpenSSL and a few lines in NGINX.
- Always test your HTTPS setup with curl and browser.
- In production, switch to Let’s Encrypt or trusted CAs.

---