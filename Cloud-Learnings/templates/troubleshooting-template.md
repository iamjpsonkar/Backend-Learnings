# Troubleshooting: {System / Service / Topic}

<!-- USAGE: Copy this file to the relevant section (e.g., 23-troubleshooting/).
     Fill in each section. Remove HTML comments before committing.
     This template is for debugging guides, runbooks, and incident-scoped investigations. -->

> **Applies to:** {service, tool, or stack component}
> **Environment:** {AWS / Kubernetes / Terraform / General}

---

## Diagnostic Checklist

<!-- Run through this before diving into individual symptoms.
     These cover the most common root causes across all issues in this domain. -->

- [ ] Are credentials/permissions valid and not expired?
- [ ] Is the target resource in the expected region/namespace/account?
- [ ] Are there any ongoing service incidents? Check the [status page]({URL}).
- [ ] Have any recent changes been deployed (config, code, infra)?
- [ ] Are resource quotas or limits being hit?
- [ ] Are dependent services (downstream, databases, queues) healthy?

---

## Symptom Index

| Symptom | Section |
|---------|---------|
| [{symptom 1}](#{anchor-1}) | [Jump](#anchor-1) |
| [{symptom 2}](#{anchor-2}) | [Jump](#anchor-2) |
| [{symptom 3}](#{anchor-3}) | [Jump](#anchor-3) |

---

## {Symptom 1} {#anchor-1}

<!-- One symptom per section. Be specific — generic titles like "not working" are unhelpful. -->

**Symptom:** ...

**Likely causes:**

1. **{Cause A}** — ...
2. **{Cause B}** — ...

**Diagnosis steps:**

```bash
# Step 1: Confirm the symptom
{diagnostic command}

# Step 2: Check logs
{log command}

# Step 3: Inspect configuration
{inspect command}
```

**Fix:**

```bash
{fix command}
```

**Verification:**

```bash
# Confirm the fix worked
{verification command}
```

**Notes / caveats:** ...

---

## {Symptom 2} {#anchor-2}

**Symptom:** ...

**Likely causes:**

1. **{Cause A}** — ...

**Diagnosis steps:**

```bash
{diagnostic command}
```

**Fix:**

```bash
{fix command}
```

---

## {Symptom 3} {#anchor-3}

**Symptom:** ...

**Likely causes:**

1. **{Cause A}** — ...

**Diagnosis steps:**

```bash
{diagnostic command}
```

**Fix:**

```bash
{fix command}
```

---

## Collecting Diagnostic Information

<!-- What to gather before escalating or opening a support ticket. -->

Run the following and attach the output:

```bash
# System / environment info
{command}

# Service-specific state dump
{command}

# Recent log excerpt
{log command} | tail -100
```

Provide:
- Exact error message (copy-paste, not a screenshot)
- Timestamp of when the issue started
- Recent changes to config, code, or infrastructure
- Output of the diagnostic commands above

---

## Common Mistakes

<!-- Non-obvious things that frequently cause issues.
     These are preventive — what people do wrong before they see any errors. -->

| Mistake | Consequence | Correct approach |
|---------|-------------|-----------------|
| {mistake} | ... | ... |
| {mistake} | ... | ... |

---

## Escalation Path

<!-- When to stop troubleshooting and who/where to involve next. -->

Escalate if:
- You have worked through all symptoms above and none match
- You suspect a cloud provider outage or platform bug
- The issue is causing active data loss or user impact

Escalate to:
- **Cloud provider support:** Open a case at {URL}
- **Internal on-call:** {process}
- **Community / forums:** {URL}

When escalating, include the diagnostic output collected above.

---

## References

- [Service documentation]({URL})
- [Known issues / release notes]({URL})
- [Community forum / Stack Overflow tag]({URL})
