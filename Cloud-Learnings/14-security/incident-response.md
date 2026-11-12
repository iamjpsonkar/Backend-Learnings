← [Previous: Compliance](./compliance.md) | [Home](../README.md) | [Next: Supply Chain Security →](./supply-chain-security.md)

---

# Incident Response

Incident response is the structured process of detecting, containing, eradicating, and recovering from security incidents. An untested IR plan is not a plan.

---

## Incident Response Lifecycle

```
┌──────────────┐    ┌────────────┐    ┌─────────────┐    ┌──────────┐    ┌──────────────┐
│  Preparation │ →  │ Detection  │ →  │ Containment │ →  │ Eradicate│ →  │  Recovery    │
│              │    │ & Analysis │    │             │    │          │    │  & Lessons   │
│ • Runbooks   │    │ • Alerts   │    │ • Isolate   │    │ • Remove │    │ • Restore    │
│ • IR team    │    │ • Triage   │    │ • Block IPs │    │   IOCs   │    │ • Post-mortem│
│ • Tools      │    │ • Severity │    │ • Revoke    │    │ • Patch  │    │ • Improve    │
│ • Drills     │    │   rating   │    │   creds     │    │          │    │   controls   │
└──────────────┘    └────────────┘    └─────────────┘    └──────────┘    └──────────────┘
```

---

## Severity Levels

| Level | Name | Definition | Response Time |
|-------|------|-----------|---------------|
| P0 | Critical | Active breach, data exfiltration, ransomware | 15 min |
| P1 | High | Confirmed unauthorized access, service outage | 1 hour |
| P2 | Medium | Suspicious activity, potential compromise | 4 hours |
| P3 | Low | Security misconfiguration, policy violation | 24 hours |

---

## Detection: AWS GuardDuty

```bash
# Enable GuardDuty in all regions
for region in $(aws ec2 describe-regions --query 'Regions[*].RegionName' --output text); do
    aws guardduty create-detector \
        --enable \
        --finding-publishing-frequency FIFTEEN_MINUTES \
        --region $region
    echo "GuardDuty enabled in $region"
done

# List active high-severity findings
DETECTOR_ID=$(aws guardduty list-detectors --query 'DetectorIds[0]' --output text)

aws guardduty list-findings \
    --detector-id $DETECTOR_ID \
    --finding-criteria '{
        "Criterion": {
            "severity": {"Gte": 7},
            "service.archived": {"Eq": ["false"]}
        }
    }' \
    --query 'FindingIds' --output json | \
    xargs -I{} aws guardduty get-findings --detector-id $DETECTOR_ID --finding-ids {} \
    --query 'Findings[*].{Title:Title,Severity:Severity,Time:CreatedAt,Resource:Resource.ResourceType}'

# Archive a finding after investigation
aws guardduty archive-findings \
    --detector-id $DETECTOR_ID \
    --finding-ids $FINDING_ID

# Send GuardDuty findings to Slack via EventBridge + Lambda
aws events put-rule \
    --name GuardDutyHighSeverity \
    --event-pattern '{
        "source": ["aws.guardduty"],
        "detail-type": ["GuardDuty Finding"],
        "detail": {"severity": [{"numeric": [">=", 7]}]}
    }' \
    --state ENABLED
```

---

## Detection: CloudTrail Anomaly Queries

```bash
# Find root account usage (always suspicious)
aws logs filter-log-events \
    --log-group-name /aws/cloudtrail \
    --filter-pattern '{ ($.userIdentity.type = "Root") && ($.eventType != "AwsServiceEvent") }' \
    --start-time $(($(date +%s) - 86400))000 \
    --query 'events[*].message' | jq -r '.[] | fromjson | "\(.eventTime) \(.eventName) from \(.sourceIPAddress)"'

# Find API calls from unknown IPs (not your VPC CIDR or office IPs)
aws logs insights query \
    --log-group-name /aws/cloudtrail \
    --start-time $(($(date +%s) - 3600)) \
    --end-time $(date +%s) \
    --query-string '
        fields @timestamp, eventName, userIdentity.arn, sourceIPAddress
        | filter sourceIPAddress not like /^10\./ and sourceIPAddress not like /^172\.16\./
        | filter errorCode is blank
        | stats count(*) as callCount by sourceIPAddress, userIdentity.arn
        | sort callCount desc
        | limit 20
    '

# Find IAM privilege escalation attempts
aws logs filter-log-events \
    --log-group-name /aws/cloudtrail \
    --filter-pattern '{ ($.eventName = "CreatePolicy*" || $.eventName = "PutUserPolicy" || $.eventName = "AttachRolePolicy") && ($.errorCode = "AccessDenied") }' \
    --start-time $(($(date +%s) - 86400))000
```

---

## Containment Playbook: Compromised IAM Credential

