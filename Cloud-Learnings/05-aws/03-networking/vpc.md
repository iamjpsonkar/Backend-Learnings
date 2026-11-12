← [Previous: AWS Networking](./README.md) | [Home](../../README.md) | [Next: Subnets & Route Tables →](./subnets-route-tables.md)

---

# AWS VPC — Virtual Private Cloud

A VPC is a logically isolated virtual network within AWS. You define the IP address space, create subnets, configure routing, and control network access. Everything deployed in AWS runs inside a VPC (or the default VPC if no custom one exists).

---

## Core VPC Concepts

| Concept | Meaning |
|---------|---------|
| **VPC** | Logically isolated virtual network; spans all AZs in a region |
| **CIDR block** | The IP address range assigned to the VPC (e.g., `10.0.0.0/16`) |
| **Subnet** | A segment of the VPC's address space in a single AZ |
| **Route table** | Rules that determine where traffic from a subnet is directed |
| **Internet Gateway (IGW)** | Provides internet access for public subnets |
| **NAT Gateway** | Allows private subnet instances to reach the internet (outbound only) |
| **Security Group** | Stateful firewall attached to ENIs (instance level) |
| **NACL** | Stateless firewall applied to subnets |
| **ENI** | Elastic Network Interface — virtual NIC attached to an instance |
| **VPC Endpoint** | Private connection to AWS services without internet traffic |

---

## Default VPC

Every AWS account in every region gets a **default VPC** with:
- CIDR: `172.31.0.0/16`
- One public subnet per AZ (connected to an IGW)
- A default route table with internet access
- A default security group

The default VPC is fine for learning and quick experiments. **Do not use it for production** — use a custom VPC with a purpose-designed CIDR and proper subnet tiers.

```bash
# List VPCs in the current region
aws ec2 describe-vpcs \
    --query 'Vpcs[*].{ID:VpcId,CIDR:CidrBlock,Default:IsDefault,State:State}' \
    --output table

# Get the default VPC ID
aws ec2 describe-vpcs \
    --filters Name=isDefault,Values=true \
    --query 'Vpcs[0].VpcId' --output text
```

---

## Creating a VPC

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=production-vpc},{Key=Environment,Value=production}]' \
    --query 'Vpc.VpcId' --output text)

echo "Created VPC: $VPC_ID"

# Enable DNS hostnames (required for Route 53 private hosted zones and some services)
aws ec2 modify-vpc-attribute \
    --vpc-id $VPC_ID \
    --enable-dns-hostnames

# Enable DNS resolution
aws ec2 modify-vpc-attribute \
    --vpc-id $VPC_ID \
    --enable-dns-support

# Verify settings
aws ec2 describe-vpc-attribute \
    --vpc-id $VPC_ID \
    --attribute enableDnsHostnames

aws ec2 describe-vpc-attribute \
    --vpc-id $VPC_ID \
    --attribute enableDnsSupport
```

---

## Secondary CIDR Blocks

A VPC can have up to 5 CIDR blocks. Adding a secondary CIDR allows growth without recreating the VPC.

```bash
# Add a secondary CIDR block
aws ec2 associate-vpc-cidr-block \
    --vpc-id $VPC_ID \
    --cidr-block 10.1.0.0/16

# View all CIDR blocks for a VPC
aws ec2 describe-vpcs \
    --vpc-ids $VPC_ID \
    --query 'Vpcs[0].CidrBlockAssociationSet[*].{CIDR:CidrBlock,State:CidrBlockState.State}'
```

---

## VPC CIDR Planning

Choose your VPC CIDR carefully — it is difficult to change once subnets and resources exist.

### Recommended Sizing

| VPC type | CIDR | Usable IPs | Subnets |
|----------|------|-----------|---------|
| Small dev | /24 | 251 | 3–4 /27 subnets |
| Standard | /20 | ~4,000 | 12+ /24 subnets |
| Production | /16 | ~65,000 | Many /24 subnets |
| Enterprise | /8 | 16M | Secondary CIDRs as needed |

### Avoid Conflicts

```
Your VPCs must not overlap with:
  - Other VPCs you plan to peer
  - On-premises networks (Direct Connect, VPN)
  - SaaS partner networks

Avoid these common ranges:
  172.31.0.0/16  — AWS default VPC
  192.168.0.0/16 — home/office networks (conflicts with VPN clients)
  10.0.0.0/8     — if already used on-premises, pick a sub-range

Suggested allocation strategy:
  Production:    10.0.0.0/16
  Staging:       10.1.0.0/16
  Development:   10.2.0.0/16
  Shared Svcs:   10.3.0.0/16
  On-premises:   172.16.0.0/12 (separate, no overlap)
```

---

## VPC Flow Logs

Flow logs capture IP traffic metadata (source, destination, port, action, bytes) for analysis and security investigation.

```bash
# Create an IAM role for flow logs to write to CloudWatch
aws iam create-role \
    --role-name VPCFlowLogsRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "vpc-flow-logs.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

