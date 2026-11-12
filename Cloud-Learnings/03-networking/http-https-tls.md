← [Previous: Load Balancing](./load-balancing.md) | [Home](../README.md) | [Next: CDN →](./cdn.md)

---

# HTTP, HTTPS, and TLS

HTTP is the application-layer protocol that powers the web. HTTPS is HTTP secured with TLS. Understanding their mechanics — methods, headers, status codes, and the TLS handshake — is fundamental for debugging, API design, and cloud security.

---

## HTTP Overview

HTTP is a **stateless, request-response** protocol. Each request is independent; state (sessions, auth) must be managed by the application via cookies, tokens, or server-side session stores.

### HTTP Versions

| Version | Transport | Key Changes |
|---------|-----------|-------------|
| **HTTP/1.0** | TCP, one request per connection | Simple; high overhead |
| **HTTP/1.1** | TCP, persistent connections | Keep-alive, pipelining, Host header required |
| **HTTP/2** | TCP + TLS (multiplexed) | Binary framing, header compression (HPACK), server push, single connection for many requests |
| **HTTP/3** | QUIC (UDP-based) | Eliminates TCP head-of-line blocking, built-in TLS 1.3, faster connection setup |

---

## HTTP Methods

| Method | Idempotent | Safe | Purpose |
|--------|-----------|------|---------|
| `GET` | Yes | Yes | Retrieve a resource |
| `HEAD` | Yes | Yes | Like GET but no body (check existence, headers) |
| `OPTIONS` | Yes | Yes | List allowed methods (CORS preflight) |
| `POST` | No | No | Create a resource or trigger an action |
| `PUT` | Yes | No | Replace a resource completely |
| `PATCH` | No | No | Partial update of a resource |
| `DELETE` | Yes | No | Delete a resource |
| `CONNECT` | No | No | Establish a tunnel (used by HTTP proxies for HTTPS) |

- **Safe**: does not modify state on the server
- **Idempotent**: calling it N times has the same effect as calling it once

---

## HTTP Status Codes

### 2xx — Success

| Code | Name | Meaning |
|------|------|---------|
| `200` | OK | Request succeeded |
| `201` | Created | Resource created (typically POST) |
| `202` | Accepted | Request accepted, processing async |
| `204` | No Content | Success, no body (typically DELETE) |
| `206` | Partial Content | Range request response |

### 3xx — Redirection

| Code | Name | Meaning |
|------|------|---------|
| `301` | Moved Permanently | URL has permanently changed; browser caches redirect |
| `302` | Found | Temporary redirect; browser re-checks each time |
| `304` | Not Modified | Cache hit; use the cached version |
| `307` | Temporary Redirect | Like 302 but method must not change |
| `308` | Permanent Redirect | Like 301 but method must not change |

### 4xx — Client Errors

| Code | Name | Meaning |
|------|------|---------|
| `400` | Bad Request | Malformed request syntax |
| `401` | Unauthorized | Authentication required |
| `403` | Forbidden | Authenticated but not authorised |
| `404` | Not Found | Resource does not exist |
| `405` | Method Not Allowed | Method not supported on this endpoint |
| `408` | Request Timeout | Client took too long to send the request |
| `409` | Conflict | Request conflicts with current resource state |
| `410` | Gone | Resource permanently deleted |
| `422` | Unprocessable Entity | Validation error (common in REST APIs) |
| `429` | Too Many Requests | Rate limit exceeded |

### 5xx — Server Errors

| Code | Name | Meaning |
|------|------|---------|
| `500` | Internal Server Error | Generic server-side failure |
| `502` | Bad Gateway | Upstream server returned invalid response |
| `503` | Service Unavailable | Server overloaded or down for maintenance |
| `504` | Gateway Timeout | Upstream server timed out |

> **502 vs 503 vs 504**: On a load balancer, `502` = backend returned garbage, `503` = no healthy backends, `504` = backend took too long.

---

## HTTP Request and Response Structure

### Request

```
GET /api/users/123 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
Accept: application/json
Content-Type: application/json
User-Agent: MyClient/1.0
X-Request-ID: 7f8a3b2c-9d12-4e01-8f5a

(blank line)
(body — only for POST/PUT/PATCH)
```

### Response

