← [Previous: CloudFront](./cloudfront.md) | [Home](../../README.md) | [Next: PrivateLink →](./privatelink.md)

---

# VPC Peering and Transit Gateway

VPC Peering and Transit Gateway are the two core mechanisms for connecting multiple VPCs in AWS. Peering is point-to-point; Transit Gateway is a hub-and-spoke router that scales to hundreds of VPCs.

---

## VPC Peering

A VPC Peering connection is a private, non-transitive network link between exactly two VPCs. Traffic stays on the AWS backbone and never traverses the public internet.

**Key constraints:**
- Non-transitive: if VPC A peers with B, and B peers with C, A cannot reach C through B
- CIDR blocks of the two VPCs must not overlap
- Works across accounts and across regions (inter-region peering)
- No bandwidth limit (unlike Direct Connect); no data transfer fee within the same AZ (cross-AZ: $0.01/GB; cross-region: standard data transfer rates)

### Create a VPC Peering Connection

```bash
VPC_A="vpc-0aaaa1111"
VPC_B="vpc-0bbbb2222"
ACCOUNT_B="222222222222"   # same or different account
REGION_B="us-east-1"       # same or different region

# Step 1: Request peering (from VPC A's account/region)
PEER_ID=$(aws ec2 create-vpc-peering-connection \
    --vpc-id $VPC_A \
    --peer-vpc-id $VPC_B \
    --peer-owner-id $ACCOUNT_B \
    --peer-region $REGION_B \
    --tag-specifications 'ResourceType=vpc-peering-connection,Tags=[{Key=Name,Value=vpc-a-to-vpc-b}]' \
    --query 'VpcPeeringConnection.VpcPeeringConnectionId' --output text)

echo "Peering connection: $PEER_ID"

# Step 2: Accept the peering (from VPC B's account/region)
# Switch profile/region as needed
aws ec2 accept-vpc-peering-connection \
    --vpc-peering-connection-id $PEER_ID \
    --region $REGION_B

# Step 3: Add routes in BOTH VPCs' route tables
# In VPC A → route to VPC B CIDR via the peering connection
aws ec2 create-route \
    --route-table-id rtb-vpc-a-private \
    --destination-cidr-block 10.1.0.0/16 \    # VPC B CIDR
    --vpc-peering-connection-id $PEER_ID

# In VPC B → route to VPC A CIDR via the peering connection
aws ec2 create-route \
    --route-table-id rtb-vpc-b-private \
    --destination-cidr-block 10.0.0.0/16 \    # VPC A CIDR
    --vpc-peering-connection-id $PEER_ID

# Step 4: Update Security Groups (SGs still need to allow traffic)
# In VPC B, allow traffic from VPC A CIDR
aws ec2 authorize-security-group-ingress \
    --group-id sg-vpcb-app \
    --protocol tcp \
    --port 8080 \
    --cidr 10.0.0.0/16   # VPC A CIDR

# Verify peering is active
aws ec2 describe-vpc-peering-connections \
    --vpc-peering-connection-ids $PEER_ID \
    --query 'VpcPeeringConnections[0].{
        ID:VpcPeeringConnectionId,
        Status:Status.Code,
        Requester:RequesterVpcInfo.CidrBlock,
        Accepter:AccepterVpcInfo.CidrBlock
    }'
```

### Limitations and When Not to Use Peering

| VPC count | Peering connections needed | Complexity |
|-----------|---------------------------|------------|
| 2 VPCs | 1 | Trivial |
| 5 VPCs (full mesh) | 10 | Manageable |
| 10 VPCs (full mesh) | 45 | Complex |
| 50 VPCs (full mesh) | 1,225 | Unmanageable |

At scale, use Transit Gateway instead.

---

## Transit Gateway (TGW)

Transit Gateway is a regional, managed network hub that simplifies connectivity at scale. Instead of a mesh of peering connections, each VPC connects to the TGW once, and routing between VPCs is controlled centrally via TGW route tables.

```
Without TGW (full mesh):          With TGW (hub-and-spoke):
VPC-A ←→ VPC-B                   VPC-A ──→ TGW ──→ VPC-B
VPC-A ←→ VPC-C                   VPC-C ──→ TGW ──→ VPC-D
VPC-B ←→ VPC-C                   (n connections, not n*(n-1)/2)
...
```

