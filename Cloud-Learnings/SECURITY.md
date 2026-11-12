# Security Policy

## Scope

This is a documentation-only repository. It contains:

- Markdown files with cloud engineering notes and tutorials
- PNG/SVG image assets
- Shell scripts for local validation

There is no deployable application code, no credentials, and no infrastructure managed from this repository.

## Reporting a Security Issue

If you find content in this repository that:

- Contains accidentally committed credentials, tokens, or secrets
- Provides instructions that could be used to cause harm
- Links to malicious external resources

Please open a GitHub issue with the label **security** or contact the maintainer directly.

## Content Security Guidelines

All contributors must follow these rules:

- **Never commit credentials** — no AWS access keys, tokens, passwords, or API keys, even as examples
- **Use placeholder values** in examples: `YOUR_ACCESS_KEY`, `<your-region>`, `xxxxxxxx`
- **No external image URLs** — all images must be stored in `assets/images/`
- **Verify commands** before documenting — ensure CLI examples do not cause unintended destructive actions without warning the reader
- **Label destructive operations clearly** — commands like `aws s3 rm --recursive` must have prominent warnings

## Responsible Disclosure

If content in this repository could assist in unauthorized access to cloud infrastructure, please report it privately before opening a public issue.
