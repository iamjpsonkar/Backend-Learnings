← [Previous: EC2](./ec2.md) | [Home](../../README.md) | [Next: Auto Scaling →](./auto-scaling.md)

---

# AMIs and Launch Templates

An Amazon Machine Image (AMI) is a snapshot of an EC2 instance that serves as the blueprint for new instances. Launch templates define the full configuration for launching EC2 instances, enabling consistent, reproducible deployments.

---

## Amazon Machine Images (AMIs)

### AMI Components

An AMI includes:
- **Root volume snapshot** — the OS, installed packages, application code
- **Block device mapping** — defines EBS volumes attached at launch
- **Launch permissions** — which accounts can use the AMI
- **Virtualization type** — HVM (all modern instance types) or PV (legacy)

### Finding AMIs

```bash
# Find the latest Amazon Linux 2023 AMI in us-east-1
aws ec2 describe-images \
    --owners amazon \
    --filters \
        "Name=name,Values=al2023-ami-2023*-x86_64" \
        "Name=state,Values=available" \
    --query 'sort_by(Images, &CreationDate)[-1].{ID:ImageId,Name:Name,Created:CreationDate}' \
    --output table

# Find latest Ubuntu 22.04 LTS AMI
aws ec2 describe-images \
    --owners 099720109477 \    # Canonical's AWS account ID
    --filters \
        "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64*" \
        "Name=state,Values=available" \
    --query 'sort_by(Images, &CreationDate)[-1].{ID:ImageId,Name:Name}' \
    --output table

# Using SSM Parameter Store for latest AMI (most reliable)
aws ssm get-parameter \
    --name /aws/service/ami-amazon-linux-latest/al2023-ami-minimal-kernel-default-x86_64 \
    --query 'Parameter.Value' --output text

# For ARM (Graviton) instances
aws ssm get-parameter \
    --name /aws/service/ami-amazon-linux-latest/al2023-ami-minimal-kernel-default-arm64 \
    --query 'Parameter.Value' --output text
```

### Creating a Custom AMI

Creating a custom (golden) AMI bakes your application dependencies and configuration into the image, eliminating bootstrap time at launch.

```bash
INSTANCE_ID="i-0abc1234"

# Step 1: Prepare the instance (install packages, configure app, clean up)
# ssh to instance, then:
#   sudo yum update -y && sudo yum install -y your-app-packages
#   sudo systemctl enable your-service
#   sudo rm -rf /tmp/* /var/log/cloud-init* ~/.bash_history
#   history -c

# Step 2: Create the AMI (instance can be running — AWS takes snapshots)
AMI_ID=$(aws ec2 create-image \
    --instance-id $INSTANCE_ID \
    --name "my-app-v1.2.3-$(date +%Y%m%d)" \
    --description "Golden AMI for my-app version 1.2.3" \
    --no-reboot \
    --tag-specifications 'ResourceType=image,Tags=[{Key=Name,Value=my-app-golden},{Key=Version,Value=1.2.3},{Key=Environment,Value=production}]' \
    --query 'ImageId' --output text)

echo "Creating AMI: $AMI_ID"

# Step 3: Wait for AMI to be available (can take 5–15 minutes)
aws ec2 wait image-available --image-ids $AMI_ID
echo "AMI ready: $AMI_ID"

# Step 4: Add block device mapping for additional volumes
aws ec2 create-image \
    --instance-id $INSTANCE_ID \
    --name "my-app-with-data-volume" \
    --block-device-mappings '[
        {
            "DeviceName": "/dev/xvda",
            "Ebs": {"VolumeType": "gp3", "Encrypted": true, "DeleteOnTermination": true}
        },
        {
            "DeviceName": "/dev/xvdb",
            "Ebs": {"VolumeSize": 100, "VolumeType": "gp3", "Encrypted": true}
        }
    ]'
```

### Copying AMIs Across Regions

