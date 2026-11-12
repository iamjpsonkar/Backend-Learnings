← [Previous: Alibaba Cloud](./alibaba-cloud.md) | [Home](../README.md) | [Next: Cloudflare →](./cloudflare.md)

---

# DigitalOcean

DigitalOcean is a developer-focused cloud platform with simple pricing, excellent documentation, and a streamlined product set. It excels at straightforward web application hosting, small-to-medium workloads, and indie/startup use cases where simplicity and predictable cost matter more than breadth of services.

---

## Key Differentiators

| Feature | Detail |
|---------|--------|
| **Simplicity** | Minimal setup friction — spin up a Droplet in under a minute |
| **Predictable pricing** | Fixed monthly prices (not pay-per-millisecond) for most resources |
| **App Platform** | PaaS — push code, DO handles build/deploy/scale |
| **Managed databases** | PostgreSQL, MySQL, Redis, MongoDB, Kafka — fully managed |
| **Spaces** | S3-compatible object storage |
| **Community** | Extensive tutorials and community content |

---

## Service Equivalents

| AWS | DigitalOcean |
|-----|-------------|
| EC2 | Droplets (VMs) |
| Auto Scaling Group | Droplet Autoscale |
| S3 | Spaces |
| CloudFront | CDN (via Spaces CDN or separate CDN) |
| RDS / ElastiCache | Managed Databases (PostgreSQL, MySQL, Redis) |
| EKS | Kubernetes (DOKS) |
| Elastic Beanstalk / App Runner | App Platform |
| Lambda | Functions |
| VPC | VPC |
| ALB | Load Balancer |
| Route 53 | DNS |
| ECR | Container Registry |

---

## CLI Setup

```bash
# Install doctl (DigitalOcean CLI)
# macOS
brew install doctl

# Linux
curl -sL https://github.com/digitalocean/doctl/releases/download/v1.110.0/doctl-1.110.0-linux-amd64.tar.gz | tar -xzv
sudo mv doctl /usr/local/bin

# Authenticate with a personal access token
doctl auth init
# Paste your token from https://cloud.digitalocean.com/account/api/tokens

# Verify
doctl account get

# List available regions
doctl compute region list

# Common regions: nyc3, sfo3, ams3, sgp1, lon1, fra1, blr1, syd1
```

---

## Droplets (VMs)

```bash
REGION="nyc3"

# List available Droplet sizes
doctl compute size list --output table

# Key sizes
# s-1vcpu-1gb    $6/mo  — basic dev/test
# s-2vcpu-4gb    $24/mo — small production
# s-4vcpu-8gb    $48/mo — medium production
# c-4            $72/mo — CPU-optimized (4 vCPU)
# m-4vcpu-32gb   $96/mo — memory-optimized

# List available images
doctl compute image list --public --output table | grep ubuntu

# Create an SSH key
doctl compute ssh-key import my-app-key --public-key-file ~/.ssh/id_rsa.pub

SSH_KEY_ID=$(doctl compute ssh-key list --output json | jq -r '.[] | select(.name=="my-app-key") | .id')

# Create a Droplet (private networking — no public IPv4)
DROPLET_ID=$(doctl compute droplet create vm-my-app-prod-001 \
    --region $REGION \
    --size s-4vcpu-8gb \
    --image ubuntu-22-04-x64 \
    --ssh-keys $SSH_KEY_ID \
    --vpc-uuid $(doctl vpcs list --output json | jq -r '.[] | select(.name=="vpc-my-app-prod") | .id') \
    --no-wait \
    --output json | jq -r '.[0].id')

# Wait for active state
doctl compute droplet get $DROPLET_ID --format Status --no-header

# List Droplets
doctl compute droplet list --output table

# Get Droplet IP
doctl compute droplet get $DROPLET_ID --format PublicIPv4 --no-header

# Power off / on
doctl compute droplet-action power-off $DROPLET_ID
doctl compute droplet-action power-on $DROPLET_ID

# Delete
doctl compute droplet delete $DROPLET_ID
```

