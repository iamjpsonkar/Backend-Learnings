← [Previous: Ansible Best Practices](../12-ansible/best-practices.md) | [Home](../README.md) | [Next: GitHub Actions →](./github-actions.md)

---

# CI/CD & GitOps

CI/CD automates the path from code commit to production. GitOps extends that model by using Git as the single source of truth for both application code and infrastructure state.

---

## CI vs CD

| | Continuous Integration (CI) | Continuous Delivery (CD) | Continuous Deployment |
|--|--|--|--|
| What | Build, test, lint on every commit | Package and stage every green build | Auto-deploy every green build to production |
| Gate | Automated tests | Human approval (or none) | No human gate |
| Goal | Catch bugs early | Keep deployable artifact ready | Maximize deployment frequency |

---

## GitOps Principles

1. **Declarative** — all system state described as code in Git
2. **Versioned and immutable** — Git history is the audit log
3. **Pulled automatically** — agents pull from Git (not pushed by CI)
4. **Continuously reconciled** — agents detect and fix drift

```
Developer → git push → CI (build/test/push image) → Git repo update
                                                          │
                                              GitOps agent (ArgoCD/Flux)
                                                          │
                                                       Cluster
```

---

## Tool Selection Guide

| Use case | Recommended tool |
|----------|-----------------|
| GitHub-hosted repositories | GitHub Actions |
| GitLab | GitLab CI |
| On-premises / legacy CI | Jenkins |
| Kubernetes GitOps | ArgoCD or FluxCD |
| Deployment strategies | Argo Rollouts, Flagger |

---

## Topics

| File | Topics |
|------|--------|
| [GitHub Actions](./github-actions.md) | Workflows, reusable workflows, matrix builds, environments |
| [GitLab CI](./gitlab-ci.md) | Pipelines, stages, runners, environments, Auto DevOps |
| [Jenkins](./jenkins.md) | Declarative pipelines, shared libraries, multi-branch |
| [ArgoCD](./argocd.md) | App management, app-of-apps, sync policies, RBAC |
| [FluxCD](./fluxcd.md) | Kustomizations, HelmReleases, image automation |
| [Deployment Strategies](./deployment-strategies.md) | Blue/green, canary, rolling, feature flags |
| [Production Pipelines](./production-pipelines.md) | End-to-end patterns, gates, observability |

---

## References

- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [GitLab CI documentation](https://docs.gitlab.com/ee/ci/)
- [ArgoCD documentation](https://argo-cd.readthedocs.io/)
- [FluxCD documentation](https://fluxcd.io/flux/)
- [GitOps Working Group](https://opengitops.dev/)

---

← [Previous: Ansible Best Practices](../12-ansible/best-practices.md) | [Home](../README.md) | [Next: GitHub Actions →](./github-actions.md)
