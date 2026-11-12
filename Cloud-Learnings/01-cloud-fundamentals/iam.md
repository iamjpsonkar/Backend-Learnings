← [Previous: Databases](./databases.md) | [Home](../README.md) | [Next: Serverless →](./serverless.md)

---

# Identity and Access Management (IAM) Fundamentals

## The Core Problem IAM Solves

Every API call to a cloud provider answers two questions:

1. **Authentication**: Who is making this request? (Are you who you say you are?)
2. **Authorization**: Are you allowed to do this? (Do you have permission?)

IAM is the system that answers both questions for every single operation — creating a VM, uploading a file, reading a secret, deleting a database.

Getting IAM wrong is the most common source of cloud security incidents.

---

## Key Concepts

### Principal

A **principal** is any entity that can make authenticated requests to cloud resources.

Types of principals:

| Type | Description | Examples |
|------|-------------|---------|
| Human user | A person who logs in | Developer, admin, auditor |
| Service account / role | A machine identity for workloads | EC2 instance, Lambda function, CI/CD pipeline |
| Group | A collection of users | `developers`, `ops-team` |
| Federated identity | External identity provider user | Google Workspace, Active Directory, GitHub Actions OIDC |

### Policy / Permission

A **policy** is a document that defines what actions are allowed or denied on what resources.

**AWS IAM policy example (JSON):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ]
    }
  ]
}
```

This policy allows reading objects from `my-bucket` and nothing else.

### Role

A **role** is a set of permissions that can be assumed by principals. Roles issue temporary credentials.

Key insight: **Roles are better than users for machine identities.** An EC2 instance that assumes a role gets temporary credentials automatically rotated every hour. A user with long-lived access keys that expire in years is a security risk.

```
EC2 Instance → Assumes IAM Role → Gets temporary credentials (1hr)
                                 → Calls S3 API with those credentials
                                 → Credentials expire → New ones issued automatically
```

---

## Least Privilege Principle

**Grant only the permissions required to perform the intended task — nothing more.**

This is the most important IAM principle. If a Lambda function only needs to read from one DynamoDB table, its IAM role should have permission to read only that table, not all DynamoDB tables and not any other service.

### Why Least Privilege Matters

If a resource is compromised:
- **Overprivileged**: Attacker can read all S3 buckets, delete EC2 instances, exfiltrate secrets
- **Least privilege**: Attacker can only do what that resource was permitted to do

### Applying Least Privilege

1. **Start with no permissions** — add only what is explicitly needed
2. **Scope by resource** — use specific ARNs, not `"Resource": "*"`
3. **Scope by action** — use specific actions, not `"Action": "*"`
4. **Review regularly** — IAM Access Analyzer, AWS Trusted Advisor, Azure Advisor flag unused permissions
5. **Use permission boundaries** — cap the maximum permissions an identity can have

---

## Authentication Methods

### Username and Password (Humans)

For humans logging into the cloud console. Always require MFA.

### Access Keys (Programmatic)

Long-lived credentials (access key ID + secret access key) for CLI and SDK access. **High risk if leaked.**

Best practice: **Don't use long-lived access keys.** Use:
- IAM roles for services running on cloud infrastructure
- IAM Identity Center (AWS SSO) for human CLI access with temporary credentials
- OIDC federation for CI/CD pipelines (GitHub Actions, GitLab CI)

### IAM Roles and Temporary Credentials

The preferred mechanism for machine-to-machine access. Roles issue temporary credentials via AWS STS (Security Token Service) that automatically expire.

```
GitHub Actions workflow
  → Authenticates via OIDC token to AWS
  → Assumes IAM role: github-actions-deploy
  → Gets temporary credentials (1 hour)
  → Deploys to ECS
  → Credentials expire (no cleanup needed)