### User Data (Cloud Init)

```bash
# Pass user data script at creation
doctl compute droplet create vm-my-app-prod-001 \
    --region $REGION \
    --size s-4vcpu-8gb \
    --image ubuntu-22-04-x64 \
    --ssh-keys $SSH_KEY_ID \
    --user-data-file ./cloud-init.sh
```

```bash
#!/bin/bash
# cloud-init.sh
set -euo pipefail
apt-get update -y
apt-get install -y python3-pip python3-venv
echo "Setup complete" | tee /var/log/cloud-init-done.txt
```

---

## VPC and Networking

```bash
# Create a VPC
VPC_ID=$(doctl vpcs create \
    --name vpc-my-app-prod \
    --region $REGION \
    --ip-range 10.0.0.0/16 \
    --output json | jq -r '.id')

# List VPCs
doctl vpcs list --output table

# Load Balancer
LB_ID=$(doctl compute load-balancer create \
    --name lb-my-app-prod \
    --region $REGION \
    --algorithm round_robin \
    --forwarding-rules entry_protocol:https,entry_port:443,target_protocol:http,target_port:8080,certificate_id:$CERT_ID \
    --forwarding-rules entry_protocol:http,entry_port:80,target_protocol:http,target_port:8080 \
    --health-check protocol:http,port:8080,path:/health,check_interval_seconds:10,response_timeout_seconds:5,healthy_threshold:2,unhealthy_threshold:5 \
    --droplet-ids $DROPLET_ID \
    --vpc-uuid $VPC_ID \
    --output json | jq -r '.id')

doctl compute load-balancer get $LB_ID --format IP --no-header
```

---

## Spaces (Object Storage)

Spaces is S3-compatible — any S3 SDK or tool works with a custom endpoint.

```bash
# Create a Space
doctl compute cdn-spaces create \
    --name my-app-prod-assets \
    --region $REGION

# Or use the web console — spaces are region-scoped buckets

# Use with AWS CLI (S3-compatible)
aws s3 ls s3://my-app-prod-assets \
    --endpoint-url https://${REGION}.digitaloceanspaces.com \
    --region $REGION

aws s3 cp ./report.pdf s3://my-app-prod-assets/reports/2024/report.pdf \
    --endpoint-url https://${REGION}.digitaloceanspaces.com \
    --acl private

# Enable CDN for a Space
doctl compute cdn create \
    --origin my-app-prod-assets.${REGION}.digitaloceanspaces.com \
    --ttl 3600
```

```python
# Python (boto3 with Spaces endpoint)
import boto3
import os

spaces_client = boto3.client(
    "s3",
    region_name=os.environ["DO_REGION"],
    endpoint_url=f"https://{os.environ['DO_REGION']}.digitaloceanspaces.com",
    aws_access_key_id=os.environ["SPACES_KEY"],
    aws_secret_access_key=os.environ["SPACES_SECRET"],
)

spaces_client.upload_file(
    "./report.pdf",
    "my-app-prod-assets",
    "reports/2024/report.pdf",
    ExtraArgs={"ContentType": "application/pdf", "ACL": "private"},
)
```

---

## App Platform (PaaS)

App Platform builds and deploys from Git or a container image — no server management.

```bash
# Deploy from GitHub
doctl apps create --spec app.yaml

# Retrieve app URL
doctl apps list --format ID,LiveURL --no-header
```

```yaml
# app.yaml — App Platform spec
name: my-app-prod
region: nyc
services:
  - name: api
    source_dir: /
    github:
      repo: your-org/your-repo
      branch: main
      deploy_on_push: true
    run_command: gunicorn main:app
    environment_slug: python
    instance_count: 2
    instance_size_slug: professional-xs  # 1 vCPU, 1 GB RAM
    http_port: 8080
    envs:
      - key: APP_ENV
        value: production
      - key: DATABASE_URL
        value: ${db.DATABASE_URL}
        scope: RUN_TIME
    health_check:
      http_path: /health

databases:
  - name: db
    engine: PG
    version: "15"
    size: db-s-1vcpu-1gb
    num_nodes: 1

domains:
  - domain: my-app.example.com
    type: PRIMARY
```

