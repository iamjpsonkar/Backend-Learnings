← [Previous: Subnets & Route Tables](./subnets-route-tables.md) | [Home](../../README.md) | [Next: Security Groups & NACLs →](./security-groups-nacl.md)

---

# Internet Gateway and NAT Gateway

These are the two core components that control internet connectivity in a VPC.

---

## Internet Gateway (IGW)

An IGW is a horizontally-scaled, redundant, highly available VPC component that enables internet connectivity for resources with public IP addresses.

**Properties:**
- One per VPC (hard limit)
- No bandwidth limit; no throughput charges (only data transfer costs)
- Performs 1:1 NAT between public (Elastic) IPs and private IPs
- Fully managed by AWS — no patching, no capacity planning

```
Instance (private IP: 10.0.0.5)  ←→  IGW  ←→  Internet
                                      (translates: 10.0.0.5 ↔ 54.12.34.56)
```

### Create and Attach an IGW

```bash
VPC_ID="vpc-0abc1234"

# Create
IGW_ID=$(aws ec2 create-internet-gateway \
    --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=production-igw}]' \
    --query 'InternetGateway.InternetGatewayId' --output text)

# Attach to VPC
aws ec2 attach-internet-gateway \
    --internet-gateway-id $IGW_ID \
    --vpc-id $VPC_ID

# Add default route in public route table
aws ec2 create-route \
    --route-table-id $RTB_PUBLIC \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id $IGW_ID

# Verify
aws ec2 describe-internet-gateways \
    --internet-gateway-ids $IGW_ID \
    --query 'InternetGateways[0].{ID:InternetGatewayId,State:Attachments[0].State,VPC:Attachments[0].VpcId}'
```

---

## NAT Gateway

A NAT Gateway allows resources in private subnets to initiate outbound connections to the internet (for updates, API calls, etc.) while blocking inbound connections from the internet.

**Properties:**
- Deployed in a **public subnet** (needs internet access via IGW)
- Requires an **Elastic IP**
- AZ-specific — not HA across AZs by itself
- Managed service — no maintenance or patching
- Scales automatically up to 100 Gbps
- Charged: per hour (~$0.045/hr) + per GB processed (~$0.045/GB)

### Create NAT Gateways (One Per AZ)

```bash
# Allocate Elastic IPs
EIP_A=$(aws ec2 allocate-address \
    --domain vpc \
    --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=nat-eip-1a}]' \
    --query 'AllocationId' --output text)

EIP_B=$(aws ec2 allocate-address \
    --domain vpc \
    --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=nat-eip-1b}]' \
    --query 'AllocationId' --output text)

# Create NAT Gateways in public subnets
NAT_A=$(aws ec2 create-nat-gateway \
    --subnet-id $PUB_A \
    --allocation-id $EIP_A \
    --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=nat-1a}]' \
    --query 'NatGateway.NatGatewayId' --output text)

NAT_B=$(aws ec2 create-nat-gateway \
    --subnet-id $PUB_B \
    --allocation-id $EIP_B \
    --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=nat-1b}]' \
    --query 'NatGateway.NatGatewayId' --output text)

# Wait until available (takes 1–2 minutes)
echo "Waiting for NAT Gateways..."
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_A $NAT_B

# Add routes in private route tables (one per AZ → its own NAT)
aws ec2 create-route \
    --route-table-id $RTB_PRIV_A \
    --destination-cidr-block 0.0.0.0/0 \
    --nat-gateway-id $NAT_A

aws ec2 create-route \
    --route-table-id $RTB_PRIV_B \
    --destination-cidr-block 0.0.0.0/0 \
    --nat-gateway-id $NAT_B

echo "NAT Gateways ready: $NAT_A (AZ-a), $NAT_B (AZ-b)"
```

### Verify Connectivity from a Private Instance

```bash
# SSH to private instance via bastion or SSM Session Manager
aws ssm start-session --target i-0private-instance-id

# From the private instance:
curl -s http://checkip.amazonaws.com    # should return the NAT Gateway's EIP
ping -c 3 8.8.8.8                       # should succeed
curl -s https://api.example.com/health  # should reach external API
```

### Check NAT Gateway Metrics

