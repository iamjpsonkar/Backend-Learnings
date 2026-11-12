← [Previous: ACM](./acm.md) | [Home](../../README.md) | [Next: Security Hub →](./security-hub.md)

---

# Amazon GuardDuty

GuardDuty is a managed threat detection service that continuously monitors AWS accounts for malicious activity and unauthorized behaviour. It uses machine learning, anomaly detection, and threat intelligence feeds — no agents to install, no log processing to manage.

---

## How GuardDuty Works

```
Data sources analyzed:
  VPC Flow Logs          → unusual traffic patterns, port scans, C2 callbacks
  CloudTrail management  → suspicious API calls, credential misuse
  CloudTrail S3 events   → data exfiltration, unusual S3 access
  DNS logs               → domains associated with malware/C2
  EKS audit logs         → container compromise, privilege escalation
  Malware Protection     → EBS volume scans on suspicious instances
  Lambda network logs    → Lambda-based threat activity
  RDS login events       → brute force, unusual DB access

GuardDuty ML + Threat Intel → Findings → EventBridge → Alerting/Remediation
```

---

## Enabling GuardDuty

```bash
# Enable GuardDuty in the current account and region
DETECTOR_ID=$(aws guardduty create-detector \
    --enable \
    --finding-publishing-frequency FIFTEEN_MINUTES \
    --data-sources '{
        "S3Logs": {"Enable": true},
        "Kubernetes": {"AuditLogs": {"Enable": true}},
        "MalwareProtection": {"ScanEc2InstanceWithFindings": {"EbsVolumes": {"Enable": true}}}
    }' \
    --tags Environment=production \
    --query 'DetectorId' --output text)

echo "Detector ID: $DETECTOR_ID"

# Enable additional protection plans
aws guardduty update-detector \
    --detector-id $DETECTOR_ID \
    --features '[
        {"Name": "S3_DATA_EVENTS", "Status": "ENABLED"},
        {"Name": "EKS_AUDIT_LOGS", "Status": "ENABLED"},
        {"Name": "EBS_MALWARE_PROTECTION", "Status": "ENABLED"},
        {"Name": "RDS_LOGIN_EVENTS", "Status": "ENABLED"},
        {"Name": "LAMBDA_NETWORK_LOGS", "Status": "ENABLED"}
    ]'

# Verify detector is enabled
aws guardduty get-detector --detector-id $DETECTOR_ID \
    --query '{Status:Status,Updated:UpdatedAt,FreqPublish:FindingPublishingFrequency}'
```

---

## Multi-Account Setup (Delegated Admin)

In an AWS Organization, designate a security account as the GuardDuty administrator to centrally manage all member accounts.

```bash
ORG_MANAGEMENT_ACCOUNT="111111111111"
SECURITY_ACCOUNT="333333333333"

# From the management account: designate the security account as delegated admin
aws guardduty enable-organization-admin-account \
    --admin-account-id $SECURITY_ACCOUNT

# From the security account: enable auto-enroll for new org accounts
aws guardduty update-organization-configuration \
    --detector-id $DETECTOR_ID \
    --auto-enable ALL \
    --features '[
        {"Name": "S3_DATA_EVENTS", "AutoEnable": "NEW"},
        {"Name": "EKS_AUDIT_LOGS", "AutoEnable": "NEW"},
        {"Name": "EBS_MALWARE_PROTECTION", "AutoEnable": "NEW"}
    ]'

# List member accounts
aws guardduty list-members \
    --detector-id $DETECTOR_ID \
    --query 'Members[*].{Account:AccountId,Email:Email,Status:RelationshipStatus}' \
    --output table
```

---

## Finding Types and Severity

GuardDuty findings are named `ThreatPurpose:ResourceTypeAffected/ThreatFamilyName.DetectionMechanism.Artifact`.

### Finding Categories

