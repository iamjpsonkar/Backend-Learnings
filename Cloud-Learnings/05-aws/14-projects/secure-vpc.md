← [Previous: 3-Tier Architecture](./3-tier-architecture.md) | [Home](../../README.md) | [Next: Static Website on AWS →](./static-website.md)

---

# Project: Build a Secure VPC from Scratch

A production-grade VPC with public/private/isolated subnet tiers, NAT Gateways, security groups, NACLs, VPC endpoints, and flow logs. This is the network foundation for nearly all other projects.

---

## Target Architecture

```
Internet
    │
    ▼
Internet Gateway
    │
    ▼  ─────────────────────────────────────────────
Public Subnets (10.0.1.0/24, 10.0.2.0/24) — AZ-a, AZ-b
    ALB, NAT Gateways, Bastion (optional)
    │
    ▼  ─────────────────────────────────────────────
Private Subnets (10.0.11.0/24, 10.0.12.0/24) — AZ-a, AZ-b
    Application servers (EC2/ECS/Lambda)
    VPC Endpoints (S3 Gateway, DynamoDB, Secrets Manager Interface)
    │
    ▼  ─────────────────────────────────────────────
Isolated Subnets (10.0.21.0/28, 10.0.22.0/28) — AZ-a, AZ-b
    RDS, ElastiCache — no outbound internet access
```

---

## Step 1: VPC and Subnets

```bash
REGION="us-east-1"

# Create VPC
VPC_ID=$(aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --region $REGION \
    --query 'Vpc.VpcId' --output text)

aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

aws ec2 create-tags --resources $VPC_ID \
    --tags Key=Name,Value=production-vpc Key=Environment,Value=production

echo "VPC: $VPC_ID"

# Get AZs
AZ_A=$(aws ec2 describe-availability-zones --region $REGION \
    --query 'AvailabilityZones[0].ZoneName' --output text)
AZ_B=$(aws ec2 describe-availability-zones --region $REGION \
    --query 'AvailabilityZones[1].ZoneName' --output text)

# Public subnets
PUBLIC_SUBNET_A=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone $AZ_A \
    --query 'Subnet.SubnetId' --output text)
PUBLIC_SUBNET_B=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone $AZ_B \
    --query 'Subnet.SubnetId' --output text)

aws ec2 modify-subnet-attribute --subnet-id $PUBLIC_SUBNET_A --map-public-ip-on-launch
aws ec2 modify-subnet-attribute --subnet-id $PUBLIC_SUBNET_B --map-public-ip-on-launch

# Private subnets
PRIVATE_SUBNET_A=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID --cidr-block 10.0.11.0/24 --availability-zone $AZ_A \
    --query 'Subnet.SubnetId' --output text)
PRIVATE_SUBNET_B=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID --cidr-block 10.0.12.0/24 --availability-zone $AZ_B \
    --query 'Subnet.SubnetId' --output text)

# Isolated subnets (databases)
ISOLATED_SUBNET_A=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID --cidr-block 10.0.21.0/28 --availability-zone $AZ_A \
    --query 'Subnet.SubnetId' --output text)
ISOLATED_SUBNET_B=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID --cidr-block 10.0.22.0/28 --availability-zone $AZ_B \
    --query 'Subnet.SubnetId' --output text)

# Tag all subnets
for id in $PUBLIC_SUBNET_A $PUBLIC_SUBNET_B; do
    aws ec2 create-tags --resources $id --tags Key=Name,Value=production-public Key=Tier,Value=public
done
for id in $PRIVATE_SUBNET_A $PRIVATE_SUBNET_B; do
    aws ec2 create-tags --resources $id --tags Key=Name,Value=production-private Key=Tier,Value=private
done
for id in $ISOLATED_SUBNET_A $ISOLATED_SUBNET_B; do
    aws ec2 create-tags --resources $id --tags Key=Name,Value=production-isolated Key=Tier,Value=isolated
done
```

---

