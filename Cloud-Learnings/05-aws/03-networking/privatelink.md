← [Previous: VPC Peering & Transit Gateway](./vpc-peering-tgw.md) | [Home](../../README.md) | [Next: AWS Compute →](../04-compute/README.md)

---

# AWS PrivateLink and VPC Endpoints

AWS PrivateLink provides private connectivity between VPCs and AWS services (or your own services) without exposing traffic to the public internet. Traffic stays entirely within the AWS network.

---

## Types of VPC Endpoints

| Type | Technology | Supports | Charge |
|------|-----------|----------|--------|
| **Gateway endpoint** | Route table entry | S3, DynamoDB | Free |
| **Interface endpoint** | ENI with private IP | 100+ AWS services | Per hour + per GB |
| **Gateway Load Balancer endpoint** | GWLB | Third-party appliances (firewall, IDS) | Per hour + per GB |

---

## Gateway Endpoints (S3 and DynamoDB)

Gateway endpoints add a route to the VPC route table that directs S3 or DynamoDB traffic through AWS's network rather than through the internet (NAT Gateway). They are free and easy to deploy.

```bash
VPC_ID="vpc-0abc1234"

# Create S3 Gateway endpoint
S3_ENDPOINT=$(aws ec2 create-vpc-endpoint \
    --vpc-id $VPC_ID \
    --service-name com.amazonaws.us-east-1.s3 \
    --vpc-endpoint-type Gateway \
    --route-table-ids rtb-private-1a rtb-private-1b rtb-db \
    --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=s3-gateway-endpoint}]' \
    --query 'VpcEndpoint.VpcEndpointId' --output text)

echo "S3 endpoint: $S3_ENDPOINT"

# Create DynamoDB Gateway endpoint
DDB_ENDPOINT=$(aws ec2 create-vpc-endpoint \
    --vpc-id $VPC_ID \
    --service-name com.amazonaws.us-east-1.dynamodb \
    --vpc-endpoint-type Gateway \
    --route-table-ids rtb-private-1a rtb-private-1b \
    --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=dynamodb-gateway-endpoint}]' \
    --query 'VpcEndpoint.VpcEndpointId' --output text)

# After creation, route tables automatically get a prefix list route:
# pl-XXXXXXXX (S3 or DynamoDB prefix list) → vpce-XXXXXXXX
# Traffic to S3 no longer goes through NAT Gateway — saving cost

# Verify the route was added
aws ec2 describe-route-tables \
    --route-table-ids rtb-private-1a \
    --query 'RouteTables[0].Routes[*].{Dest:DestinationPrefixListId,Target:GatewayId}' \
    --output table

# Add endpoint policy (restrict which S3 buckets or DynamoDB tables are accessible)
aws ec2 modify-vpc-endpoint \
    --vpc-endpoint-id $S3_ENDPOINT \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            "Resource": [
                "arn:aws:s3:::my-production-bucket",
                "arn:aws:s3:::my-production-bucket/*"
            ]
        }]
    }'
```

---

## Interface Endpoints (PrivateLink)

Interface endpoints create an ENI (Elastic Network Interface) in your subnet with a private IP address. Applications connect to the endpoint's DNS name, which resolves to the private IP — traffic stays within the VPC.

### Common Interface Endpoints

```bash
VPC_ID="vpc-0abc1234"
SG_VPCE="sg-vpc-endpoint"

# Create interface endpoints for common AWS services
SERVICES=(
    "com.amazonaws.us-east-1.ssm"              # SSM Parameter Store + Session Manager
    "com.amazonaws.us-east-1.ssmmessages"       # SSM Session Manager agent messages
    "com.amazonaws.us-east-1.ec2messages"       # SSM EC2 agent messages
    "com.amazonaws.us-east-1.secretsmanager"    # Secrets Manager
    "com.amazonaws.us-east-1.kms"              # KMS
    "com.amazonaws.us-east-1.logs"             # CloudWatch Logs
    "com.amazonaws.us-east-1.monitoring"       # CloudWatch metrics
    "com.amazonaws.us-east-1.ecr.api"         # ECR API
    "com.amazonaws.us-east-1.ecr.dkr"        # ECR Docker registry
    "com.amazonaws.us-east-1.sts"             # STS (role assumption)
)

for SERVICE in "${SERVICES[@]}"; do
    echo "Creating endpoint for $SERVICE..."
    aws ec2 create-vpc-endpoint \
        --vpc-id $VPC_ID \
        --service-name $SERVICE \
        --vpc-endpoint-type Interface \
        --subnet-ids subnet-private-1a subnet-private-1b \
        --security-group-ids $SG_VPCE \
        --private-dns-enabled \
        --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=$(echo $SERVICE | awk -F. '{print $NF}')-endpoint}]"
done
```

