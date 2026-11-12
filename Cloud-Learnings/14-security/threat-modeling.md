← [Previous: Application Security](./application-security.md) | [Home](../README.md) | [Next: Compliance →](./compliance.md)

---

# Threat Modeling

Threat modeling is a structured approach to identifying security threats before they are built into a system. Do it during design, not after deployment.

---

## When to Threat Model

- New service or feature design
- Changes to authentication or authorization
- Introduction of new data flows (especially PII)
- New external integrations or third-party dependencies
- Infrastructure changes (new VPC, new cloud region, new IAM roles)

---

## STRIDE Framework

STRIDE categorizes threats by what an attacker is trying to do:

| Category | Threat | What is violated | Example |
|----------|--------|------------------|---------|
| **S**poofing | Impersonate another identity | Authentication | Stolen JWT token used to call API as admin |
| **T**ampering | Modify data or code | Integrity | Alter order total in transit |
| **R**epudiation | Deny performing an action | Non-repudiation | User denies placing fraudulent order |
| **I**nformation Disclosure | Access data without permission | Confidentiality | Leaked S3 bucket with user PII |
| **D**enial of Service | Make service unavailable | Availability | Flood API with requests |
| **E**levation of Privilege | Gain higher permissions | Authorization | SSRF to read EC2 metadata → IAM creds |

---

## Threat Modeling Process

```
1. Decompose the System
   ├── Identify components (services, databases, queues, external APIs)
   ├── Draw data flow diagram (DFD)
   └── Mark trust boundaries (where data crosses privilege levels)

2. Identify Threats (STRIDE per component)
   ├── For each trust boundary crossing → what could go wrong?
   ├── For each data store → who can read/write without authorization?
   └── For each external entity → can they be spoofed?

3. Rate Threats (DREAD or CVSS)
   ├── Likelihood × Impact
   └── Prioritize by risk score

4. Define Mitigations
   ├── Authentication controls
   ├── Encryption
   ├── Input validation
   └── Monitoring / alerting

5. Validate
   ├── Review with security team
   └── Track in issue tracker
```

---

## Data Flow Diagram (DFD)

```
External entities  →  Trust boundary  →  Internal processes  →  Data stores

┌──────────┐          ┌────────────┐          ┌───────────┐
│  Browser │ ─HTTPS─► │    WAF     │ ─HTTP─►  │  API      │
│ (User)   │          │  (public)  │          │  Service  │
└──────────┘          └────────────┘          └─────┬─────┘
                                                    │ SQL
                                              ┌─────▼─────┐
                                              │  Database │
                                              │  (VPC)    │
                                              └───────────┘
                          Trust boundary: WAF ↔ API Service
                          Trust boundary: API Service ↔ Database
```

---

## STRIDE Applied: REST API Example

```
Component: POST /api/v1/orders

Spoofing:
  Threat: Attacker uses stolen JWT to place order as another user
  Mitigation: Short JWT TTL (15min), refresh token rotation, per-request fingerprinting

Tampering:
  Threat: MITM modifies order payload (change price or quantity)
  Mitigation: TLS 1.3 enforced; HMAC-signed request body for payment flows

Repudiation:
  Threat: User disputes order, no audit trail
  Mitigation: Immutable audit log with user ID + timestamp + action + IP in append-only store

Information Disclosure:
  Threat: Error message reveals database schema or stack trace
  Mitigation: Generic error responses to clients; full details only in internal logs

Denial of Service:
  Threat: Flood POST /orders to exhaust DB connections
  Mitigation: Rate limit by user ID (100 req/min); circuit breaker; connection pool limits

Elevation of Privilege:
  Threat: Regular user calls admin endpoint by modifying URL
  Mitigation: Server-side RBAC check on every request; no client-supplied role claims
```

---

## Attack Surface Reduction

```bash
# Enumerate open ports on a host
nmap -sV -p- --open 10.0.10.5

# List all public AWS resources (exposed to 0.0.0.0/0)
# Security groups with inbound from anywhere
aws ec2 describe-security-groups \
    --query "SecurityGroups[?IpPermissions[?IpRanges[?CidrIp=='0.0.0.0/0']]].{SG:GroupId,Name:GroupName}" \
    --output table

# S3 buckets with public access
aws s3api list-buckets --query 'Buckets[*].Name' --output text | tr '\t' '\n' | while read bucket; do
    ACL=$(aws s3api get-bucket-acl --bucket "$bucket" 2>/dev/null \
        | jq -r '.Grants[] | select(.Grantee.URI == "http://acs.amazonaws.com/groups/global/AllUsers") | .Permission' 2>/dev/null)
    [ -n "$ACL" ] && echo "PUBLIC: $bucket ($ACL)"
done

# RDS instances publicly accessible
aws rds describe-db-instances \
    --query "DBInstances[?PubliclyAccessible==\`true\`].{ID:DBInstanceIdentifier,Engine:Engine}" \
    --output table

# Lambda functions with public URL
aws lambda list-function-url-configs \
    --function-name my-function \
    --query 'FunctionUrlConfigs[?AuthType==`NONE`]'
```

---

## Threat Modeling Template

```markdown
## Threat Model: [Feature/System Name]
**Date:** YYYY-MM-DD
**Author:** @username
**Reviewer:** @security-team

### System Description
[1-2 sentence description of what this does]

### Data Flow Summary
[Describe data inputs, transformations, outputs, and storage]

### Trust Boundaries
1. Internet → WAF/Load Balancer
2. Load Balancer → Application Tier (VPC boundary)
3. Application Tier → Database (security group boundary)

### Threat Analysis

| ID | Category | Component | Threat | Likelihood | Impact | Risk | Mitigation | Status |
|----|----------|-----------|--------|------------|--------|------|------------|--------|
| T1 | Spoofing | Auth endpoint | Token replay | Medium | High | High | Short TTL + rotation | ✅ Done |
| T2 | InfoDisc | API errors | Stack trace leak | Low | Medium | Medium | Generic errors | 🔄 In progress |
| T3 | DoS | Order API | Request flood | High | High | Critical | Rate limiting | ❌ Open |

### Out of Scope
- Physical security of cloud provider DCs
- End-user device compromise

### References
- [OWASP Threat Modeling](https://owasp.org/www-community/Application_Threat_Modeling)
```

---

## PASTA (Process for Attack Simulation and Threat Analysis)

A risk-centric alternative to STRIDE:

```
Stage 1: Define business objectives
Stage 2: Define technical scope (DFDs, infrastructure)
Stage 3: Decompose application (APIs, data flows, trust boundaries)
Stage 4: Threat analysis (threat intelligence, attack patterns)
Stage 5: Vulnerability and weakness analysis (SAST, DAST results)
Stage 6: Attack modeling (attack trees, threat scenarios)
Stage 7: Risk and impact analysis (prioritize by business impact)
```

---

## References

- [OWASP Threat Modeling](https://owasp.org/www-community/Application_Threat_Modeling)
- [Microsoft STRIDE](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool)
- [PASTA methodology](https://versprite.com/blog/what-is-pasta-threat-modeling/)
- [Google Design Doc: Threat Modeling](https://security.googleblog.com/2020/04/threat-modeling-for-google-cloud.html)

---

← [Previous: Application Security](./application-security.md) | [Home](../README.md) | [Next: Compliance →](./compliance.md)
