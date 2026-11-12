← [Previous: Vulnerability Management](./vulnerability-management.md) | [Home](../README.md) | [Next: Threat Modeling →](./threat-modeling.md)

---

# Application Security

Application security (AppSec) integrates security testing into the development lifecycle — finding vulnerabilities before they reach production rather than after.

---

## AppSec in the SDLC

```
Plan → Code → Build → Test → Deploy → Operate
  │      │       │       │       │        │
Threat  SAST   SCA    DAST   Image    RASP/WAF
model  linting  deps  scans  signing  monitoring
```

---

## SAST (Static Application Security Testing)

SAST analyzes source code without running it.

```bash
# Bandit — Python security linter
pip install bandit
bandit -r src/ -f json -o bandit-report.json
bandit -r src/ -l -ii          # Only medium+ severity, medium+ confidence
bandit -r src/ --skip B101     # Skip assert_used (common in tests)

# Semgrep — polyglot SAST (Python/JS/Go/Java/Ruby/Terraform)
pip install semgrep
semgrep --config=auto .                      # Auto-select rules
semgrep --config=p/python .                  # Python-specific
semgrep --config=p/owasp-top-ten .           # OWASP Top 10
semgrep --config=p/secrets .                 # Secrets detection
semgrep --config=p/terraform .               # Terraform misconfiguration

# Output formats
semgrep --config=auto . --json > semgrep.json
semgrep --config=auto . --sarif > semgrep.sarif

# CodeQL (GitHub) — deep semantic analysis
# Configured via GitHub Actions (see production-pipelines.md)

# ESLint with security plugin (JavaScript)
npm install --save-dev eslint-plugin-security eslint-plugin-no-secrets
# Add to .eslintrc.json: "plugins": ["security", "no-secrets"]
npx eslint src/ --rule 'no-secrets/no-secrets: error'

# Gosec (Go)
go install github.com/securego/gosec/v2/cmd/gosec@latest
gosec -fmt json -out gosec-report.json ./...
gosec -severity high ./...
```

### Common Findings and Fixes

```python
# ❌ SQL injection
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ Parameterized query
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))

# ❌ Hardcoded secret
API_KEY = "sk-prod-abc123"

# ✅ From environment / secrets manager
API_KEY = os.environ["API_KEY"]

# ❌ Insecure deserialization
import pickle
data = pickle.loads(user_supplied_bytes)

# ✅ Use JSON or validated schema
import json
data = json.loads(user_supplied_string)
# Validate against schema
from pydantic import BaseModel
class RequestData(BaseModel):
    id: int
    name: str
data = RequestData.model_validate_json(user_supplied_string)

# ❌ Path traversal
filepath = os.path.join("/uploads", user_filename)
with open(filepath) as f: ...

# ✅ Validate and canonicalize
import pathlib
base = pathlib.Path("/uploads").resolve()
target = (base / user_filename).resolve()
if not str(target).startswith(str(base)):
    raise ValueError("Path traversal attempt")

# ❌ SSRF — unvalidated URL fetch
response = requests.get(request.args["url"])

# ✅ Allowlist destinations
ALLOWED_HOSTS = {"api.trusted.com", "partner.example.com"}
from urllib.parse import urlparse
parsed = urlparse(request.args["url"])
if parsed.hostname not in ALLOWED_HOSTS:
    raise ValueError(f"Disallowed host: {parsed.hostname}")
```

---

## DAST (Dynamic Application Security Testing)

DAST tests a running application by sending malicious inputs.

```bash
# OWASP ZAP (Zed Attack Proxy)
# Passive scan (spider + observe only — safe for production-like envs)
docker run -t owasp/zap2docker-stable zap-baseline.py \
    -t https://staging.my-app.com \
    -r zap-report.html \
    -J zap-report.json

# Active scan (actually attacks the app — staging/dev only)
docker run -t owasp/zap2docker-stable zap-full-scan.py \
    -t https://staging.my-app.com \
    -r zap-full-report.html \
    -J zap-full-report.json

# API scan (OpenAPI/Swagger spec)
docker run -t owasp/zap2docker-stable zap-api-scan.py \
    -t https://staging.my-app.com/openapi.json \
    -f openapi \
    -r zap-api-report.html

# Nuclei — template-based vulnerability scanner
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
nuclei -u https://staging.my-app.com -tags owasp,cve -severity critical,high
nuclei -u https://staging.my-app.com -t ~/nuclei-templates/ -o nuclei-results.txt
```

### ZAP in CI

```yaml
# GitHub Actions: ZAP baseline scan on ephemeral environment
- name: ZAP Baseline Scan
  uses: zaproxy/action-baseline@v0.12.0
  with:
    target: https://staging.my-app.com
    rules_file_name: .zap/rules.tsv    # Ignore known false positives
    issue_title: ZAP Scan Report
    fail_action: false    # Set to true to fail build on findings
```

---

## Dependency Auditing

```bash
# Python — pip-audit (see vulnerability-management.md for full flags)
pip-audit -r requirements.txt --fix     # Auto-upgrade where possible

# Check for abandoned or typosquatted packages
pip install pip-audit[optional]

# Verify package integrity (hash pinning)
# requirements.txt with hashes:
# pip install --require-hashes -r requirements.txt
# Generate:
pip-compile --generate-hashes requirements.in -o requirements.txt

# Node — check for known malicious packages
npm install -g @npmcli/arborist better-npm-audit
better-npm-audit audit --level high

# License compliance check (ensure no GPL in proprietary code)
pip install pip-licenses
pip-licenses --format=markdown --with-urls
```

---

## Security Headers

```python
# FastAPI middleware — security headers
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",                     # Disabled — CSP handles this in modern browsers
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "frame-ancestors 'none';"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cache-Control": "no-store",                  # For authenticated endpoints
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.debug("Applying security headers", extra={"path": request.url.path})
        response: Response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response


app = FastAPI()
app.add_middleware(SecurityHeadersMiddleware)
```

---

## Input Validation

```python
# Pydantic v2 — strict input validation
from pydantic import BaseModel, Field, field_validator
from typing import Annotated
import re

class CreateUserRequest(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")]
    email: Annotated[str, Field(max_length=254)]
    age: Annotated[int, Field(ge=0, le=150)]
    role: Annotated[str, Field(default="user")]

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        # Basic format check — use email-validator library in production
        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"user", "editor", "viewer"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {allowed}")
        return v
```

---

## OWASP Top 10 Quick Reference

| # | Risk | Key Mitigation |
|---|------|----------------|
| A01 | Broken Access Control | Deny by default; server-side authorization checks |
| A02 | Cryptographic Failures | TLS everywhere; AES-256-GCM; no MD5/SHA1 |
| A03 | Injection | Parameterized queries; input validation |
| A04 | Insecure Design | Threat modeling; secure defaults in architecture |
| A05 | Security Misconfiguration | Hardening; disable defaults; remove unused features |
| A06 | Vulnerable Components | SCA scanning; pin versions; update regularly |
| A07 | Auth & Session Failures | MFA; session expiry; secure cookie flags |
| A08 | Software Integrity Failures | Sign artifacts; verify checksums; SLSA provenance |
| A09 | Logging & Monitoring Failures | Structured logs; alerts; no secrets in logs |
| A10 | SSRF | Allowlist external destinations; block metadata IPs |

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Bandit](https://bandit.readthedocs.io/)
- [Semgrep](https://semgrep.dev/docs/)
- [OWASP ZAP](https://www.zaproxy.org/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)

---

← [Previous: Vulnerability Management](./vulnerability-management.md) | [Home](../README.md) | [Next: Threat Modeling →](./threat-modeling.md)
