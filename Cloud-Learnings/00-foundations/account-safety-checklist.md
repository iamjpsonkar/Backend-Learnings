← [Previous: Billing Basics](./billing-basics.md) | [Home](../README.md) | [Next: Cloud Fundamentals →](../01-cloud-fundamentals/README.md)

---

# New Cloud Account Safety Checklist

Complete these steps within the first hour of creating any new cloud account. These are the minimum security controls that should be in place before you deploy anything.

---

## AWS New Account Checklist

### Root Account

- [ ] **Enable MFA on the root account** — Use a hardware key (YubiKey) or authenticator app. The root account has unrestricted access and cannot be locked down by IAM policies.

  ```
  AWS Console → Account → Security credentials → Multi-factor authentication → Assign MFA
  ```

- [ ] **Do not create access keys for the root account** — If root access keys exist, delete them immediately.

  ```
  AWS Console → Account → Security credentials → Access keys → Delete (if any exist)
  ```

- [ ] **Set a strong root account password** — Use a password manager. Store the root credentials securely (not in a shared document).

- [ ] **Set up account recovery email and phone** — Ensure the account recovery contact details are accurate and accessible.

---

### Account-Level Settings

- [ ] **Set account alias** — Replace your account ID with a human-readable name.

  ```bash
  aws iam create-account-alias --account-alias my-company-prod
  ```

- [ ] **Enable CloudTrail in all regions** — Creates an audit log of every API call.

  ```bash
  aws cloudtrail create-trail \
    --name org-audit-trail \
    --s3-bucket-name my-cloudtrail-logs \
    --is-multi-region-trail \
    --enable-log-file-validation
  aws cloudtrail start-logging --name org-audit-trail
  ```

- [ ] **Enable AWS Config** — Tracks configuration changes to resources.

- [ ] **Enable GuardDuty** — Threat detection across VPC flow logs, DNS logs, and CloudTrail.

  ```bash
  aws guardduty create-detector --enable
  ```

- [ ] **Enable Security Hub** — Aggregates findings from GuardDuty, Macie, Inspector, and third-party tools.

- [ ] **Set up billing alerts** — Create a budget with email alert before you have unexpected spend.

  ```bash
  # Via Console: Billing → Budgets → Create budget
  # Set a monthly budget (e.g., $20 for a personal account) with alert at 80%
  ```

- [ ] **Block S3 public access at account level** — Prevents any S3 bucket in the account from being accidentally made public.

  ```bash
  aws s3control put-public-access-block \
    --account-id 123456789012 \
    --public-access-block-configuration \
      "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
  ```

- [ ] **Enable EBS default encryption** — All new EBS volumes will be encrypted by default.

  ```bash
  aws ec2 enable-ebs-encryption-by-default
  ```

---

### IAM Setup

- [ ] **Create an IAM admin user or role — do not use root for daily work**

  Create a user with `AdministratorAccess` policy for initial setup:

  ```bash
  aws iam create-user --user-name admin-bootstrap
  aws iam attach-user-policy \
    --user-name admin-bootstrap \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
  ```

  Then switch to using IAM Identity Center (SSO) for long-term human access.

- [ ] **Enable MFA on all IAM users with console access**

- [ ] **Do not create long-lived access keys for human users** — Use IAM Identity Center for CLI access (temporary credentials). If you must use access keys, set a rotation policy.

- [ ] **Apply least-privilege IAM policies** — Start with minimal permissions; add as needed. Avoid `*` in Action or Resource.

- [ ] **Enable IAM credential report** — Audit all users, their MFA status, key age, and last-used dates.

  ```bash
  aws iam generate-credential-report
  aws iam get-credential-report --query 'Content' --output text | base64 -d
  ```

- [ ] **Enable AWS IAM Access Analyzer** — Detects resources shared with external entities.

  ```bash
  aws accessanalyzer create-analyzer \
    --analyzer-name account-analyzer \
    --type ACCOUNT
  ```

---

### Networking Defaults

- [ ] **Review and harden the default VPC** — The default VPC has permissive settings. Either delete it or restrict its security groups before deploying workloads.

- [ ] **Do not use the default security group** — The default security group allows all inbound traffic from itself. Create purpose-specific security groups.

---

## Azure New Account Checklist

### Identity and Access

- [ ] **Enable MFA for all Azure AD (Entra ID) users** — Especially the global administrator account.
- [ ] **Do not use the global administrator account for daily work** — Create a dedicated admin user.
- [ ] **Enable Privileged Identity Management (PIM)** — Require just-in-time activation for admin roles. Reduces the window of exposure.
- [ ] **Configure Conditional Access policies** — Require MFA for all users, block legacy authentication protocols.
- [ ] **Enable Azure AD Identity Protection** — Detects risky sign-ins and compromised credentials.

### Subscription Settings

- [ ] **Set up billing alerts (Budget Alerts)** — Configure alerts on the subscription to prevent unexpected spend.
- [ ] **Enable Microsoft Defender for Cloud (free tier)** — Provides security recommendations and posture score.
- [ ] **Enable Azure Activity Log** — Audit log of all subscription-level operations. Send to a Log Analytics Workspace or Storage Account.
- [ ] **Enable Azure Policy** — Apply guardrails like "require tags", "allowed VM SKUs", "require encryption".

### Resource Defaults

- [ ] **Set a tagging policy** — Enforce required tags (`Environment`, `Owner`, `CostCenter`) via Azure Policy.
- [ ] **Enable soft delete for Key Vault** — Prevents accidental permanent deletion of secrets and keys.

---

## GCP New Account Checklist

### Organization and Identity

- [ ] **Set up Cloud Identity or Google Workspace** — Use organizational accounts, not personal Gmail accounts.
- [ ] **Enable 2-Step Verification for all users**
- [ ] **Enable Organization Policy constraints** — Restrict which resource types can be created, which regions are allowed.
- [ ] **Set up Resource Hierarchy** — Organization → Folders → Projects. Apply IAM policies at folder level where possible.

### Project Settings

- [ ] **Enable Cloud Audit Logs** — Admin Activity logs are always on; enable Data Access logs for sensitive projects.
- [ ] **Enable Security Command Center** — GCP's equivalent of AWS Security Hub.
- [ ] **Set up billing alerts** — Create budgets with email alerts on each project.
- [ ] **Enable VPC Service Controls** — Define a security perimeter around sensitive APIs.

---

## Universal Rules (All Providers)

These apply regardless of which cloud provider you use:

- [ ] Separate production, staging, and development into different accounts/subscriptions/projects
- [ ] Use infrastructure as code (Terraform, CDK, Bicep) from day one — never click through the console to create production resources
- [ ] Set up centralized logging immediately — logs are useless if they don't exist when you need them
- [ ] Test your backup/restore procedure before you need it
- [ ] Document who has access to the root/global admin account and review it quarterly

---

## References

- [AWS Security Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Well-Architected — Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- [Azure security baseline](https://learn.microsoft.com/en-us/security/benchmark/azure/security-baselines-overview)
- [GCP security best practices](https://cloud.google.com/security/best-practices)
- [CIS Cloud Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
---

← [Previous: Billing Basics](./billing-basics.md) | [Home](../README.md) | [Next: Cloud Fundamentals →](../01-cloud-fundamentals/README.md)
