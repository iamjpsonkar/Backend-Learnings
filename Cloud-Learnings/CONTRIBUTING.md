# Contributing to Cloud-Learnings

Thank you for your interest in contributing. This is a knowledge base built to be accurate, practical, and consistently structured.

---

## What You Can Contribute

- New topics or service documentation
- Corrections to existing content
- Diagrams (Mermaid, SVG, Draw.io)
- Cheatsheets and quick references
- Hands-on project walkthroughs
- Interview prep questions and answers

---

## Content Standards

### Accuracy

- Only document behavior you have verified, either from official documentation or hands-on testing.
- If something is uncertain, say so explicitly: "verify this against your configuration."
- Do not invent API names, command flags, or service behavior.

### Depth

Each doc should include where applicable:

1. What the service/concept is (plain explanation)
2. Why it exists / what problem it solves
3. Core components or architecture
4. Key configuration options or parameters
5. Common use cases with examples
6. Pricing model (for cloud services)
7. Comparison with similar services
8. AWS CLI / SDK / Terraform examples
9. Common gotchas and troubleshooting
10. References to official documentation

### File Naming

| Type | Convention | Example |
|------|-----------|---------|
| Folders | `lowercase-kebab-case` with numeric prefix | `05-aws/` |
| Docs | `lowercase-kebab-case.md` | `ec2.md`, `vpc-peering.md` |
| Images | `{service}-{concept}.png` or `.svg` | `s3-storage-class.png` |
| Mermaid | `{concept}.mmd` | `aws-vpc-architecture.mmd` |
| Scripts | `verb-noun.sh` | `validate-repo.sh` |

---

## Image and Diagram Guidelines

- Place images in `assets/images/{provider}/{service}/`
- Prefer SVG for diagrams, PNG for screenshots
- Maximum image size: 500KB
- Every image must have a descriptive `alt` attribute
- New diagrams: create Mermaid source in `assets/diagrams/mermaid/` first
- If you use an image from an external source, add it to `assets/ATTRIBUTIONS.md`
- Do not embed external image URLs in Markdown

---

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/topic-name`
3. Write or update content following the standards above
4. Run validation: `./scripts/validate-repo.sh`
5. Open a pull request against `main`

### PR Title Format

Use conventional commit style:

```
feat: add aws elasticache documentation
fix: correct s3 storage class retrieval times
docs: expand kubernetes rbac section
chore: update image paths after restructure
```

### PR Checklist

- [ ] Content is accurate and referenced to official docs where possible
- [ ] File naming follows conventions
- [ ] Images are in `assets/images/` and have `alt` text
- [ ] Every new folder has a `README.md`
- [ ] No broken relative links
- [ ] No placeholder `TODO` code without a `# TODO:` comment prefix
- [ ] `./scripts/validate-repo.sh` passes locally

---

## Issue Reporting

Use the GitHub Issue templates:

- **Bug report** — broken link, incorrect information, rendering issue
- **Content gap** — missing topic you want to see documented
- **New topic** — proposal for a new section or service

---

## Code of Conduct

By contributing, you agree to abide by the [Code of Conduct](./CODE_OF_CONDUCT.md).
