# Contributing

Keep additions concise, interview-oriented, and technically verifiable.

## Content Guidelines

- Explain the concept before showing an example.
- Include trade-offs or failure modes for architectural topics.
- Prefer minimal examples that demonstrate one idea clearly.
- Never include real credentials, tokens, or production connection strings.
- Use descriptive headings and fenced code blocks with a language identifier.

## Validation

Run the checks before opening a pull request:

```bash
python3 scripts/validate_docs.py
```

The same command runs in continuous integration for pushes and pull requests.
