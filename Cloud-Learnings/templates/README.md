# Templates

Reusable scaffolds for contributing content to Cloud-Learnings. Each template includes inline instructions (HTML comments) explaining what to put in each section.

## Available Templates

| Template | Use when... |
|----------|-------------|
| [service-template.md](./service-template.md) | Documenting a cloud service (EC2, S3, Cloud Run, etc.) |
| [command-template.md](./command-template.md) | Writing a CLI tool reference or cheatsheet |
| [troubleshooting-template.md](./troubleshooting-template.md) | Creating a debugging guide with symptom index |
| [project-template.md](./project-template.md) | Writing a hands-on end-to-end project walkthrough |
| [architecture-template.md](./architecture-template.md) | Documenting a multi-service architecture pattern |
| [comparison-template.md](./comparison-template.md) | Comparing two or more services, tools, or approaches |
| [checklist-template.md](./checklist-template.md) | Creating an operational checklist with sign-off tracking |

## How to Use

1. Copy the relevant template to the target location:

```bash
cp templates/service-template.md 05-aws/04-compute/new-service.md
```

2. Fill in each section. Remove all HTML comments (`<!-- ... -->`) before committing.

3. Required sections are marked in the template. Optional sections can be deleted if not applicable.

4. Run validation before committing:

```bash
./scripts/validate-repo.sh
```
