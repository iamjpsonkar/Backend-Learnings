← [Previous: IBM Cloud](./ibm-cloud.md) | [Home](../README.md) | [Next: DigitalOcean →](./digitalocean.md)

---

# Alibaba Cloud

Alibaba Cloud (Aliyun) is Asia's largest cloud provider and the dominant choice for workloads requiring presence in mainland China. It also operates globally across 30+ regions.

---

## Key Differentiators

| Feature | Detail |
|---------|--------|
| **China coverage** | Only major cloud with compliant infrastructure inside mainland China (ICP license required) |
| **Asia-Pacific strength** | Strong coverage across Southeast Asia, Japan, Australia |
| **Apsara Stack** | On-premises private cloud version of Alibaba Cloud |
| **DDoS protection** | Industry-leading Anti-DDoS service from handling Alibaba's own traffic scale |
| **Hybrid cloud** | Alibaba Cloud Express Connect links to on-premises and other clouds |

---

## Service Equivalents

| AWS | Alibaba Cloud |
|-----|--------------|
| EC2 | Elastic Compute Service (ECS) |
| VPC | Virtual Private Cloud (VPC) |
| S3 | Object Storage Service (OSS) |
| CloudFront | CDN / DCDN |
| RDS | ApsaraDB RDS (MySQL, PostgreSQL, SQL Server) |
| DynamoDB | Table Store (Tablestore) |
| ElastiCache | ApsaraDB for Redis |
| Lambda | Function Compute |
| EKS | Container Service for Kubernetes (ACK) |
| ALB | Application Load Balancer (ALB) |
| Route 53 | Cloud DNS |
| IAM | Resource Access Management (RAM) |
| CloudTrail | ActionTrail |
| CloudWatch | CloudMonitor |

---

## CLI Setup

```bash
# Install Alibaba Cloud CLI
# macOS
brew install aliyun-cli

# Linux
curl -o aliyun-cli-linux-latest-amd64.tgz \
    https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli-linux-latest-amd64.tgz
mv aliyun /usr/local/bin/

# Configure with Access Key ID and Secret
aliyun configure --profile default
# Enter: AccessKey ID, AccessKey Secret, Region (e.g., cn-hangzhou or ap-southeast-1)

# Verify
aliyun ecs DescribeRegions --output json | jq '.Regions.Region[].RegionId'

# List regions
aliyun ecs DescribeRegions

# Common regions
# cn-hangzhou       — China (Hangzhou) — Alibaba HQ region
# cn-shanghai       — China (Shanghai)
# cn-beijing        — China (Beijing)
# ap-southeast-1    — Singapore (recommended for global workloads)
# ap-northeast-1    — Japan (Tokyo)
# us-west-1         — US West (Silicon Valley)
```

---

## Networking (VPC)

```bash
REGION="ap-southeast-1"

# Create a VPC
VPC_ID=$(aliyun vpc CreateVpc \
    --RegionId $REGION \
    --CidrBlock 10.0.0.0/16 \
    --VpcName vpc-my-app-prod \
    | jq -r '.VpcId')

# Create a VSwitch (subnet)
VSWITCH_APP=$(aliyun vpc CreateVSwitch \
    --RegionId $REGION \
    --VpcId $VPC_ID \
    --ZoneId "${REGION}-a" \
    --CidrBlock 10.0.11.0/24 \
    --VSwitchName snet-app-ap-southeast-1a \
    | jq -r '.VSwitchId')

VSWITCH_DATA=$(aliyun vpc CreateVSwitch \
    --RegionId $REGION \
    --VpcId $VPC_ID \
    --ZoneId "${REGION}-b" \
    --CidrBlock 10.0.21.0/24 \
    --VSwitchName snet-data-ap-southeast-1b \
    | jq -r '.VSwitchId')

# NAT Gateway (for private instance outbound access)
NAT_ID=$(aliyun vpc CreateNatGateway \
    --RegionId $REGION \
    --VpcId $VPC_ID \
    --VSwitchId $VSWITCH_APP \
    --NatGatewayName nat-my-app-prod \
    --NatType Enhanced \
    | jq -r '.NatGatewayId')

# Security Group
SG_ID=$(aliyun ecs CreateSecurityGroup \
    --RegionId $REGION \
    --VpcId $VPC_ID \
    --SecurityGroupName sg-app-tier \
    --SecurityGroupType enterprise \
    | jq -r '.SecurityGroupId')

# Add inbound rule (HTTPS from anywhere)
aliyun ecs AuthorizeSecurityGroup \
    --RegionId $REGION \
    --SecurityGroupId $SG_ID \
    --IpProtocol TCP \
    --PortRange 443/443 \
    --SourceCidrIp 0.0.0.0/0 \
    --Policy accept
```

