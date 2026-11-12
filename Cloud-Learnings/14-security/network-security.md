← [Previous: IAM & Least Privilege](./iam-least-privilege.md) | [Home](../README.md) | [Next: Secrets Management →](./secrets-management.md)

---

# Network Security

Defence-in-depth for cloud networks means layering controls: VPC isolation, security groups, NACLs, WAF, DDoS protection, and private endpoints.

---

## VPC Design Principles

```
┌─────────────────────────────────────────────────────────┐
│  VPC 10.0.0.0/16                                        │
│                                                         │
│  ┌─── Public subnets ─────────────────────────────┐    │
│  │  Load balancer, NAT Gateway (no app code here) │    │
│  │  10.0.0.0/24  10.0.1.0/24  10.0.2.0/24        │    │
│  └────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─── Private subnets ────────────────────────────┐    │
│  │  Application servers, Kubernetes nodes         │    │
│  │  10.0.10.0/24  10.0.11.0/24  10.0.12.0/24     │    │
│  └────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─── Data subnets ───────────────────────────────┐    │
│  │  Databases, cache — no route to internet       │    │
│  │  10.0.20.0/24  10.0.21.0/24  10.0.22.0/24     │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## AWS Security Groups

```bash
# Create security group for ALB (public-facing)
aws ec2 create-security-group \
    --group-name sg-alb-prod \
    --description "ALB — allow HTTPS from internet" \
    --vpc-id vpc-12345678

ALB_SG="sg-alb-prod-id"

# ALB: allow HTTPS in, deny everything else
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG \
    --protocol tcp --port 443 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG \
    --protocol tcp --port 80 --cidr 0.0.0.0/0

# App tier: only from ALB SG (no CIDR!)
APP_SG="sg-app-prod-id"
aws ec2 authorize-security-group-ingress \
    --group-id $APP_SG \
    --protocol tcp --port 8080 \
    --source-group $ALB_SG

# DB tier: only from App SG
DB_SG="sg-db-prod-id"
aws ec2 authorize-security-group-ingress \
    --group-id $DB_SG \
    --protocol tcp --port 5432 \
    --source-group $APP_SG

# Deny all outbound except required services
aws ec2 revoke-security-group-egress \
    --group-id $APP_SG \
    --protocol -1 --port -1 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-egress \
    --group-id $APP_SG \
    --protocol tcp --port 443 --cidr 0.0.0.0/0   # HTTPS to AWS APIs

aws ec2 authorize-security-group-egress \
    --group-id $APP_SG \
    --protocol tcp --port 5432 --source-group $DB_SG
```

### AWS Network ACLs (Stateless)

```bash
# NACLs evaluate all rules, lowest number first, stateless (return traffic needs explicit allow)
# Use for coarse-grained subnet-level blocking (e.g., block entire countries via IP ranges)

# Block a known malicious CIDR
aws ec2 create-network-acl-entry \
    --network-acl-id acl-12345678 \
    --rule-number 90 \
    --protocol -1 \
    --rule-action deny \
    --cidr-block 198.51.100.0/24 \
    --egress false
```

---

## WAF (Web Application Firewall)

### AWS WAF

```bash
# Create a WAF Web ACL
aws wafv2 create-web-acl \
    --name my-app-waf \
    --scope REGIONAL \
    --region us-east-1 \
    --default-action Allow={} \
    --rules file://waf-rules.json \
    --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=MyAppWAF

# Associate with ALB
ALB_ARN="arn:aws:elasticloadbalancing:..."
WAF_ARN="arn:aws:wafv2:us-east-1:123456789012:regional/webacl/my-app-waf/abc123"

aws wafv2 associate-web-acl \
    --web-acl-arn $WAF_ARN \
    --resource-arn $ALB_ARN \
    --region us-east-1
```

```json
// waf-rules.json
[
    {
        "Name": "AWSManagedRulesCommonRuleSet",
        "Priority": 1,
        "Statement": {
            "ManagedRuleGroupStatement": {
                "VendorName": "AWS",
                "Name": "AWSManagedRulesCommonRuleSet",
                "ExcludedRules": []
            }
        },
        "OverrideAction": {"None": {}},
        "VisibilityConfig": {
            "SampledRequestsEnabled": true,
            "CloudWatchMetricsEnabled": true,
            "MetricName": "CommonRuleSet"
        }
    },
    {
        "Name": "AWSManagedRulesKnownBadInputsRuleSet",
        "Priority": 2,
        "Statement": {
            "ManagedRuleGroupStatement": {
                "VendorName": "AWS",
                "Name": "AWSManagedRulesKnownBadInputsRuleSet"
            }
        },
        "OverrideAction": {"None": {}},
        "VisibilityConfig": {
            "SampledRequestsEnabled": true,
            "CloudWatchMetricsEnabled": true,
            "MetricName": "KnownBadInputs"
        }
    },
    {
        "Name": "RateLimitRule",
        "Priority": 10,
        "Statement": {
            "RateBasedStatement": {
                "Limit": 2000,
                "AggregateKeyType": "IP"
            }
        },
        "Action": {"Block": {}},
        "VisibilityConfig": {
            "SampledRequestsEnabled": true,
            "CloudWatchMetricsEnabled": true,
            "MetricName": "RateLimit"
        }
    }
]
```

---

## Private Endpoints / VPC Endpoints

```bash
# AWS VPC Endpoint — keep S3 traffic inside AWS network (no internet gateway)
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-12345678 \
    --service-name com.amazonaws.us-east-1.s3 \
    --vpc-endpoint-type Gateway \
    --route-table-ids rtb-12345678

