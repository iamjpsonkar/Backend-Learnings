← [Previous: GuardDuty](./guardduty.md) | [Home](../../README.md) | [Next: WAF & Shield →](./waf-shield.md)

---

# AWS Security Hub

Security Hub aggregates security findings from GuardDuty, Inspector, Macie, Firewall Manager, IAM Access Analyzer, and third-party tools into a single pane of glass. It evaluates your environment against security standards (CIS, PCI-DSS, NIST, AWS Foundational Security Best Practices) and produces a security score.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Finding** | A security observation in ASFF (Amazon Security Finding Format) |
| **Security standard** | A collection of controls (e.g., AWS FSBP, CIS AWS Foundations v1.4) |
| **Control** | A specific check (e.g., "S3 buckets should block public access") |
| **Security score** | 0–100% — percentage of enabled controls passing |
| **Insight** | A saved filter and grouping for a set of findings |
| **Custom action** | An EventBridge rule trigger for findings — enables automated response |
| **Aggregation region** | Central region that receives findings from all linked regions |

---

## Enabling Security Hub

```bash
# Enable Security Hub in the current account and region
aws securityhub enable-security-hub \
    --enable-default-standards \
    --tags Environment=production

# Verify
aws securityhub describe-hub \
    --query '{HubArn:HubArn,SubscribedAt:SubscribedAt,AutoEnableControls:AutoEnableControls}'

# List enabled security standards
aws securityhub get-enabled-standards \
    --query 'StandardsSubscriptions[*].{Standard:StandardsArn,Status:StandardsStatus}' \
    --output table

# Enable specific standards (if not enabled by default)
# AWS Foundational Security Best Practices
aws securityhub batch-enable-standards \
    --standards-subscription-requests \
        StandardsArn=arn:aws:securityhub:us-east-1::standards/aws-foundational-security-best-practices/v/1.0.0

# CIS AWS Foundations Benchmark v1.4
aws securityhub batch-enable-standards \
    --standards-subscription-requests \
        StandardsArn=arn:aws:securityhub:us-east-1::standards/cis-aws-foundations-benchmark/v/1.4.0

# PCI DSS
aws securityhub batch-enable-standards \
    --standards-subscription-requests \
        StandardsArn=arn:aws:securityhub:us-east-1::standards/pci-dss/v/3.2.1
```

---

## Multi-Account Setup (Delegated Admin)

```bash
SECURITY_ACCOUNT="333333333333"

# From the management account: designate security account as admin
aws securityhub enable-organization-admin-account \
    --admin-account-id $SECURITY_ACCOUNT

# From the security account: auto-enable for all org accounts
aws securityhub update-organization-configuration \
    --auto-enable \
    --auto-enable-standards DEFAULT

# Set an aggregation region (central region receives findings from all regions)
aws securityhub create-finding-aggregator \
    --region-linking-mode ALL_REGIONS

# List member accounts
aws securityhub list-members \
    --query 'Members[*].{Account:AccountId,Status:MemberStatus,Email:Email}' \
    --output table
```

---

## Viewing Controls and Findings

```bash
# Get overall security score
aws securityhub get-security-hub-compliance-score \
    --standards-subscription-arn arn:aws:securityhub:us-east-1:123456789012:subscription/aws-foundational-security-best-practices/v/1.0.0

# List failing controls
aws securityhub describe-standards-controls \
    --standards-subscription-arn arn:aws:securityhub:us-east-1:123456789012:subscription/aws-foundational-security-best-practices/v/1.0.0 \
    --control-status FAILED \
    --query 'Controls[*].{
        ID:ControlId,
        Title:Title,
        Status:ControlStatus,
        Severity:SeverityRating,
        FailedChecks:CurrentRegionSummary.FailedChecks
    }' \
    --output table

# Get findings (active, high or critical severity, not suppressed)
aws securityhub get-findings \
    --filters '{
        "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}, {"Value": "NOTIFIED", "Comparison": "EQUALS"}],
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
        "SeverityLabel": [{"Value": "HIGH", "Comparison": "EQUALS"}, {"Value": "CRITICAL", "Comparison": "EQUALS"}]
    }' \
    --sort-criteria Field=SeverityNormalized,SortOrder=desc \
    --max-items 20 \
    --query 'Findings[*].{
        ID:Id,
        Title:Title,
        Severity:Severity.Label,
        Type:Types[0],
        Resource:Resources[0].Id,
        Updated:UpdatedAt
    }' \
    --output table

# Get findings for a specific resource (e.g., an S3 bucket)
aws securityhub get-findings \
    --filters '{
        "ResourceId": [{"Value": "arn:aws:s3:::my-bucket", "Comparison": "EQUALS"}],
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}]
    }' \
    --query 'Findings[*].{Title:Title,Severity:Severity.Label,Control:ProductFields.ControlId}'
```

---

## Managing Finding Workflows

```bash
# Update finding workflow status (e.g., mark as resolved)
aws securityhub batch-update-findings \
    --finding-identifiers Id=arn:aws:securityhub:...:finding/abc123,ProductArn=arn:aws:securityhub:... \
    --workflow Status=RESOLVED \
    --note Text="Remediated — S3 bucket now has public access blocked",UpdatedBy=alice@example.com

# Suppress a finding (SUPPRESSED = acknowledged, will not resurface)
aws securityhub batch-update-findings \
    --finding-identifiers Id=...,ProductArn=... \
    --workflow Status=SUPPRESSED \
    --note Text="False positive — internal scanner",UpdatedBy=alice@example.com

# Disable a control (e.g., a control not applicable to your environment)
aws securityhub update-standards-control \
    --standards-control-arn arn:aws:securityhub:us-east-1:123456789012:control/aws-foundational-security-best-practices/v/1.0.0/EC2.10 \
    --control-status DISABLED \
    --disabled-reason "Not applicable — we do not use EC2-Classic"
```

