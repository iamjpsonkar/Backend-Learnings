← [Previous: CodePipeline](../12-cicd/codepipeline.md) | [Home](../../README.md) | [Next: CloudFormation →](./cloudformation.md)

---

# AWS Infrastructure as Code

Infrastructure as Code (IaC) treats your cloud resources as software: version-controlled, peer-reviewed, and repeatable.

---

## IaC Tool Selection

| Tool | Language | State | Scope |
|------|----------|-------|-------|
| **CloudFormation** | YAML/JSON | AWS-managed | AWS only |
| **AWS CDK** | Python, TypeScript, Java, C#, Go | CloudFormation (synthesized) | AWS only |
| **Terraform / OpenTofu** | HCL | State file (S3 backend) | Multi-cloud |

**Guidance:**
- AWS-only shop, prefer declarative YAML → CloudFormation
- AWS-only shop, prefer code → CDK (compiles to CloudFormation)
- Multi-cloud or existing Terraform expertise → Terraform/OpenTofu

---

## Topics

| File | Description |
|------|-------------|
| [cloudformation.md](./cloudformation.md) | Stacks, templates, change sets, nested stacks, drift detection |
| [cdk.md](./cdk.md) | CDK constructs, stacks, context, aspects, testing |
| [terraform-on-aws.md](./terraform-on-aws.md) | AWS provider, remote state in S3, modules, workspaces |

---

## Minimum Competency Checklist

- [ ] Write a CloudFormation template that creates a VPC + EC2 instance + Security Group
- [ ] Create a stack, update it via a change set, and delete it cleanly
- [ ] Write a CDK stack in Python that deploys a Lambda function behind an API Gateway
- [ ] Configure Terraform with S3 remote state and DynamoDB state locking
- [ ] Use Terraform modules to encapsulate a VPC pattern

---

## References

- [CloudFormation documentation](https://docs.aws.amazon.com/cloudformation/latest/userguide/)
- [AWS CDK documentation](https://docs.aws.amazon.com/cdk/v2/guide/)
- [Terraform AWS provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
---

← [Previous: CodePipeline](../12-cicd/codepipeline.md) | [Home](../../README.md) | [Next: CloudFormation →](./cloudformation.md)
