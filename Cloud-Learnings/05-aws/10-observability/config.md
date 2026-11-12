← [Previous: CloudTrail](./cloudtrail.md) | [Home](../../README.md) | [Next: AWS Management →](../11-management/README.md)

---

# AWS Config

AWS Config continuously records the configuration state of your AWS resources and evaluates them against rules. It answers: "What did this resource look like at time T?" and "Does this resource comply with our policies?"

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Configuration item (CI)** | A snapshot of a resource's configuration at a point in time |
| **Configuration history** | Timeline of CIs for a resource — who changed what and when |
| **Configuration snapshot** | A point-in-time export of all resource configurations delivered to S3 |
| **Config rule** | An evaluation that checks if a resource is compliant with a policy |
| **Conformance pack** | A collection of Config rules deployed together (often from AWS sample packs) |
| **Remediation action** | An SSM Automation document triggered when a rule is non-compliant |
| **Aggregator** | Collects data from multiple accounts/regions into a single view |

---

## Enabling AWS Config

```bash
# Create S3 bucket for Config recordings
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="aws-config-recordings-$ACCOUNT_ID"

aws s3api create-bucket --bucket $BUCKET_NAME --region us-east-1

aws s3api put-bucket-policy \
    --bucket $BUCKET_NAME \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AWSConfigBucketPermissionsCheck",
                "Effect": "Allow",
                "Principal": {"Service": "config.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": "arn:aws:s3:::'"$BUCKET_NAME"'"
            },
            {
                "Sid": "AWSConfigBucketDelivery",
                "Effect": "Allow",
                "Principal": {"Service": "config.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": "arn:aws:s3:::'"$BUCKET_NAME"'/AWSLogs/'"$ACCOUNT_ID"'/Config/*",
                "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
            }
        ]
    }'

# Create an SNS topic for Config delivery notifications
SNS_ARN=$(aws sns create-topic --name aws-config-notifications --query 'TopicArn' --output text)

# Set up the Config recorder
aws configservice put-configuration-recorder \
    --configuration-recorder '{
        "name": "default",
        "roleARN": "arn:aws:iam::'"$ACCOUNT_ID"':role/AWSConfigRole",
        "recordingGroup": {
            "allSupported": true,
            "includeGlobalResourceTypes": true
        }
    }'

# Set up delivery channel
aws configservice put-delivery-channel \
    --delivery-channel '{
        "name": "default",
        "s3BucketName": "'"$BUCKET_NAME"'",
        "snsTopicARN": "'"$SNS_ARN"'",
        "configSnapshotDeliveryProperties": {
            "deliveryFrequency": "TwentyFour_Hours"
        }
    }'

# Start recording
aws configservice start-configuration-recorder --configuration-recorder-name default

# Verify
aws configservice describe-configuration-recorder-status \
    --query 'ConfigurationRecordersStatus[0].{Name:name,Recording:recording,LastStatus:lastStatus}'
```

---

## Config Rules

### AWS Managed Rules

