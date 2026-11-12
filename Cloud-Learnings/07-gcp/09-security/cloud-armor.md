← [Previous: Cloud KMS](./cloud-kms.md) | [Home](../../README.md) | [Next: VPC Service Controls →](./vpc-service-controls.md)

---

# Cloud Armor

Cloud Armor is GCP's DDoS protection and Web Application Firewall (WAF) service. It integrates with Cloud Load Balancing to protect HTTP/S applications.

---

## Security Policies

```bash
PROJECT="my-app-prod-123456"

# Create a security policy (backend service attachment)
gcloud compute security-policies create waf-my-app \
    --project=$PROJECT \
    --description="WAF policy for my-app production" \
    --type=CLOUD_ARMOR

# Attach to a backend service
gcloud compute backend-services update bs-my-app \
    --project=$PROJECT \
    --global \
    --security-policy=waf-my-app
```

---

## Rules

Cloud Armor rules are evaluated in priority order (lowest number = highest priority). The default rule (priority 2147483647) is always present.

```bash
POLICY="waf-my-app"

# --- IP allowlist: only allow trusted CIDRs ---
gcloud compute security-policies rules create 100 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --action=allow \
    --src-ip-ranges="10.0.0.0/8,203.0.113.0/24" \
    --description="Allow internal + office IP ranges"

# --- Geo-block: block requests from specific countries ---
gcloud compute security-policies rules create 200 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --action=deny-403 \
    --expression="origin.region_code == 'XX' || origin.region_code == 'YY'" \
    --description="Block traffic from regions XX and YY"

# --- Allow only specific countries ---
gcloud compute security-policies rules create 300 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --action=deny-403 \
    --expression="!( origin.region_code == 'US' || origin.region_code == 'GB' || origin.region_code == 'CA' )" \
    --description="Only allow US, GB, CA traffic"

# --- Rate limiting: 100 req/min per IP ---
gcloud compute security-policies rules create 400 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --action=rate-based-ban \
    --src-ip-ranges="*" \
    --rate-limit-threshold-count=100 \
    --rate-limit-threshold-interval-sec=60 \
    --ban-duration-sec=300 \
    --conform-action=allow \
    --exceed-action=deny-429 \
    --enforce-on-key=IP \
    --description="Rate limit: 100 req/min per IP, ban 5 min if exceeded"

# --- Stricter rate limit for login endpoint ---
gcloud compute security-policies rules create 500 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --action=rate-based-ban \
    --expression="request.path.startsWith('/api/v1/auth')" \
    --rate-limit-threshold-count=10 \
    --rate-limit-threshold-interval-sec=60 \
    --ban-duration-sec=600 \
    --conform-action=allow \
    --exceed-action=deny-429 \
    --enforce-on-key=IP \
    --description="Strict rate limit on auth endpoints"

# --- OWASP WAF rules (preconfigured rule sets) ---
# CRS 3.3 — covers SQLi, XSS, RFI, LFI, etc.
gcloud compute security-policies rules create 1000 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --action=deny-403 \
    --expression="evaluatePreconfiguredWaf('sqli-v33-stable', {'sensitivity': 2})" \
    --description="Block SQL injection (sensitivity 2)"

gcloud compute security-policies rules create 1010 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --action=deny-403 \
    --expression="evaluatePreconfiguredWaf('xss-v33-stable', {'sensitivity': 1})" \
    --description="Block XSS (sensitivity 1)"

gcloud compute security-policies rules create 1020 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --action=deny-403 \
    --expression="evaluatePreconfiguredWaf('rce-v33-stable')" \
    --description="Block remote code execution"

gcloud compute security-policies rules create 1030 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --action=deny-403 \
    --expression="evaluatePreconfiguredWaf('lfi-v33-stable')" \
    --description="Block local file inclusion"

# --- Default rule: allow all other traffic ---
gcloud compute security-policies rules update 2147483647 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --action=allow

# List all rules in a policy
gcloud compute security-policies describe $POLICY \
    --project=$PROJECT \
    --format="json(rules)"
```

---

## Adaptive Protection (ML-based DDoS)

```bash
# Enable Adaptive Protection
gcloud compute security-policies update $POLICY \
    --project=$PROJECT \
    --enable-layer7-ddos-defense

# Set auto-deploy threshold (0.5 = medium confidence, 0.95 = high confidence)
gcloud compute security-policies update $POLICY \
    --project=$PROJECT \
    --layer7-ddos-defense-auto-deploy-load-threshold=0.7 \
    --layer7-ddos-defense-auto-deploy-confidence-threshold=0.85 \
    --layer7-ddos-defense-auto-deploy-impacted-baseline-threshold=0.01 \
    --layer7-ddos-defense-auto-deploy-expiration-sec=3600
```

---

## Named IP Lists

```bash
# Use a named IP list (e.g., Tor exit nodes, known scanners)
gcloud compute security-policies rules create 150 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --action=deny-403 \
    --expression="inIpRange(origin.ip, '0.0.0.0/0') && evaluateThreatIntelligence('iplist-tor-exit-nodes')" \
    --description="Block Tor exit nodes"

# Other named lists: iplist-known-malicious-ips, iplist-crawler-ips, iplist-anon-vpn
```

---

## Preview Mode (Test Rules Without Blocking)

```bash
# Set a rule to preview mode
gcloud compute security-policies rules update 1000 \
    --project=$PROJECT \
    --security-policy=$POLICY \
    --preview \
    --description="SQLi rule in preview — evaluate before enforcing"

# Check preview mode hits in Cloud Logging:
# resource.type="http_load_balancer"
# jsonPayload.enforcedSecurityPolicy.outcome="PREVIEW"
```

---

## References

- [Cloud Armor documentation](https://cloud.google.com/armor/docs)
- [WAF rule tuning](https://cloud.google.com/armor/docs/rule-tuning)
- [Adaptive Protection](https://cloud.google.com/armor/docs/adaptive-protection-overview)
- [Named IP lists](https://cloud.google.com/armor/docs/threat-intelligence)

---

← [Previous: Cloud KMS](./cloud-kms.md) | [Home](../../README.md) | [Next: VPC Service Controls →](./vpc-service-controls.md)