## Step 2: Internet Gateway and Route Tables

```bash
# Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
    --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID
aws ec2 create-tags --resources $IGW_ID --tags Key=Name,Value=production-igw

# Public route table
PUBLIC_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID \
    --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id $PUBLIC_RT \
    --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_A --route-table-id $PUBLIC_RT
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_B --route-table-id $PUBLIC_RT
aws ec2 create-tags --resources $PUBLIC_RT --tags Key=Name,Value=production-public-rt
```

---

## Step 3: NAT Gateways (HA — one per AZ)

```bash
# Elastic IPs for NAT Gateways
EIP_A=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
EIP_B=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)

# NAT Gateways
NGW_A=$(aws ec2 create-nat-gateway \
    --subnet-id $PUBLIC_SUBNET_A --allocation-id $EIP_A \
    --query 'NatGateway.NatGatewayId' --output text)
NGW_B=$(aws ec2 create-nat-gateway \
    --subnet-id $PUBLIC_SUBNET_B --allocation-id $EIP_B \
    --query 'NatGateway.NatGatewayId' --output text)

aws ec2 wait nat-gateway-available --filter "Name=nat-gateway-id,Values=$NGW_A"
aws ec2 wait nat-gateway-available --filter "Name=nat-gateway-id,Values=$NGW_B"

# Private route tables (one per AZ, pointing to respective NAT)
PRIVATE_RT_A=$(aws ec2 create-route-table --vpc-id $VPC_ID \
    --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id $PRIVATE_RT_A \
    --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NGW_A
aws ec2 associate-route-table --subnet-id $PRIVATE_SUBNET_A --route-table-id $PRIVATE_RT_A

PRIVATE_RT_B=$(aws ec2 create-route-table --vpc-id $VPC_ID \
    --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id $PRIVATE_RT_B \
    --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NGW_B
aws ec2 associate-route-table --subnet-id $PRIVATE_SUBNET_B --route-table-id $PRIVATE_RT_B

# Isolated subnets: local route only (no internet, no NAT)
ISOLATED_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID \
    --query 'RouteTable.RouteTableId' --output text)
aws ec2 associate-route-table --subnet-id $ISOLATED_SUBNET_A --route-table-id $ISOLATED_RT
aws ec2 associate-route-table --subnet-id $ISOLATED_SUBNET_B --route-table-id $ISOLATED_RT
```

---

## Step 4: Security Groups

```bash
# ALB Security Group — internet-facing HTTPS
ALB_SG=$(aws ec2 create-security-group \
    --group-name production-alb-sg \
    --description "ALB — HTTPS from internet" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG --protocol tcp --port 80 --cidr 0.0.0.0/0

# App Server Security Group — ALB only
APP_SG=$(aws ec2 create-security-group \
    --group-name production-app-sg \
    --description "App servers — ALB on 8080" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress \
    --group-id $APP_SG --protocol tcp --port 8080 --source-group $ALB_SG

# Database Security Group — app servers only on 5432 (PostgreSQL)
DB_SG=$(aws ec2 create-security-group \
    --group-name production-db-sg \
    --description "RDS — app servers on 5432" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress \
    --group-id $DB_SG --protocol tcp --port 5432 --source-group $APP_SG

# Cache Security Group — app servers only on 6379 (Redis)
CACHE_SG=$(aws ec2 create-security-group \
    --group-name production-cache-sg \
    --description "ElastiCache — app servers on 6379" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress \
    --group-id $CACHE_SG --protocol tcp --port 6379 --source-group $APP_SG

echo "Security Groups: ALB=$ALB_SG APP=$APP_SG DB=$DB_SG CACHE=$CACHE_SG"
```

---

## Step 5: VPC Endpoints (Avoid NAT Gateway Costs)

