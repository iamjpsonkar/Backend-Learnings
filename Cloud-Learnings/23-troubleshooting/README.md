← [Previous: Multi-Cloud Deployment](../22-projects/multi-cloud-deployment.md) | [Home](../README.md) | [Next: AWS Networking →](./aws-networking.md)

---

# Troubleshooting

Effective troubleshooting follows a method: observe, hypothesize, test, confirm. This section provides diagnostic playbooks for the most common failure categories in cloud environments.

---

## Diagnostic Framework

```
1. What changed?      — recent deploy, config change, scheduled job, external event
2. What is the blast radius?  — one service, one region, all users, subset
3. What do the metrics say?   — CPU, memory, network, error rate, latency
4. What do the logs say?      — error messages, stack traces, connection errors
5. Can you reproduce it?      — same input, same environment, consistent failure
6. What is the minimal test?  — narrow the failure to one component
```

---

## Topics

| File | Coverage |
|------|----------|
| [AWS Networking](./aws-networking.md) | VPC connectivity, security groups, NACLs, DNS, Route 53 |
| [Containers & Kubernetes](./containers-k8s.md) | Docker build failures, ECS task failures, pod crashes, OOMKilled |
| [Databases](./databases.md) | Connection exhaustion, slow queries, replication lag, failover issues |
| [CI/CD](./cicd.md) | Pipeline failures, deploy rollbacks, artifact issues, permission errors |
| [Performance](./performance.md) | High latency, CPU/memory pressure, cold starts, autoscaling lag |

---

## Quick Symptom → Section Map

| Symptom | Start here |
|---------|-----------|
| `Connection refused` / `Connection timed out` | AWS Networking |
| ECS task exits immediately / CrashLoopBackOff | Containers & Kubernetes |
| `too many connections` / slow queries | Databases |
| GitHub Actions failing / deploy not happening | CI/CD |
| High p99 latency / requests timing out | Performance |
| Lambda cold start > 5s | Performance |
| `ImagePullBackOff` / `403 Forbidden on ECR` | Containers & Kubernetes |
| Route 53 not resolving / wrong IP | AWS Networking |

---

## References

- [AWS re:Post (community Q&A)](https://repost.aws/)
- [AWS CloudTrail — who did what when](https://docs.aws.amazon.com/cloudtrail/latest/userguide/)
- [AWS Health Dashboard](https://health.aws.amazon.com/health/status)

---

← [Previous: Multi-Cloud Deployment](../22-projects/multi-cloud-deployment.md) | [Home](../README.md) | [Next: AWS Networking →](./aws-networking.md)