**Key features:**
- Supports up to 5,000 VPC attachments per TGW
- Works across accounts (via Resource Access Manager)
- Supports Site-to-Site VPN and Direct Connect Gateway attachments
- TGW route tables allow segmentation (e.g., prod VPCs cannot reach dev VPCs)
- Multicast support
- Bandwidth: up to 50 Gbps per AZ

### Create a Transit Gateway

```bash
# Step 1: Create the TGW (in the hub/network account)
TGW_ID=$(aws ec2 create-transit-gateway \
    --description "Central hub TGW" \
    --options "AmazonSideAsn=64512,AutoAcceptSharedAttachments=disable,DefaultRouteTableAssociation=enable,DefaultRouteTablePropagation=enable,VpnEcmpSupport=enable,DnsSupport=enable" \
    --tag-specifications 'ResourceType=transit-gateway,Tags=[{Key=Name,Value=central-tgw}]' \
    --query 'TransitGateway.TransitGatewayId' --output text)

echo "TGW: $TGW_ID"

# Wait for TGW to become available
aws ec2 wait transit-gateway-available --filters Name=transit-gateway-id,Values=$TGW_ID 2>/dev/null || \
    echo "Wait command unavailable, check status manually"

aws ec2 describe-transit-gateways \
    --transit-gateway-ids $TGW_ID \
    --query 'TransitGateways[0].{ID:TransitGatewayId,State:State}'
```

### Attach VPCs to the Transit Gateway

```bash
TGW_ID="tgw-0abc1234"

# Attach VPC A (use private subnets — one per AZ)
TGW_ATTACH_A=$(aws ec2 create-transit-gateway-vpc-attachment \
    --transit-gateway-id $TGW_ID \
    --vpc-id vpc-0aaaa1111 \
    --subnet-ids subnet-priv-1a subnet-priv-1b \
    --tag-specifications 'ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=tgw-attach-vpc-a}]' \
    --query 'TransitGatewayVpcAttachment.TransitGatewayAttachmentId' --output text)

# Attach VPC B
TGW_ATTACH_B=$(aws ec2 create-transit-gateway-vpc-attachment \
    --transit-gateway-id $TGW_ID \
    --vpc-id vpc-0bbbb2222 \
    --subnet-ids subnet-priv-1a subnet-priv-1b \
    --tag-specifications 'ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=tgw-attach-vpc-b}]' \
    --query 'TransitGatewayVpcAttachment.TransitGatewayAttachmentId' --output text)

# List all attachments
aws ec2 describe-transit-gateway-vpc-attachments \
    --filters Name=transit-gateway-id,Values=$TGW_ID \
    --query 'TransitGatewayVpcAttachments[*].{
        ID:TransitGatewayAttachmentId,
        VPC:VpcId,
        State:State
    }' \
    --output table
```

### Add Routes in VPC Route Tables to TGW

Each VPC's route tables must direct cross-VPC traffic to the TGW.

```bash
# In VPC A: route to VPC B (and any other VPCs) via TGW
aws ec2 create-route \
    --route-table-id rtb-vpc-a-private-1a \
    --destination-cidr-block 10.1.0.0/16 \    # VPC B CIDR
    --transit-gateway-id $TGW_ID

aws ec2 create-route \
    --route-table-id rtb-vpc-a-private-1b \
    --destination-cidr-block 10.1.0.0/16 \
    --transit-gateway-id $TGW_ID

# Alternatively: aggregate all spoke VPCs under a supernet
aws ec2 create-route \
    --route-table-id rtb-vpc-a-private-1a \
    --destination-cidr-block 10.0.0.0/8 \     # all spoke VPCs
    --transit-gateway-id $TGW_ID
```

### TGW Route Tables for Traffic Segmentation

TGW route tables allow you to control which VPCs can communicate with each other. For example, production VPCs can reach shared services but not development VPCs.

