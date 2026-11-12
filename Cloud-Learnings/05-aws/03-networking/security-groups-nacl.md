← [Previous: IGW & NAT Gateway](./igw-natgw.md) | [Home](../../README.md) | [Next: Route 53 →](./route53.md)

---

# Security Groups and Network ACLs

Security Groups (SGs) and Network ACLs (NACLs) are the two layers of network access control in a VPC. They complement each other — SGs control traffic at the instance level, NACLs at the subnet level.

---

## Core Differences

| | Security Group | Network ACL |
|--|----------------|-------------|
| Applies to | ENI (instance, ALB, RDS, etc.) | Subnet |
| State | **Stateful** — return traffic is automatically allowed | **Stateless** — return traffic needs an explicit allow rule |
| Rule types | Allow only | Allow and Deny |
| Rule evaluation | All rules evaluated; most permissive wins | Rules evaluated in order (lowest number first); first match wins |
| Default (new) | Deny all inbound, allow all outbound | Allow all inbound and outbound (default NACL) |
| Max rules | 60 inbound + 60 outbound (soft limit) | 20 inbound + 20 outbound (soft limit) |
| Association | Many-to-many (SG ↔ ENIs) | One NACL per subnet; one subnet per NACL |

---

## Security Groups

### How Security Groups Work

A Security Group is a stateful virtual firewall. When you allow inbound TCP port 443, the response packets (ephemeral ports, typically 1024–65535) are automatically allowed back out — you do not need an outbound rule for response traffic.

```
Client → SG inbound rule matches port 443 → Instance
Instance → SG automatically allows response → Client
```

### Creating and Managing Security Groups

```bash
VPC_ID="vpc-0abc1234"

# Create a security group
SG_WEB=$(aws ec2 create-security-group \
    --group-name web-servers \
    --description "Allow HTTP/HTTPS from internet, SSH from bastion" \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=web-sg}]' \
    --query 'GroupId' --output text)

echo "Created SG: $SG_WEB"

# Add inbound rules
# Allow HTTPS from anywhere
aws ec2 authorize-security-group-ingress \
    --group-id $SG_WEB \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

# Allow HTTP from anywhere (for redirect)
aws ec2 authorize-security-group-ingress \
    --group-id $SG_WEB \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

# Allow SSH from bastion SG only (not from internet)
SG_BASTION="sg-0bastion1234"
aws ec2 authorize-security-group-ingress \
    --group-id $SG_WEB \
    --protocol tcp \
    --port 22 \
    --source-group $SG_BASTION

# Allow all traffic from within the same SG (cluster/peer communication)
aws ec2 authorize-security-group-ingress \
    --group-id $SG_WEB \
    --protocol -1 \
    --source-group $SG_WEB

# View current rules
aws ec2 describe-security-groups \
    --group-ids $SG_WEB \
    --query 'SecurityGroups[0].{
        ID:GroupId,
        Name:GroupName,
        Inbound:IpPermissions[*].{Port:FromPort,Proto:IpProtocol,Sources:IpRanges[*].CidrIp},
        Outbound:IpPermissionsEgress[*].{Port:FromPort,Proto:IpProtocol}
    }'

# Remove a rule
aws ec2 revoke-security-group-ingress \
    --group-id $SG_WEB \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0
```

### Common Security Group Patterns

```bash
# ===== App tier: allow from ALB SG only =====
SG_APP=$(aws ec2 create-security-group \
    --group-name app-servers \
    --description "Allow from ALB only" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)

SG_ALB="sg-0alb1234"

aws ec2 authorize-security-group-ingress \
    --group-id $SG_APP \
    --protocol tcp \
    --port 8080 \
    --source-group $SG_ALB

# ===== DB tier: allow from app SG only =====
SG_DB=$(aws ec2 create-security-group \
    --group-name databases \
    --description "Allow MySQL from app tier only" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress \
    --group-id $SG_DB \
    --protocol tcp \
    --port 3306 \
    --source-group $SG_APP

# ===== VPC Endpoint SG: allow HTTPS from private subnets =====
SG_VPCE=$(aws ec2 create-security-group \
    --group-name vpc-endpoint-sg \
    --description "Allow HTTPS to VPC endpoints from private subnets" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress \
    --group-id $SG_VPCE \
    --protocol tcp \
    --port 443 \
    --cidr 10.0.10.0/23    # private subnets range
```