### Endpoint DNS with Private DNS Enabled

When `--private-dns-enabled` is set, the endpoint overrides the public DNS for the service within the VPC:

```
Without private DNS:
  secretsmanager.us-east-1.amazonaws.com → 52.x.x.x (public IP)
  → traffic goes through NAT Gateway

With private DNS enabled:
  secretsmanager.us-east-1.amazonaws.com → 10.0.10.147 (private ENI IP)
  → traffic stays inside VPC, no internet required

Code change: NONE — the SDK/CLI uses the same endpoint URL automatically.
```

### Security Group for VPC Endpoints

```bash
# Create a security group for interface endpoints
SG_VPCE=$(aws ec2 create-security-group \
    --group-name vpc-endpoint-sg \
    --description "Allow HTTPS from private subnets to VPC endpoints" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)

# Allow HTTPS from all private subnets
aws ec2 authorize-security-group-ingress \
    --group-id $SG_VPCE \
    --protocol tcp \
    --port 443 \
    --cidr 10.0.10.0/23    # private subnets (10.0.10.0/24 + 10.0.11.0/24)

# Allow HTTPS from DB subnets (for RDS to call Secrets Manager, etc.)
aws ec2 authorize-security-group-ingress \
    --group-id $SG_VPCE \
    --protocol tcp \
    --port 443 \
    --cidr 10.0.20.0/23    # DB subnets

echo "VPC endpoint SG: $SG_VPCE"
```

### List and Inspect Endpoints

```bash
# List all endpoints in a VPC
aws ec2 describe-vpc-endpoints \
    --filters Name=vpc-id,Values=$VPC_ID \
    --query 'VpcEndpoints[*].{
        ID:VpcEndpointId,
        Type:VpcEndpointType,
        Service:ServiceName,
        State:State,
        DNS:DnsEntries[0].DnsName
    }' \
    --output table

# List all available services in the region
aws ec2 describe-vpc-endpoint-services \
    --query 'ServiceDetails[*].{
        ServiceName:ServiceName,
        Type:ServiceType[0].ServiceType,
        PrivateDNS:PrivateDnsName
    }' \
    --output table | grep amazonaws
```

---

## Custom PrivateLink Services (Endpoint Services)

PrivateLink can expose your own services privately to other VPCs or AWS accounts. This is how SaaS providers expose services to customers without VPC peering.

```
Consumer VPC                    Provider VPC
  Interface endpoint ──────────→ Network Load Balancer
  (private IP in consumer VPC)      │
                                     ▼
                                 Your service (EC2, ECS, Lambda)
```

### Create an Endpoint Service

