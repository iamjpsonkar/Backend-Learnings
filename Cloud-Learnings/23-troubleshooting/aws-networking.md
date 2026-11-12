← [Previous: Troubleshooting Overview](./README.md) | [Home](../README.md) | [Next: Containers & Kubernetes →](./containers-k8s.md)

---

# Troubleshooting: AWS Networking

Most AWS networking problems fall into one of four categories: security group rules blocking traffic, route tables missing routes, DNS resolution failures, or NACLs with deny rules. Work through them in that order — security groups are the most common cause.

---

## Connectivity Troubleshooting Flow

```
Can't reach EC2/ECS/RDS from client?
  │
  ├── Is the target listening?
  │     aws ssm start-session → netstat -tlnp
  │
  ├── Security Group allows the source IP/SG?
  │     aws ec2 describe-security-groups
  │
  ├── Route table has a route to the destination?
  │     aws ec2 describe-route-tables
  │
  ├── NACL allows traffic (both inbound AND outbound)?
  │     aws ec2 describe-network-acls
  │
  ├── Is the instance in the right subnet (public vs private)?
  │     aws ec2 describe-instances → SubnetId
  │
  └── VPC Flow Logs show REJECT?
        aws logs filter-log-events --log-group-name /aws/vpc/flowlogs
```

---

## Security Groups

```bash
# Get security groups attached to a specific instance
INSTANCE_ID="i-0123456789abcdef0"

aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].{
        SG:SecurityGroups[*].GroupId,
        PrivateIP:PrivateIpAddress,
        Subnet:SubnetId,
        State:State.Name
    }'

# Check inbound rules for a security group
SG_ID="sg-0123456789abcdef0"

aws ec2 describe-security-groups \
    --group-ids $SG_ID \
    --query 'SecurityGroups[0].IpPermissions[*].{
        Port:FromPort,
        Protocol:IpProtocol,
        Sources:IpRanges[*].CidrIp,
        SourceSGs:UserIdGroupPairs[*].GroupId
    }'

# Common fix: allow traffic from ALB security group to ECS tasks
aws ec2 authorize-security-group-ingress \
    --group-id sg-ecs-tasks \
    --protocol tcp \
    --port 8080 \
    --source-group sg-alb

# Check if a specific port is reachable (from within VPC)
# Via SSM Session Manager (no SSH key required)
aws ssm start-session --target $INSTANCE_ID
# Then on the instance:
# nc -zv 10.0.1.50 5432   # test TCP connectivity to RDS
# curl -v http://10.0.2.30:8080/health  # test HTTP
```

---

## Route Tables

```bash
# Find route table for a subnet
SUBNET_ID="subnet-0123456789abcdef0"

aws ec2 describe-route-tables \
    --filters Name=association.subnet-id,Values=$SUBNET_ID \
    --query 'RouteTables[0].Routes[*].{
        Dest:DestinationCidrBlock,
        Target:GatewayId,
        NatGW:NatGatewayId,
        State:State
    }'

# Common problems:
# 1. Private subnet missing NAT Gateway route (0.0.0.0/0 → nat-xxx)
# 2. Public subnet missing Internet Gateway route (0.0.0.0/0 → igw-xxx)
# 3. VPC peering route missing or going to wrong VPC

# Check if a subnet is public (has IGW route) or private
aws ec2 describe-route-tables \
    --filters Name=association.subnet-id,Values=$SUBNET_ID \
    --query 'RouteTables[0].Routes[?DestinationCidrBlock==`0.0.0.0/0`].{Target:GatewayId,NatGW:NatGatewayId}'
# If GatewayId starts with igw- → public subnet
# If NatGatewayId starts with nat- → private subnet (has outbound internet)
# If neither → no internet access
```

---

## VPC Flow Logs

```bash
# Enable VPC Flow Logs (if not already enabled)
VPC_ID="vpc-0123456789abcdef0"
LOG_GROUP="/aws/vpc/flowlogs"

aws logs create-log-group --log-group-name $LOG_GROUP

aws ec2 create-flow-logs \
    --resource-type VPC \
    --resource-ids $VPC_ID \
    --traffic-type ALL \
    --log-destination-type cloud-watch-logs \
    --log-group-name $LOG_GROUP \
    --deliver-logs-permission-arn arn:aws:iam::$ACCOUNT_ID:role/vpc-flow-logs-role

# Query flow logs for REJECT traffic to an IP
# Format: version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes windowstart windowend action flowlogstatus
aws logs filter-log-events \
    --log-group-name $LOG_GROUP \
    --filter-pattern "REJECT" \
    --start-time $(($(date +%s) - 3600))000 \
    --query 'events[*].message' \
    --output text | grep "10.0.1.50" | head -20

# CloudWatch Logs Insights query for connection analysis
aws logs start-query \
    --log-group-name $LOG_GROUP \
    --start-time $(($(date +%s) - 3600)) \
    --end-time $(date +%s) \
    --query-string '
        fields @timestamp, srcAddr, dstAddr, dstPort, action
        | filter action = "REJECT"
        | stats count(*) as rejectCount by srcAddr, dstAddr, dstPort
        | sort rejectCount desc
        | limit 20
    '
```