---

## Custom Actions and Automated Remediation

Custom actions create EventBridge events when a finding is selected in the Security Hub console.

```bash
# Create a custom action
ACTION_ARN=$(aws securityhub create-action-target \
    --name isolate-ec2-instance \
    --description "Isolate the EC2 instance associated with this finding" \
    --id ISOLATE-EC2 \
    --query 'ActionTargetArn' --output text)

# Create an EventBridge rule that triggers when this action is invoked
aws events put-rule \
    --name security-hub-isolate-ec2 \
    --event-pattern '{
        "source": ["aws.securityhub"],
        "detail-type": ["Security Hub Findings - Custom Action"],
        "detail": {
            "actionName": ["isolate-ec2-instance"]
        }
    }' \
    --state ENABLED

# Route to remediation Lambda
aws events put-targets \
    --rule security-hub-isolate-ec2 \
    --targets Id=remediation-lambda,Arn=arn:aws:lambda:us-east-1:123456789012:function:isolate-ec2
```

### Automated Remediation for All Findings

```bash
# EventBridge rule for all new critical Security Hub findings
aws events put-rule \
    --name security-hub-critical-findings \
    --event-pattern '{
        "source": ["aws.securityhub"],
        "detail-type": ["Security Hub Findings - Imported"],
        "detail": {
            "findings": {
                "Severity": {
                    "Label": ["CRITICAL"]
                },
                "Workflow": {
                    "Status": ["NEW"]
                },
                "RecordState": ["ACTIVE"]
            }
        }
    }' \
    --state ENABLED

aws events put-targets \
    --rule security-hub-critical-findings \
    --targets \
        "Id=remediation-lambda,Arn=arn:aws:lambda:us-east-1:123456789012:function:security-hub-remediation" \
        "Id=ops-pagerduty,Arn=arn:aws:sns:us-east-1:123456789012:critical-alerts"
```

---

## Sending Custom Findings

Applications can send custom findings to Security Hub using the ASFF format.

```python
import boto3
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
sh = boto3.client("securityhub", region_name="us-east-1")

ACCOUNT_ID = "123456789012"
REGION = "us-east-1"


def report_finding(
    title: str,
    description: str,
    severity: str,   # INFORMATIONAL, LOW, MEDIUM, HIGH, CRITICAL
    resource_type: str,
    resource_id: str,
    finding_id: str,
) -> None:
    """Send a custom finding to Security Hub."""
    logger.info("Reporting security finding: title=%s severity=%s resource=%s", title, severity, resource_id)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    response = sh.batch_import_findings(
        Findings=[{
            "SchemaVersion": "2018-10-08",
            "Id": f"{REGION}/{ACCOUNT_ID}/{finding_id}",
            "ProductArn": f"arn:aws:securityhub:{REGION}:{ACCOUNT_ID}:product/{ACCOUNT_ID}/default",
            "GeneratorId": "my-app-security-scanner",
            "AwsAccountId": ACCOUNT_ID,
            "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
            "FirstObservedAt": now,
            "UpdatedAt": now,
            "CreatedAt": now,
            "Severity": {"Label": severity},
            "Title": title,
            "Description": description,
            "Resources": [{
                "Type": resource_type,
                "Id": resource_id,
                "Region": REGION,
            }],
            "WorkflowState": "NEW",
            "RecordState": "ACTIVE",
        }]
    )

    failed = response.get("FailedCount", 0)
    if failed > 0:
        logger.error("Failed to import finding: title=%s failures=%s", title, response["FailedFindings"])
    else:
        logger.info("Finding imported successfully: title=%s", title)
```

---

## Insights (Saved Filters)

```bash
# Create an insight: group active high/critical findings by resource type
aws securityhub create-insight \
    --name "Active Critical Findings by Resource" \
    --filters '{
        "SeverityLabel": [{"Value": "CRITICAL", "Comparison": "EQUALS"}, {"Value": "HIGH", "Comparison": "EQUALS"}],
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
        "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}]
    }' \
    --group-by-attribute "ResourceType"

# Get insight results
INSIGHT_ARN=$(aws securityhub get-insights \
    --query 'Insights[?Name==`Active Critical Findings by Resource`].InsightArn' --output text)

aws securityhub get-insight-results \
    --insight-arn $INSIGHT_ARN \
    --query 'InsightResults.ResultItems[*].{Resource:GroupByAttributeValue,Count:Count}' \
    --output table
```

---

## References

- [Security Hub documentation](https://docs.aws.amazon.com/securityhub/latest/userguide/)
- [ASFF (Amazon Security Finding Format)](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-findings-format.html)
- [AWS Foundational Security Best Practices](https://docs.aws.amazon.com/securityhub/latest/userguide/fsbp-standard.html)
- [Automated remediation patterns](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cloudwatch-events.html)
---

← [Previous: GuardDuty](./guardduty.md) | [Home](../../README.md) | [Next: WAF & Shield →](./waf-shield.md)