```

### Instance Profiles (EC2)

An IAM role attached to an EC2 instance. The EC2 metadata service (`169.254.169.254`) vends temporary credentials to any process running on the instance.

```bash
# Any process on EC2 can retrieve credentials without any config:
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/my-role-name
```

AWS SDKs use this automatically. You don't need to hard-code credentials in your application.

---

## Provider-Specific IAM

### AWS IAM

**Policy types:**
- **Identity-based policies**: Attached to users, groups, or roles — define what that identity can do
- **Resource-based policies**: Attached to resources (S3 bucket policy, KMS key policy) — define who can access that resource
- **Permission boundaries**: Max permissions an identity can have (even if their identity policy allows more)
- **SCPs (Service Control Policies)**: Applied at AWS Organization level — restrict what accounts can do

**Policy evaluation logic:**
1. Explicit Deny in any policy → **Deny** (always wins)
2. SCP doesn't allow → **Deny**
3. No applicable allow → **Deny**
4. All applicable policies allow → **Allow**

**IAM Identity Center (SSO):**
The modern way to manage human access. Connects to your identity provider (Okta, Active Directory, Google Workspace). Users log in once and get temporary credentials for AWS accounts. No long-lived access keys.

### Azure IAM (RBAC)

Azure uses **Role-Based Access Control (RBAC)**. You assign roles to principals at a scope.

**Scopes (hierarchy):**
```
Management Group → Subscription → Resource Group → Resource
```

Assigning a role at a higher scope gives access to everything below it.

**Built-in roles:**
| Role | Access |
|------|--------|
| Owner | Full access + manage access |
| Contributor | Full access to resources, no RBAC management |
| Reader | Read-only access |
| Custom roles | Specific permissions you define |

**Azure Managed Identity:** The Azure equivalent of AWS IAM roles for machines. A VM or Function with a managed identity automatically gets credentials without any keys.

### GCP IAM

GCP uses **policy bindings** at each resource level. A policy binding associates a principal (member) with a role on a resource.

**Resource hierarchy:** Organization → Folder → Project → Resource

Policies are inherited down the hierarchy. A role granted at folder level applies to all projects in that folder.

**GCP service accounts:** Machine identities in GCP (equivalent to IAM roles in AWS). Service accounts are principals that can be granted roles, and also the identity that compute resources (GCE, Cloud Run) run as.

**Workload Identity Federation:** Allow workloads outside GCP (GitHub Actions, AWS Lambda) to authenticate to GCP without service account keys.

---

## Common IAM Patterns

### EC2 Accessing S3 (AWS)

```
1. Create IAM role: ec2-s3-read-role
   Policy: Allow s3:GetObject on arn:aws:s3:::my-bucket/*

2. Create instance profile with ec2-s3-read-role

3. Launch EC2 with the instance profile

4. In application code:
   import boto3
   s3 = boto3.client('s3')  # Credentials from instance metadata automatically
   s3.get_object(Bucket='my-bucket', Key='file.txt')
```

### Lambda Accessing DynamoDB (AWS)

```
1. Create IAM role: lambda-dynamodb-role
   Trust policy: Allow lambda.amazonaws.com to assume this role
   Permission policy: Allow dynamodb:GetItem, PutItem on specific table ARN

2. Assign role to Lambda function at creation/update

3. Lambda SDK uses role credentials automatically
```

### GitHub Actions Deploying to AWS (OIDC)

```yaml
# No long-lived AWS keys stored in GitHub secrets
permissions:
  id-token: write   # Required for OIDC

- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
    aws-region: us-east-1
```

---

## IAM Anti-Patterns to Avoid

| Anti-pattern | Risk | Better approach |
|-------------|------|----------------|
| `"Action": "*", "Resource": "*"` | Full account access — any compromise is catastrophic | Specific actions and ARNs |
| Long-lived access keys for services | Keys can be leaked, no expiry | IAM roles with instance profiles or OIDC |
| Sharing access keys between services | Incident scope is the entire key, not one service | One role per service |
| No MFA on admin accounts | Single factor → single point of failure | Always require MFA for humans |
| Root account for daily work | Root cannot be restricted | Create an IAM admin user, lock root away |
| IAM user per developer long-term | Access keys accumulate; hard to audit | IAM Identity Center (SSO) |
| `AdministratorAccess` for automation | Over-privileged CI/CD pipeline | Scope to exactly the actions the pipeline needs |

---

## References

- [AWS IAM documentation](https://docs.aws.amazon.com/iam/)
- [AWS IAM best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS IAM Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html)
- [Azure RBAC documentation](https://learn.microsoft.com/en-us/azure/role-based-access-control/overview)
- [GCP IAM overview](https://cloud.google.com/iam/docs/overview)
- [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
---

← [Previous: Databases](./databases.md) | [Home](../README.md) | [Next: Serverless →](./serverless.md)
