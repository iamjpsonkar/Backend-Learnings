← [Previous: Production Pipelines](../13-cicd-gitops/production-pipelines.md) | [Home](../README.md) | [Next: IAM & Least Privilege →](./iam-least-privilege.md)

---

# Cloud Security

Security is not a feature — it is a baseline requirement. This section covers the security controls, tools, and practices that protect cloud infrastructure and applications.

---

## Security Domains

| Domain | What it covers |
|--------|----------------|
| **Identity & Access** | IAM, least privilege, service accounts, federation |
| **Network Security** | VPCs, firewalls, WAF, DDoS, private endpoints |
| **Secrets Management** | Vaults, rotation, no plaintext secrets |
| **Encryption** | At-rest, in-transit, key management, HSMs |
| **Vulnerability Management** | CVE scanning, patching, SBOM |
| **Application Security** | SAST, DAST, dependency auditing |
| **Threat Modeling** | STRIDE, attack surface, data flow analysis |
| **Compliance** | SOC 2, PCI-DSS, HIPAA, ISO 27001, CIS |
| **Incident Response** | Detection, containment, eradication |
| **Supply Chain Security** | SLSA, image signing, provenance |

---

## Shared Responsibility Model (Quick Reference)

| Cloud component | AWS/Azure/GCP responsibility | Your responsibility |
|-----------------|------------------------------|---------------------|
| Physical hardware | ✅ | |
| Hypervisor / host OS | ✅ | |
| Managed service (RDS, GCS, etc.) | ✅ (service) | Config, data, access |
| VM OS (EC2, Compute Engine) | | ✅ patching, hardening |
| Application code | | ✅ |
| IAM / access policies | | ✅ |
| Data classification | | ✅ |
| Network configuration | Shared | Shared |

---

## Topics

| File | Topics |
|------|--------|
| [IAM & Least Privilege](./iam-least-privilege.md) | Permission boundaries, SCPs, conditions, auditing |
| [Network Security](./network-security.md) | VPCs, security groups, WAF, private endpoints |
| [Secrets Management](./secrets-management.md) | Vaults, rotation, no-secrets-in-code patterns |
| [Encryption](./encryption.md) | KMS, HSM, envelope encryption, TLS, at-rest |
| [Vulnerability Management](./vulnerability-management.md) | CVE scanning, SBOM, patching cadence |
| [Application Security](./application-security.md) | SAST, DAST, dependency audit, secure coding |
| [Threat Modeling](./threat-modeling.md) | STRIDE, data flow, attack surface reduction |
| [Compliance](./compliance.md) | SOC 2, PCI-DSS, HIPAA, ISO 27001, CIS benchmarks |
| [Incident Response](./incident-response.md) | Detection, containment, eradication, lessons learned |
| [Supply Chain Security](./supply-chain-security.md) | SLSA, SBOM, image signing, Sigstore |
| [Security Checklist](./security-checklist.md) | Pre-launch and operational security checklist |

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Cloud Security Alliance](https://cloudsecurityalliance.org/)

---

← [Previous: Production Pipelines](../13-cicd-gitops/production-pipelines.md) | [Home](../README.md) | [Next: IAM & Least Privilege →](./iam-least-privilege.md)
