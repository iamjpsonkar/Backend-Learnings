← [Previous: Security Hub](./security-hub.md) | [Home](../../README.md) | [Next: AWS Observability →](../10-observability/README.md)

---

# AWS WAF and Shield

WAF (Web Application Firewall) protects HTTP/HTTPS applications against common web exploits at Layer 7. Shield protects against DDoS attacks at Layers 3, 4, and 7. They are complementary services, commonly deployed together on CloudFront, ALB, and API Gateway.

---

## AWS WAF

### Core Concepts

| Concept | Meaning |
|---------|---------|
| **Web ACL** | A collection of rules applied to a resource (CloudFront, ALB, API Gateway, AppSync, Cognito) |
| **Rule** | A condition + action (Allow, Block, Count, CAPTCHA, Challenge) |
| **Rule group** | A named, reusable collection of rules (AWS Managed, Marketplace, or custom) |
| **Managed rule group** | Pre-built rules maintained by AWS or AWS Marketplace partners |
| **Statement** | The matching logic: IP set, geo match, regex, rate-based, SQL injection, XSS, size constraint |
| **WCU** | Web ACL Capacity Unit — rules consume WCU; default limit: 1,500 per web ACL |
| **Scope** | REGIONAL (ALB, API Gateway, AppSync) or CLOUDFRONT (must be created in us-east-1) |

---

### Creating a Web ACL

```bash
# Create a web ACL for an ALB (regional)
WEBACL_ARN=$(aws wafv2 create-web-acl \
    --scope REGIONAL \
    --region us-east-1 \
    --name my-app-waf \
    --default-action Allow={} \
    --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=my-app-waf \
    --description "WAF for my-app ALB" \
    --tags Key=Environment,Value=production \
    --rules '[
        {
            "Name": "AWSManagedRulesCommonRuleSet",
            "Priority": 10,
            "OverrideAction": {"None": {}},
            "Statement": {
                "ManagedRuleGroupStatement": {
                    "VendorName": "AWS",
                    "Name": "AWSManagedRulesCommonRuleSet"
                }
            },
            "VisibilityConfig": {
                "SampledRequestsEnabled": true,
                "CloudWatchMetricsEnabled": true,
                "MetricName": "AWSManagedRulesCommonRuleSet"
            }
        },
        {
            "Name": "AWSManagedRulesKnownBadInputsRuleSet",
            "Priority": 20,
            "OverrideAction": {"None": {}},
            "Statement": {
                "ManagedRuleGroupStatement": {
                    "VendorName": "AWS",
                    "Name": "AWSManagedRulesKnownBadInputsRuleSet"
                }
            },
            "VisibilityConfig": {
                "SampledRequestsEnabled": true,
                "CloudWatchMetricsEnabled": true,
                "MetricName": "AWSManagedRulesKnownBadInputsRuleSet"
            }
        },
        {
            "Name": "AWSManagedRulesSQLiRuleSet",
            "Priority": 30,
            "OverrideAction": {"None": {}},
            "Statement": {
                "ManagedRuleGroupStatement": {
                    "VendorName": "AWS",
                    "Name": "AWSManagedRulesSQLiRuleSet"
                }
            },
            "VisibilityConfig": {
                "SampledRequestsEnabled": true,
                "CloudWatchMetricsEnabled": true,
                "MetricName": "AWSManagedRulesSQLiRuleSet"
            }
        }
    ]' \
    --query 'Summary.ARN' --output text)

echo "Web ACL: $WEBACL_ARN"
```

### AWS Managed Rule Groups

```bash
# List all available AWS managed rule groups
aws wafv2 list-available-managed-rule-groups \
    --scope REGIONAL \
    --query 'ManagedRuleGroups[?VendorName==`AWS`].{Name:Name,Description:Description,Capacity:EstimatedCapacity}' \
    --output table
```

Key AWS managed rule groups:

| Rule Group | WCU | Protects against |
|-----------|-----|-----------------|
| `AWSManagedRulesCommonRuleSet` | 700 | OWASP Top 10 — XSS, path traversal, SSRF |
| `AWSManagedRulesKnownBadInputsRuleSet` | 200 | Log4Shell, Spring4Shell, local file inclusion |
| `AWSManagedRulesSQLiRuleSet` | 200 | SQL injection |
| `AWSManagedRulesLinuxRuleSet` | 200 | Linux-specific attacks |
| `AWSManagedRulesAmazonIpReputationList` | 25 | Amazon IP reputation (bots, scrapers) |
| `AWSManagedRulesAnonymousIpList` | 50 | Tor, VPNs, proxies |
| `AWSManagedRulesBotControlRuleSet` | 150 | Bot detection and mitigation |

### Custom Rules

```bash
WEBACL_ID=$(aws wafv2 list-web-acls --scope REGIONAL \
    --query "WebACLs[?Name=='my-app-waf'].Id" --output text)
WEBACL_LOCK=$(aws wafv2 get-web-acl --id $WEBACL_ID --name my-app-waf --scope REGIONAL \
    --query 'LockToken' --output text)

# Add custom rules via update-web-acl — include all existing rules + new ones
# Rule: Rate limit by IP — block if >1000 req/5min
# Rule: Block specific countries
# Rule: Block specific IP set

# Create an IP set (e.g., allowed office CIDRs)
IPSET_ARN=$(aws wafv2 create-ip-set \
    --scope REGIONAL \
    --name allow-office-ips \
    --ip-address-version IPV4 \
    --addresses "203.0.113.0/24" "198.51.100.0/24" \
    --query 'Summary.ARN' --output text)

# Rate-based rule (blocks IPs sending > 1000 requests in 5 minutes)
RATE_RULE='{
    "Name": "RateLimitByIP",
    "Priority": 5,
    "Action": {"Block": {}},
    "Statement": {
        "RateBasedStatement": {
            "Limit": 1000,
            "AggregateKeyType": "IP"
        }
    },
    "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimitByIP"
    }
}'

# Geo-block rule (block specific countries)
GEO_RULE='{
    "Name": "BlockHighRiskCountries",
    "Priority": 15,
    "Action": {"Block": {}},
    "Statement": {
        "GeoMatchStatement": {
            "CountryCodes": ["XX", "YY"]
        }
    },
    "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "BlockHighRiskCountries"
    }
}'
```