---

## DNS and Route 53

```bash
# Test DNS resolution from within a VPC (use SSM or EC2)
# On an EC2 instance inside the VPC:
nslookup prod-postgres.xxxx.us-east-1.rds.amazonaws.com
dig +short prod-postgres.xxxx.us-east-1.rds.amazonaws.com

# Check Route 53 health check status
HEALTH_CHECK_ID="abc123"
aws route53 get-health-check-status \
    --health-check-id $HEALTH_CHECK_ID \
    --query 'HealthCheckObservations[*].{Region:Region,Status:StatusReport.Status,Reason:StatusReport.CheckedTime}'

# Check Route 53 routing for a domain
aws route53 list-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --query 'ResourceRecordSets[?Name==`api.myapp.com.`]'

# Test if ALIAS record resolves to correct target
dig api.myapp.com @8.8.8.8
host api.myapp.com

# Common DNS issues:
# 1. enableDnsHostnames or enableDnsSupport disabled on VPC
aws ec2 describe-vpc-attribute --vpc-id $VPC_ID --attribute enableDnsSupport
aws ec2 describe-vpc-attribute --vpc-id $VPC_ID --attribute enableDnsHostnames
# Fix:
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support "{\"Value\":true}"
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames "{\"Value\":true}"

# 2. Route 53 private hosted zone not associated with VPC
aws route53 associate-vpc-with-hosted-zone \
    --hosted-zone-id $PRIVATE_ZONE_ID \
    --vpc VPCRegion=us-east-1,VPCId=$VPC_ID
```

---

## NACLs

```bash
# NACLs are stateless — must allow both inbound AND outbound (including ephemeral ports)
# Ephemeral ports: 1024-65535 (client side of TCP connection)

# Check NACL for a subnet
aws ec2 describe-network-acls \
    --filters Name=association.subnet-id,Values=$SUBNET_ID \
    --query 'NetworkAcls[0].{
        Inbound:Entries[?!Egress]|[*].{Rule:RuleNumber,Action:RuleAction,CIDR:CidrBlock,Port:PortRange},
        Outbound:Entries[?Egress]|[*].{Rule:RuleNumber,Action:RuleAction,CIDR:CidrBlock,Port:PortRange}
    }'

# Most common NACL mistake: blocked ephemeral ports outbound
# Fix: ensure outbound rule allows 1024-65535 from 0.0.0.0/0

aws ec2 create-network-acl-entry \
    --network-acl-id $NACL_ID \
    --rule-number 900 \
    --protocol tcp \
    --rule-action allow \
    --egress \
    --cidr-block 0.0.0.0/0 \
    --port-range From=1024,To=65535
```

---

## ALB Troubleshooting

```bash
# Check ALB target health
TARGET_GROUP_ARN="arn:aws:elasticloadbalancing:..."

aws elbv2 describe-target-health \
    --target-group-arn $TARGET_GROUP_ARN \
    --query 'TargetHealthDescriptions[*].{
        Target:Target.Id,
        Port:Target.Port,
        State:TargetHealth.State,
        Reason:TargetHealth.Reason,
        Description:TargetHealth.Description
    }'

# Common reasons for unhealthy targets:
# - Target.ResponseCodeMismatch → health check returns non-200
# - Target.Timeout → health check endpoint too slow
# - Target.FailedHealthChecks → target not listening on health check port
# - Elb.InternalError → ALB internal issue

# Check ALB access logs (must be enabled first)
aws s3 ls s3://alb-logs-bucket/alb/AWSLogs/$ACCOUNT_ID/elasticloadbalancing/$REGION/

# Query ALB logs for 5xx errors
aws athena start-query-execution \
    --query-string "
        SELECT elb_status_code, request_url, COUNT(*) as count
        FROM alb_logs
        WHERE elb_status_code >= 500
          AND time > date_add('hour', -1, now())
        GROUP BY 1, 2
        ORDER BY count DESC
        LIMIT 20
    " \
    --query-execution-context Database=alb_logs \
    --result-configuration "OutputLocation=s3://query-results/"
```

---

## References

- [AWS VPC troubleshooting guide](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-troubleshooting.html)
- [VPC Reachability Analyzer](https://docs.aws.amazon.com/vpc/latest/reachability/)
- [Route 53 DNS troubleshooting](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/troubleshooting-new-dns-settings-not-in-effect.html)

---

← [Previous: Troubleshooting Overview](./README.md) | [Home](../README.md) | [Next: Containers & Kubernetes →](./containers-k8s.md)
