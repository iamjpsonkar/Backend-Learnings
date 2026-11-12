← [Previous: Assessment](./assessment.md) | [Home](../README.md) | [Next: Replatform →](./replatform.md)

---

# Lift & Shift (Rehost)

Rehost moves a workload to AWS with no code changes. The VM keeps the same OS, same software, same configuration — it just runs on EC2 instead of on-premises hardware. It's the fastest migration path and the right choice for legacy apps that need to move quickly.

---

## AWS Application Migration Service (MGN)

AWS MGN is the primary rehost tool. It replicates disks continuously via a lightweight agent, then performs a cutover with typically < 1 hour of downtime.

### Architecture

```
On-premises server          AWS
      │                      │
      │  Agent (TCP 443)     │
      ├─────────────────────►│  Replication Server (t3.small)
      │  Block-level          │        │
      │  replication          │        ▼
      │                      │  Staging Area (EBS volumes)
      │                      │        │  (same type/size as source)
      │                      │        ▼
      │  Cutover             │  Target EC2 Instance
      └─────────────────────►│  (your chosen instance type)
```

### Setup and Agent Installation

```bash
# Step 1: Initialize MGN in the target region
aws mgn initialize-service --region us-east-1

# Step 2: Create replication settings template
aws mgn create-replication-configuration-template \
    --staging-area-subnet-id subnet-abc123 \
    --replication-server-instance-type t3.small \
    --replication-servers-security-groups-ids sg-replication \
    --use-dedicated-replication-server false \
    --default-large-staging-disk-type gp3 \
    --bandwidth-throttling 0 \
    --create-public-ip false \
    --staging-area-tags '{"purpose":"mgn-staging"}' \
    --region us-east-1

# Step 3: Install agent on source server (Linux)
wget -O ./aws-replication-installer-init.py \
    https://aws-application-migration-service-us-east-1.s3.amazonaws.com/latest/linux/aws-replication-installer-init.py

sudo python3 aws-replication-installer-init.py \
    --region us-east-1 \
    --aws-access-key-id $ACCESS_KEY \
    --aws-secret-access-key $SECRET_KEY \
    --no-prompt

# Step 4: Install agent on source server (Windows — PowerShell)
# Download installer from AWS console, then:
# .\AwsReplicationWindowsInstaller.exe --region us-east-1 --aws-access-key-id ... --aws-secret-access-key ...
```

### Configure Launch Template

```bash
SOURCE_SERVER_ID=$(aws mgn describe-source-servers \
    --filters itemType=SOURCE_SERVER,machineStatus=READY_FOR_TEST \
    --query 'items[0].sourceServerID' --output text)

# Update launch template: instance type, VPC, subnet, SG, IAM profile
aws mgn update-launch-configuration \
    --source-server-id $SOURCE_SERVER_ID \
    --target-instance-type-right-sizing-method BASIC \
    --launch-disposition STOPPED \
    --licensing '{"osByol": false}' \
    --name "prod-web-01-launch-config"

# Set EC2 launch template overrides
aws mgn update-launch-configuration-template \
    --launch-configuration-template-id $TEMPLATE_ID \
    --post-launch-actions '{"deploymentType": "CUTOVER_ONLY"}'
```

### Test and Cutover

```bash
# Launch test instance (non-destructive — runs alongside source)
aws mgn start-test \
    --source-server-ids $SOURCE_SERVER_ID

# Wait for test instance to be ready
aws mgn describe-source-servers \
    --filters itemType=SOURCE_SERVER \
    --query 'items[0].dataReplicationInfo.dataReplicationState'

# Validate test instance (run your smoke tests, health checks)
# Then mark test as passed
aws mgn mark-as-ready-for-cutover \
    --source-server-ids $SOURCE_SERVER_ID

# Schedule cutover (during maintenance window)
aws mgn start-cutover \
    --source-server-ids $SOURCE_SERVER_ID

# After cutover: finalize (stops replication, cleans up staging area)
aws mgn finalize-cutover \
    --source-server-ids $SOURCE_SERVER_ID

# Archive the source server record
aws mgn disconnect-from-service \
    --source-server-ids $SOURCE_SERVER_ID
```

---

## VM Import / Export

For one-off imports without the MGN agent (e.g., importing a VM snapshot, exporting back to on-premises).

