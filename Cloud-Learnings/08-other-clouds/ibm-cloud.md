← [Previous: OCI](./oci.md) | [Home](../README.md) | [Next: Alibaba Cloud →](./alibaba-cloud.md)

---

# IBM Cloud

IBM Cloud is positioned for hybrid and multicloud enterprise workloads, regulated industries (financial services, healthcare), and AI via the watsonx platform. It integrates tightly with IBM's on-premises portfolio (IBM Z, Power, Db2).

---

## Key Differentiators

| Feature | Detail |
|---------|--------|
| **Financial Services Cloud** | Compliance-ready platform with pre-configured controls for FFIEC, PCI-DSS, SOC 2 |
| **Red Hat OpenShift** | Managed OpenShift (ROKS) — enterprise Kubernetes with developer tools |
| **watsonx** | Enterprise AI platform — watsonx.ai (model training/inference), watsonx.data (lakehouse), watsonx.governance |
| **IBM Z integration** | Hybrid connectivity to IBM Z (mainframe) and Power systems |
| **Satellite** | Run IBM Cloud services on any infrastructure (on-prem, edge, other clouds) |

---

## Service Equivalents

| AWS | IBM Cloud |
|-----|-----------|
| EC2 | Virtual Server for VPC |
| VPC | VPC |
| S3 | Cloud Object Storage (COS) |
| RDS | Db2 on Cloud / Databases for PostgreSQL |
| Lambda | Code Engine (Functions / Jobs / Apps) |
| EKS | Red Hat OpenShift on IBM Cloud (ROKS) / IBM Kubernetes Service (IKS) |
| CloudWatch | IBM Cloud Monitoring (Sysdig) |
| CloudTrail | IBM Cloud Activity Tracker |
| Secrets Manager | Secrets Manager |
| KMS | Key Protect / Hyper Protect Crypto Services (HSM) |

---

## CLI Setup

```bash
# Install IBM Cloud CLI
curl -fsSL https://clis.cloud.ibm.com/install/linux | sh

# Log in
ibmcloud login --sso
# or with API key
ibmcloud login --apikey $IBM_CLOUD_API_KEY -r us-south

# Target resource group and region
ibmcloud target -g production -r us-south

# Install essential plugins
ibmcloud plugin install vpc-infrastructure
ibmcloud plugin install container-service
ibmcloud plugin install code-engine
ibmcloud plugin install cloud-object-storage
ibmcloud plugin install key-protect

# List plugins
ibmcloud plugin list

# List regions
ibmcloud regions
```

---

## Resource Groups

IBM Cloud uses **resource groups** to organize and manage access to resources.

```bash
# Create a resource group
ibmcloud resource group-create production

# Target the resource group for subsequent commands
ibmcloud target -g production

# List resource groups
ibmcloud resource groups

# List all resources in the current resource group
ibmcloud resource service-instances
```

---

## VPC and Networking

```bash
REGION="us-south"
ZONE="us-south-1"

# Create a VPC
ibmcloud is vpc-create vpc-my-app-prod \
    --resource-group-name production

VPC_ID=$(ibmcloud is vpcs --output json | jq -r '.[] | select(.name=="vpc-my-app-prod") | .id')

# Create subnets
ibmcloud is subnet-create snet-app-us-south-1 $VPC_ID \
    --zone $ZONE \
    --ipv4-cidr-block 10.0.11.0/24

ibmcloud is subnet-create snet-data-us-south-1 $VPC_ID \
    --zone $ZONE \
    --ipv4-cidr-block 10.0.21.0/24

# Public gateway (allows outbound internet for private instances)
PGW_ID=$(ibmcloud is public-gateway-create pgw-my-app-prod $VPC_ID $ZONE \
    --output json | jq -r '.id')

# Attach public gateway to subnet
ibmcloud is subnet-update snet-app-us-south-1 --pgw $PGW_ID

# Security groups
SG_ID=$(ibmcloud is security-group-create sg-app-tier $VPC_ID \
    --output json | jq -r '.id')

# Allow inbound HTTPS
ibmcloud is security-group-rule-add $SG_ID inbound tcp \
    --port-min 443 --port-max 443 --remote 0.0.0.0/0

# Allow inbound HTTP (redirect)
ibmcloud is security-group-rule-add $SG_ID inbound tcp \
    --port-min 80 --port-max 80 --remote 0.0.0.0/0
```

---

## Virtual Servers

```bash
# List available profiles (instance types)
ibmcloud is instance-profiles --output table | head -20

# Key profiles
# cx2-2x4    — 2 vCPU, 4 GB (compute)
# bx2-4x16   — 4 vCPU, 16 GB (balanced)
# mx2-4x32   — 4 vCPU, 32 GB (memory)

SUBNET_ID=$(ibmcloud is subnets --output json | jq -r '.[] | select(.name=="snet-app-us-south-1") | .id')
IMAGE_ID=$(ibmcloud is images --output json | jq -r '[.[] | select(.name | contains("ibm-ubuntu-22-04"))] | .[0].id')

# Create an SSH key
ibmcloud is key-create my-app-key @~/.ssh/id_rsa.pub

# Create a virtual server
ibmcloud is instance-create vm-my-app-prod-001 $VPC_ID $ZONE bx2-4x16 $SUBNET_ID \
    --image $IMAGE_ID \
    --keys my-app-key \
    --security-group $SG_ID \
    --output json | jq '.id'

# List instances
ibmcloud is instances --output table

# Get instance details
ibmcloud is instance vm-my-app-prod-001

# Stop / start
ibmcloud is instance-stop vm-my-app-prod-001
ibmcloud is instance-start vm-my-app-prod-001
```

