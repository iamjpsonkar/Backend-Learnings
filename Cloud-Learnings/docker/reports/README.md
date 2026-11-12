# Reports

Generated reports from lab runs, security scans, and cost analysis.

All reports are gitignored (except this README). Run labs and validations to generate them.

---

## Directory Structure

```
reports/
├── validations/       # Lab validation results (pass/fail per task)
├── lab-results/       # Full lab run outputs and screenshots
├── security-scans/    # Trivy, Checkov, Hadolint scan output
├── cost-analysis/     # FinOps simulation reports
└── troubleshooting/   # Saved incident investigation notes
```

---

## Generating Reports

### Lab validation report
```bash
./run.sh lab validate aws-localstack > reports/validations/aws-localstack-$(date +%Y%m%d).txt
```

### Security scan report
```bash
# Trivy image scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --format json \
  --output reports/security-scans/trivy-$(date +%Y%m%d).json \
  cloud-learnings-lab-sample-api

# Checkov IaC scan
docker run --rm -v "$(pwd)/infrastructure:/tf" \
  bridgecrew/checkov -d /tf \
  --output-file-path reports/security-scans/
```

### Cost analysis
```bash
# After running FinOps lab
./run.sh lab start finops-simulation
# Reports generated at reports/cost-analysis/
```

---

## Report Formats

| Type | Format | Tool |
|---|---|---|
| Validation | Plain text / JSON | run.sh validate |
| Trivy | JSON / SARIF | trivy |
| Checkov | JSON / JUnit | checkov |
| Hadolint | JSON | hadolint |
| FinOps | CSV / JSON | custom scripts |

---

Reports are excluded from version control. Use `.gitkeep` files to preserve directory structure.
