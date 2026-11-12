← [Previous: AWS](../README.md) | [Home](../../README.md) | [Next: Account Setup →](./account-setup.md)

---

# AWS Account Setup

Before building anything in AWS, you need a secure account foundation. Accounts that skip this step become security incidents.

---

## Topics

| File | What it covers |
|------|---------------|
| [account-setup.md](account-setup.md) | Root account security, MFA, CloudTrail, GuardDuty, day-one hardening |
| [billing-budgets.md](billing-budgets.md) | Cost Explorer, Budgets, billing alerts, cost allocation tags |
| [cli-setup.md](cli-setup.md) | AWS CLI v2 installation, named profiles, credential chain, SSO login |

---

## Day-One Checklist

```
[ ] Root account: enable MFA (hardware key or TOTP app)
[ ] Root account: delete all access keys
[ ] Root account: set strong unique password; never use for daily work
[ ] Create an admin IAM Identity Center user or IAM admin user
[ ] Enable CloudTrail in all regions (management events)
[ ] Enable GuardDuty in all regions
[ ] Block S3 Public Access at the account level
[ ] Enable EBS default encryption in each region you use
[ ] Set a billing budget with email alerts ($50 / $100 / $500)
[ ] Tag every resource: Environment, Owner, Project
```

---

## References

- [AWS Security best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Well-Architected Framework — Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/)
---

← [Previous: AWS](../README.md) | [Home](../../README.md) | [Next: Account Setup →](./account-setup.md)