---

## Elastic Compute Service (ECS)

```bash
# List available instance types
aliyun ecs DescribeInstanceTypes \
    --RegionId $REGION \
    --output json | jq '.InstanceTypes.InstanceType[] | {type: .InstanceTypeId, cpu: .CpuCoreCount, mem: .MemorySize}' | head -30

# Key instance families
# ecs.c7    — Compute optimized (Intel)
# ecs.g7    — General purpose (Intel)
# ecs.r7    — Memory optimized (Intel)
# ecs.c7a   — Compute optimized (AMD)
# ecs.u1    — General purpose (burstable)

# Get latest Alibaba Linux image ID
IMAGE_ID=$(aliyun ecs DescribeImages \
    --RegionId $REGION \
    --OSType linux \
    --Platform "Alibaba Cloud Linux" \
    --ImageOwnerAlias system \
    --output json | jq -r '.Images.Image[0].ImageId')

# Create a key pair
aliyun ecs CreateKeyPair \
    --RegionId $REGION \
    --KeyPairName my-app-key

# Create an ECS instance (private, no public IP)
INSTANCE_ID=$(aliyun ecs CreateInstance \
    --RegionId $REGION \
    --ZoneId "${REGION}-a" \
    --InstanceType ecs.g7.xlarge \
    --ImageId $IMAGE_ID \
    --SecurityGroupId $SG_ID \
    --VSwitchId $VSWITCH_APP \
    --SystemDisk.Category cloud_essd \
    --SystemDisk.Size 60 \
    --InstanceName vm-my-app-prod-001 \
    --KeyPairName my-app-key \
    --InternetMaxBandwidthOut 0 \
    --output json | jq -r '.InstanceId')

# Start the instance
aliyun ecs StartInstance --InstanceId $INSTANCE_ID

# Describe instance
aliyun ecs DescribeInstances \
    --RegionId $REGION \
    --InstanceIds "[\"$INSTANCE_ID\"]" \
    --output json | jq '.Instances.Instance[0] | {state: .Status, ip: .VpcAttributes.PrivateIpAddress.IpAddress[0]}'

# Stop
aliyun ecs StopInstance --InstanceId $INSTANCE_ID --ForceStop false
```

---

## Object Storage Service (OSS)

```bash
# OSS uses its own endpoint format: https://bucket.oss-region.aliyuncs.com

# Install ossutil (recommended OSS CLI tool)
# macOS: brew install ossutil
# Linux: curl -o ossutil64 https://gosspublic.alicdn.com/ossutil/1.7.17/ossutil64 && chmod +x ossutil64

# Configure ossutil
ossutil config \
    -e oss-ap-southeast-1.aliyuncs.com \
    -i $ALICLOUD_ACCESS_KEY_ID \
    -k $ALICLOUD_ACCESS_KEY_SECRET

# Create a bucket (private, in Singapore)
ossutil mb oss://my-app-prod-assets \
    --region ap-southeast-1 \
    --acl private \
    --storage-class Standard

# Upload a file
ossutil cp ./report.pdf oss://my-app-prod-assets/reports/2024/report.pdf \
    --meta "Content-Type:application/pdf"

# Upload a directory
ossutil cp -r ./dist oss://my-app-prod-assets/static/ \
    --meta "Cache-Control:public, max-age=31536000"

# Download
ossutil cp oss://my-app-prod-assets/reports/2024/report.pdf /tmp/report.pdf

# List objects
ossutil ls oss://my-app-prod-assets/reports/ -s

# Set lifecycle rule (transition to Infrequent Access after 30 days)
ossutil lifecycle --method put oss://my-app-prod-assets lifecycle.xml
```