### Attaching Security Groups to Instances

```bash
# At launch
aws ec2 run-instances \
    --image-id ami-0abc1234 \
    --instance-type t3.micro \
    --subnet-id subnet-private \
    --security-group-ids $SG_APP \
    --count 1

# Add SG to running instance
aws ec2 modify-instance-attribute \
    --instance-id i-0abc1234 \
    --groups $SG_WEB $SG_APP    # replaces existing SGs

# For non-EC2 ENIs (RDS, ALB, Lambda, etc.) — modify the ENI directly
aws ec2 modify-network-interface-attribute \
    --network-interface-id eni-0abc1234 \
    --groups $SG_DB
```

---

## Network ACLs

### How NACLs Work

NACLs are stateless. Both the inbound request and the outbound response need explicit allow rules. NACLs evaluate rules in ascending rule number order and stop at the first match (including explicit denies).

```
Rule 100 → Allow TCP 443 from 0.0.0.0/0   ← matches first
Rule 200 → Allow TCP 80 from 0.0.0.0/0
Rule 32767 → * Deny all                    ← implicit deny
```

**Important:** Because NACLs are stateless, you must allow **ephemeral ports (1024–65535)** for return traffic on the outbound rules.

### Default NACL vs Custom NACL

| | Default NACL | Custom NACL |
|--|-------------|-------------|
| Created with | VPC (automatically) | Manually |
| Default rules | Allow all inbound + outbound | Deny all (implicit) until rules added |
| Subnet association | All subnets not explicitly associated | Only explicitly associated subnets |

### Creating a Custom NACL

```bash
VPC_ID="vpc-0abc1234"

# Create a NACL
NACL_ID=$(aws ec2 create-network-acl \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=network-acl,Tags=[{Key=Name,Value=private-nacl}]' \
    --query 'NetworkAcl.NetworkAclId' --output text)

echo "Created NACL: $NACL_ID"

# ===== Inbound rules =====

# Rule 100: Allow HTTPS from VPC CIDR
aws ec2 create-network-acl-entry \
    --network-acl-id $NACL_ID \
    --rule-number 100 \
    --protocol tcp \
    --port-range From=443,To=443 \
    --cidr-block 10.0.0.0/16 \
    --rule-action allow \
    --ingress

# Rule 200: Allow ephemeral return ports from internet
aws ec2 create-network-acl-entry \
    --network-acl-id $NACL_ID \
    --rule-number 200 \
    --protocol tcp \
    --port-range From=1024,To=65535 \
    --cidr-block 0.0.0.0/0 \
    --rule-action allow \
    --ingress

# ===== Outbound rules =====

# Rule 100: Allow HTTPS to internet (e.g., via NAT Gateway to external APIs)
aws ec2 create-network-acl-entry \
    --network-acl-id $NACL_ID \
    --rule-number 100 \
    --protocol tcp \
    --port-range From=443,To=443 \
    --cidr-block 0.0.0.0/0 \
    --rule-action allow \
    --egress

# Rule 200: Allow ephemeral ports back to VPC (response traffic)
aws ec2 create-network-acl-entry \
    --network-acl-id $NACL_ID \
    --rule-number 200 \
    --protocol tcp \
    --port-range From=1024,To=65535 \
    --cidr-block 10.0.0.0/16 \
    --rule-action allow \
    --egress

# Associate NACL with private subnets
aws ec2 replace-network-acl-association \
    --association-id aclassoc-0abc1234 \   # existing association ID
    --network-acl-id $NACL_ID

# Get existing association IDs for subnets
aws ec2 describe-network-acls \
    --filters Name=vpc-id,Values=$VPC_ID \
    --query 'NetworkAcls[*].Associations[*].{AssocId:NetworkAclAssociationId,SubnetId:SubnetId,NaclId:NetworkAclId}' \
    --output table
```

### Blocking a Specific IP (NACL Use Case)

NACLs can explicitly deny traffic — Security Groups cannot. This makes NACLs useful for blocking bad actors.

```bash
# Block a specific IP at the NACL level (add before existing allow rules)
aws ec2 create-network-acl-entry \
    --network-acl-id $NACL_ID \
    --rule-number 50 \
    --protocol -1 \
    --cidr-block 198.51.100.1/32 \
    --rule-action deny \
    --ingress

# Rule 50 (deny) is evaluated before Rule 100 (allow), so the IP is blocked
```