```bash
SOURCE_REGION="us-east-1"
DEST_REGION="eu-west-1"
AMI_ID="ami-0abc1234"

# Copy AMI to another region (for multi-region deployment)
COPIED_AMI=$(aws ec2 copy-image \
    --source-region $SOURCE_REGION \
    --source-image-id $AMI_ID \
    --region $DEST_REGION \
    --name "my-app-v1.2.3-eu-west-1" \
    --encrypted \
    --query 'ImageId' --output text)

echo "Copied AMI in $DEST_REGION: $COPIED_AMI"
```

### Sharing AMIs Across Accounts

```bash
TARGET_ACCOUNT="222222222222"

# Share AMI with another account
aws ec2 modify-image-attribute \
    --image-id $AMI_ID \
    --launch-permission "Add=[{UserId=$TARGET_ACCOUNT}]"

# Share with all accounts in your organization
aws ec2 modify-image-attribute \
    --image-id $AMI_ID \
    --launch-permission "Add=[{OrganizationArn=arn:aws:organizations::111111111111:organization/o-abc123}]"

# Make AMI public (use carefully — contains your OS config)
aws ec2 modify-image-attribute \
    --image-id $AMI_ID \
    --launch-permission "Add=[{Group=all}]"

# View current permissions
aws ec2 describe-image-attribute \
    --image-id $AMI_ID \
    --attribute launchPermission
```

### AMI Lifecycle Management

```bash
# List all your AMIs sorted by creation date
aws ec2 describe-images \
    --owners self \
    --query 'sort_by(Images, &CreationDate)[*].{ID:ImageId,Name:Name,Created:CreationDate,State:State}' \
    --output table

# Deregister an old AMI (does not delete snapshots automatically)
aws ec2 deregister-image --image-id ami-old1234

# Find and delete associated snapshots
aws ec2 describe-snapshots \
    --owner-ids self \
    --filters "Name=description,Values=*ami-old1234*" \
    --query 'Snapshots[*].SnapshotId' --output text | \
    xargs -I {} aws ec2 delete-snapshot --snapshot-id {}

# Enable AMI lifecycle management with AWS DLM (Data Lifecycle Manager)
aws dlm create-lifecycle-policy \
    --description "Retain last 5 golden AMIs" \
    --state ENABLED \
    --execution-role-arn arn:aws:iam::123456789012:role/AWSDataLifecycleManagerDefaultRoleForAMIManagement \
    --policy-details '{
        "PolicyType": "IMAGE_MANAGEMENT",
        "ResourceTypes": ["INSTANCE"],
        "TargetTags": [{"Key": "Environment", "Value": "production"}],
        "Schedules": [{
            "Name": "weekly-ami",
            "CreateRule": {
                "Interval": 7,
                "IntervalUnit": "DAYS",
                "Times": ["03:00"]
            },
            "RetainRule": {"Count": 5},
            "TagsToAdd": [{"Key": "CreatedBy", "Value": "DLM"}]
        }]
    }'
```

---

## Launch Templates

A launch template captures the full configuration for launching EC2 instances. It replaces and supersedes launch configurations (used by older ASGs).

**Advantages over launch configurations:**
- Supports versioning (v1, v2, v3… you can roll back)
- Supports all instance types including Spot and multiple instance types
- Can be used with EC2 Fleet, Spot Fleet, and Auto Scaling Groups
- Supports T3/T4g unlimited credit mode, EFA, Nitro Enclaves, Capacity Reservations

### Create a Launch Template

