# Adding New Labs

How to create a custom lab for the Cloud-Learnings Lab Platform.

## Lab Structure

Each lab is a directory in `labs/` with exactly 7 files:

```
labs/my-new-lab/
├── README.md           Introduction, objectives, prerequisites
├── tasks.md            Step-by-step tasks
├── commands.md         Command reference
├── expected-output.md  What success looks like
├── validate.md         How to verify work
├── troubleshooting.md  Common issues
└── solution.md         Reference solution
```

## Step 1 — Create the Directory

```bash
mkdir -p labs/my-new-lab
```

## Step 2 — Write README.md

```markdown
# Lab: My New Lab

One-sentence description.

## Objectives

1. Learn X
2. Practice Y
3. Build Z

## Prerequisites

Start required services:
\`\`\`bash
./run.sh start <profile>
\`\`\`

## Continue

See [tasks.md](tasks.md).
```

## Step 3 — Write tasks.md

Structure each task as:
```markdown
## Task N — Task Name

Brief description of what to accomplish.

- [ ] Checkbox item 1
- [ ] Checkbox item 2

\`\`\`bash
# Key command
command here
\`\`\`

Expected: what you should see.
```

## Step 4 — Write commands.md

A complete command reference. Users should be able to complete the lab using only this file plus their knowledge.

## Step 5 — Write expected-output.md

Include:
- Exact or representative output from successful commands
- Screenshots described in text if helpful
- Key indicators of success

## Step 6 — Write validate.md

Include shell commands that verify completion:

```bash
# Check if a resource was created
aws --endpoint-url=http://localhost:4566 s3 ls | grep my-bucket
# Expected: line containing my-bucket
```

Optionally create `validate.sh` for automated validation.

## Step 7 — Write troubleshooting.md

For each common failure mode:
```markdown
## Error: <error message>

**Cause**: What typically causes this.

**Fix**:
\`\`\`bash
command to fix it
\`\`\`
```

## Step 8 — Write solution.md

Complete working solution with explanations. Start with:

```markdown
# Solution — My New Lab

**Try the tasks yourself before reading this!**
```

## Step 9 — Add to Lab Index

Edit `labs/lab-index.yaml` and add an entry:

```yaml
- id: my-new-lab
  name: "My New Lab"
  description: "Brief description"
  profile: core         # which profile to start
  difficulty: beginner  # beginner | intermediate | advanced
  estimated_time: "30 min"
  topics: [topic1, topic2]
```

## Step 10 — Verify

```bash
./run.sh lab list | grep my-new-lab
./run.sh lab start my-new-lab
```

## Lab Best Practices

1. **Keep it focused** — one concept per lab, not ten
2. **Progressive complexity** — start simple, add complexity in later tasks
3. **Include cleanup** — every task that creates resources should have a cleanup step
4. **Test it yourself** — follow your own tasks from a clean state
5. **Write the troubleshooting** — include issues you hit while writing the lab
6. **Verify the solution works** — run through solution.md end-to-end
7. **No real cloud credentials** — all examples must work with local emulators

## Contributing Labs

If you create a useful lab:
1. Follow the structure above
2. Test from a clean state
3. Submit a PR to the Cloud-Learnings repository