---

## Managed Databases

```bash
# Create a PostgreSQL cluster
DB_ID=$(doctl databases create pg-my-app-prod \
    --engine pg \
    --version 15 \
    --size db-s-2vcpu-4gb \
    --region $REGION \
    --num-nodes 2 \
    --output json | jq -r '.id')

# Get connection details
doctl databases connection $DB_ID --output json | jq '{
    host: .host,
    port: .port,
    user: .user,
    database: .database,
    uri: .uri
}'

# Create a database
doctl databases db create $DB_ID myapp

# Create a restricted user
doctl databases user create $DB_ID myapp_user

# Add a trusted IP range (restrict access)
doctl databases firewalls append $DB_ID \
    --rule ip_addr:10.0.0.0/8

# Create a Redis cluster
REDIS_ID=$(doctl databases create redis-my-app-prod \
    --engine redis \
    --version 7 \
    --size db-s-1vcpu-1gb \
    --region $REGION \
    --num-nodes 1 \
    --output json | jq -r '.id')

doctl databases connection $REDIS_ID
```

---

## Kubernetes (DOKS)

```bash
# Create a Kubernetes cluster
doctl kubernetes cluster create doks-my-app-prod \
    --region $REGION \
    --version 1.29 \
    --node-pool "name=default;size=s-4vcpu-8gb;count=3;auto-scale=true;min-nodes=2;max-nodes=10" \
    --vpc-uuid $VPC_ID

# Get kubeconfig
doctl kubernetes cluster kubeconfig save doks-my-app-prod
kubectl get nodes
```

---

## Container Registry

```bash
# Create a registry (one per account)
doctl registry create my-app-registry --subscription-tier basic

# Authenticate Docker
doctl registry login

# Tag and push
docker tag my-app/api:v1.0.0 registry.digitalocean.com/my-app-registry/api:v1.0.0
docker push registry.digitalocean.com/my-app-registry/api:v1.0.0

# Integrate with DOKS (grants the cluster pull access)
doctl registry kubernetes-manifest | kubectl apply -f -

# Garbage collect untagged images
doctl registry garbage-collection start my-app-registry
```

---

## DNS

```bash
# Add a domain
doctl compute domain create example.com

# Add an A record
doctl compute domain records create example.com \
    --record-type A \
    --record-name my-app \
    --record-data $(doctl compute load-balancer get $LB_ID --format IP --no-header) \
    --record-ttl 300

# Add a CNAME
doctl compute domain records create example.com \
    --record-type CNAME \
    --record-name www \
    --record-data my-app.example.com. \
    --record-ttl 300

# List DNS records
doctl compute domain records list example.com --output table
```

---

## Pricing Snapshot (2024)

| Resource | Price |
|----------|-------|
| Droplet 1 vCPU / 1 GB | $6/mo |
| Droplet 2 vCPU / 4 GB | $24/mo |
| Managed PostgreSQL (smallest) | $15/mo |
| Managed Redis (smallest) | $15/mo |
| Spaces (250 GB + 1 TB transfer) | $5/mo |
| DOKS cluster (3× 2 vCPU nodes) | ~$72/mo |
| Load Balancer | $12/mo |

---

## References

- [DigitalOcean documentation](https://docs.digitalocean.com)
- [doctl CLI reference](https://docs.digitalocean.com/reference/doctl/)
- [App Platform docs](https://docs.digitalocean.com/products/app-platform/)
- [Spaces S3 compatibility](https://docs.digitalocean.com/products/spaces/reference/s3-compatibility/)
---

← [Previous: Alibaba Cloud](./alibaba-cloud.md) | [Home](../README.md) | [Next: Cloudflare →](./cloudflare.md)