### Associating Web ACL with Resources

```bash
ALB_ARN="arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/abc123"

# Associate with ALB
aws wafv2 associate-web-acl \
    --web-acl-arn $WEBACL_ARN \
    --resource-arn $ALB_ARN

# Associate with API Gateway stage
API_GW_ARN="arn:aws:apigateway:us-east-1::/restapis/API_ID/stages/prod"
aws wafv2 associate-web-acl \
    --web-acl-arn $WEBACL_ARN \
    --resource-arn $API_GW_ARN

# For CloudFront: use scope=CLOUDFRONT from us-east-1 and set in the distribution config
# (web ACL must be created in us-east-1)

# List resources protected by a web ACL
aws wafv2 list-resources-for-web-acl \
    --web-acl-arn $WEBACL_ARN
```

### WAF Logging

```bash
# Enable WAF logging to Kinesis Firehose → S3
aws wafv2 put-logging-configuration \
    --logging-configuration '{
        "ResourceArn": "'$WEBACL_ARN'",
        "LogDestinationConfigs": [
            "arn:aws:firehose:us-east-1:123456789012:deliverystream/waf-logs"
        ],
        "RedactedFields": [
            {"SingleHeader": {"Name": "authorization"}}
        ]
    }'

# Query WAF logs with Athena (after ingesting to S3)
# Sample Athena query to find blocked requests:
# SELECT timestamp, httprequest.clientip, httprequest.uri, terminatingruleid
# FROM waf_logs
# WHERE action = 'BLOCK'
# ORDER BY timestamp DESC
# LIMIT 100;
```

---

## AWS Shield

### Shield Standard (Free, Always On)

Shield Standard is automatically active on all AWS accounts. It protects against:
- Layer 3/4 volumetric attacks (UDP flood, SYN flood, DNS amplification)
- State exhaustion attacks against EC2 and ELB
- Route 53, CloudFront, Global Accelerator — automatic DDoS mitigation

No configuration required. Not visible in the console.

### Shield Advanced

Shield Advanced provides enhanced protection, 24/7 access to the DDoS Response Team (DRT), cost protection, and real-time attack metrics.

```bash
# Subscribe to Shield Advanced ($3,000/month — covers all resources in the account)
aws shield create-subscription

# Verify subscription
aws shield describe-subscription \
    --query 'Subscription.{Status:SubscriptionState,StartTime:StartTime,End:EndTime}'

# Enable proactive engagement (DRT contacts you during potential events)
aws shield update-proactive-engagement --proactive-engagement-status ENABLED

aws shield associate-proactive-engagement-details \
    --emergency-contact-list \
        EmailAddress=security-oncall@example.com,PhoneNumber="+12025551234",ContactNotes="Primary SOC contact" \
        EmailAddress=backup-oncall@example.com,PhoneNumber="+12025555678",ContactNotes="Backup contact"

# Protect specific resources
aws shield create-protection \
    --name my-alb-protection \
    --resource-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/abc123

aws shield create-protection \
    --name my-cloudfront-protection \
    --resource-arn arn:aws:cloudfront::123456789012:distribution/E1234ABCDEFGH

# List protected resources
aws shield list-protections \
    --query 'Protections[*].{Name:Name,Resource:ResourceArn,ID:Id}' \
    --output table

# Associate WAF web ACL with Shield Advanced protection (enhanced L7 protection)
PROTECTION_ID=$(aws shield list-protections \
    --query 'Protections[?Name==`my-alb-protection`].Id' --output text)

aws shield associate-drt-role \
    --role-arn arn:aws:iam::123456789012:role/AWSShieldDRTAccessPolicy

# View attacks
aws shield list-attacks \
    --start-time StartTime=$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-7d +%Y-%m-%dT%H:%M:%SZ) \
    --end-time EndTime=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --query 'AttackSummaries[*].{ID:AttackId,Start:StartTime,Resource:ResourceArn[0]}' \
    --output table
```

---

## WAF + Shield Deployment Pattern

```
Internet
   │
   ▼
Route 53 (latency / geolocation routing)
   │
   ▼
CloudFront (Edge — Shield Standard + WAF web ACL scope=CLOUDFRONT)
   │
   ▼
ALB (Regional — Shield Advanced + WAF web ACL scope=REGIONAL)
   │
   ▼
EC2 / ECS / Lambda (Security Groups — no direct internet exposure)
```

**Best practices:**
1. Deploy CloudFront in front of ALB and restrict ALB to CloudFront IPs only (via WAF IP set or Security Group with CloudFront managed prefix list)
2. Attach AWS Managed Rules in Count mode first; review sampled requests; switch to Block
3. Enable WAF logging — route to S3 via Firehose + create Athena table for ad-hoc analysis
4. Use Shield Advanced if you run a high-profile or latency-sensitive service

---

## References

- [WAF documentation](https://docs.aws.amazon.com/waf/latest/developerguide/)
- [AWS Managed Rules](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-list.html)
- [Shield Advanced](https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html)
- [WAF pricing](https://aws.amazon.com/waf/pricing/)
---

← [Previous: Security Hub](./security-hub.md) | [Home](../../README.md) | [Next: AWS Observability →](../10-observability/README.md)