```bash
# Monitor NAT Gateway performance via CloudWatch
aws cloudwatch get-metric-statistics \
    --namespace AWS/NATGateway \
    --metric-name BytesOutToDestination \
    --dimensions Name=NatGatewayId,Value=$NAT_A \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum \
    --query 'Datapoints[*].{Time:Timestamp,BytesOut:Sum}' \
    --output table

# Key NAT Gateway metrics:
# BytesOutToDestination   — outbound bytes (billable)
# BytesInFromDestination  — inbound bytes from internet to private subnet
# PacketsDropCount        — dropped packets (connection issues)
# ErrorPortAllocation     — NAT port exhaustion (increase instance count or split traffic)
```

### NAT Gateway Cost Optimisation

NAT Gateway is often one of the biggest surprise costs. Reduce it by:

```bash
# 1. Use VPC Endpoints for AWS services (traffic bypasses NAT)
# S3 and DynamoDB: free Gateway endpoints
# SSM, Secrets Manager, ECR: Interface endpoints (hourly charge, but cheaper than NAT for high-volume)

# 2. Keep traffic in the same AZ
#    EC2 in AZ-a → NAT in AZ-a (no cross-AZ data transfer charge)

# 3. Deploy NAT per AZ (not shared), even though it costs more per hour —
#    prevents cross-AZ charges that accumulate quickly in high-traffic environments

# 4. Identify unexpected outbound traffic
aws cloudwatch get-metric-statistics \
    --namespace AWS/NATGateway \
    --metric-name BytesOutToDestination \
    --dimensions Name=NatGatewayId,Value=$NAT_A \
    --start-time $(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 86400 \
    --statistics Sum \
    --output table
```

---

## Egress-Only Internet Gateway (for IPv6)

IPv6 addresses are globally routable — there is no private IPv6 (unlike RFC 1918 for IPv4). An Egress-Only IGW provides outbound-only IPv6 internet access for private subnets (equivalent to NAT for IPv4).

```bash
# Create Egress-Only IGW
EIGW_ID=$(aws ec2 create-egress-only-internet-gateway \
    --vpc-id $VPC_ID \
    --tag-specifications 'ResourceType=egress-only-internet-gateway,Tags=[{Key=Name,Value=eigw}]' \
    --query 'EgressOnlyInternetGateway.EgressOnlyInternetGatewayId' --output text)

# Add to private subnet route table (IPv6 default route)
aws ec2 create-route \
    --route-table-id $RTB_PRIV_A \
    --destination-ipv6-cidr-block ::/0 \
    --egress-only-internet-gateway-id $EIGW_ID
```

---

## Elastic IP (EIP)

Elastic IPs are static public IPv4 addresses that you allocate to your account and associate with instances or NAT Gateways.

```bash
# Allocate an Elastic IP
EIP_ALLOC=$(aws ec2 allocate-address \
    --domain vpc \
    --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=web-server-eip}]' \
    --query 'AllocationId' --output text)

# Associate with an instance
aws ec2 associate-address \
    --instance-id i-0abc1234 \
    --allocation-id $EIP_ALLOC

# Disassociate (detach from instance)
aws ec2 disassociate-address \
    --association-id eipassoc-0abc1234

# Release (return to AWS — billing stops)
aws ec2 release-address --allocation-id $EIP_ALLOC

# List all your EIPs
aws ec2 describe-addresses \
    --query 'Addresses[*].{EIP:PublicIp,Allocated:AllocationId,Associated:AssociationId,Instance:InstanceId}' \
    --output table
```

**Important**: Unassociated Elastic IPs incur a charge (~$0.005/hr). Release EIPs you are not using.

---

## IGW vs NAT Gateway Summary

| | IGW | NAT Gateway |
|--|-----|-------------|
| Direction | Bidirectional (inbound + outbound) | Outbound only (private → internet) |
| Per VPC | One (attached) | One per AZ (recommended) |
| Requires public IP | Instance must have EIP or auto-assigned public IP | No; NAT has its own EIP |
| Use for | Public subnet instances, ALB, bastion | Private subnet instances reaching internet |
| Cost | No hourly charge | $0.045/hr + $0.045/GB |

---

## References

- [Internet Gateways documentation](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html)
- [NAT Gateways documentation](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)
- [NAT Gateway troubleshooting](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-troubleshooting.html)
---

← [Previous: Subnets & Route Tables](./subnets-route-tables.md) | [Home](../../README.md) | [Next: Security Groups & NACLs →](./security-groups-nacl.md)
