← [Previous: Redshift](../06-databases/redshift.md) | [Home](../../README.md) | [Next: ECR →](./ecr.md)

---

# AWS Containers

AWS offers managed container services at every layer of the stack: a fully managed registry (ECR), an orchestrator without Kubernetes (ECS), and a managed Kubernetes control plane (EKS).

---

## Container Service Selection

```
Do you want to manage Kubernetes?
├── No  → ECS (simpler ops; Fargate for serverless containers)
└── Yes → EKS (managed Kubernetes; bring your own node groups or use Fargate profiles)

Do you need a private container registry?
└── ECR (integrated with ECS/EKS/CodePipeline, immutable tags, vulnerability scanning)
```

---

## Topics

| File | Description |
|------|-------------|
| [ecr.md](./ecr.md) | Elastic Container Registry — private registry, image scanning, lifecycle policies |
| [ecs.md](./ecs.md) | Elastic Container Service — task definitions, services, Fargate and EC2 launch types |
| [eks.md](./eks.md) | Elastic Kubernetes Service — managed control plane, node groups, Fargate profiles |

---

## Minimum Competency Checklist

- [ ] Push an image to ECR and configure a lifecycle policy
- [ ] Write a Fargate task definition and run it via an ECS service behind an ALB
- [ ] Understand ECS service auto scaling (Application Auto Scaling with ALB request-count target)
- [ ] Create an EKS cluster, deploy a workload, and expose it via a LoadBalancer Service
- [ ] Attach an IAM role to a pod using IRSA (IAM Roles for Service Accounts)
- [ ] Store secrets in Secrets Manager and inject them into ECS containers / Kubernetes pods

---

## References

- [ECS documentation](https://docs.aws.amazon.com/ecs/latest/developerguide/)
- [EKS documentation](https://docs.aws.amazon.com/eks/latest/userguide/)
- [ECR documentation](https://docs.aws.amazon.com/ecr/latest/userguide/)
---

← [Previous: Redshift](../06-databases/redshift.md) | [Home](../../README.md) | [Next: ECR →](./ecr.md)