| Category | Examples | Meaning |
|----------|---------|---------|
| **Backdoor** | `Backdoor:EC2/C&CActivity.B` | Instance communicating with known C2 server |
| **Behavior** | `Behavior:EC2/NetworkPortUnusual` | Unusual outbound port activity |
| **CryptoCurrency** | `CryptoCurrency:EC2/BitcoinTool.B` | Bitcoin mining detected |
| **DefenseEvasion** | `DefenseEvasion:IAMUser/TrojanizedCodeExecution` | Attempts to disable security controls |
| **Discovery** | `Discovery:S3/MaliciousIPCaller` | S3 API calls from threat-listed IPs |
| **Exfiltration** | `Exfiltration:S3/ObjectRead.Unusual` | Unusual S3 read volume |
| **Impact** | `Impact:EC2/PortSweep` | Port scanning from your instances |
| **InitialAccess** | `InitialAccess:IAMUser/TorIPCaller` | API calls via Tor exit nodes |
| **Persistence** | `Persistence:IAMUser/UserPermissions` | IAM changes suggesting persistence |
| **PrivilegeEscalation** | `PrivilegeEscalation:IAMUser/AdministrativePermissions` | User gaining admin rights |
| **Recon** | `Recon:IAMUser/UserPermissions` | Discovery of IAM policies/users |
| **Stealth** | `Stealth:IAMUser/CloudTrailLoggingDisabled` | CloudTrail disabled |
| **Trojan** | `Trojan:EC2/BlackholeTraffic` | Traffic to blackhole IPs |
| **UnauthorizedAccess** | `UnauthorizedAccess:EC2/SSHBruteForce` | SSH brute force detected |

**Severity:** 0.1–3.9 Low, 4.0–6.9 Medium, 7.0–8.9 High, 9.0–10.0 Critical.

---

## Viewing and Managing Findings

```bash
DETECTOR_ID="abc123def456"

# List findings (most severe first)
aws guardduty list-findings \
    --detector-id $DETECTOR_ID \
    --finding-criteria '{
        "Criterion": {
            "severity": {"Gte": 7}
        }
    }' \
    --sort-criteria AttributeName=severity,OrderBy=DESC \
    --query 'FindingIds' --output text | head -5

# Get finding details
aws guardduty get-findings \
    --detector-id $DETECTOR_ID \
    --finding-ids FINDING_ID_1 FINDING_ID_2 \
    --query 'Findings[*].{
        ID:Id,
        Type:Type,
        Severity:Severity,
        Title:Title,
        Region:Region,
        Account:AccountId,
        Created:CreatedAt
    }' \
    --output table

# Archive resolved findings
aws guardduty archive-findings \
    --detector-id $DETECTOR_ID \
    --finding-ids FINDING_ID_1

# List archived findings
aws guardduty list-findings \
    --detector-id $DETECTOR_ID \
    --finding-criteria '{"Criterion": {"service.archived": {"Eq": ["true"]}}}'

# Create a suppression rule (suppress findings matching criteria — e.g., known vulnerability scanners)
aws guardduty create-filter \
    --detector-id $DETECTOR_ID \
    --name suppress-security-scanner \
    --action ARCHIVE \
    --finding-criteria '{
        "Criterion": {
            "type": {"Eq": ["Recon:EC2/PortProbeUnprotectedPort"]},
            "service.action.networkConnectionAction.remoteIpDetails.ipAddressV4": {
                "Eq": ["203.0.113.10"]
            }
        }
    }'
```

---

## Automated Remediation via EventBridge

Route GuardDuty findings to EventBridge and trigger automated responses.

```bash
# Create EventBridge rule for high-severity GuardDuty findings
aws events put-rule \
    --name guardduty-high-severity \
    --event-pattern '{
        "source": ["aws.guardduty"],
        "detail-type": ["GuardDuty Finding"],
        "detail": {
            "severity": [{"numeric": [">=", 7.0]}]
        }
    }' \
    --state ENABLED

# Route to Lambda for automated response
aws events put-targets \
    --rule guardduty-high-severity \
    --targets \
        "Id=remediation-lambda,Arn=arn:aws:lambda:us-east-1:123456789012:function:guardduty-remediation" \
        "Id=ops-alert,Arn=arn:aws:sns:us-east-1:123456789012:ops-alerts"
```

