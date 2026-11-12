← [Previous: WAF & Shield](../09-security/waf-shield.md) | [Home](../../README.md) | [Next: CloudWatch →](./cloudwatch.md)

---

# AWS Observability

Observability in AWS is built on three pillars: metrics (CloudWatch), audit logs (CloudTrail), and resource configuration history (Config). Together they give you operational visibility, security audit trails, and compliance evidence.

---

## Contents

| File | Description |
|------|-------------|
| [cloudwatch.md](./cloudwatch.md) | Metrics, alarms, dashboards, Logs Insights, Container Insights |
| [cloudtrail.md](./cloudtrail.md) | API audit logging, multi-region trails, event selectors, Athena queries |
| [config.md](./config.md) | Resource inventory, config history, compliance rules, conformance packs |

---

## The Three Pillars

```
Metrics (What is happening right now?)
  CloudWatch Metrics → Alarms → SNS / Auto Scaling → Dashboards

Logs (What happened and why?)
  CloudWatch Logs ← Lambda, ECS, EC2, API Gateway, VPC Flow Logs
  CloudTrail → S3 → Athena (who called what API, when, from where)

Configuration (What changed and is it compliant?)
  AWS Config → configuration timeline → Config Rules → findings → SSM remediation
```

---

## Minimum Competency Checklist

- [ ] Create a CloudWatch alarm on CPUUtilization with SNS notification
- [ ] Write a CloudWatch Logs Insights query to find errors in the last hour
- [ ] Create a CloudWatch dashboard with multiple widgets
- [ ] Enable a multi-region CloudTrail trail writing to S3 + CloudWatch Logs
- [ ] Query CloudTrail with Athena to find who deleted an S3 bucket
- [ ] Enable AWS Config and explain the difference between rules and conformance packs
- [ ] Create a custom Config rule using Lambda
- [ ] Set up automatic remediation for a Config rule violation

---

## Key Service Relationships

| Service | Data produced | Consumed by |
|---------|--------------|-------------|
| CloudTrail | API calls (who/what/when/where) | Athena, CloudWatch Logs, Security Hub, EventBridge |
| CloudWatch Logs | Application and service logs | Logs Insights, Metric Filters, Lambda subscriptions |
| CloudWatch Metrics | Numeric time-series data | Alarms, Dashboards, Auto Scaling, Anomaly Detection |
| AWS Config | Resource config snapshots + changes | Config Rules, Security Hub, Audit Manager |
---

← [Previous: WAF & Shield](../09-security/waf-shield.md) | [Home](../../README.md) | [Next: CloudWatch →](./cloudwatch.md)
