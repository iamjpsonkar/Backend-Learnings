← [Previous: Supply Chain Security](./supply-chain-security.md) | [Home](../README.md) | [Next: Observability →](../15-observability/README.md)

---

# Security Checklist

A pre-launch and operational security checklist covering the most impactful controls. Complete the Pre-Launch checklist before any public-facing service goes live. Review the Operational checklist quarterly.

---

## Pre-Launch Checklist

### Identity & Access

- [ ] No IAM users with console access without MFA
- [ ] Root account MFA enabled; root access keys deleted
- [ ] All services use IAM roles, not long-lived access keys
- [ ] IAM roles follow least-privilege (no `*:*` unless absolutely justified)
- [ ] Permission boundaries set for developer-created roles
- [ ] SCPs in place to restrict dangerous actions at org level
- [ ] OIDC federation configured for CI/CD (no stored AWS credentials)

### Network Security

- [ ] No security group allows 0.0.0.0/0 to port 22 or 3389
- [ ] Application servers in private subnets (no public IP)
- [ ] Databases in isolated data subnets with no internet route
- [ ] WAF attached to all public-facing load balancers
- [ ] VPC endpoints configured for AWS services (S3, Secrets Manager, KMS)
- [ ] VPC Flow Logs enabled
- [ ] NACLs reviewed for subnet-level blocking

### Encryption

- [ ] All data at rest encrypted (S3 SSE-KMS, RDS encrypted, EBS encrypted)
- [ ] TLS 1.2+ enforced everywhere; TLS 1.0/1.1 disabled
- [ ] HTTP → HTTPS redirect in place
- [ ] HSTS header set with min 1-year max-age
- [ ] No plaintext secrets in environment variables, code, or container images
- [ ] KMS CMKs in use for sensitive workloads (not AWS-managed default keys)
- [ ] Key rotation enabled on all KMS CMKs

### Secrets Management

- [ ] All secrets in AWS Secrets Manager / HashiCorp Vault / GCP Secret Manager
- [ ] No secrets in Git (git-secrets or gitleaks pre-commit hook installed)
- [ ] Secret rotation configured for database credentials
- [ ] Secrets Manager resource policies restrict access to specific roles

### Container Security

- [ ] Container images scanned with Trivy (0 CRITICAL, 0 HIGH unpatched)
- [ ] Images run as non-root user
- [ ] Read-only root filesystem where possible
- [ ] No privileged containers
- [ ] Images pinned to digest (not mutable tags like `latest`)
- [ ] Images signed with Cosign
- [ ] SBOM generated and stored

### Kubernetes (if applicable)

- [ ] Pod Security Admission enforced (restricted profile)
- [ ] Network Policies: default deny, explicit allow
- [ ] RBAC: no wildcard permissions; no cluster-admin for workloads
- [ ] Secrets not mounted as environment variables (use volume mounts or ESO)
- [ ] `runAsNonRoot: true` and `readOnlyRootFilesystem: true` in securityContext
- [ ] Resource limits set on all containers
- [ ] kube-bench CIS benchmark: 0 FAIL on critical controls

### Application Security

- [ ] SAST scan run (Bandit/Semgrep/CodeQL); critical/high findings resolved
- [ ] Dependency audit run; no known HIGH/CRITICAL CVEs
- [ ] Input validation on all user-controlled inputs
- [ ] No SQL injection vectors (parameterized queries everywhere)
- [ ] Security headers configured (CSP, HSTS, X-Frame-Options, etc.)
- [ ] CORS policy restrictive (not `*` in production)
- [ ] Rate limiting on public APIs
- [ ] DAST scan run on staging environment (ZAP baseline)

### Logging & Monitoring

- [ ] CloudTrail enabled in all regions with log file validation
- [ ] CloudTrail logs shipped to S3 with MFA delete enabled
- [ ] GuardDuty enabled in all regions
- [ ] Security Hub enabled with CIS benchmark
- [ ] Application logs structured (no secrets in logs)
- [ ] Alerts on: root account usage, IAM changes, SG changes, failed logins
- [ ] Log retention ≥ 90 days hot, ≥ 1 year cold (adjust for compliance)

### Incident Response

- [ ] IR runbooks written and accessible to on-call
- [ ] Escalation path documented (who to call at 2am)
- [ ] Incident communication channel ready (Slack #incidents)
- [ ] GuardDuty findings routed to on-call via PagerDuty/OpsGenie
- [ ] Tabletop exercise run in last 6 months

### Compliance

- [ ] Data classification complete (PII, PCI, PHI identified)
- [ ] Data retention and deletion policies implemented
- [ ] Privacy policy current and accurate
- [ ] Vendor BAAs in place for HIPAA-covered services
- [ ] SOC 2 evidence collection automated (Config, CloudTrail)

---

## Operational Checklist (Quarterly)

### Review & Audit

- [ ] IAM Access Analyzer: review and resolve unused permissions
- [ ] List all IAM access keys older than 90 days → rotate or delete
- [ ] Review all IAM users with console access → confirm still needed
- [ ] Review security group rules for drift from baseline
- [ ] Review S3 bucket ACLs and public access settings
- [ ] Run CIS benchmark scan → review new failures

### Patching

- [ ] OS patches applied within SLA (critical: 7 days, high: 30 days)
- [ ] Container base images rebuilt with latest patches
- [ ] Kubernetes version within N-1 of latest supported
- [ ] Third-party dependencies updated (check for deprecated packages)

### Certificates

- [ ] All TLS certificates valid for > 30 days
- [ ] Certificate auto-renewal tested (certbot/ACM)
- [ ] Wildcard certs reviewed (scope them appropriately)

### Access Reviews

- [ ] Offboard departed employees from all systems
- [ ] Review service account permissions for deprecated services
- [ ] Rotate any credentials not in automated rotation
- [ ] Review third-party app OAuth permissions

### Testing

- [ ] Penetration test (annually for external surface)
- [ ] Internal red team exercise or tabletop
- [ ] DR failover test (can you actually restore from backup?)
- [ ] Incident response drill

---

## Quick Wins (Do These First)

If you're starting from scratch, these controls provide the highest risk reduction per unit of effort:

| Priority | Control | Why |
|----------|---------|-----|
| 1 | Enable MFA on all accounts | Stops most credential-based attacks |
| 2 | Delete root access keys | Root compromise = full account takeover |
| 3 | Enable GuardDuty | Automatic threat detection, low false positives |
| 4 | No secrets in Git | Prevents credential exfiltration at the source |
| 5 | Private subnets for workloads | Reduces attack surface dramatically |
| 6 | TLS everywhere + HSTS | Stops network interception |
| 7 | Structured logs + CloudTrail | Required for any incident investigation |
| 8 | WAF on public endpoints | Blocks most commodity web attacks |
| 9 | Dependency scanning in CI | Catches vulnerabilities before production |
| 10 | Least-privilege IAM roles | Limits blast radius of any compromise |

---

## References

- [AWS Security Best Practices](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- [OWASP Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/)
- [Cloud Security Alliance Cloud Controls Matrix](https://cloudsecurityalliance.org/research/cloud-controls-matrix/)

---

← [Previous: Supply Chain Security](./supply-chain-security.md) | [Home](../README.md) | [Next: Observability →](../15-observability/README.md)
