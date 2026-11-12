# {Tool / CLI} Command Reference

<!-- USAGE: Copy this file to the relevant section (e.g., 24-cheatsheets/).
     Fill in each section. Remove HTML comments before committing.
     This template is for CLI tool references, cheatsheets, and command-line guides. -->

> **Tool:** {aws / kubectl / terraform / git / helm / ansible / docker / other}
> **Version confirmed:** {version}
> **Official docs:** {URL}

---

## Installation and Setup

```bash
# Install
{install command}

# Verify version
{tool} --version

# Initial configuration
{configuration command}
```

---

## Authentication / Context

```bash
# Configure credentials or context
{auth command}

# Verify active context or identity
{verify command}
```

---

## {Category 1 — e.g., "Resource Management"}

<!-- Group related commands under a heading. Use subheadings for sub-categories. -->

### List resources

```bash
{command}
# Example: aws ec2 describe-instances --output table
```

### Get a single resource

```bash
{command} --{id-flag} {resource-id}
```

### Create a resource

```bash
{command} \
  --{param1} {value} \
  --{param2} {value}
```

**Important flags:**

| Flag | Description | Default |
|------|-------------|---------|
| `--{flag}` | ... | `{default}` |
| `--{flag}` | ... | `{default}` |

### Update a resource

```bash
{command} --{id-flag} {resource-id} --{param} {new-value}
```

### Delete a resource

> **Warning:** This operation is irreversible. Verify the resource ID before running.

```bash
{command} --{id-flag} {resource-id}
```

---

## {Category 2 — e.g., "Filtering and Output"}

### Filter results with JMESPath / JSONPath / selectors

```bash
# AWS CLI: filter with --query
{tool} {command} --query '{jmespath-expression}'

# kubectl: filter with -l
kubectl get {resource} -l {label}={value}
```

### Output formats

```bash
# JSON (default for most tools)
{command} --output json

# Table (human-readable)
{command} --output table

# Plain text / tsv
{command} --output text
```

---

## {Category 3 — e.g., "Common Operations"}

### {Operation name}

```bash
{command}
```

**When to use:** ...

### {Operation name}

```bash
{command}
```

---

## Useful Flags (Global)

| Flag | Description |
|------|-------------|
| `--{flag}` | ... |
| `--{flag}` | ... |
| `--dry-run` | Simulate the operation without making changes (if supported) |
| `--region {region}` | Override default region (AWS) |
| `--namespace {ns}` | Target namespace (kubectl) |
| `-o json` | Output as JSON |
| `-v` / `--verbose` | Increase log verbosity |

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{VAR}` | ... | `{value}` |
| `{VAR}` | ... | `{value}` |

---

## Scripting Patterns

### Wait for a condition

```bash
# Poll until resource reaches desired state
{command} wait {state} --{id-flag} {resource-id}
```

### Loop over resources

```bash
for id in $({command to list ids}); do
  echo "Processing $id"
  {command} --{id-flag} "$id"
done
```

### Pipe output to another tool

```bash
{command} --output json | jq '.{field}[]'
```

---

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `{error message}` | ... | ... |
| `{error message}` | ... | ... |
| Permission denied / AccessDenied | Missing IAM/RBAC permissions | Add the required policy or role binding |

---

## References

- [Official CLI reference]({URL})
- [Configuration docs]({URL})
- [Cheatsheet (official or community)]({URL})
