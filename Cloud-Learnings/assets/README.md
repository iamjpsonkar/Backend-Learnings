# Assets

This directory contains all static assets used in the Cloud-Learnings knowledge base.

## Structure

```
assets/
├── images/
│   ├── aws/          # AWS service screenshots and diagrams
│   │   ├── aws/      # General AWS (overview, zones, benefits, support, SSM)
│   │   ├── ec2/      # EC2, AMI, EBS
│   │   ├── s3/       # S3 storage classes, access management
│   │   └── dns/      # DNS resolution diagrams
│   ├── azure/        # Azure service images
│   ├── gcp/          # GCP service images
│   ├── concepts/     # Cloud-agnostic concept diagrams
│   └── architecture/ # Multi-service architecture diagrams
├── diagrams/
│   ├── mermaid/      # Mermaid .mmd source files
│   ├── svg/          # Rendered SVG diagrams
│   └── drawio/       # Draw.io source files
└── prompts/
    ├── image-generation-prompts.md
    └── diagram-generation-prompts.md
```

## Usage in Markdown

Always use relative paths from the document location:

From a file two levels deep (e.g., `05-aws/04-compute/ec2.md`):

```
src="../../assets/images/aws/ec2/ec2_overview.png"
```

From a file one level deep (e.g., `05-aws/README.md`):

```
src="../assets/images/aws/aws/aws_overview.png"
```

## Rules

- Maximum image size: 500KB per file
- Prefer SVG for diagrams, PNG for screenshots
- Every `<img>` tag must have a descriptive `alt` attribute
- No external image URLs — all assets must be stored here
- If an image is from an external source, add it to [ATTRIBUTIONS.md](./ATTRIBUTIONS.md)

## Naming Convention

| Asset type | Convention | Example |
|------------|-----------|---------|
| Screenshots | `{service}_{concept}.png` | `ec2_overview.png` |
| Diagrams | `{concept}.svg` | `vpc-architecture.svg` |
| Mermaid sources | `{concept}.mmd` | `aws-vpc-architecture.mmd` |