```bash
#!/usr/bin/env bash
# IR-001: Compromised IAM credential containment
# Usage: ./contain-compromised-cred.sh ACCESS_KEY_ID

set -euo pipefail

KEY_ID="$1"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
IR_LOG="/tmp/ir-${KEY_ID}-${TIMESTAMP}.log"

log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$IR_LOG"; }

log "=== IR-001 CONTAINMENT STARTED ==="
log "Compromised key: $KEY_ID"
log "Operator: $(aws sts get-caller-identity --query 'Arn' --output text)"

# Step 1: Identify the owner
log "--- Step 1: Identify key owner ---"
aws iam list-users --query "Users[*].UserName" --output text | tr '\t' '\n' | while read user; do
    KEYS=$(aws iam list-access-keys --user-name "$user" --query "AccessKeyMetadata[?AccessKeyId=='$KEY_ID'].AccessKeyId" --output text)
    if [ -n "$KEYS" ]; then
        log "Key belongs to IAM user: $user"
        OWNER_USER="$user"
    fi
done

# Step 2: Disable the key immediately
log "--- Step 2: Disabling key ---"
aws iam update-access-key \
    --access-key-id "$KEY_ID" \
    --status Inactive
log "Key $KEY_ID disabled"

# Step 3: Deny all actions via inline policy (belt + suspenders)
log "--- Step 3: Applying deny-all policy ---"
aws iam put-user-policy \
    --user-name "${OWNER_USER}" \
    --policy-name "IR-LOCKOUT-${TIMESTAMP}" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Deny","Action": "*","Resource": "*"}]
    }'
log "Deny-all policy applied to ${OWNER_USER}"

# Step 4: Get recent API calls from this key
log "--- Step 4: Collecting recent activity ---"
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=AccessKeyId,AttributeValue="$KEY_ID" \
    --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
    --query 'Events[*].{Time:EventTime,Event:EventName,IP:CloudTrailEvent}' \
    --output json > "${IR_LOG%.log}-activity.json"
log "Recent activity saved to ${IR_LOG%.log}-activity.json"

# Step 5: Check for resources created by this key
log "--- Step 5: Check for created resources ---"
jq -r '.[].Event' "${IR_LOG%.log}-activity.json" 2>/dev/null | \
    python3 -c "import sys, json; [print(json.loads(l).get('eventName','')) for l in sys.stdin]" | \
    grep -E "^Create|^Run|^Launch" | sort | uniq -c | sort -rn | head -20 | tee -a "$IR_LOG"

log "=== CONTAINMENT COMPLETE ==="
log "Next: investigate activity log, check for exfiltrated data, notify stakeholders"
log "IR log: $IR_LOG"
```

---

## Containment Playbook: Compromised EC2 Instance

```bash
# IR-002: Isolate compromised EC2 instance

INSTANCE_ID="$1"
ISOLATION_SG="sg-ir-isolation"  # SG with NO inbound/outbound rules

# Step 1: Take memory snapshot (forensics — before isolation)
# Use AWS Systems Manager to run memory dump
aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters commands=["sudo avml /tmp/memory.lime && aws s3 cp /tmp/memory.lime s3://ir-evidence-${INSTANCE_ID}/"]

# Step 2: Take EBS snapshot (disk forensics)
VOLUME_ID=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query "Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId" \
    --output text)
aws ec2 create-snapshot \
    --volume-id "$VOLUME_ID" \
    --description "IR-${INSTANCE_ID}-$(date +%Y%m%d)" \
    --tag-specifications "ResourceType=snapshot,Tags=[{Key=ir-evidence,Value=true},{Key=instance,Value=$INSTANCE_ID}]"

# Step 3: Isolate — replace all security groups with isolation SG
aws ec2 modify-instance-attribute \
    --instance-id "$INSTANCE_ID" \
    --groups "$ISOLATION_SG"
echo "Instance $INSTANCE_ID isolated"

# Step 4: Disable instance metadata (prevent further cred exfiltration)
aws ec2 modify-instance-metadata-options \
    --instance-id "$INSTANCE_ID" \
    --http-endpoint disabled

# Step 5: Preserve — do NOT terminate yet (preserve forensic evidence)
# Stop instead
aws ec2 stop-instances --instance-ids "$INSTANCE_ID"
```

---

## Post-Incident Review Template

```markdown
## Incident Report: [INC-YYYY-NNN]

**Date:** YYYY-MM-DD
**Severity:** P[0-3]
**Duration:** X hours Y minutes
**Responders:** @responder1, @responder2
**Status:** Resolved / Monitoring

### Timeline

| Time (UTC) | Event |
|------------|-------|
| HH:MM | Alert triggered |
| HH:MM | Incident declared P1 |
| HH:MM | Root cause identified |
| HH:MM | Containment applied |
| HH:MM | Service restored |

### Root Cause
[Single sentence: what specifically went wrong]

### Impact
- Systems affected:
- Data exposure: None / Potential / Confirmed
- Users affected:
- Business impact:

### Detection Gap
[Why did it take X minutes to detect?]

### What Went Well
- Fast containment via automated playbook
- Clear escalation path

### What Needs Improvement
- Alert threshold too high (took 45 min to page)
- No runbook for this scenario

### Action Items

| Item | Owner | Due date | Priority |
|------|-------|----------|----------|
| Lower GuardDuty alert threshold | @owner | 2024-02-15 | P1 |
| Write IR-003 runbook | @owner | 2024-02-22 | P2 |
| Add MFA to all IAM users | @owner | 2024-02-28 | P1 |
```

---

## References

- [AWS Security Incident Response Guide](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/welcome.html)
- [NIST SP 800-61 Incident Handling](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf)
- [AWS GuardDuty](https://docs.aws.amazon.com/guardduty/latest/ug/)
- [SANS Incident Handler's Handbook](https://www.sans.org/white-papers/33901/)

---

← [Previous: Compliance](./compliance.md) | [Home](../README.md) | [Next: Supply Chain Security →](./supply-chain-security.md)
