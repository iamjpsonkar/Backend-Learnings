← [Previous: CDN](./cdn.md) | [Home](../README.md) | [Next: Networking Troubleshooting →](./troubleshooting.md)

---

# Zero Trust Networking

Zero Trust is a security model based on the principle "**never trust, always verify**". It replaces the traditional perimeter (castle-and-moat) model — where everything inside the network is trusted — with per-request authentication and authorisation regardless of network location.

---

## The Problem with Perimeter Security

Traditional model:

```
─────────────────────────────────────────────
│              Corporate Network             │
│  (inside = trusted, outside = untrusted)  │
│                                           │
│  Laptop → server → database (all trusted) │
─────────────────────────────────────────────
        ▲
    Firewall
        │
  Untrusted internet
```

**Failures of the perimeter model:**
- Insider threats: malicious or compromised internal users have broad access
- Lateral movement: an attacker who gets inside can reach everything
- VPN gives full network access — one stolen credential = full breach
- Cloud + SaaS mean the "perimeter" no longer exists
- Remote work and BYOD dissolve the physical perimeter

---

## Zero Trust Principles

1. **Verify explicitly**: always authenticate and authorise based on all available signals (identity, device, location, behaviour, service health)
2. **Use least privilege access**: limit access to exactly what is needed, for the minimum time required (JIT — just-in-time access)
3. **Assume breach**: design as if attackers are already inside — segment networks, encrypt internally, log everything, monitor for anomalies

---

## Zero Trust Architecture Components

```
User/Device                  Identity Provider              Resource
    │                               │                          │
    │── 1. Authenticate ───────────▶│                          │
    │◀── 2. Identity token ──────────│                          │
    │                               │                          │
    │── 3. Request resource + token ────────────────────────▶  │
    │                     [Policy Engine: verify token,        │
    │                      device posture, context]            │
    │◀── 4. Allow/deny + audit log ─────────────────────────── │
```

### Key Components

| Component | Purpose | AWS example |
|-----------|---------|-------------|
| **Identity Provider (IdP)** | Authenticate users and workloads | AWS IAM Identity Center, Cognito |
| **Policy Engine** | Evaluate access requests against policy | IAM policies, Cedar (Verified Permissions) |
| **Device Posture** | Assess device health before granting access | AWS Verified Access |
| **Micro-segmentation** | Fine-grained network isolation | Security groups per service, private subnets |
| **Mutual TLS (mTLS)** | Both sides present certificates | AWS App Mesh, ACM Private CA |
| **Just-In-Time access** | Grant elevated privileges only when needed, auto-expire | AWS IAM Roles Anywhere, temporary STS credentials |
| **Continuous monitoring** | Detect anomalies in real time | CloudTrail, GuardDuty, Security Hub |

---

## Identity-Aware Access (BeyondCorp Pattern)

Google's BeyondCorp pioneered moving access control from VPN to an identity-aware proxy:

```
Old model:  Employee → VPN → internal network → app
Zero Trust: Employee → Identity-Aware Proxy → [verify identity + device] → app
```

The app is never directly exposed to the network; the proxy enforces identity, device compliance, and context before forwarding the request.

**AWS equivalent: AWS Verified Access**

```bash
# Create a Verified Access trust provider (OIDC-based)
aws ec2 create-verified-access-trust-provider \
    --trust-provider-type user \
    --user-trust-provider-type oidc \
    --oidc-options '{
        "Issuer": "https://accounts.google.com",
        "AuthorizationEndpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        "TokenEndpoint": "https://oauth2.googleapis.com/token",
        "UserInfoEndpoint": "https://openid.googleapis.com/v1/userinfo",
        "ClientId": "my-client-id",
        "ClientSecret": "my-client-secret",
        "Scope": "openid email profile"
    }' \
    --description "Google OIDC"

# Attach to a Verified Access instance and create access groups with policies
# Policy example (Cedar):
# permit(
#   principal,
#   action == AWS::VerifiedAccess::HTTP::Action::"GET",
#   resource
# )
# when {
#   context.oidc.email.endsWith("@example.com")
#   && context.http.request.http_method == "GET"
# };
```

---

## Workload Identity (Service-to-Service)

In Zero Trust, services also authenticate to each other — not just users.

### IAM Roles (AWS Workload Identity)

EC2 instances, Lambda functions, and ECS tasks assume IAM roles. Credentials are automatically rotated by the metadata service. No hard-coded keys.

```bash
# Instance metadata delivers temporary credentials
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/my-role-name
# Returns: AccessKeyId, SecretAccessKey, Token, Expiration (rotates automatically)

# Applications use the SDK — credentials are picked up automatically
import boto3
s3 = boto3.client('s3')   # uses role credentials, never hard-coded keys
```

### Kubernetes Service Accounts (IRSA — IAM Roles for Service Accounts)

```yaml
# Pod's service account is annotated with an IAM role ARN
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-app-role
```

### SPIFFE/SPIRE — Universal Workload Identity