aws iam put-role-policy \
    --role-name VPCFlowLogsRole \
    --policy-name FlowLogsPolicy \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents","logs:DescribeLogGroups","logs:DescribeLogStreams"],
            "Resource": "*"
        }]
    }'

# Enable flow logs for entire VPC (ALL traffic)
aws ec2 create-flow-logs \
    --resource-type VPC \
    --resource-ids $VPC_ID \
    --traffic-type ALL \
    --log-group-name /vpc/flow-logs/$VPC_ID \
    --deliver-logs-permission-arn arn:aws:iam::123456789012:role/VPCFlowLogsRole

# Enable flow logs to S3 (cheaper, queryable with Athena)
aws ec2 create-flow-logs \
    --resource-type VPC \
    --resource-ids $VPC_ID \
    --traffic-type ALL \
    --log-destination-type s3 \
    --log-destination arn:aws:s3:::my-flow-logs-bucket/flow-logs/

# View flow logs
aws ec2 describe-flow-logs \
    --filter Name=resource-id,Values=$VPC_ID
```

---

## VPC Endpoints

VPC Endpoints allow private communication with AWS services (S3, DynamoDB, SSM, Secrets Manager, etc.) without internet traffic. This saves NAT Gateway costs and improves security.

### Gateway Endpoints (S3 and DynamoDB — Free)

```bash
# Create a Gateway endpoint for S3
aws ec2 create-vpc-endpoint \
    --vpc-id $VPC_ID \
    --service-name com.amazonaws.us-east-1.s3 \
    --vpc-endpoint-type Gateway \
    --route-table-ids rtb-private-az-a rtb-private-az-b

# The endpoint automatically adds a route: pl-XXXXXXXX (S3 prefix list) → vpce-XXXXXXXX
# in the specified route tables. Traffic to S3 never leaves the AWS network.
```

### Interface Endpoints (PrivateLink — Charged per hour + per GB)

```bash
# Create an Interface endpoint for Secrets Manager
aws ec2 create-vpc-endpoint \
    --vpc-id $VPC_ID \
    --service-name com.amazonaws.us-east-1.secretsmanager \
    --vpc-endpoint-type Interface \
    --subnet-ids subnet-private-az-a subnet-private-az-b \
    --security-group-ids sg-vpc-endpoint \
    --private-dns-enabled    # creates private DNS: secretsmanager.us-east-1.amazonaws.com → private IP

# Common interface endpoints to consider
SERVICES=(
    "com.amazonaws.us-east-1.ssm"               # SSM Parameter Store + Session Manager
    "com.amazonaws.us-east-1.ssmmessages"        # SSM Session Manager (required)
    "com.amazonaws.us-east-1.ec2messages"        # SSM agent (required)
    "com.amazonaws.us-east-1.secretsmanager"     # Secrets Manager
    "com.amazonaws.us-east-1.kms"                # KMS
    "com.amazonaws.us-east-1.logs"               # CloudWatch Logs
    "com.amazonaws.us-east-1.monitoring"         # CloudWatch metrics
    "com.amazonaws.us-east-1.ecr.api"            # ECR (container registry)
    "com.amazonaws.us-east-1.ecr.dkr"            # ECR Docker registry
)

# List all available services in a region
aws ec2 describe-vpc-endpoint-services \
    --query 'ServiceNames[*]' --output text | tr '\t' '\n' | grep amazonaws
```

### Security Group for VPC Endpoints

```bash
# Create a security group specifically for interface endpoints
aws ec2 create-security-group \
    --group-name vpc-endpoint-sg \
    --description "Allow HTTPS from private subnets to VPC endpoints" \
    --vpc-id $VPC_ID

# Allow HTTPS from the private subnet CIDRs
aws ec2 authorize-security-group-ingress \
    --group-id sg-vpc-endpoint \
    --protocol tcp --port 443 \
    --cidr 10.0.10.0/23    # private subnets CIDR
```

---

## Listing and Cleaning Up

```bash
# List all resources in a VPC (to clean up before deletion)
aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC_ID \
    --query 'Subnets[*].SubnetId' --output text

aws ec2 describe-internet-gateways \
    --filters Name=attachment.vpc-id,Values=$VPC_ID \
    --query 'InternetGateways[*].InternetGatewayId' --output text

aws ec2 describe-nat-gateways \
    --filter Name=vpc-id,Values=$VPC_ID \
    --query 'NatGateways[?State!=`deleted`].NatGatewayId' --output text

# Delete VPC (must delete all resources first: subnets, IGW, route tables, SGs, etc.)
aws ec2 delete-vpc --vpc-id $VPC_ID
```

---

## References

- [VPC documentation](https://docs.aws.amazon.com/vpc/latest/userguide/)
- [VPC Endpoints documentation](https://docs.aws.amazon.com/vpc/latest/privatelink/)
- [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)
---

← [Previous: AWS Networking](./README.md) | [Home](../../README.md) | [Next: Subnets & Route Tables →](./subnets-route-tables.md)
