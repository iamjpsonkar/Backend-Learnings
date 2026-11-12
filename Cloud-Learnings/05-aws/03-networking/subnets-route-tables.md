← [Previous: VPC](./vpc.md) | [Home](../../README.md) | [Next: IGW & NAT Gateway →](./igw-natgw.md)

---

# Subnets and Route Tables

Subnets divide a VPC's CIDR block into smaller segments, each in a single Availability Zone. Route tables control where traffic flows from each subnet.

---

## Subnet Fundamentals

- A subnet lives in exactly **one AZ** (Availability Zone)
- A VPC can span multiple AZs; deploy subnets into at least 2 AZs for HA
- AWS reserves 5 IP addresses in every subnet (see [cidr-subnetting.md](../../../03-networking/cidr-subnetting.md))
- A subnet is **public** if its route table has a route to an Internet Gateway
- A subnet is **private** if it has no direct internet route

---

## Subnet Design Pattern

```
VPC: 10.0.0.0/16  (65,536 addresses)

Tier            AZ-a (us-east-1a)    AZ-b (us-east-1b)    AZ-c (us-east-1c)
──────────────  ────────────────     ────────────────      ────────────────
Public          10.0.0.0/24          10.0.1.0/24           10.0.2.0/24
Private         10.0.10.0/24         10.0.11.0/24          10.0.12.0/24
Database        10.0.20.0/24         10.0.21.0/24          10.0.22.0/24
```

**Rules:**
- Keep the same subnet size across AZs for symmetry
- Leave room between tiers for future expansion (10.0.0–2, 10.0.10–12, 10.0.20–22 leaves plenty)
- Use separate route tables per tier (not per subnet)
- Name everything clearly from the start

---

## Creating Subnets

```bash
VPC_ID="vpc-0abc1234"

# Public subnets
PUB_A=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.0.0/24 \
    --availability-zone us-east-1a \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-us-east-1a},{Key=Tier,Value=public}]' \
    --query 'Subnet.SubnetId' --output text)

PUB_B=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.1.0/24 \
    --availability-zone us-east-1b \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-us-east-1b},{Key=Tier,Value=public}]' \
    --query 'Subnet.SubnetId' --output text)

# Private subnets
PRIV_A=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.10.0/24 \
    --availability-zone us-east-1a \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-us-east-1a},{Key=Tier,Value=private}]' \
    --query 'Subnet.SubnetId' --output text)

PRIV_B=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.11.0/24 \
    --availability-zone us-east-1b \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-us-east-1b},{Key=Tier,Value=private}]' \
    --query 'Subnet.SubnetId' --output text)

# Database subnets
DB_A=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.20.0/24 \
    --availability-zone us-east-1a \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=database-us-east-1a},{Key=Tier,Value=database}]' \
    --query 'Subnet.SubnetId' --output text)

DB_B=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.21.0/24 \
    --availability-zone us-east-1b \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=database-us-east-1b},{Key=Tier,Value=database}]' \
    --query 'Subnet.SubnetId' --output text)

# Enable auto-assign public IPs for public subnets
aws ec2 modify-subnet-attribute \
    --subnet-id $PUB_A --map-public-ip-on-launch
aws ec2 modify-subnet-attribute \
    --subnet-id $PUB_B --map-public-ip-on-launch
```

---

## Route Tables

Each subnet is associated with exactly one route table. The **main route table** is the default for subnets not explicitly associated with another.

### Create Route Tables Per Tier

