← [Previous: Other Clouds](./README.md) | [Home](../README.md) | [Next: IBM Cloud →](./ibm-cloud.md)

---

# Oracle Cloud Infrastructure (OCI)

OCI is Oracle's second-generation cloud platform, designed for performance-sensitive and database-heavy workloads. It competes aggressively on price — particularly for Oracle Database — and offers a generous Always Free tier.

---

## Key Differentiators

| Feature | Detail |
|---------|--------|
| **Always Free tier** | 2 AMD VMs (1/8 OCPU, 1 GB RAM each) or 4 Ampere A1 cores + 24 GB RAM total — permanent free forever |
| **Oracle DB pricing** | BYOL and included options — significant savings vs running Oracle on AWS/Azure |
| **Autonomous Database** | Self-driving, self-securing, self-repairing Oracle DB — no DBA required |
| **Flat networking** | No data egress charges between regions in the same realm |
| **Bare metal** | Dedicated physical servers without hypervisor overhead |

---

## Service Equivalents

| AWS | OCI |
|-----|-----|
| EC2 | Compute Instance |
| EBS | Block Volume |
| S3 | Object Storage |
| VPC | Virtual Cloud Network (VCN) |
| RDS | MySQL HeatWave / PostgreSQL |
| Aurora | Autonomous Database |
| Lambda | Functions |
| EKS | Container Engine for Kubernetes (OKE) |
| IAM | Identity and Access Management |
| KMS | Vault |
| CloudWatch | Monitoring |
| CloudTrail | Audit |

---

## CLI Setup

```bash
# Install OCI CLI
bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"

# Configure (creates ~/.oci/config)
oci setup config

# Verify
oci iam region list --output table

# Set profile for multiple tenancies
oci iam region list --profile my-profile

# Common environment variables
export OCI_CLI_PROFILE=my-profile
export OCI_CLI_REGION=us-ashburn-1
```

---

## Resource Organization

OCI uses **Compartments** to organize resources — similar to AWS accounts or GCP folders, but within a single tenancy.

```bash
TENANCY_OCID="ocid1.tenancy.oc1..example"
ROOT_COMPARTMENT=$TENANCY_OCID

# Create a compartment
oci iam compartment create \
    --compartment-id $TENANCY_OCID \
    --name production \
    --description "Production workloads"

PROD_COMPARTMENT=$(oci iam compartment list \
    --compartment-id $TENANCY_OCID \
    --name production \
    --query 'data[0].id' --raw-output)

# List compartments
oci iam compartment list \
    --compartment-id $TENANCY_OCID \
    --query 'data[*].{Name:name,OCID:id,State:"lifecycle-state"}' \
    --output table
```

---

## Networking (VCN)

```bash
REGION="us-ashburn-1"

# Create a VCN
VCN_ID=$(oci network vcn create \
    --compartment-id $PROD_COMPARTMENT \
    --cidr-block 10.0.0.0/16 \
    --display-name vcn-my-app-prod \
    --dns-label myappprod \
    --query 'data.id' --raw-output)

# Internet Gateway
IGW_ID=$(oci network internet-gateway create \
    --compartment-id $PROD_COMPARTMENT \
    --vcn-id $VCN_ID \
    --is-enabled true \
    --display-name igw-my-app-prod \
    --query 'data.id' --raw-output)

# NAT Gateway (for private subnets)
NAT_ID=$(oci network nat-gateway create \
    --compartment-id $PROD_COMPARTMENT \
    --vcn-id $VCN_ID \
    --display-name nat-my-app-prod \
    --query 'data.id' --raw-output)

# Public subnet
PUB_SUBNET_ID=$(oci network subnet create \
    --compartment-id $PROD_COMPARTMENT \
    --vcn-id $VCN_ID \
    --cidr-block 10.0.1.0/24 \
    --display-name snet-public \
    --dns-label public \
    --prohibit-public-ip-on-vnic false \
    --route-table-id $(oci network route-table list \
        --compartment-id $PROD_COMPARTMENT \
        --vcn-id $VCN_ID \
        --query 'data[0].id' --raw-output) \
    --query 'data.id' --raw-output)

# Private subnet
PVT_SUBNET_ID=$(oci network subnet create \
    --compartment-id $PROD_COMPARTMENT \
    --vcn-id $VCN_ID \
    --cidr-block 10.0.11.0/24 \
    --display-name snet-private \
    --dns-label private \
    --prohibit-public-ip-on-vnic true \
    --query 'data.id' --raw-output)
```

---

## Compute