```bash
# Step 1: Upload VM disk image to S3
aws s3 cp ./my-server.vmdk s3://migration-bucket/vmimport/my-server.vmdk

# Step 2: Create import role (required for VMImport)
# Trust policy: vmie.amazonaws.com
aws iam create-role \
    --role-name vmimport \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"vmie.amazonaws.com"},"Action":"sts:AssumeRole","Condition":{"StringEquals":{"sts:Externalid":"vmimport"}}}]}'

aws iam put-role-policy \
    --role-name vmimport \
    --policy-name vmimport-policy \
    --policy-document '{
        "Version":"2012-10-17",
        "Statement":[
            {"Effect":"Allow","Action":["s3:GetBucketLocation","s3:GetObject","s3:ListBucket"],"Resource":["arn:aws:s3:::migration-bucket","arn:aws:s3:::migration-bucket/*"]},
            {"Effect":"Allow","Action":["ec2:ModifySnapshotAttribute","ec2:CopySnapshot","ec2:RegisterImage","ec2:Describe*"],"Resource":"*"}
        ]
    }'

# Step 3: Import the image
cat > containers.json << 'EOF'
[{
    "Description": "My Server",
    "Format": "vmdk",
    "Url": "s3://migration-bucket/vmimport/my-server.vmdk"
}]
EOF

aws ec2 import-image \
    --description "My Server Import" \
    --disk-containers file://containers.json

IMPORT_TASK_ID=$(aws ec2 describe-import-image-tasks \
    --query 'ImportImageTasks[0].ImportTaskId' --output text)

# Monitor progress
aws ec2 describe-import-image-tasks \
    --import-task-ids $IMPORT_TASK_ID \
    --query 'ImportImageTasks[0].{Status:Status,Progress:Progress,Detail:StatusMessage}'

# Once complete, launch from the imported AMI
AMI_ID=$(aws ec2 describe-import-image-tasks \
    --import-task-ids $IMPORT_TASK_ID \
    --query 'ImportImageTasks[0].ImageId' --output text)

aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type m5.xlarge \
    --subnet-id subnet-target \
    --security-group-ids sg-app \
    --iam-instance-profile Name=EC2-SSM-Profile \
    --no-associate-public-ip-address \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=migrated-server}]'
```

---

## Rehost Patterns

### Database Lift-and-Shift

```bash
# EC2-hosted database: same engine, same version, just on EC2
# Use this when: specific version lock, custom config, licensing constraints

# 1. Create target EC2 for database
aws ec2 run-instances \
    --image-id ami-rhel-latest \
    --instance-type r5.2xlarge \
    --subnet-id subnet-private \
    --security-group-ids sg-db \
    --no-associate-public-ip-address \
    --ebs-optimized

# 2. Create optimized EBS volumes
aws ec2 create-volume \
    --availability-zone us-east-1a \
    --volume-type io2 \
    --size 500 \
    --iops 16000 \
    --encrypted \
    --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abc123

# 3. Use rsync for initial data sync (then switch to native replication)
rsync -avz --progress \
    --exclude=/proc --exclude=/sys --exclude=/dev \
    -e "ssh -i ~/.ssh/migration-key.pem" \
    /data/postgres/ \
    ec2-user@$TARGET_IP:/data/postgres/

# 4. Switch to PostgreSQL streaming replication for cutover
# On source: pg_hba.conf — add replication slot for target
# On target: recovery.conf / postgresql.conf primary_conninfo
```

### Network Cutover Checklist

```bash
# Pre-cutover
# 1. Reduce DNS TTL to 60s (24h before cutover)
aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch '{
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "app.mycompany.com",
                "Type": "A",
                "TTL": 60,
                "ResourceRecords": [{"Value": "OLD_IP"}]
            }
        }]
    }'

# 2. Verify target instance health
curl -sf http://$TARGET_IP/health/ready || echo "NOT READY — do not cut over"

# Cutover
# 3. Stop writes on source (application-level freeze or maintenance mode)
# 4. Final data sync
# 5. Validate data on target
# 6. Update DNS to target IP
aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch "{
        \"Changes\": [{
            \"Action\": \"UPSERT\",
            \"ResourceRecordSet\": {
                \"Name\": \"app.mycompany.com\",
                \"Type\": \"A\",
                \"TTL\": 300,
                \"ResourceRecords\": [{\"Value\": \"$TARGET_IP\"}]
            }
        }]
    }"

# Post-cutover (keep source running for 48h as rollback option)
```

---

## Post-Rehost Optimization

After a successful rehost, right-size and modernize incrementally:

| Immediate (Week 1) | Short-term (Month 1) | Medium-term (Quarter 1) |
|-------------------|---------------------|------------------------|
| Enable CloudWatch agent | Right-size instances (Compute Optimizer) | Enable Auto Scaling |
| Enable Systems Manager | Replace static creds with IAM roles | Migrate to managed services (RDS) |
| Tag all resources | Enable encryption at rest | Enable backups via AWS Backup |
| Enable VPC Flow Logs | Patch OS + software | Consider Reserved Instances |

---

## References

- [AWS Application Migration Service](https://docs.aws.amazon.com/mgn/latest/ug/)
- [VM Import/Export](https://docs.aws.amazon.com/vm-import/latest/userguide/)
- [MGN best practices](https://docs.aws.amazon.com/mgn/latest/ug/best-practices.html)

---

← [Previous: Assessment](./assessment.md) | [Home](../README.md) | [Next: Replatform →](./replatform.md)