### Modifying and Deleting NACL Rules

```bash
# Replace an existing rule (same rule number)
aws ec2 replace-network-acl-entry \
    --network-acl-id $NACL_ID \
    --rule-number 100 \
    --protocol tcp \
    --port-range From=443,To=443 \
    --cidr-block 10.0.0.0/8 \     # expanded CIDR
    --rule-action allow \
    --ingress

# Delete a rule
aws ec2 delete-network-acl-entry \
    --network-acl-id $NACL_ID \
    --rule-number 50 \
    --ingress

# View all NACL rules
aws ec2 describe-network-acls \
    --network-acl-ids $NACL_ID \
    --query 'NetworkAcls[0].Entries[*].{
        Rule:RuleNumber,
        Proto:Protocol,
        From:PortRange.From,
        To:PortRange.To,
        CIDR:CidrBlock,
        Dir:Egress,
        Action:RuleAction
    }' \
    --output table
```

---

## Security Group vs NACL: When to Use Each

| Scenario | Use SG | Use NACL |
|----------|--------|----------|
| Allow traffic to a specific instance | Yes | No (too broad) |
| Reference another SG as source | Yes | No |
| Deny a specific IP | No (allow-only) | Yes |
| Subnet-level firewall baseline | No | Yes |
| Return traffic handling | Automatic (stateful) | Manual (add ephemeral rules) |
| Emergency IP block | No | Yes (immediate effect) |

**Best practice:** Use Security Groups as your primary control. Use NACLs only for subnet-level baselines and emergency IP blocking.

---

## Defense in Depth: Layered Approach

```
Internet
   │
   ▼
[NACL: public subnet]         ← subnet-level: broad rules, emergency blocks
   │
   ▼
[Security Group: ALB]         ← allow 80/443 from 0.0.0.0/0
   │
   ▼
[NACL: private subnet]        ← allow from VPC CIDR + ephemeral ports
   │
   ▼
[Security Group: App servers] ← allow port 8080 from ALB SG only
   │
   ▼
[Security Group: RDS]         ← allow port 3306 from App SG only
```

---

## Troubleshooting Connectivity Issues

```bash
# Step 1: Check Security Group rules
aws ec2 describe-security-groups --group-ids sg-0abc1234 \
    --query 'SecurityGroups[0].IpPermissions'

# Step 2: Check NACL rules for the subnet
SUBNET_ID="subnet-0abc1234"
aws ec2 describe-network-acls \
    --filters Name=association.subnet-id,Values=$SUBNET_ID \
    --query 'NetworkAcls[0].Entries[*].{Rule:RuleNumber,Action:RuleAction,CIDR:CidrBlock,Port:PortRange}' \
    --output table

# Step 3: Check route table
aws ec2 describe-route-tables \
    --filters Name=association.subnet-id,Values=$SUBNET_ID \
    --query 'RouteTables[0].Routes[*].{Dest:DestinationCidrBlock,Target:GatewayId,State:State}' \
    --output table

# Step 4: Use VPC Reachability Analyzer (point-to-point path check)
aws ec2 create-network-insights-path \
    --source i-0source-instance \
    --destination i-0dest-instance \
    --protocol tcp \
    --destination-port 443

aws ec2 start-network-insights-analysis \
    --network-insights-path-id nip-0abc1234

# Get analysis result
aws ec2 describe-network-insights-analyses \
    --network-insights-analysis-ids nia-0abc1234 \
    --query 'NetworkInsightsAnalyses[0].{Status:Status,Reachable:NetworkPathFound,Explanation:Explanations}'
```

### Common Root Causes

| Symptom | Likely Cause |
|---------|-------------|
| Timeout (no response) | SG missing inbound rule, or NACL deny rule |
| Connection refused | Port reached instance but nothing listening |
| Works inbound, fails outbound | NACL missing outbound ephemeral port rule |
| Works for some instances, not others | Instance has different SG, or different subnet (NACL) |
| Intermittent failures | NACL stateless issue with ephemeral ports |

---

## References

- [Security Groups documentation](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)
- [Network ACLs documentation](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)
- [VPC Reachability Analyzer](https://docs.aws.amazon.com/vpc/latest/reachability/what-is-reachability-analyzer.html)
---

← [Previous: IGW & NAT Gateway](./igw-natgw.md) | [Home](../../README.md) | [Next: Route 53 →](./route53.md)