```bash
# Gateway endpoint for S3 (free, routes within AWS network)
aws ec2 create-vpc-endpoint \
    --vpc-id $VPC_ID \
    --service-name com.amazonaws.us-east-1.s3 \
    --route-table-ids $PRIVATE_RT_A $PRIVATE_RT_B $ISOLATED_RT

# Gateway endpoint for DynamoDB (free)
aws ec2 create-vpc-endpoint \
    --vpc-id $VPC_ID \
    --service-name com.amazonaws.us-east-1.dynamodb \
    --route-table-ids $PRIVATE_RT_A $PRIVATE_RT_B

# Interface endpoint for Secrets Manager (charged per hour)
SECRETS_SG=$(aws ec2 create-security-group \
    --group-name production-endpoint-sg \
    --description "VPC endpoints — HTTPS from private subnets" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress \
    --group-id $SECRETS_SG --protocol tcp --port 443 --cidr 10.0.0.0/16

aws ec2 create-vpc-endpoint \
    --vpc-id $VPC_ID \
    --vpc-endpoint-type Interface \
    --service-name com.amazonaws.us-east-1.secretsmanager \
    --subnet-ids $PRIVATE_SUBNET_A $PRIVATE_SUBNET_B \
    --security-group-ids $SECRETS_SG \
    --private-dns-enabled
```

---

## Step 6: VPC Flow Logs

```bash
# Log group
aws logs create-log-group --log-group-name /vpc/production-flow-logs
aws logs put-retention-policy \
    --log-group-name /vpc/production-flow-logs \
    --retention-in-days 30

# Flow logs role (trust policy for vpc-flow-logs.amazonaws.com)
FLOW_LOG_ROLE_ARN="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/VPCFlowLogsRole"

# Enable flow logs on the VPC
aws ec2 create-flow-logs \
    --resource-type VPC \
    --resource-ids $VPC_ID \
    --traffic-type ALL \
    --log-destination-type cloud-watch-logs \
    --log-destination arn:aws:logs:us-east-1:$(aws sts get-caller-identity --query Account --output text):log-group:/vpc/production-flow-logs \
    --deliver-logs-permission-arn $FLOW_LOG_ROLE_ARN \
    --log-format '${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}'
```

---

## Step 7: Validate the Network

```bash
# List all subnets in the VPC
aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[*].{ID:SubnetId,CIDR:CidrBlock,AZ:AvailabilityZone,PublicIP:MapPublicIpOnLaunch}' \
    --output table

# List all route tables
aws ec2 describe-route-tables \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'RouteTables[*].{ID:RouteTableId,Routes:Routes[*].{Dest:DestinationCidrBlock,Target:GatewayId}}' \
    --output table

# Test connectivity with VPC Reachability Analyzer
PATH_ID=$(aws ec2 create-network-insights-path \
    --source $APP_SG \
    --destination $DB_SG \
    --protocol TCP \
    --destination-port 5432 \
    --query 'NetworkInsightsPath.NetworkInsightsPathId' --output text)

aws ec2 start-network-insights-analysis \
    --network-insights-path-id $PATH_ID \
    --query 'NetworkInsightsAnalysis.{ID:NetworkInsightsAnalysisId}'
```

---

## Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| NAT Gateway (2 HA) | ~$65 (each $32.40/month + data) |
| VPC Flow Logs → CloudWatch | ~$0.50/GB ingested |
| Interface VPC Endpoints (2 AZs) | ~$14.40/endpoint/month |
| Elastic IPs (2) | Free while attached |
| **Total (infrastructure only)** | **~$80–100/month** |

**Cost optimization:** Use 1 NAT Gateway in dev/staging; use S3/DynamoDB gateway endpoints (free) before considering interface endpoints.

---

## References

- [VPC documentation](https://docs.aws.amazon.com/vpc/latest/userguide/)
- [VPC pricing](https://aws.amazon.com/vpc/pricing/)
- [VPC Reachability Analyzer](https://docs.aws.amazon.com/vpc/latest/reachability/)
---

← [Previous: 3-Tier Architecture](./3-tier-architecture.md) | [Home](../../README.md) | [Next: Static Website on AWS →](./static-website.md)