# Interface endpoint for Secrets Manager (uses PrivateLink — costs $)
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-12345678 \
    --service-name com.amazonaws.us-east-1.secretsmanager \
    --vpc-endpoint-type Interface \
    --subnet-ids subnet-private-1 subnet-private-2 \
    --security-group-ids sg-app-prod-id \
    --private-dns-enabled

# Services that should use VPC endpoints in production:
# S3, DynamoDB (Gateway — free), SSM, Secrets Manager, KMS, ECR, STS,
# CloudWatch Logs, SQS, SNS (Interface — $0.01/hr/AZ)
```

---

## TLS Everywhere

```bash
# AWS: Force HTTPS redirect on ALB
aws elbv2 create-rule \
    --listener-arn $HTTP_LISTENER_ARN \
    --conditions '[{"Field":"path-pattern","PathPatternConfig":{"Values":["/*"]}}]' \
    --priority 1 \
    --actions '[{"Type":"redirect","RedirectConfig":{"Protocol":"HTTPS","Port":"443","StatusCode":"HTTP_301"}}]'

# AWS: Require TLS 1.2+ on ALB
aws elbv2 modify-listener \
    --listener-arn $HTTPS_LISTENER_ARN \
    --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06

# Check TLS configuration
openssl s_client -connect api.my-app.com:443 \
    -tls1_2 -brief 2>/dev/null | head -5

# Test cipher suites
nmap --script ssl-enum-ciphers -p 443 api.my-app.com
```

---

## DDoS Protection

```bash
# AWS Shield Standard is automatic (free) for all AWS accounts
# AWS Shield Advanced (paid) adds 24/7 DRT support + cost protection

# Enable Shield Advanced
aws shield create-subscription

# Protect a resource (ALB, CloudFront, EIP, Route 53)
aws shield create-protection \
    --name my-app-alb \
    --resource-arn $ALB_ARN

# GCP: Cloud Armor Adaptive Protection (see 07-gcp/09-security/cloud-armor.md)
# Azure: DDoS Protection Standard — enable on VNet
az network ddos-protection create \
    --name my-app-ddos-plan \
    --resource-group rg-production \
    --location eastus

az network vnet update \
    --name vnet-production \
    --resource-group rg-production \
    --ddos-protection true \
    --ddos-protection-plan my-app-ddos-plan
```

---

## Network Flow Logs

```bash
# AWS VPC Flow Logs — capture all traffic metadata
aws ec2 create-flow-logs \
    --resource-type VPC \
    --resource-ids vpc-12345678 \
    --traffic-type ALL \
    --log-destination-type cloud-watch-logs \
    --log-group-name /aws/vpc/flow-logs \
    --deliver-logs-permission-arn arn:aws:iam::123456789012:role/FlowLogsRole

# Query flow logs in Athena
# SELECT sourceaddress, destinationaddress, destinationport, action, count(*)
# FROM vpc_flow_logs
# WHERE action = 'REJECT'
# GROUP BY 1,2,3,4
# ORDER BY 5 DESC
# LIMIT 50;

# GCP VPC Flow Logs
gcloud compute networks subnets update subnet-private-prod \
    --region=us-central1 \
    --enable-flow-logs \
    --logging-aggregation-interval=INTERVAL_5_SEC \
    --logging-flow-sampling=0.5 \
    --logging-metadata=INCLUDE_ALL_METADATA
```

---

## References

- [AWS VPC security best practices](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-best-practices.html)
- [AWS WAF documentation](https://docs.aws.amazon.com/waf/latest/developerguide/)
- [GCP Cloud Armor](https://cloud.google.com/armor/docs)
- [Azure DDoS Protection](https://learn.microsoft.com/en-us/azure/ddos-protection/)
- [OWASP Network Security Cheat Sheet](https://cheatsheetseries.owasp.org/)

---

← [Previous: IAM & Least Privilege](./iam-least-privilege.md) | [Home](../README.md) | [Next: Secrets Management →](./secrets-management.md)