```bash
# Enable a managed rule: S3 buckets must block public access
aws configservice put-config-rule \
    --config-rule '{
        "ConfigRuleName": "s3-bucket-public-access-prohibited",
        "Description": "Checks that S3 buckets have public access blocked",
        "Source": {
            "Owner": "AWS",
            "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED"
        },
        "Scope": {
            "ComplianceResourceTypes": ["AWS::S3::Bucket"]
        }
    }'

# Enable rule: root MFA should be enabled
aws configservice put-config-rule \
    --config-rule '{
        "ConfigRuleName": "root-account-mfa-enabled",
        "Source": {
            "Owner": "AWS",
            "SourceIdentifier": "ROOT_ACCOUNT_MFA_ENABLED"
        },
        "MaximumExecutionFrequency": "TwentyFour_Hours"
    }'

# Enable rule: all EBS volumes should be encrypted
aws configservice put-config-rule \
    --config-rule '{
        "ConfigRuleName": "encrypted-volumes",
        "Description": "EBS volumes attached to instances must be encrypted",
        "Source": {
            "Owner": "AWS",
            "SourceIdentifier": "ENCRYPTED_VOLUMES"
        },
        "Scope": {
            "ComplianceResourceTypes": ["AWS::EC2::Volume"]
        }
    }'

# Enable rule: RDS instances should not be publicly accessible
aws configservice put-config-rule \
    --config-rule '{
        "ConfigRuleName": "rds-instance-public-access-check",
        "Source": {
            "Owner": "AWS",
            "SourceIdentifier": "RDS_INSTANCE_PUBLIC_ACCESS_CHECK"
        },
        "Scope": {
            "ComplianceResourceTypes": ["AWS::RDS::DBInstance"]
        }
    }'

# List all rules and their compliance status
aws configservice describe-config-rules \
    --query 'ConfigRules[*].{Name:ConfigRuleName,Source:Source.SourceIdentifier,State:ConfigRuleState}' \
    --output table
```

### Custom Lambda Rules

```bash
# Register a custom rule backed by a Lambda function
aws configservice put-config-rule \
    --config-rule '{
        "ConfigRuleName": "ec2-instance-no-public-ip",
        "Description": "EC2 instances must not have a public IP",
        "Source": {
            "Owner": "CUSTOM_LAMBDA",
            "SourceIdentifier": "arn:aws:lambda:us-east-1:123456789012:function:config-ec2-public-ip-check",
            "SourceDetails": [
                {
                    "EventSource": "aws.config",
                    "MessageType": "ConfigurationItemChangeNotification"
                },
                {
                    "EventSource": "aws.config",
                    "MessageType": "OversizedConfigurationItemChangeNotification"
                }
            ]
        },
        "Scope": {
            "ComplianceResourceTypes": ["AWS::EC2::Instance"]
        }
    }'
```

```python
import boto3
import json
import logging

logger = logging.getLogger(__name__)
config_client = boto3.client("config")


def handler(event, context):
    """
    Custom Config rule Lambda: EC2 instances must not have a public IP.
    Called by Config whenever an EC2 instance configuration changes.
    """
    invoking_event = json.loads(event["invokingEvent"])
    rule_parameters = json.loads(event.get("ruleParameters", "{}"))

    if invoking_event.get("messageType") == "ScheduledNotification":
        logger.info("Scheduled notification — no CI to evaluate")
        return

    ci = invoking_event.get("configurationItem")
    if not ci:
        logger.warning("No configurationItem in event")
        return

    resource_type = ci["resourceType"]
    resource_id = ci["resourceId"]
    configuration = ci.get("configuration", {})
    status = ci.get("configurationItemStatus")

    logger.info(
        "Evaluating resource: type=%s id=%s status=%s",
        resource_type, resource_id, status
    )

    if status in ("ResourceDeleted", "ResourceNotRecorded", "ResourceDeletedNotRecorded"):
        compliance = "NOT_APPLICABLE"
    elif configuration.get("publicIpAddress"):
        logger.warning(
            "EC2 instance has public IP — NON_COMPLIANT: id=%s public_ip=%s",
            resource_id, configuration["publicIpAddress"]
        )
        compliance = "NON_COMPLIANT"
    else:
        logger.info("EC2 instance has no public IP — COMPLIANT: id=%s", resource_id)
        compliance = "COMPLIANT"

    config_client.put_evaluations(
        Evaluations=[{
            "ComplianceResourceType": resource_type,
            "ComplianceResourceId": resource_id,
            "ComplianceType": compliance,
            "Annotation": f"Public IP: {configuration.get('publicIpAddress', 'none')}",
            "OrderingTimestamp": ci["configurationItemCaptureTime"],
        }],
        ResultToken=event["resultToken"],
    )
    logger.info("Evaluation submitted: id=%s compliance=%s", resource_id, compliance)
```

---

## Viewing Compliance