```
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: 342
Cache-Control: no-store
X-Request-ID: 7f8a3b2c-9d12-4e01-8f5a
Strict-Transport-Security: max-age=31536000; includeSubDomains

{"id": 123, "name": "Alice"}
```

---

## Important HTTP Headers

### Request Headers

| Header | Purpose | Example |
|--------|---------|---------|
| `Host` | Target hostname (required in HTTP/1.1) | `api.example.com` |
| `Authorization` | Auth credentials | `Bearer <token>` / `Basic <b64>` |
| `Content-Type` | Body media type | `application/json` |
| `Accept` | Acceptable response types | `application/json, text/html` |
| `User-Agent` | Client identifier | `curl/7.79.1` |
| `X-Forwarded-For` | Original client IP through proxies | `203.0.113.1, 10.0.0.1` |
| `X-Request-ID` | Distributed tracing correlation | `7f8a3b2c-9d12-4e01-8f5a` |
| `Cache-Control` | Caching directives | `no-cache`, `max-age=3600` |
| `If-None-Match` | Conditional request (ETag-based) | `"abc123"` |
| `If-Modified-Since` | Conditional request (time-based) | `Wed, 21 Oct 2024 07:28:00 GMT` |

### Response Headers

| Header | Purpose | Example |
|--------|---------|---------|
| `Content-Type` | Body media type | `application/json; charset=utf-8` |
| `Content-Length` | Body size in bytes | `342` |
| `Cache-Control` | Caching directives | `max-age=3600, public` |
| `ETag` | Resource version identifier | `"abc123"` |
| `Location` | Redirect target | `https://api.example.com/users/123` |
| `Set-Cookie` | Set a cookie | `session=abc; HttpOnly; Secure; SameSite=Strict` |
| `Strict-Transport-Security` | Force HTTPS (HSTS) | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | Prevent MIME sniffing | `nosniff` |
| `X-Frame-Options` | Clickjacking protection | `DENY` |
| `Content-Security-Policy` | XSS / injection protection | `default-src 'self'` |

---

## CORS — Cross-Origin Resource Sharing

A browser security mechanism that restricts which origins can call an API.

```
Origin: https://app.example.com   requests   https://api.example.com
                                     ↑
                              CORS headers control this
```

**Preflight request** (for non-simple methods like PUT/DELETE, or custom headers):

```
OPTIONS /api/users HTTP/1.1
Origin: https://app.example.com
Access-Control-Request-Method: DELETE
Access-Control-Request-Headers: Authorization

HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, DELETE
Access-Control-Allow-Headers: Authorization
Access-Control-Max-Age: 3600
```

---

## TLS — Transport Layer Security

TLS encrypts the connection between client and server. HTTPS = HTTP over TLS.

### TLS Versions

| Version | Status | Notes |
|---------|--------|-------|
| SSLv2, SSLv3 | Deprecated — disable | Multiple critical vulnerabilities |
| TLS 1.0, 1.1 | Deprecated — disable | Prohibited by PCI DSS 4.0, not FIPS compliant |
| **TLS 1.2** | Acceptable | Widely supported; needs careful cipher configuration |
| **TLS 1.3** | Preferred | Faster handshake (1 RTT vs 2), forward secrecy mandatory, removed weak ciphers |

### TLS 1.2 Handshake (2 Round Trips)

```
Client                              Server
  │── ClientHello ────────────────▶│
  │   (supported TLS versions,     │
  │    cipher suites, random nonce)│
  │                                │
  │◀── ServerHello ─────────────────│
  │   (chosen cipher, server cert, │
  │    server random nonce)        │
  │                                │
  │── (verify cert) ───────────────│
  │── ClientKeyExchange ──────────▶│  (pre-master secret, encrypted with server pubkey)
  │── ChangeCipherSpec ────────────▶│
  │── Finished ───────────────────▶│
  │                                │
  │◀── ChangeCipherSpec ────────────│
  │◀── Finished ────────────────────│
  │                                │
  │══════ Encrypted HTTP ══════════│
```

### TLS 1.3 Handshake (1 Round Trip)