```bash
# Create separate TGW route tables for prod and non-prod
TGW_RTB_PROD=$(aws ec2 create-transit-gateway-route-table \
    --transit-gateway-id $TGW_ID \
    --tag-specifications 'ResourceType=transit-gateway-route-table,Tags=[{Key=Name,Value=prod-rtb}]' \
    --query 'TransitGatewayRouteTable.TransitGatewayRouteTableId' --output text)

TGW_RTB_DEV=$(aws ec2 create-transit-gateway-route-table \
    --transit-gateway-id $TGW_ID \
    --tag-specifications 'ResourceType=transit-gateway-route-table,Tags=[{Key=Name,Value=dev-rtb}]' \
    --query 'TransitGatewayRouteTable.TransitGatewayRouteTableId' --output text)

# Associate prod VPC attachment with prod route table
aws ec2 associate-transit-gateway-route-table \
    --transit-gateway-route-table-id $TGW_RTB_PROD \
    --transit-gateway-attachment-id $TGW_ATTACH_PROD

# Propagate shared services routes into prod route table
aws ec2 enable-transit-gateway-route-table-propagation \
    --transit-gateway-route-table-id $TGW_RTB_PROD \
    --transit-gateway-attachment-id $TGW_ATTACH_SHARED

# Add static route in prod table → shared services VPC
aws ec2 create-transit-gateway-route \
    --transit-gateway-route-table-id $TGW_RTB_PROD \
    --destination-cidr-block 10.3.0.0/16 \   # shared services VPC
    --transit-gateway-attachment-id $TGW_ATTACH_SHARED

# View TGW route table
aws ec2 search-transit-gateway-routes \
    --transit-gateway-route-table-id $TGW_RTB_PROD \
    --filters Name=type,Values=static,propagated \
    --query 'Routes[*].{CIDR:DestinationCidrBlock,Attach:TransitGatewayAttachments[0].TransitGatewayAttachmentId,Type:Type,State:State}' \
    --output table
```

### Cross-Account TGW Sharing

Share the TGW from the network account to workload accounts using AWS Resource Access Manager (RAM).

```bash
NETWORK_ACCOUNT="111111111111"
WORKLOAD_ACCOUNT="222222222222"
ORG_ARN="arn:aws:organizations::111111111111:organization/o-abc12345"

# Create a RAM share for the TGW
aws ram create-resource-share \
    --name "central-tgw-share" \
    --resource-arns arn:aws:ec2:us-east-1:$NETWORK_ACCOUNT:transit-gateway/$TGW_ID \
    --principals $ORG_ARN \    # share with entire org
    --allow-external-principals false

# In the workload account: accept the RAM invite (or auto-accepted if same org)
aws ram get-resource-share-invitations \
    --query 'resourceShareInvitations[?status==`PENDING`].resourceShareInvitationArn' \
    --output text

aws ram accept-resource-share-invitation \
    --resource-share-invitation-arn arn:aws:ram:us-east-1:$NETWORK_ACCOUNT:resource-share-invitation/abc123

# Now the workload account can create attachments to the shared TGW
aws ec2 create-transit-gateway-vpc-attachment \
    --transit-gateway-id $TGW_ID \
    --vpc-id vpc-workload \
    --subnet-ids subnet-workload-priv-1a subnet-workload-priv-1b \
    --tag-specifications 'ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=workload-attach}]'
```

---

## VPC Peering vs Transit Gateway

| | VPC Peering | Transit Gateway |
|--|-------------|-----------------|
| Topology | Point-to-point | Hub-and-spoke |
| Transitivity | No | Yes (configurable) |
| Max connections | 125 peerings per VPC | 5,000 attachments per TGW |
| Setup per new VPC | Add peering + routes in all existing VPCs | One attachment + one route per VPC |
| Cross-account | Yes | Yes (via RAM) |
| Cross-region | Yes | Yes (TGW peering) |
| Data transfer cost | Within AZ: free; cross-AZ: $0.01/GB | $0.02/GB processed + $0.05/hr per attachment |
| Routing control | Route table per VPC | TGW route tables with segments |
| Best for | 2–5 VPCs, simple connectivity | 5+ VPCs, segmentation required, centralized egress |

---

## References

- [VPC Peering documentation](https://docs.aws.amazon.com/vpc/latest/peering/)
- [Transit Gateway documentation](https://docs.aws.amazon.com/vpc/latest/tgw/)
- [Transit Gateway with RAM](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-transit-gateways.html#tgw-sharing)
---

← [Previous: CloudFront](./cloudfront.md) | [Home](../../README.md) | [Next: PrivateLink →](./privatelink.md)
