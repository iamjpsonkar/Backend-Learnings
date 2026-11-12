← [Previous: CloudWatch](./cloudwatch.md) | [Home](../../README.md) | [Next: AWS Config →](./config.md)

---

# AWS CloudTrail

CloudTrail records every API call made to your AWS account — who called what, from where, and when. It is the primary source of truth for security audits, compliance, and incident investigation.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Trail** | A configuration that delivers log files to an S3 bucket (optionally to CloudWatch Logs and EventBridge) |
| **Event** | A record of an API call: management event, data event, or Insights event |
| **Management event** | Control-plane actions — create/delete/modify AWS resources (always enabled for free in Event History) |
| **Data event** | Data-plane actions — S3 object reads/writes, Lambda invocations, DynamoDB item operations (charged) |
| **Insights event** | Anomaly detection — unusual write API call volume vs baseline (charged) |
| **Event History** | Last 90 days of management events, free, in the console — not configurable |
| **Organization trail** | A trail that covers all accounts in an AWS Organization |

---

## Creating a Trail

```bash
# Create an S3 bucket for CloudTrail logs
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="cloudtrail-logs-$ACCOUNT_ID-us-east-1"

aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region us-east-1

# Apply required bucket policy (CloudTrail needs permission to write)
aws s3api put-bucket-policy \
    --bucket $BUCKET_NAME \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AWSCloudTrailAclCheck",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": "arn:aws:s3:::'"$BUCKET_NAME"'"
            },
            {
                "Sid": "AWSCloudTrailWrite",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": "arn:aws:s3:::'"$BUCKET_NAME"'/AWSLogs/'"$ACCOUNT_ID"'/*",
                "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
            }
        ]
    }'

# Enable S3 server-side encryption and block public access
aws s3api put-bucket-encryption \
    --bucket $BUCKET_NAME \
    --server-side-encryption-configuration '{
        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "aws:kms", "KMSMasterKeyID": "alias/aws/s3"}}]
    }'

aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Create a multi-region trail with CloudWatch Logs integration
LOG_GROUP_ARN=$(aws logs create-log-group \
    --log-group-name "cloudtrail-management-events" \
    --query 'arn' 2>/dev/null || \
    aws logs describe-log-groups \
    --log-group-name-prefix "cloudtrail-management-events" \
    --query 'logGroups[0].arn' --output text)

aws logs put-retention-policy \
    --log-group-name "cloudtrail-management-events" \
    --retention-in-days 365

TRAIL_ARN=$(aws cloudtrail create-trail \
    --name org-management-trail \
    --s3-bucket-name $BUCKET_NAME \
    --is-multi-region-trail \
    --enable-log-file-validation \
    --cloud-watch-logs-log-group-arn "arn:aws:logs:us-east-1:$ACCOUNT_ID:log-group:cloudtrail-management-events:*" \
    --cloud-watch-logs-role-arn "arn:aws:iam::$ACCOUNT_ID:role/CloudTrail-CWLogs-Role" \
    --kms-key-id alias/cloudtrail-key \
    --tags-list Key=Environment,Value=production \
    --query 'TrailARN' --output text)

# Start logging
aws cloudtrail start-logging --name org-management-trail

# Verify status
aws cloudtrail get-trail-status --name org-management-trail \
    --query '{IsLogging:IsLogging,LatestDelivery:LatestDeliveryTime,LatestDigest:LatestDigestDeliveryTime}'
```

---

## Data Events

Data events are high-volume and charged per 100,000 events.

```bash
# Enable S3 data events (object-level logging) on all buckets
aws cloudtrail put-event-selectors \
    --trail-name org-management-trail \
    --event-selectors '[
        {
            "ReadWriteType": "All",
            "IncludeManagementEvents": true,
            "DataResources": [
                {
                    "Type": "AWS::S3::Object",
                    "Values": ["arn:aws:s3:::"]
                }
            ]
        }
    ]'

# Selective S3 data events (specific bucket only — recommended to control cost)
aws cloudtrail put-event-selectors \
    --trail-name org-management-trail \
    --event-selectors '[
        {
            "ReadWriteType": "WriteOnly",
            "IncludeManagementEvents": true,
            "DataResources": [
                {
                    "Type": "AWS::S3::Object",
                    "Values": ["arn:aws:s3:::my-sensitive-bucket/"]
                }
            ]
        }
    ]'

# Advanced event selectors (more granular — exclude noisy read events from specific prefixes)
aws cloudtrail put-advanced-event-selectors \
    --trail-name org-management-trail \
    --advanced-event-selectors '[
        {
            "Name": "Lambda invocations — all functions",
            "FieldSelectors": [
                {"Field": "eventCategory", "Equals": ["Data"]},
                {"Field": "resources.type", "Equals": ["AWS::Lambda::Function"]},
                {"Field": "readOnly", "Equals": ["false"]}
            ]
        },
        {
            "Name": "DynamoDB PutItem/DeleteItem on sensitive tables",
            "FieldSelectors": [
                {"Field": "eventCategory", "Equals": ["Data"]},
                {"Field": "resources.type", "Equals": ["AWS::DynamoDB::Table"]},
                {"Field": "resources.ARN", "StartsWith": ["arn:aws:dynamodb:us-east-1:123456789012:table/orders"]}
            ]
        }
    ]'
```