```bash
VPC_ID="vpc-0abc1234"
SG_APP="sg-0app1234"
SUBNET_PRIV_A="subnet-0priv1a"

TEMPLATE_ID=$(aws ec2 create-launch-template \
    --launch-template-name "my-app-lt" \
    --version-description "v1 — initial" \
    --launch-template-data '{
        "ImageId": "ami-0abc1234",
        "InstanceType": "t3.medium",
        "KeyName": "my-key-pair",
        "NetworkInterfaces": [{
            "AssociatePublicIpAddress": false,
            "DeviceIndex": 0,
            "SubnetId": "'$SUBNET_PRIV_A'",
            "Groups": ["'$SG_APP'"]
        }],
        "IamInstanceProfile": {
            "Name": "EC2AppInstanceProfile"
        },
        "EbsOptimized": true,
        "BlockDeviceMappings": [{
            "DeviceName": "/dev/xvda",
            "Ebs": {
                "VolumeSize": 30,
                "VolumeType": "gp3",
                "Iops": 3000,
                "Throughput": 125,
                "Encrypted": true,
                "DeleteOnTermination": true
            }
        }],
        "MetadataOptions": {
            "HttpTokens": "required",
            "HttpPutResponseHopLimit": 1,
            "HttpEndpoint": "enabled"
        },
        "TagSpecifications": [{
            "ResourceType": "instance",
            "Tags": [
                {"Key": "Name", "Value": "my-app"},
                {"Key": "Environment", "Value": "production"}
            ]
        }],
        "UserData": "'$(base64 -w0 <<'USERDATA'
#!/bin/bash
set -euo pipefail
exec > /var/log/user-data.log 2>&1

echo "[INFO] Starting bootstrap at $(date)"

# Install application dependencies
yum install -y amazon-cloudwatch-agent

# Configure and start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config -m ec2 -s \
    -c ssm:/app/cloudwatch-agent-config

# Start application service
systemctl enable --now my-app

echo "[INFO] Bootstrap complete at $(date)"
USERDATA
)'"
    }' \
    --query 'LaunchTemplate.LaunchTemplateId' --output text)

echo "Launch template: $TEMPLATE_ID"
```

### Update a Launch Template (New Version)

```bash
LT_ID="lt-0abc1234"

# Create a new version with updated AMI
aws ec2 create-launch-template-version \
    --launch-template-id $LT_ID \
    --version-description "v2 — updated AMI" \
    --source-version 1 \
    --launch-template-data '{
        "ImageId": "ami-0new1234"
    }'

# Set the new version as default
aws ec2 modify-launch-template \
    --launch-template-id $LT_ID \
    --default-version 2

# List versions
aws ec2 describe-launch-template-versions \
    --launch-template-id $LT_ID \
    --query 'LaunchTemplateVersions[*].{
        Ver:VersionNumber,
        Default:DefaultVersion,
        Desc:VersionDescription,
        AMI:LaunchTemplateData.ImageId,
        Type:LaunchTemplateData.InstanceType
    }' \
    --output table
```

### Launch an Instance from a Template

```bash
# Launch using the default template version
aws ec2 run-instances \
    --launch-template LaunchTemplateId=$LT_ID,Version='$Default' \
    --count 1

# Launch with overrides (useful for testing different sizes)
aws ec2 run-instances \
    --launch-template LaunchTemplateId=$LT_ID,Version=2 \
    --instance-type t3.large \
    --count 1
```

---

## IMDSv2 Requirement

All launch templates should enforce IMDSv2 (token-based metadata service). IMDSv1 is vulnerable to SSRF attacks.

```bash
# Enforce IMDSv2 in the launch template (shown above as MetadataOptions)
# Verify from inside the instance:
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
    http://169.254.169.254/latest/meta-data/instance-id

# Enforce IMDSv2 at account level (blocks IMDSv1 on all new instances)
aws ec2 modify-instance-metadata-defaults \
    --http-tokens required \
    --http-endpoint enabled
```

---

## References

- [AMI documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html)
- [Launch templates documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-launch-templates.html)
- [Data Lifecycle Manager](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snapshot-lifecycle.html)
- [IMDSv2 best practices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-IMDS-new-instances.html)
---

← [Previous: EC2](./ec2.md) | [Home](../../README.md) | [Next: Auto Scaling →](./auto-scaling.md)