---

## Cloud Object Storage (COS)

```bash
# Create a COS instance
ibmcloud resource service-instance-create cos-my-app-prod \
    cloud-object-storage standard global \
    --resource-group-name production

# Create a bucket (using the COS plugin)
ibmcloud cos bucket-create \
    --bucket my-app-prod-assets \
    --region us-south \
    --ibm-service-instance-id $(ibmcloud resource service-instance cos-my-app-prod --output json | jq -r '.[0].guid')

# Upload an object
ibmcloud cos object-put \
    --bucket my-app-prod-assets \
    --key reports/2024/report.pdf \
    --body ./report.pdf \
    --content-type "application/pdf"

# List objects
ibmcloud cos objects --bucket my-app-prod-assets

# Generate a pre-signed URL (time-limited download link)
ibmcloud cos object-get-presigned-url \
    --bucket my-app-prod-assets \
    --key reports/2024/report.pdf \
    --expiry 3600
```

---

## Code Engine (Serverless)

IBM Code Engine runs containerized applications, batch jobs, and event-driven functions — all serverless, no cluster management.

```bash
# Create a project
ibmcloud ce project create --name my-app-prod

ibmcloud ce project select --name my-app-prod

# Deploy an application from a container image
ibmcloud ce application create \
    --name my-app-api \
    --image us.icr.io/my-namespace/my-app-api:v1.0.0 \
    --cpu 0.5 \
    --memory 1G \
    --min-scale 1 \
    --max-scale 50 \
    --concurrency 80 \
    --env APP_ENV=production \
    --env-from-secret my-app-secrets

# Create a secret for app config
ibmcloud ce secret create \
    --name my-app-secrets \
    --from-literal DATABASE_URL=postgres://user:pass@host/db

# Get the application URL
ibmcloud ce application get --name my-app-api --output json | jq -r '.status.url'

# Run a one-off job
ibmcloud ce job create \
    --name db-migration \
    --image us.icr.io/my-namespace/my-app-api:v1.0.0 \
    --command python \
    --argument "manage.py" \
    --argument "migrate"

ibmcloud ce jobrun submit --job db-migration

# List applications
ibmcloud ce application list

# View logs
ibmcloud ce application logs --name my-app-api --follow
```

---

## IBM Kubernetes Service (IKS) and OpenShift

```bash
# Create an IKS cluster (VPC Gen 2)
ibmcloud ks cluster create vpc-gen2 \
    --name iks-my-app-prod-us-south \
    --zone us-south-1 \
    --flavor bx2.4x16 \
    --workers 3 \
    --version 1.29 \
    --vpc-id $VPC_ID \
    --subnet-id $SUBNET_ID

# Get kubeconfig
ibmcloud ks cluster config --cluster iks-my-app-prod-us-south
kubectl get nodes

# Create a Red Hat OpenShift cluster
ibmcloud oc cluster create vpc-gen2 \
    --name roks-my-app-prod \
    --zone us-south-1 \
    --flavor bx2.4x16 \
    --workers 3 \
    --version 4.14_openshift \
    --vpc-id $VPC_ID \
    --subnet-id $SUBNET_ID

# Get oc CLI config
ibmcloud oc cluster config --cluster roks-my-app-prod --admin
oc get nodes
```

---

## Databases

```bash
# Provision a managed PostgreSQL database
ibmcloud resource service-instance-create pg-my-app-prod \
    databases-for-postgresql standard us-south \
    --resource-group-name production \
    -p '{"members_disk_allocation_mb": 20480, "members_memory_allocation_mb": 4096, "version": "15"}'

# Get connection strings
ibmcloud resource service-key-create pg-my-app-creds Administrator \
    --instance-name pg-my-app-prod

ibmcloud resource service-key pg-my-app-creds --output json | jq '.credentials.connection.postgres.composed[0]'
```

---

## Key Protect (KMS)

```bash
# Create a Key Protect instance
ibmcloud resource service-instance-create kp-my-app-prod kms tiered-pricing us-south \
    --resource-group-name production

KP_INSTANCE_ID=$(ibmcloud resource service-instance kp-my-app-prod --output json | jq -r '.[0].guid')

# Create a root key (used to envelope-encrypt data keys)
ibmcloud kp key create my-app-root-key \
    --instance-id $KP_INSTANCE_ID \
    --key-material "" \
    --root-key

# List keys
ibmcloud kp keys --instance-id $KP_INSTANCE_ID
```

---

## References

- [IBM Cloud documentation](https://cloud.ibm.com/docs)
- [IBM Cloud CLI reference](https://cloud.ibm.com/docs/cli)
- [Code Engine documentation](https://cloud.ibm.com/docs/codeengine)
- [IBM Kubernetes Service](https://cloud.ibm.com/docs/containers)
- [watsonx platform](https://www.ibm.com/watsonx)
---

← [Previous: OCI](./oci.md) | [Home](../README.md) | [Next: Alibaba Cloud →](./alibaba-cloud.md)
