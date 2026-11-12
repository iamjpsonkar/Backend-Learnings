# Infrastructure

Infrastructure-as-code configurations for the Cloud-Learnings Lab Platform.

## Directory Structure

```
infrastructure/
├── terraform/     Terraform configurations (LocalStack + MinIO backend)
├── opentofu/      OpenTofu configurations (drop-in Terraform replacement)
├── ansible/       Ansible inventory and playbooks
├── kubernetes/    Kubernetes manifests (for kind/k3d cluster)
├── helm/          Sample Helm chart
└── kustomize/     Kustomize base + overlays
```

## Usage

### Terraform

```bash
# Start required services
./run.sh start aws iac

# Enter Terraform container
docker exec -it cloud-learnings-terraform bash

# Or run from host (if terraform installed)
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

### Ansible

```bash
# Start iac profile
./run.sh start iac

# Enter Ansible container
docker exec -it cloud-learnings-ansible bash
ansible-playbook -i inventory playbooks/setup.yml
```

### Kubernetes

```bash
# Create cluster first
./run.sh kubernetes create kind

# Apply manifests
kubectl apply -f infrastructure/kubernetes/
```

## All configurations use fake/local credentials

No real cloud credentials needed. All Terraform targets LocalStack or MinIO.