```bash
# Get compliance summary across all rules
aws configservice get-compliance-summary-by-config-rule \
    --query 'ComplianceSummariesByConfigRule[*].{Rule:ConfigRuleName,Compliant:ComplianceByConfigRule.CompliantCount,NonCompliant:ComplianceByConfigRule.NonCompliantCount}' \
    --output table

# Get compliance by resource type
aws configservice get-compliance-summary-by-resource-type \
    --query 'ComplianceSummariesByResourceType[*].{Type:ResourceType,Compliant:ComplianceSummary.CompliantResourceCount,NonCompliant:ComplianceSummary.NonCompliantResourceCount}' \
    --output table

# List non-compliant resources for a specific rule
aws configservice get-compliance-details-by-config-rule \
    --config-rule-name "s3-bucket-public-access-prohibited" \
    --compliance-types NON_COMPLIANT \
    --query 'EvaluationResults[*].{ResourceType:EvaluationResultIdentifier.EvaluationResultQualifier.ResourceType,ResourceId:EvaluationResultIdentifier.EvaluationResultQualifier.ResourceId,Annotation:Annotation}' \
    --output table

# List non-compliant rules for a specific resource
aws configservice get-compliance-details-by-resource \
    --resource-type "AWS::S3::Bucket" \
    --resource-id "my-bucket-name" \
    --query 'EvaluationResults[*].{Rule:EvaluationResultIdentifier.EvaluationResultQualifier.ConfigRuleName,Compliance:ComplianceType,Annotation:Annotation}' \
    --output table

# Trigger manual re-evaluation of a rule
aws configservice start-config-rules-evaluation \
    --config-rule-names "s3-bucket-public-access-prohibited" "encrypted-volumes"
```

---

## Configuration History

```bash
# Get the configuration history for a specific resource
aws configservice get-resource-config-history \
    --resource-type "AWS::S3::Bucket" \
    --resource-id "my-bucket-name" \
    --limit 5 \
    --query 'configurationItems[*].{CapturedAt:configurationItemCaptureTime,Status:configurationItemStatus,ARN:arn}' \
    --output table

# List all recorded resources of a type
aws configservice list-discovered-resources \
    --resource-type "AWS::EC2::SecurityGroup" \
    --query 'resourceIdentifiers[*].{ResourceId:resourceId,Name:resourceName}' \
    --output table

# Deliver a configuration snapshot on demand
aws configservice deliver-config-snapshot --delivery-channel-name default
```

---

## Remediation

```bash
# Create a remediation for non-compliant S3 buckets — run SSM automation to block public access
aws configservice put-remediation-configurations \
    --remediation-configurations '[
        {
            "ConfigRuleName": "s3-bucket-public-access-prohibited",
            "TargetType": "SSM_DOCUMENT",
            "TargetId": "AWS-DisableS3BucketPublicReadWrite",
            "Parameters": {
                "AutomationAssumeRole": {
                    "StaticValue": {"Values": ["arn:aws:iam::123456789012:role/ConfigRemediationRole"]}
                },
                "S3BucketName": {
                    "ResourceValue": {"Value": "RESOURCE_ID"}
                }
            },
            "Automatic": true,
            "MaximumAutomaticAttempts": 3,
            "RetryAttemptSeconds": 60
        }
    ]'

# Manually trigger remediation for specific non-compliant resources
aws configservice start-remediation-execution \
    --config-rule-name "s3-bucket-public-access-prohibited" \
    --resource-keys '[{"resourceType": "AWS::S3::Bucket", "resourceId": "my-non-compliant-bucket"}]'

# Check remediation execution status
aws configservice describe-remediation-execution-statuses \
    --config-rule-name "s3-bucket-public-access-prohibited" \
    --query 'RemediationExecutionStatuses[*].{ResourceId:ResourceKey.resourceId,State:State,ErrorMessage:ErrorMessage}' \
    --output table
```

---

## Conformance Packs