```bash
# List available shapes (instance types)
oci compute shape list \
    --compartment-id $PROD_COMPARTMENT \
    --query 'data[*].{Shape:shape,OCPUs:"ocpu-options".max,Memory:"memory-options"."max-in-gbs"}' \
    --output table | head -30

# Key shapes
# VM.Standard.A1.Flex  — Ampere Arm (Always Free: up to 4 OCPUs, 24 GB)
# VM.Standard.E4.Flex  — AMD EPYC (flexible OCPU/memory)
# VM.Standard3.Flex    — Intel (flexible)
# BM.Standard3.64      — Bare metal, 64 cores

# Create an instance (Ampere A1 — Always Free eligible)
INSTANCE_ID=$(oci compute instance launch \
    --compartment-id $PROD_COMPARTMENT \
    --availability-domain "$(oci iam availability-domain list \
        --compartment-id $TENANCY_OCID \
        --query 'data[0].name' --raw-output)" \
    --shape VM.Standard.A1.Flex \
    --shape-config '{"ocpus": 2, "memoryInGBs": 12}' \
    --image-id $(oci compute image list \
        --compartment-id $PROD_COMPARTMENT \
        --operating-system "Oracle Linux" \
        --operating-system-version "9" \
        --sort-by TIMECREATED \
        --query 'data[0].id' --raw-output) \
    --subnet-id $PVT_SUBNET_ID \
    --assign-public-ip false \
    --display-name vm-my-app-prod-001 \
    --ssh-authorized-keys-file ~/.ssh/id_rsa.pub \
    --user-data-file cloud-init.sh \
    --query 'data.id' --raw-output)

# Get instance state
oci compute instance get \
    --instance-id $INSTANCE_ID \
    --query 'data.{"lifecycle-state":"lifecycle-state","ip-address":"primary-private-ip"}' \
    --output table

# Stop / Start
oci compute instance action --instance-id $INSTANCE_ID --action STOP
oci compute instance action --instance-id $INSTANCE_ID --action START

# SSH via OCI Bastion service (no public IP needed)
oci bastion session create-port-forwarding \
    --bastion-id $BASTION_ID \
    --target-resource-id $INSTANCE_ID \
    --target-private-ip 10.0.11.5 \
    --target-port 22 \
    --session-ttl-in-seconds 3600
```

---

## Object Storage

```bash
NAMESPACE=$(oci os ns get --query 'data' --raw-output)

# Create a bucket
oci os bucket create \
    --compartment-id $PROD_COMPARTMENT \
    --name my-app-prod-assets \
    --storage-tier Standard \
    --public-access-type NoPublicAccess \
    --versioning Enabled

# Upload an object
oci os object put \
    --bucket-name my-app-prod-assets \
    --name reports/2024/report.pdf \
    --file ./report.pdf \
    --content-type "application/pdf"

# Download
oci os object get \
    --bucket-name my-app-prod-assets \
    --name reports/2024/report.pdf \
    --file /tmp/report.pdf

# List objects
oci os object list \
    --bucket-name my-app-prod-assets \
    --prefix reports/ \
    --query 'data[*].{Name:name,Size:size,"Last-Modified":"time-modified"}' \
    --output table

# Pre-authenticated request (time-limited public URL)
oci os preauth-request create \
    --bucket-name my-app-prod-assets \
    --name temp-report-access \
    --access-type ObjectRead \
    --object-name reports/2024/report.pdf \
    --time-expires "$(date -u -v+1H +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d '+1 hour' +"%Y-%m-%dT%H:%M:%SZ")"
```

---

## Autonomous Database

```bash
# Create an Autonomous Transaction Processing (ATP) database
oci db autonomous-database create \
    --compartment-id $PROD_COMPARTMENT \
    --db-name myappdb \
    --display-name "My App Production DB" \
    --db-workload OLTP \
    --cpu-core-count 2 \
    --data-storage-size-in-tbs 1 \
    --admin-password "Str0ngP@ssw0rd1!" \
    --is-auto-scaling-enabled true \
    --subnet-id $PVT_SUBNET_ID \
    --is-dedicated false \
    --license-model LICENSE_INCLUDED

# Download wallet (mTLS connection bundle)
oci db autonomous-database generate-wallet \
    --autonomous-database-id $ADB_ID \
    --file adb-wallet.zip \
    --password "WalletP@ssw0rd!"
```

---

## IAM

```bash
# Create a group
oci iam group create \
    --name developers \
    --description "Application developers"

GROUP_ID=$(oci iam group list \
    --name developers \
    --query 'data[0].id' --raw-output)

# Create a user and add to group
USER_ID=$(oci iam user create \
    --name alice@example.com \
    --description "Alice — backend developer" \
    --query 'data.id' --raw-output)

oci iam group add-user \
    --group-id $GROUP_ID \
    --user-id $USER_ID

# Create a policy (grants permissions to a group in a compartment)
oci iam policy create \
    --compartment-id $PROD_COMPARTMENT \
    --name developers-policy \
    --description "Developers access to production compartment" \
    --statements '["Allow group developers to manage compute-instances in compartment production",
                   "Allow group developers to read buckets in compartment production",
                   "Allow group developers to read objects in compartment production"]'

# Create a Dynamic Group (for instances/functions to call OCI APIs)
oci iam dynamic-group create \
    --name my-app-instances \
    --description "All instances in production compartment" \
    --matching-rule "All {instance.compartment.id = '\''$PROD_COMPARTMENT'\''}"

# Policy for the dynamic group
oci iam policy create \
    --compartment-id $TENANCY_OCID \
    --name my-app-instances-policy \
    --description "Allow app instances to read secrets" \
    --statements '["Allow dynamic-group my-app-instances to read secret-bundle in compartment production"]'
```

---

## Always Free Resources

| Resource | Free Limit |
|----------|-----------|
| Compute VMs | 2 AMD VMs (1/8 OCPU, 1 GB RAM) OR 4 Arm A1 OCPUs + 24 GB total RAM |
| Block Storage | 200 GB total |
| Object Storage | 20 GB |
| Autonomous Database | 2 databases, 20 GB each |
| Load Balancer | 1 instance, 10 Mbps |
| Monitoring | 500 million ingestion datapoints/month |
| Networking | 10 TB outbound/month |

---

## References

- [OCI documentation](https://docs.oracle.com/en-us/iaas/Content/home.htm)
- [OCI CLI reference](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/)
- [OCI Always Free tier](https://www.oracle.com/cloud/free/)
- [Autonomous Database](https://docs.oracle.com/en-us/iaas/autonomous-database/)
---

← [Previous: Other Clouds](./README.md) | [Home](../README.md) | [Next: IBM Cloud →](./ibm-cloud.md)