SPIFFE (Secure Production Identity Framework For Everyone) provides cryptographic identities to workloads via X.509 SVIDs (SPIFFE Verifiable Identity Documents):

```
spiffe://cluster.example.com/ns/production/sa/payment-service
```

Used by service meshes (Istio, Linkerd) to implement mTLS between services automatically, without managing certificates manually.

---

## Mutual TLS (mTLS)

Standard TLS: client verifies server's certificate.
mTLS: **both** client and server verify each other's certificates.

```
Client Service                         Server Service
     │── ClientHello ────────────────▶ │
     │◀── ServerHello + ServerCert ─── │
     │── ClientCert + ClientVerify ──▶ │   ← mTLS: client presents its cert too
     │   [both verify each other]      │
     │══════════ Encrypted data ══════ │
```

**Benefits:**
- Service identity is cryptographic — not based on IP or network position
- Any service without a valid cert is rejected, even if it's inside the network
- Enables zero-trust service mesh

**AWS implementation with App Mesh + ACM Private CA:**

```bash
# Create a private CA
aws acm-pca create-certificate-authority \
    --certificate-authority-configuration '{
        "KeyAlgorithm": "RSA_2048",
        "SigningAlgorithm": "SHA256WITHRSA",
        "Subject": {
            "Country": "US",
            "Organization": "My Company",
            "CommonName": "Internal CA"
        }
    }' \
    --certificate-authority-type ROOT

# App Mesh virtual node with mTLS
aws appmesh update-virtual-node \
    --mesh-name my-mesh \
    --virtual-node-name payment-service \
    --spec '{
        "listeners": [{
            "tls": {
                "mode": "STRICT",
                "certificate": {"acm": {"certificateArn": "arn:aws:acm:..."}},
                "validation": {"trust": {"acm": {"certificateAuthorityArns": ["arn:aws:acm-pca:..."]}}}
            }
        }]
    }'
```

---

## Micro-Segmentation

Divide the network into small segments where each service can only reach the services it legitimately needs.

### AWS Implementation: Security Group per Service

```
SG Rules (principle of least privilege):
  sg-frontend:
    Inbound:  443 from ALB sg
    Outbound: 8080 to sg-api
  sg-api:
    Inbound:  8080 from sg-frontend
    Outbound: 5432 to sg-database, 6379 to sg-cache
  sg-database:
    Inbound:  5432 from sg-api only
    Outbound: (deny all)
```

No CIDR ranges — reference security groups by ID. This means only the specific services you intend can talk to each other, regardless of what IP they have.

### VPC Endpoints — Never Traverse the Internet

Use VPC Endpoints (PrivateLink) to access AWS services (S3, DynamoDB, SSM, Secrets Manager) without leaving your VPC:

```bash
# Create a Gateway endpoint for S3
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-0def5678 \
    --service-name com.amazonaws.us-east-1.s3 \
    --route-table-ids rtb-0abc1234 \
    --vpc-endpoint-type Gateway

# Create an Interface endpoint for Secrets Manager
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-0def5678 \
    --service-name com.amazonaws.us-east-1.secretsmanager \
    --vpc-endpoint-type Interface \
    --subnet-ids subnet-az-a subnet-az-b \
    --security-group-ids sg-vpc-endpoint
```

---

## Zero Trust Checklist

### Identity

- [ ] No hardcoded credentials — all workloads use IAM roles or SPIFFE SVIDs
- [ ] MFA enforced for all human access (console, VPN, IdP)
- [ ] Short-lived credentials only (STS tokens, OIDC JWTs)
- [ ] Privileged access is just-in-time and logged (AWS IAM Identity Center with permission sets)

### Network

- [ ] All services communicate over TLS (internal + external)
- [ ] mTLS for service-to-service in sensitive environments
- [ ] Security groups follow least privilege (no 0.0.0.0/0 inbound on internal ports)
- [ ] No direct SSH/RDP — use SSM Session Manager
- [ ] VPC endpoints for AWS service access

### Monitoring

- [ ] All API calls logged (CloudTrail with log file validation)
- [ ] GuardDuty enabled in all regions
- [ ] Anomaly alerts for unusual cross-service access patterns
- [ ] Access logs retained and queryable

### Data

- [ ] All data encrypted at rest and in transit
- [ ] KMS key policies grant access by identity, not by network
- [ ] No bucket or resource policies with `Principal: "*"` without conditions

---

## References

- [NIST SP 800-207 — Zero Trust Architecture](https://csrc.nist.gov/publications/detail/sp/800-207/final)
- [Google BeyondCorp whitepaper](https://cloud.google.com/beyondcorp)
- [AWS Verified Access documentation](https://docs.aws.amazon.com/verified-access/latest/ug/)
- [SPIFFE/SPIRE project](https://spiffe.io/)
- [CISA Zero Trust Maturity Model](https://www.cisa.gov/zero-trust-maturity-model)
---

← [Previous: CDN](./cdn.md) | [Home](../README.md) | [Next: Networking Troubleshooting →](./troubleshooting.md)