---

## CloudTrail Insights

```bash
# Enable Insights on an existing trail (detects unusual API call volume/error rate)
aws cloudtrail put-insight-selectors \
    --trail-name org-management-trail \
    --insight-selectors \
        InsightType=ApiCallRateInsight \
        InsightType=ApiErrorRateInsight

# Describe current insight configuration
aws cloudtrail get-insight-selectors --trail-name org-management-trail
```

---

## Querying CloudTrail

### Event History (Last 90 Days — No S3 Needed)

```bash
# Look up recent IAM events
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=CreateUser \
    --start-time "2024-01-01T00:00:00Z" \
    --query 'Events[*].{Time:EventTime,User:Username,EventName:EventName,Source:EventSource}' \
    --output table

# Find all API calls made by a specific IAM user
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=Username,AttributeValue=alice \
    --max-results 20 \
    --query 'Events[*].{Time:EventTime,Event:EventName,Source:EventSource,IP:CloudTrailEvent}' \
    --output table

# Find events for a specific resource
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=ResourceName,AttributeValue=my-s3-bucket \
    --query 'Events[*].{Time:EventTime,Event:EventName,User:Username}' \
    --output table
```

### Athena — Querying Archived Logs

```bash
# Create an Athena database and table over the CloudTrail S3 bucket
aws athena start-query-execution \
    --query-string "CREATE DATABASE IF NOT EXISTS cloudtrail_analysis" \
    --result-configuration OutputLocation=s3://my-athena-results/

# Create the CloudTrail table (replace bucket and account as needed)
aws athena start-query-execution \
    --query-string "
        CREATE EXTERNAL TABLE IF NOT EXISTS cloudtrail_analysis.cloudtrail_logs (
            eventVersion STRING,
            userIdentity STRUCT<
                type: STRING,
                principalId: STRING,
                arn: STRING,
                accountId: STRING,
                userName: STRING,
                sessionContext: STRUCT<
                    sessionIssuer: STRUCT<type: STRING, principalId: STRING, arn: STRING, accountId: STRING, userName: STRING>
                >
            >,
            eventTime STRING,
            eventSource STRING,
            eventName STRING,
            awsRegion STRING,
            sourceIPAddress STRING,
            userAgent STRING,
            errorCode STRING,
            errorMessage STRING,
            requestParameters STRING,
            responseElements STRING,
            requestID STRING,
            eventID STRING,
            readOnly BOOLEAN,
            resources ARRAY<STRUCT<ARN: STRING, accountId: STRING, type: STRING>>,
            eventType STRING,
            recipientAccountId STRING
        )
        ROW FORMAT SERDE 'com.amazon.emr.hive.serde.CloudTrailSerde'
        STORED AS INPUTFORMAT 'com.amazon.emr.cloudtrail.CloudTrailInputFormat'
        OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
        LOCATION 's3://$BUCKET_NAME/AWSLogs/$ACCOUNT_ID/CloudTrail/'
        TBLPROPERTIES ('classification'='cloudtrail')
    " \
    --result-configuration OutputLocation=s3://my-athena-results/

# Example query: Failed console logins in the last 7 days
# SELECT eventTime, userIdentity.userName, sourceIPAddress, errorCode, errorMessage
# FROM cloudtrail_analysis.cloudtrail_logs
# WHERE eventName = 'ConsoleLogin'
#   AND errorCode IS NOT NULL
#   AND eventTime > date_format(date_add('day', -7, current_date), '%Y-%m-%d')
# ORDER BY eventTime DESC

# Example query: IAM privilege escalation (AttachRolePolicy, PutUserPolicy)
# SELECT eventTime, userIdentity.arn, eventName, requestParameters
# FROM cloudtrail_analysis.cloudtrail_logs
# WHERE eventName IN ('AttachRolePolicy', 'PutUserPolicy', 'AttachUserPolicy', 'CreateAccessKey')
#   AND NOT errorCode IS NOT NULL
# ORDER BY eventTime DESC
# LIMIT 100
```

---

## CloudWatch Logs — Real-time Alerting on CloudTrail

After configuring CloudTrail → CloudWatch Logs, create metric filters for critical events:

```bash
# Alert on root account login
aws logs put-metric-filter \
    --log-group-name "cloudtrail-management-events" \
    --filter-name "root-account-login" \
    --filter-pattern '{ ($.userIdentity.type = "Root") && ($.eventType != "AwsServiceEvent") }' \
    --metric-transformations metricName=RootAccountLogins,metricNamespace=CloudTrailAlerts,metricValue=1,unit=Count

aws cloudwatch put-metric-alarm \
    --alarm-name "root-account-login" \
    --alarm-description "Root account login detected" \
    --namespace CloudTrailAlerts --metric-name RootAccountLogins \
    --statistic Sum --period 300 --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:security-alerts \
    --treat-missing-data notBreaching

# Alert on CloudTrail being disabled
aws logs put-metric-filter \
    --log-group-name "cloudtrail-management-events" \
    --filter-name "cloudtrail-disabled" \
    --filter-pattern '{ ($.eventName = StopLogging) }' \
    --metric-transformations metricName=CloudTrailDisabled,metricNamespace=CloudTrailAlerts,metricValue=1,unit=Count

# Alert on unauthorized API calls
aws logs put-metric-filter \
    --log-group-name "cloudtrail-management-events" \
    --filter-name "unauthorized-api-calls" \
    --filter-pattern '{ ($.errorCode = "AccessDenied") || ($.errorCode = "UnauthorizedAccess") }' \
    --metric-transformations metricName=UnauthorizedAPICalls,metricNamespace=CloudTrailAlerts,metricValue=1,unit=Count

# Alert on security group changes
aws logs put-metric-filter \
    --log-group-name "cloudtrail-management-events" \
    --filter-name "security-group-changes" \
    --filter-pattern '{ ($.eventName = AuthorizeSecurityGroupIngress) || ($.eventName = AuthorizeSecurityGroupEgress) || ($.eventName = RevokeSecurityGroupIngress) || ($.eventName = RevokeSecurityGroupEgress) }' \
    --metric-transformations metricName=SecurityGroupChanges,metricNamespace=CloudTrailAlerts,metricValue=1,unit=Count

# Alert on IAM policy changes
aws logs put-metric-filter \
    --log-group-name "cloudtrail-management-events" \
    --filter-name "iam-policy-changes" \
    --filter-pattern '{ ($.eventName = DeleteGroupPolicy) || ($.eventName = DeleteRolePolicy) || ($.eventName = DeleteUserPolicy) || ($.eventName = PutGroupPolicy) || ($.eventName = PutRolePolicy) || ($.eventName = PutUserPolicy) || ($.eventName = CreatePolicy) || ($.eventName = DeletePolicy) || ($.eventName = AttachGroupPolicy) || ($.eventName = DetachGroupPolicy) || ($.eventName = AttachRolePolicy) || ($.eventName = DetachRolePolicy) || ($.eventName = AttachUserPolicy) || ($.eventName = DetachUserPolicy) }' \
    --metric-transformations metricName=IAMPolicyChanges,metricNamespace=CloudTrailAlerts,metricValue=1,unit=Count
```

---

## Organization Trail

```bash
# Create a trail covering all accounts in the AWS Organization
# Must be run from the management account
aws cloudtrail create-trail \
    --name org-wide-trail \
    --s3-bucket-name $BUCKET_NAME \
    --is-multi-region-trail \
    --is-organization-trail \
    --enable-log-file-validation \
    --kms-key-id alias/cloudtrail-key

aws cloudtrail start-logging --name org-wide-trail

# List all trails (including shadow trails in member accounts)
aws cloudtrail describe-trails \
    --include-shadow-trails \
    --query 'trailList[*].{Name:Name,ARN:TrailARN,MultiRegion:IsMultiRegionTrail,OrgTrail:IsOrganizationTrail,LogValidation:LogFileValidationEnabled}' \
    --output table
```

---

## Log File Validation

CloudTrail creates a digest file every hour that can be used to detect tampering.

```bash
# Validate log files for the past 7 days
aws cloudtrail validate-logs \
    --trail-arn $TRAIL_ARN \
    --start-time "$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)" \
    --verbose
# Output shows: "Results requested for..." and "Files validated, 0 log file(s) invalid"
```

---

## Key Events for Security Monitoring

| Event | Significance |
|-------|-------------|
| `ConsoleLogin` with `errorCode` | Failed login — credential stuffing, brute force |
| `ConsoleLogin` with `userIdentity.type=Root` | Root login — should almost never happen |
| `StopLogging` | Someone disabled CloudTrail |
| `DeleteTrail` | Trail deleted — loss of audit trail |
| `CreateUser` / `CreateAccessKey` | New IAM principal — verify authorization |
| `AttachUserPolicy` / `AttachRolePolicy` | Privilege escalation risk |
| `PutBucketPolicy` / `PutBucketAcl` | S3 permissions change — data exfiltration risk |
| `AuthorizeSecurityGroupIngress` | Network exposure change |
| `AssumeRoleWithWebIdentity` | Federated access — verify IdP trust |

---

## References

- [CloudTrail documentation](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/)
- [CloudTrail log file format](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference.html)
- [Athena table for CloudTrail](https://docs.aws.amazon.com/athena/latest/ug/cloudtrail-logs.html)
- [CIS Benchmark CloudTrail controls](https://docs.aws.amazon.com/securityhub/latest/userguide/cis-aws-foundations-benchmark.html)
- [CloudTrail pricing](https://aws.amazon.com/cloudtrail/pricing/)
---

← [Previous: CloudWatch](./cloudwatch.md) | [Home](../../README.md) | [Next: AWS Config →](./config.md)