```bash
# Step 1: Create a Network Load Balancer for your service
NLB_ARN=$(aws elbv2 create-load-balancer \
    --name my-private-service-nlb \
    --type network \
    --scheme internal \
    --subnets subnet-private-1a subnet-private-1b \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Step 2: Create the endpoint service backed by the NLB
ENDPOINT_SERVICE_ID=$(aws ec2 create-vpc-endpoint-service-configuration \
    --network-load-balancer-arns $NLB_ARN \
    --acceptance-required \
    --tag-specifications 'ResourceType=vpc-endpoint-service,Tags=[{Key=Name,Value=my-private-service}]' \
    --query 'ServiceConfiguration.ServiceId' --output text)

SERVICE_NAME=$(aws ec2 describe-vpc-endpoint-service-configurations \
    --service-ids $ENDPOINT_SERVICE_ID \
    --query 'ServiceConfigurations[0].ServiceName' --output text)

echo "Endpoint service: $SERVICE_NAME"
# Output: com.amazonaws.vpce.us-east-1.vpce-svc-0abc1234

# Step 3: Allow specific accounts to use this endpoint service
aws ec2 modify-vpc-endpoint-service-permissions \
    --service-id $ENDPOINT_SERVICE_ID \
    --add-allowed-principals arn:aws:iam::222222222222:root

# Step 4: View pending connection requests
aws ec2 describe-vpc-endpoint-connections \
    --filters Name=service-id,Values=$ENDPOINT_SERVICE_ID \
    --query 'VpcEndpointConnections[*].{
        EndpointId:VpcEndpointId,
        Account:VpcEndpointOwner,
        State:VpcEndpointState
    }' \
    --output table

# Step 5: Accept or reject a connection request
aws ec2 accept-vpc-endpoint-connections \
    --service-id $ENDPOINT_SERVICE_ID \
    --vpc-endpoint-ids vpce-0consumer123
```

### Consumer Side: Connect to the Custom Service

```bash
# In the consumer account/VPC:
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-consumer \
    --service-name com.amazonaws.vpce.us-east-1.vpce-svc-0abc1234 \
    --vpc-endpoint-type Interface \
    --subnet-ids subnet-consumer-1a subnet-consumer-1b \
    --security-group-ids sg-consumer-endpoint \
    --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=my-service-endpoint}]'

# The endpoint will show as "pending acceptance" until provider accepts
```

---

## PrivateLink vs VPC Peering vs Transit Gateway

| | PrivateLink (Interface Endpoint) | VPC Peering | Transit Gateway |
|--|----------------------------------|-------------|-----------------|
| CIDR overlap allowed | Yes | No | No |
| Transitive routing | No | No | Yes |
| Initiator | Consumer only | Bidirectional | Configurable |
| Exposes | Specific service/port | Entire VPC CIDR | Configurable |
| Cross-account | Yes | Yes | Yes (via RAM) |
| Cost | Per hour + per GB | Per GB (cross-AZ/region) | Per hour + per GB |
| Best for | SaaS, shared services, AWS APIs | Direct VPC-to-VPC | Many VPCs, network hub |

**Key advantage of PrivateLink:** CIDR blocks can overlap. A provider exposes only a specific service endpoint, not the entire network — making it ideal for SaaS and multi-tenant architectures.

---

## Cost Considerations

```bash
# Identify unused interface endpoints (state = available but no traffic)
aws ec2 describe-vpc-endpoints \
    --filters Name=vpc-id,Values=$VPC_ID Name=state,Values=available \
    --query 'VpcEndpoints[*].{ID:VpcEndpointId,Service:ServiceName,Created:CreationTimestamp}' \
    --output table

# Each interface endpoint costs ~$0.01/hr per AZ = ~$0.02/hr for 2 AZs = ~$14.4/month
# For rarely used services: cheaper to route through NAT Gateway
# For high-volume services: interface endpoints save NAT Gateway processing costs

# Typical cost break-even: ~500GB/month through NAT vs interface endpoint
# NAT: 500 GB × $0.045 = $22.50
# Interface endpoint: $14.40 (hourly) + 500 GB × $0.01 (data) = $19.40
# At >500GB/month, interface endpoints save money
```

---

## References

- [VPC Endpoints documentation](https://docs.aws.amazon.com/vpc/latest/privatelink/)
- [PrivateLink concepts](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-share-your-services.html)
- [Endpoint service configuration](https://docs.aws.amazon.com/vpc/latest/privatelink/create-endpoint-service.html)
- [Endpoint policies](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-access.html)
---

← [Previous: VPC Peering & Transit Gateway](./vpc-peering-tgw.md) | [Home](../../README.md) | [Next: AWS Compute →](../04-compute/README.md)