```bash
# Public route table (shared by all public subnets)
RTB_PUBLIC=$(aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=public-rtb}]' \
    --query 'RouteTable.RouteTableId' --output text)

# Private route tables — one per AZ (so each AZ uses its own NAT Gateway)
RTB_PRIV_A=$(aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=private-rtb-1a}]' \
    --query 'RouteTable.RouteTableId' --output text)

RTB_PRIV_B=$(aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=private-rtb-1b}]' \
    --query 'RouteTable.RouteTableId' --output text)

# Database route table (no internet access)
RTB_DB=$(aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=database-rtb}]' \
    --query 'RouteTable.RouteTableId' --output text)

# Add default internet route to public route table
# (after creating IGW — see igw-natgw.md)
aws ec2 create-route \
    --route-table-id $RTB_PUBLIC \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id igw-0abc1234

# Add NAT Gateway routes to private route tables
# (after creating NAT Gateways — one per AZ)
aws ec2 create-route \
    --route-table-id $RTB_PRIV_A \
    --destination-cidr-block 0.0.0.0/0 \
    --nat-gateway-id nat-AZ_A_ID

aws ec2 create-route \
    --route-table-id $RTB_PRIV_B \
    --destination-cidr-block 0.0.0.0/0 \
    --nat-gateway-id nat-AZ_B_ID

# Associate subnets with their route tables
aws ec2 associate-route-table --subnet-id $PUB_A --route-table-id $RTB_PUBLIC
aws ec2 associate-route-table --subnet-id $PUB_B --route-table-id $RTB_PUBLIC
aws ec2 associate-route-table --subnet-id $PRIV_A --route-table-id $RTB_PRIV_A
aws ec2 associate-route-table --subnet-id $PRIV_B --route-table-id $RTB_PRIV_B
aws ec2 associate-route-table --subnet-id $DB_A --route-table-id $RTB_DB
aws ec2 associate-route-table --subnet-id $DB_B --route-table-id $RTB_DB
```

### View Route Tables

```bash
# Show all routes in a route table
aws ec2 describe-route-tables \
    --route-table-ids $RTB_PUBLIC \
    --query 'RouteTables[0].Routes[*].{Dest:DestinationCidrBlock,Target:GatewayId,State:State}' \
    --output table

# Show all route tables in a VPC
aws ec2 describe-route-tables \
    --filters Name=vpc-id,Values=$VPC_ID \
    --query 'RouteTables[*].{ID:RouteTableId,Name:Tags[?Key==`Name`].Value|[0],Routes:Routes[*].DestinationCidrBlock}' \
    --output table

# Show which subnets are associated with a route table
aws ec2 describe-route-tables \
    --route-table-ids $RTB_PRIV_A \
    --query 'RouteTables[0].Associations[*].{SubnetId:SubnetId,Main:Main}' \
    --output table
```

---

## Route Priority (Longest Prefix Match)

AWS uses longest prefix match to decide which route applies:

```
Routes in private route table:
  10.0.0.0/16   → local          (most specific for VPC traffic)
  10.1.0.0/16   → pcx-0abc1234  (peered VPC)
  0.0.0.0/0     → nat-0abc1234  (least specific = default for all other traffic)

Traffic to 10.0.10.5  → matches 10.0.0.0/16 (local) — stays in VPC
Traffic to 10.1.0.5   → matches 10.1.0.0/16 (peering) — goes to peered VPC
Traffic to 8.8.8.8    → matches 0.0.0.0/0 (NAT) — goes through NAT Gateway
```

---

## Subnet Types Summary

| Type | Route to IGW | Auto-assign public IP | Internet access |
|------|-------------|----------------------|----------------|
| **Public** | Yes (0.0.0.0/0 → IGW) | Enabled (optional) | Inbound + Outbound |
| **Private** | No | No | Outbound only (via NAT) |
| **Isolated/DB** | No | No | None |

---

## Why One NAT Gateway Per AZ

If all private subnets in multiple AZs share one NAT Gateway:
- That NAT Gateway is in one AZ
- If that AZ has an outage: all private subnet instances lose internet access
- Cross-AZ NAT traffic also incurs extra data transfer charges ($0.01/GB)

**Best practice**: one NAT Gateway per AZ, one private route table per AZ pointing to the local NAT Gateway.

```
AZ-a:
  private-rtb-1a:  0.0.0.0/0 → nat-gateway-1a (in public-1a)
AZ-b:
  private-rtb-1b:  0.0.0.0/0 → nat-gateway-1b (in public-1b)
```

---

## Listing Subnets

```bash
# List all subnets with key attributes
aws ec2 describe-subnets \
    --filters Name=vpc-id,Values=$VPC_ID \
    --query 'Subnets[*].{
        ID:SubnetId,
        AZ:AvailabilityZone,
        CIDR:CidrBlock,
        Available:AvailableIpAddressCount,
        Public:MapPublicIpOnLaunch,
        Name:Tags[?Key==`Name`].Value|[0]
    }' \
    --output table
```

---

## References

- [VPC subnets documentation](https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html)
- [Route tables documentation](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
---

← [Previous: VPC](./vpc.md) | [Home](../../README.md) | [Next: IGW & NAT Gateway →](./igw-natgw.md)