```xml
<!-- lifecycle.xml -->
<LifecycleConfiguration>
  <Rule>
    <ID>move-to-ia</ID>
    <Prefix>data/</Prefix>
    <Status>Enabled</Status>
    <Transition>
      <Days>30</Days>
      <StorageClass>IA</StorageClass>
    </Transition>
    <Expiration>
      <Days>365</Days>
    </Expiration>
  </Rule>
</LifecycleConfiguration>
```

---

## Function Compute

```bash
# Install Fun (Function Compute deployment tool) or use Serverless Framework

# Create a function via CLI
aliyun fc CreateFunction \
    --region $REGION \
    --serviceName my-app-service \
    --functionName my-app-api \
    --runtime python3.10 \
    --handler index.handler \
    --code "{\"ossBucketName\":\"my-app-prod-assets\",\"ossObjectName\":\"functions/my-app-api.zip\"}" \
    --memorySize 512 \
    --timeout 30

# Invoke a function (for testing)
aliyun fc InvokeFunction \
    --region $REGION \
    --serviceName my-app-service \
    --functionName my-app-api \
    --event '{"action":"test"}'
```

---

## Resource Access Management (RAM)

```bash
# Create a RAM user
aliyun ram CreateUser --UserName alice@example.com

# Create an access key for the user
aliyun ram CreateAccessKey --UserName alice@example.com

# Attach a policy to a user
aliyun ram AttachPolicyToUser \
    --PolicyType System \
    --PolicyName AliyunOSSReadOnlyAccess \
    --UserName alice@example.com

# Create a RAM role for ECS instances (instance profile equivalent)
aliyun ram CreateRole \
    --RoleName my-app-ecs-role \
    --AssumeRolePolicyDocument '{
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": ["ecs.aliyuncs.com"]}
        }],
        "Version": "1"
    }'

# Attach OSS read policy to the role
aliyun ram AttachPolicyToRole \
    --PolicyType System \
    --PolicyName AliyunOSSReadOnlyAccess \
    --RoleName my-app-ecs-role
```

---

## China vs International Regions

| Aspect | China Regions | International Regions |
|--------|--------------|----------------------|
| ICP License | Required for public-facing websites | Not required |
| Access | Accessible from China without VPN | May require VPN from China |
| Data residency | Governed by Chinese law (PIPL, MLPS) | Standard international |
| Products | Full product catalog | Full product catalog |
| Registration | Must use Chinese company entity | No restriction |

> If your workload requires both China and global reach, deploy to both a China region (e.g., `cn-hangzhou`) and an international region (e.g., `ap-southeast-1`) and use Alibaba Cloud CDN for unified delivery.

---

## References

- [Alibaba Cloud documentation](https://www.alibabacloud.com/help)
- [Alibaba Cloud CLI reference](https://www.alibabacloud.com/help/cli)
- [OSS documentation](https://www.alibabacloud.com/help/oss)
- [Function Compute documentation](https://www.alibabacloud.com/help/function-compute)
- [ICP filing for China](https://www.alibabacloud.com/help/icp-filing)
---

← [Previous: IBM Cloud](./ibm-cloud.md) | [Home](../README.md) | [Next: DigitalOcean →](./digitalocean.md)