```bash
# Deploy the AWS Operational Best Practices for S3 conformance pack
aws configservice put-conformance-pack \
    --conformance-pack-name "operational-best-practices-s3" \
    --template-s3-uri "s3://aws-configservice-us-east-1/conformance-packs-for-aws-config/Operational-Best-Practices-for-Amazon-S3.yaml" \
    --delivery-s3-bucket $BUCKET_NAME

# Check conformance pack compliance status
aws configservice get-conformance-pack-compliance-summary \
    --conformance-pack-names "operational-best-practices-s3" \
    --query 'ConformancePackComplianceSummaryList[*].{Pack:ConformancePackName,Compliant:ConformancePackComplianceSummary.CompliantRuleCount,NonCompliant:ConformancePackComplianceSummary.NonCompliantRuleCount}'

# List available AWS sample conformance packs
# AWS publishes packs for: CIS, NIST, PCI-DSS, HIPAA, FedRAMP, etc.
# Browse: https://docs.aws.amazon.com/config/latest/developerguide/conformancepack-sample-templates.html
```

---

## Multi-Account Aggregator

```bash
# Create an aggregator covering all accounts in the organization
aws configservice put-configuration-aggregator \
    --configuration-aggregator-name org-aggregator \
    --organization-aggregation-source \
        RoleArn=arn:aws:iam::123456789012:role/ConfigAggregationRole,AllAwsRegions=true

# Query aggregate compliance
aws configservice get-aggregate-compliance-details-by-config-rule \
    --configuration-aggregator-name org-aggregator \
    --config-rule-name "s3-bucket-public-access-prohibited" \
    --compliance-type NON_COMPLIANT \
    --query 'AggregateEvaluationResults[*].{Account:EvaluationResultIdentifier.EvaluationResultQualifier.ResourceId,Region:ResultRecordedTime}' \
    --output table

# Advanced query — SQL-like resource inventory search across all accounts
aws configservice select-aggregate-resource-config \
    --configuration-aggregator-name org-aggregator \
    --expression "
        SELECT accountId, awsRegion, resourceId, configuration.publiclyAccessible
        FROM AWS::RDS::DBInstance
        WHERE configuration.publiclyAccessible = true
    " \
    --query 'Results' --output text
```

---

## Common Managed Rules Reference

| Rule Identifier | What it checks |
|----------------|----------------|
| `S3_BUCKET_PUBLIC_READ_PROHIBITED` | S3 bucket not publicly readable |
| `ENCRYPTED_VOLUMES` | EBS volumes encrypted |
| `RDS_INSTANCE_PUBLIC_ACCESS_CHECK` | RDS not publicly accessible |
| `IAM_ROOT_ACCESS_KEY_CHECK` | Root account has no access keys |
| `ROOT_ACCOUNT_MFA_ENABLED` | Root MFA is enabled |
| `IAM_PASSWORD_POLICY` | Account password policy meets requirements |
| `CLOUDTRAIL_ENABLED` | CloudTrail is enabled in the account |
| `MULTI_REGION_CLOUD_TRAIL_ENABLED` | Multi-region trail exists |
| `VPC_FLOW_LOGS_ENABLED` | VPC flow logs are enabled |
| `EC2_SECURITY_GROUP_ATTACHED_TO_ENI` | Security groups are in use |
| `REQUIRED_TAGS` | Required tags are present on resources |
| `LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED` | Lambda not publicly accessible |

---

## References

- [AWS Config documentation](https://docs.aws.amazon.com/config/latest/developerguide/)
- [AWS Managed Rules list](https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html)
- [Conformance pack samples](https://docs.aws.amazon.com/config/latest/developerguide/conformancepack-sample-templates.html)
- [Advanced query](https://docs.aws.amazon.com/config/latest/developerguide/querying-AWS-resources.html)
- [AWS Config pricing](https://aws.amazon.com/config/pricing/)
---

← [Previous: CloudTrail](./cloudtrail.md) | [Home](../../README.md) | [Next: AWS Management →](../11-management/README.md)
