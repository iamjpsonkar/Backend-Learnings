# {Service Name}

<!-- USAGE: Copy this file to the relevant section, rename it, and fill in each section.
     Remove all HTML comments before committing.
     Required sections: Overview, What It Solves, Core Concepts, Key Features, Common Use Cases, Examples, Pricing, Comparison, References
     Optional sections: mark as "N/A" or delete if not applicable. -->

> **Provider:** {AWS / Azure / GCP / Other}
> **Category:** {Compute / Storage / Networking / Database / Security / Serverless / Containers / Observability / IaC / Other}
> **Official docs:** {URL}

---

## What Is {Service Name}?

<!-- One paragraph. Plain explanation — no jargon in the first sentence.
     Answer: what is this thing, what does it do, what category of problem does it address? -->

{Service Name} is ...

**Simple analogy:** Think of it like ...

---

## What Problem It Solves

<!-- Why does this service exist? What was painful or manual before it?
     2–5 bullet points covering the real-world pain points it addresses. -->

Without {Service Name}:

- ...
- ...
- ...

---

## Core Concepts

<!-- Define 3–8 key terms/components a reader must understand before using the service.
     Keep each definition to 1–3 sentences. -->

### {Concept 1}

...

### {Concept 2}

...

### {Concept 3}

...

---

## Architecture

<!-- High-level diagram of how the service fits into the broader system.
     Use a Mermaid diagram or ASCII art. If a diagram exists in assets/, reference it.
     Show: inputs → service → outputs, and how it connects to dependent services. -->

```
{Input / Client}
       ↓
{Service Name}
       ↓
{Output / Downstream}
```

<!-- If a Mermaid or image asset exists: -->
<!-- <img src="../../assets/images/{provider}/{service}/{concept}.png" alt="{Service Name} Architecture"/> -->

---

## Key Features

<!-- List the major capabilities. For each feature: name, 1-sentence description, and when it matters. -->

| Feature | Description | When to use |
|---------|-------------|-------------|
| {Feature 1} | ... | ... |
| {Feature 2} | ... | ... |
| {Feature 3} | ... | ... |

---

## Configuration Options

<!-- Cover the most important settings a practitioner needs to know.
     Focus on options that affect behavior, cost, or security — not every possible parameter. -->

| Option | Default | Description |
|--------|---------|-------------|
| `{option}` | `{default}` | ... |
| `{option}` | `{default}` | ... |

---

## Common Use Cases

<!-- 3–6 real-world scenarios. For each: name, brief description, which features are used. -->

### 1. {Use Case Name}

**Scenario:** ...
**How {Service Name} helps:** ...

### 2. {Use Case Name}

**Scenario:** ...
**How {Service Name} helps:** ...

---

## Hands-On Examples

<!-- Concrete, runnable examples. Prefer CLI/SDK/IaC over console steps.
     Each example should be self-contained and produce a visible result. -->

### Example 1: {Action}

```bash
# {Brief description of what this does}
{command}
```

Expected output:
```
{output}
```

### Example 2: {Action}

```bash
{command}
```

### Terraform Example

```hcl
resource "{provider}_{resource}" "{name}" {
  # ...
}
```

---

## IAM / Access Control

<!-- What permissions are needed to use this service?
     List the minimum required actions for common operations. -->

Minimum IAM permissions for read access:

```json
{
  "Effect": "Allow",
  "Action": [
    "{service}:Get{Resource}",
    "{service}:List{Resource}"
  ],
  "Resource": "*"
}
```

---

## Pricing Model

<!-- How is this service billed? What are the cost drivers?
     Include free tier if applicable. -->

| Billing dimension | Unit | Notes |
|------------------|------|-------|
| {dimension} | per {unit} | ... |
| {dimension} | per {unit} | ... |

**Free tier:** {Yes — X per month / No}

**Cost optimization tips:**
- ...
- ...

---

## Limits and Quotas

<!-- List the most commonly hit service limits. Mark which ones are adjustable. -->

| Limit | Default | Adjustable? |
|-------|---------|-------------|
| {limit} | {value} | Yes / No |
| {limit} | {value} | Yes / No |

---

## Comparison with Similar Services

<!-- How does this compare to the closest alternatives within the same provider or cross-cloud?
     Keep it factual — not a sales pitch. -->

| Feature | {This Service} | {Alternative 1} | {Alternative 2} |
|---------|---------------|-----------------|-----------------|
| {criterion} | ... | ... | ... |
| {criterion} | ... | ... | ... |

**When to choose {Service Name} over {Alternative}:** ...

---

## Common Gotchas

<!-- Warn about non-obvious behaviors, defaults that surprise people, and mistakes made in production. -->

- **{Gotcha 1}:** ...
- **{Gotcha 2}:** ...
- **{Gotcha 3}:** ...

---

## Troubleshooting

<!-- 3–5 common error conditions with their root cause and fix. -->

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `{error message}` | ... | ... |
| `{error message}` | ... | ... |

---

## References

- [Official documentation]({URL})
- [Pricing page]({URL})
- [Service quotas]({URL})
- [AWS CLI reference]({URL}) _(if AWS)_
