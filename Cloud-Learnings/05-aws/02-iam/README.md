← [Previous: CLI Setup](../01-account-setup/cli-setup.md) | [Home](../../README.md) | [Next: IAM Overview →](./iam-overview.md)

---

# AWS IAM — Identity and Access Management

IAM is the foundation of AWS security. Every API call is authenticated (who are you?) and authorised (what are you allowed to do?) through IAM.

---

## Topics

| File | What it covers |
|------|---------------|
| [iam-overview.md](iam-overview.md) | IAM concepts, principals, authentication, authorisation flow |
| [users-groups-roles.md](users-groups-roles.md) | IAM users, groups, roles, instance profiles, trust policies |
| [policies.md](policies.md) | Policy types, JSON structure, conditions, evaluation logic |
| [organizations-scp.md](organizations-scp.md) | AWS Organizations, OUs, Service Control Policies |
| [identity-center.md](identity-center.md) | IAM Identity Center (SSO), permission sets, SCIM provisioning |

---

## Key Concepts at a Glance

| Concept | One-liner |
|---------|----------|
| **Principal** | Who is making the request (user, role, service, account) |
| **Policy** | JSON document defining what actions are allowed/denied |
| **IAM User** | Long-term identity for a human or application (use sparingly) |
| **IAM Role** | Temporary identity assumed by services, EC2, Lambda, CI/CD |
| **IAM Group** | Collection of users that share policies |
| **Permission boundary** | Maximum permissions a user or role can ever have |
| **SCP** | Maximum permissions any account in an OU can ever have |

---

## References

- [IAM documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/)
- [IAM policy reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies.html)
- [AWS Organizations documentation](https://docs.aws.amazon.com/organizations/latest/userguide/)
---

← [Previous: CLI Setup](../01-account-setup/cli-setup.md) | [Home](../../README.md) | [Next: IAM Overview →](./iam-overview.md)