Example remediation Lambda:

```python
import boto3
import json
import logging

logger = logging.getLogger(__name__)
ec2 = boto3.client("ec2")
iam = boto3.client("iam")


def handler(event, context):
    """
    Automated GuardDuty remediation for high-severity findings.
    Isolates compromised EC2 instances and disables suspicious IAM users.
    """
    finding = event["detail"]
    finding_type = finding["type"]
    severity = finding["severity"]
    account_id = finding["accountId"]
    request_id = context.aws_request_id

    logger.info("Remediating finding: type=%s severity=%.1f account=%s request_id=%s",
                finding_type, severity, account_id, request_id)

    resource_type = finding["resource"]["resourceType"]

    if resource_type == "Instance":
        instance_id = finding["resource"]["instanceDetails"]["instanceId"]
        logger.warning("Isolating EC2 instance: instance_id=%s finding_type=%s", instance_id, finding_type)
        isolate_instance(instance_id, finding_type)

    elif resource_type == "AccessKey":
        user_name = finding["resource"]["accessKeyDetails"].get("userName")
        if user_name:
            logger.warning("Disabling IAM user: user=%s finding_type=%s", user_name, finding_type)
            disable_iam_user(user_name, finding_type)

    logger.info("Remediation complete: type=%s", finding_type)


def isolate_instance(instance_id: str, reason: str) -> None:
    """Apply an empty security group to stop all traffic to/from the instance."""
    try:
        # Create isolation security group (no rules = no traffic)
        sg_id = ec2.create_security_group(
            GroupName=f"isolation-{instance_id}",
            Description=f"Isolation SG — GuardDuty finding: {reason}",
            VpcId=get_instance_vpc(instance_id),
        )["GroupId"]

        ec2.modify_instance_attribute(
            InstanceId=instance_id,
            Groups=[sg_id],
        )
        logger.warning("Instance isolated: instance_id=%s sg_id=%s", instance_id, sg_id)
    except Exception as e:
        logger.error("Failed to isolate instance: instance_id=%s error=%s", instance_id, str(e))
        raise


def disable_iam_user(user_name: str, reason: str) -> None:
    """Disable all access keys for a suspicious IAM user."""
    try:
        keys = iam.list_access_keys(UserName=user_name)["AccessKeyMetadata"]
        for key in keys:
            if key["Status"] == "Active":
                iam.update_access_key(
                    UserName=user_name,
                    AccessKeyId=key["AccessKeyId"],
                    Status="Inactive",
                )
                logger.warning("Access key disabled: user=%s key_id=%s reason=%s",
                               user_name, key["AccessKeyId"], reason)
    except Exception as e:
        logger.error("Failed to disable IAM user: user=%s error=%s", user_name, str(e))
        raise


def get_instance_vpc(instance_id: str) -> str:
    response = ec2.describe_instances(InstanceIds=[instance_id])
    return response["Reservations"][0]["Instances"][0]["VpcId"]
```

---

## Sample Findings for Testing

```bash
# Generate a sample finding to test your alerting pipeline
aws guardduty create-sample-findings \
    --detector-id $DETECTOR_ID \
    --finding-types \
        "UnauthorizedAccess:EC2/SSHBruteForce" \
        "Recon:IAMUser/UserPermissions" \
        "CryptoCurrency:EC2/BitcoinTool.B"
```

---

## References

- [GuardDuty documentation](https://docs.aws.amazon.com/guardduty/latest/ug/)
- [Finding types reference](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-active.html)
- [Automated remediation patterns](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_remediate.html)
- [GuardDuty pricing](https://aws.amazon.com/guardduty/pricing/)
---

← [Previous: ACM](./acm.md) | [Home](../../README.md) | [Next: Security Hub →](./security-hub.md)
