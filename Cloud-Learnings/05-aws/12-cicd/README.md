← [Previous: Systems Manager](../11-management/systems-manager.md) | [Home](../../README.md) | [Next: CodeBuild →](./codebuild.md)

---

# AWS CI/CD

AWS Code services provide a fully managed CI/CD pipeline without running Jenkins or any other build infrastructure.

---

## Pipeline Flow

```
Developer pushes code
        │
        ▼
CodeCommit / GitHub / Bitbucket   (source)
        │
        ▼
CodeBuild                          (build, test, package, push to ECR/S3)
        │
        ▼
CodeDeploy                         (deploy to EC2 / ECS / Lambda)
        │
        ▼
CodePipeline                       (orchestrates all stages end-to-end)
```

---

## Topics

| File | Description |
|------|-------------|
| [codebuild.md](./codebuild.md) | Managed build service — buildspec.yml, Docker builds, caching |
| [codedeploy.md](./codedeploy.md) | Deployment automation — rolling, blue/green, canary strategies |
| [codepipeline.md](./codepipeline.md) | End-to-end orchestration — source → build → approve → deploy |

---

## Minimum Competency Checklist

- [ ] Write a `buildspec.yml` that builds a Docker image and pushes to ECR
- [ ] Create a CodeDeploy deployment group for ECS blue/green deployments
- [ ] Build a CodePipeline that goes from GitHub → CodeBuild → CodeDeploy
- [ ] Add a manual approval action between staging and production stages

---

## References

- [CodeBuild documentation](https://docs.aws.amazon.com/codebuild/latest/userguide/)
- [CodeDeploy documentation](https://docs.aws.amazon.com/codedeploy/latest/userguide/)
- [CodePipeline documentation](https://docs.aws.amazon.com/codepipeline/latest/userguide/)
---

← [Previous: Systems Manager](../11-management/systems-manager.md) | [Home](../../README.md) | [Next: CodeBuild →](./codebuild.md)
