← [Previous: Cloud Armor](./cloud-armor.md) | [Home](../../README.md) | [Next: GCP Observability →](../10-observability/README.md)

---

# VPC Service Controls

VPC Service Controls (VPC-SC) creates security perimeters around GCP resources to prevent data exfiltration. Resources inside a perimeter can communicate with each other, but cannot be accessed from outside without explicit access policies.

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Access policy** | Organization-level container for all perimeters and access levels |
| **Service perimeter** | Boundary protecting a set of GCP resources/services |
| **Access level** | Conditions under which principals can cross a perimeter (IP range, device trust, etc.) |
| **Restricted services** | GCP APIs restricted within the perimeter |
| **Perimeter bridges** | Allows controlled communication between two perimeters |

---

## Setup

```bash
PROJECT="my-app-prod-123456"
ORG_ID="123456789012"
POLICY_NAME="my-org-access-policy"

# Create an access policy (one per organization)
gcloud access-context-manager policies create \
    --organization=$ORG_ID \
    --title="My Org Access Policy"

# Get the policy name (e.g., accessPolicies/1234567890)
POLICY=$(gcloud access-context-manager policies list \
    --organization=$ORG_ID \
    --format="value(name)")

echo "Policy: $POLICY"
```

---

## Access Levels

```bash
# Create an access level based on IP range (e.g., corporate network)
gcloud access-context-manager levels create corporate-network \
    --policy=$POLICY \
    --title="Corporate Network" \
    --basic-level-spec=conditions.yaml

# conditions.yaml:
# conditions:
# - ipSubnetworks:
#   - "203.0.113.0/24"
#   - "10.0.0.0/8"
#   requireScreenlock: false

# Create an access level based on device trust (requires Endpoint Verification)
cat > device-trust.yaml <<EOF
conditions:
- devicePolicy:
    requireScreenlock: true
    allowedEncryptionStatuses:
    - ENCRYPTED
    osConstraints:
    - osType: DESKTOP_MAC
      minimumVersion: "14.0"
    - osType: DESKTOP_WINDOWS
      minimumVersion: "10"
    requireAdminApproval: false
    requireCorpOwned: true
EOF

gcloud access-context-manager levels create corp-device \
    --policy=$POLICY \
    --title="Corp-Managed Device" \
    --basic-level-spec=device-trust.yaml

# List access levels
gcloud access-context-manager levels list \
    --policy=$POLICY \
    --format="table(name,title,basic.conditions)"
```

---

## Service Perimeters

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format="value(projectNumber)")

# Create a perimeter protecting BigQuery and Cloud Storage
gcloud access-context-manager perimeters create my-app-perimeter \
    --policy=$POLICY \
    --title="My App Data Perimeter" \
    --resources=projects/$PROJECT_NUMBER \
    --restricted-services="bigquery.googleapis.com,storage.googleapis.com,secretmanager.googleapis.com" \
    --access-levels="$POLICY/accessLevels/corporate-network"

# Dry-run mode first (simulate — doesn't block traffic yet)
gcloud access-context-manager perimeters create my-app-perimeter-dryrun \
    --policy=$POLICY \
    --title="My App Data Perimeter (Dry Run)" \
    --resources=projects/$PROJECT_NUMBER \
    --restricted-services="bigquery.googleapis.com,storage.googleapis.com" \
    --perimeter-type=regular

# Enable enforcement (convert dry-run to enforced)
gcloud access-context-manager perimeters update my-app-perimeter \
    --policy=$POLICY \
    --enable-restriction

# Add a project to an existing perimeter
gcloud access-context-manager perimeters update my-app-perimeter \
    --policy=$POLICY \
    --add-resources=projects/$PROJECT_NUMBER

# List perimeters
gcloud access-context-manager perimeters list \
    --policy=$POLICY \
    --format="table(name,title,status.resources,status.restrictedServices)"
```

---

## Ingress and Egress Rules

```yaml
# ingress-rule.yaml — allow specific SA to access BigQuery from outside perimeter
ingressPolicies:
- ingressFrom:
    identities:
    - serviceAccount:sa-analytics@external-project.iam.gserviceaccount.com
    sources:
    - resource: projects/external-project-number
  ingressTo:
    operations:
    - serviceName: bigquery.googleapis.com
      methodSelectors:
      - method: "*"
    resources:
    - projects/my-app-prod-123456

# egress-rule.yaml — allow Cloud Run to call an API outside the perimeter
egressPolicies:
- egressFrom:
    identities:
    - serviceAccount:sa-my-app@my-app-prod-123456.iam.gserviceaccount.com
  egressTo:
    operations:
    - serviceName: api.googleapis.com
      methodSelectors:
      - method: "*"
    resources:
    - "*"
```

```bash
# Apply ingress/egress policies to a perimeter
gcloud access-context-manager perimeters update my-app-perimeter \
    --policy=$POLICY \
    --set-ingress-policies=ingress-rule.yaml \
    --set-egress-policies=egress-rule.yaml
```

---

## Monitoring VPC-SC Violations

```bash
# VPC-SC violations appear in Cloud Logging with protoPayload.status.code=403
# and methodName matching restricted service API calls.
#
# Log query to find violations:
# resource.type="audited_resource"
# protoPayload.status.code=403
# protoPayload.metadata."@type"="type.googleapis.com/google.cloud.audit.VpcServiceControlAuditMetadata"

# Create a log-based metric for violations
gcloud logging metrics create vpc-sc-violations \
    --project=$PROJECT \
    --description="Count of VPC Service Controls access denials" \
    --log-filter='protoPayload.status.code=403 AND protoPayload.metadata."@type"="type.googleapis.com/google.cloud.audit.VpcServiceControlAuditMetadata"'
```

---

## References

- [VPC Service Controls documentation](https://cloud.google.com/vpc-service-controls/docs)
- [Configuring perimeters](https://cloud.google.com/vpc-service-controls/docs/create-service-perimeters)
- [Access levels](https://cloud.google.com/access-context-manager/docs/create-basic-access-level)
- [Ingress/egress rules](https://cloud.google.com/vpc-service-controls/docs/ingress-egress-rules)

---

← [Previous: Cloud Armor](./cloud-armor.md) | [Home](../../README.md) | [Next: GCP Observability →](../10-observability/README.md)