```
Client                              Server
  │── ClientHello + key_share ─────▶│
  │   (TLS 1.3, ECDHE key share,   │
  │    supported cipher suites)     │
  │                                │
  │◀── ServerHello + key_share ─────│
  │◀── {Certificate} ───────────────│  (encrypted in TLS 1.3)
  │◀── {CertificateVerify} ─────────│
  │◀── {Finished} ──────────────────│
  │                                │
  │── {Finished} ─────────────────▶│
  │                                │
  │══════ Encrypted HTTP ══════════│
```

TLS 1.3 adds **0-RTT** for session resumption (the client can send data immediately on reconnect using a session ticket — note: 0-RTT is not replay-safe for non-idempotent requests).

### Certificates

```
Root CA (e.g., DigiCert)
  └── Intermediate CA
        └── Server Certificate (example.com)
```

- **Subject**: the entity the cert is issued to (e.g., `*.example.com`)
- **Issuer**: the CA that signed it
- **SANs (Subject Alternative Names)**: additional hostnames this cert covers
- **Validity**: not-before and not-after dates
- **Public key**: used by clients to encrypt the pre-master secret or verify signatures

```bash
# View a certificate
openssl s_client -connect example.com:443 -servername example.com < /dev/null \
    | openssl x509 -text -noout

# Check expiry date
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
    | openssl x509 -noout -dates

# Check from a PEM file
openssl x509 -in cert.pem -noout -text
openssl x509 -in cert.pem -noout -enddate    # just the expiry

# Verify the full chain
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt cert.pem
```

### SNI — Server Name Indication

SNI is a TLS extension that allows the client to tell the server which hostname it is trying to reach **before** the TLS handshake completes. This allows one IP address to serve TLS certificates for multiple domains (virtual hosting over TLS).

```bash
# curl uses SNI automatically; override if needed
curl --resolve api.example.com:443:93.184.216.34 https://api.example.com/

# openssl s_client with explicit SNI
openssl s_client -connect 93.184.216.34:443 -servername api.example.com
```

---

## HSTS — HTTP Strict Transport Security

Instructs browsers to **only** connect via HTTPS for a domain, even if the user types `http://`.

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

- `max-age`: seconds to remember the policy
- `includeSubDomains`: applies to all subdomains
- `preload`: eligible for browser HSTS preload list (hardcoded in browsers)

> Once HSTS with `preload` is set, rolling it back is difficult. Start with a short `max-age` in testing.

---

## AWS Certificate Manager (ACM)

ACM provisions and auto-renews TLS certificates for use with ALB, CloudFront, API Gateway, and other AWS services.

```bash
# Request a public certificate
aws acm request-certificate \
    --domain-name example.com \
    --subject-alternative-names www.example.com api.example.com \
    --validation-method DNS

# List certificates
aws acm list-certificates

# Describe certificate status (check validation)
aws acm describe-certificate \
    --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc-123

# Import an existing certificate
aws acm import-certificate \
    --certificate fileb://cert.pem \
    --private-key fileb://key.pem \
    --certificate-chain fileb://chain.pem
```

ACM certificates **cannot be exported** (private key stays in ACM). For EC2 instances or containers that need cert files, use Let's Encrypt, self-managed certs, or AWS Private CA.

---

## curl Debugging

```bash
# Full request/response headers
curl -v https://api.example.com/health

# Timing breakdown
curl -w "\nnamelookup=%{time_namelookup}s connect=%{time_connect}s tls=%{time_appconnect}s total=%{time_total}s\n" \
     -o /dev/null -s https://api.example.com/health

# Follow redirects
curl -L https://example.com/

# Send JSON body
curl -X POST https://api.example.com/users \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"name": "Alice"}'

# Ignore certificate errors (testing only — never in production)
curl -k https://self-signed.example.com

# Test with a specific TLS version
curl --tlsv1.3 https://example.com
curl --tlsv1.2 --tls-max 1.2 https://example.com

# Show certificate info
curl -vI https://example.com 2>&1 | grep -A 5 "Server certificate"
```

---

## References

- [MDN HTTP Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP)
- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110)
- [RFC 8446 — TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446)
- [AWS Certificate Manager](https://docs.aws.amazon.com/acm/latest/userguide/)
- [Cloudflare: TLS Explained](https://www.cloudflare.com/learning/ssl/what-is-tls/)
---

← [Previous: Load Balancing](./load-balancing.md) | [Home](../README.md) | [Next: CDN →](./cdn.md)
