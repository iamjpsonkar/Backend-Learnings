# Practice Exercises

DIY exercises where you implement the solution yourself. Unlike labs, these don't provide step-by-step commands — only the problem statement, requirements, and hints.

## Structure

```
practice/
├── beginner/
│   ├── docker-basics/
│   ├── linux-debugging/
│   ├── cloud-cli-basics/
│   └── object-storage/
├── intermediate/
│   ├── terraform-localstack/
│   ├── monitoring-dashboard/
│   ├── queue-worker/
│   ├── reverse-proxy/
│   └── database-backup/
├── advanced/
│   ├── microservices-platform/
│   ├── multi-cloud-local/
│   ├── incident-response/
│   ├── secure-platform/
│   └── production-observability/
├── broken-scenarios/
│   ├── broken-dns/
│   ├── broken-container/
│   ├── broken-db/
│   ├── broken-queue/
│   ├── broken-kubernetes/
│   ├── broken-terraform/
│   └── broken-pipeline/
└── sandbox/
    ├── docker/
    ├── terraform/
    ├── kubernetes/
    ├── ansible/
    └── experiments/
```

## Exercise Format

Each exercise contains:

| File | Contents |
|---|---|
| `problem.md` | Goal, requirements, constraints |
| `hints.md` | Progressive hints (read only if stuck) |
| `starter/` | Skeleton code with TODO comments |
| `solution/` | Reference solution |
| `validate.sh` | Automated validation |

## How to Use

1. Read `problem.md` — understand what you need to build
2. Try to implement it yourself using `starter/` as a starting point
3. If stuck, read `hints.md` (progressive hints — read one at a time)
4. Validate with `./validate.sh`
5. Compare your solution to `solution/`

## Difficulty Levels

| Level | Prerequisites | Typical time |
|---|---|---|
| Beginner | Docker Desktop installed | 30-60 min |
| Intermediate | Beginner exercises complete, basic CLI knowledge | 1-3 hours |
| Advanced | Intermediate exercises complete, cloud knowledge | 3-8 hours |

## Sandbox

The `sandbox/` directory is your free workspace — no instructions, just tools. Use it to experiment with Terraform, Kubernetes manifests, Ansible playbooks, or Docker configurations. These directories are in `.gitignore`.
