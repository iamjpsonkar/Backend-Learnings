#!/usr/bin/env bash
# Validate lab: terraform-basics
set -euo pipefail

echo "=== Terraform Basics Lab Validation ==="

# Check terraform or tofu is installed
if terraform version &>/dev/null; then
    TF_VER=$(terraform version | head -1)
    echo "PASS: $TF_VER"
elif tofu version &>/dev/null; then
    TF_VER=$(tofu version | head -1)
    echo "PASS: $TF_VER (OpenTofu)"
else
    echo "FAIL: Neither terraform nor tofu is installed"
    echo "      Install: brew install terraform  OR  brew install opentofu"
    exit 1
fi

# Check Docker is running
if docker info &>/dev/null; then
    echo "PASS: Docker is running"
else
    echo "FAIL: Docker is not running"
    exit 1
fi

# Check if lab-nginx container exists (created by terraform apply)
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^lab-nginx$"; then
    echo "PASS: lab-nginx container is running"

    # Check if it responds to HTTP
    if curl -sf http://localhost:8765 2>/dev/null | grep -qi "nginx\|html\|Welcome"; then
        echo "PASS: lab-nginx responds to HTTP on port 8765"
    else
        echo "WARN: lab-nginx is running but port 8765 not responding (may be on different port)"
    fi
else
    echo "WARN: lab-nginx container not running"
    echo "      Run: cd ~/tf-lab && terraform apply -auto-approve"
fi

# Check terraform state file
if [ -f ~/tf-lab/terraform.tfstate ]; then
    RESOURCE_COUNT=$(python3 -c "
import json
try:
    d = json.load(open('$HOME/tf-lab/terraform.tfstate'))
    resources = d.get('resources', [])
    print(len(resources))
except Exception as e:
    print(0)
" 2>/dev/null)
    if [ "$RESOURCE_COUNT" -gt 0 ]; then
        echo "PASS: terraform.tfstate has $RESOURCE_COUNT resource(s)"
    else
        echo "WARN: terraform.tfstate exists but has no resources"
    fi
else
    echo "INFO: No terraform.tfstate found at ~/tf-lab/ (project may be in different location)"
fi

# Check for providers.tf
if [ -f ~/tf-lab/providers.tf ]; then
    echo "PASS: providers.tf found"
else
    echo "INFO: providers.tf not found at ~/tf-lab/"
fi

# Check for .terraform directory (init was run)
if [ -d ~/tf-lab/.terraform ]; then
    echo "PASS: .terraform/ directory exists (terraform init was run)"
else
    echo "INFO: .terraform/ directory not found — run terraform init first"
fi

echo ""
echo "=== Validation complete ==="
