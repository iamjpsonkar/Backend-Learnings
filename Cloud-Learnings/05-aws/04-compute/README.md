← [Previous: PrivateLink](../03-networking/privatelink.md) | [Home](../../README.md) | [Next: EC2 →](./ec2.md)

---

# AWS Compute

EC2 is the foundation of AWS compute: virtual machines you fully control. This section covers everything from launching instances to building auto-scaling fleets with load balancers, and running serverless functions with Lambda.

---

## Contents

| File | Description |
|------|-------------|
| [ec2.md](./ec2.md) | EC2 instances, AMIs, EBS, instance types, pricing |
| [ami-launch-templates.md](./ami-launch-templates.md) | Custom AMIs, launch templates, golden images |
| [auto-scaling.md](./auto-scaling.md) | Auto Scaling Groups, policies, lifecycle hooks |
| [load-balancers.md](./load-balancers.md) | ALB, NLB, GLB — listeners, rules, target groups |
| [lambda.md](./lambda.md) | Lambda functions, triggers, concurrency, layers |

---

## Compute Decision Tree

```
Need compute?
├── Always-on, stateful, or requires specific OS?
│   └── EC2 (with ASG + ALB for scale)
├── Containerized workload?
│   └── ECS Fargate or EKS (see 07-containers/)
├── Event-driven, short-lived, stateless?
│   └── Lambda (see lambda.md)
└── Batch/HPC workload?
    └── AWS Batch or EC2 Spot fleet
```

---

## Minimum Competency Checklist

- [ ] Launch an EC2 instance with a custom AMI in a private subnet
- [ ] Create a launch template with user data for bootstrap automation
- [ ] Build a custom AMI from a running instance
- [ ] Configure an Auto Scaling Group with min/max/desired capacity
- [ ] Set scaling policies (target tracking, step, scheduled)
- [ ] Attach an ALB to an ASG and verify health checks
- [ ] Deploy a Lambda function with an IAM execution role
- [ ] Configure a Lambda trigger (API Gateway, SQS, EventBridge)
- [ ] Tune Lambda memory and understand the price/performance trade-off

---

## Key Pricing Models

| Model | Best for | Commitment |
|-------|----------|------------|
| On-Demand | Dev/test, unpredictable | None |
| Reserved (1yr/3yr) | Steady-state production | 1 or 3 years |
| Savings Plans | Flexible commitment | 1 or 3 years |
| Spot | Fault-tolerant batch, CI | None (can be interrupted) |
| Dedicated Host | Licensing, compliance | On-demand or reserved |
---

← [Previous: PrivateLink](../03-networking/privatelink.md) | [Home](../../README.md) | [Next: EC2 →](./ec2.md)
