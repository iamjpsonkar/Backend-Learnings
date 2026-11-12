← [Previous: Step Functions](../08-serverless/step-functions.md) | [Home](../../README.md) | [Next: KMS →](./kms.md)

---

# AWS Security

Security in AWS is a shared responsibility. AWS secures the infrastructure; you secure what runs on it. This section covers the core AWS security services: encryption (KMS), secrets management, threat detection (GuardDuty), compliance aggregation (Security Hub), edge protection (WAF + Shield), and TLS certificates (ACM).

---

## Contents

| File | Description |
|------|-------------|
| [kms.md](./kms.md) | KMS — CMKs, key policies, envelope encryption, grants |
| [secrets-manager.md](./secrets-manager.md) | Secrets Manager — storage, rotation, cross-account access |
| [guardduty.md](./guardduty.md) | GuardDuty — ML-based threat detection, finding types, remediation |
| [security-hub.md](./security-hub.md) | Security Hub — aggregated findings, CSPM standards, custom actions |
| [waf-shield.md](./waf-shield.md) | WAF — web ACLs, managed rules; Shield — DDoS protection |
| [acm.md](./acm.md) | ACM — certificate provisioning, validation, renewal, private CA |

---

## Security Layers

```
Edge (CloudFront / API Gateway)
  └── WAF web ACL (SQLi, XSS, geo-blocking, rate limits)
      └── Shield Advanced (DDoS, 24/7 DRT support)

Identity
  └── IAM least-privilege + SCPs + Permission Boundaries
      └── IAM Identity Center (SSO) + MFA enforced

Network
  └── Security Groups (stateful, ENI-level)
      └── NACLs (stateless, subnet-level)
          └── VPC endpoints (no internet for AWS API calls)

Data at Rest
  └── KMS CMKs (S3, EBS, RDS, DynamoDB, Secrets Manager)

Data in Transit
  └── TLS everywhere — ACM certificates on ALB, CloudFront, API Gateway

Threat Detection
  └── GuardDuty (anomaly, threat intel, ML)
      └── Security Hub (aggregate findings from GuardDuty, Inspector, Macie)

Audit
  └── CloudTrail (API audit log)
      └── AWS Config (resource config history + compliance rules)
```

---

## Minimum Competency Checklist

- [ ] Create a KMS CMK with a key policy and rotate it annually
- [ ] Store and retrieve a secret from Secrets Manager with auto-rotation
- [ ] Enable GuardDuty and explain the three finding categories
- [ ] Enable Security Hub and understand AWS Foundational Security Best Practices
- [ ] Create a WAF web ACL with AWS Managed Rules attached to an ALB
- [ ] Provision and validate an ACM public certificate via DNS validation
- [ ] Distinguish ACM public vs ACM Private CA
---

← [Previous: Step Functions](../08-serverless/step-functions.md) | [Home](../../README.md) | [Next: KMS →](./kms.md)
