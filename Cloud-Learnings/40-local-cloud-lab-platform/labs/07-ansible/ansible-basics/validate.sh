#!/usr/bin/env bash
# Validate lab: ansible-basics
set -euo pipefail

echo "=== Ansible Basics Lab Validation ==="

# Check ansible is installed
if ansible --version &>/dev/null; then
    ANSIBLE_VER=$(ansible --version | head -1)
    echo "PASS: $ANSIBLE_VER"
else
    echo "FAIL: ansible not installed — pip3 install ansible"
    exit 1
fi

# Check community.docker collection
if ansible-galaxy collection list 2>/dev/null | grep -q "community.docker"; then
    echo "PASS: community.docker collection installed"
else
    echo "WARN: community.docker not found"
    echo "      Install: ansible-galaxy collection install community.docker"
fi

# Check Docker is running
if docker info &>/dev/null; then
    echo "PASS: Docker is running"
else
    echo "FAIL: Docker is not running"
    exit 1
fi

# Check node containers are running
NODE1_RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c "^node1$" || true)
NODE2_RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c "^node2$" || true)

if [ "$NODE1_RUNNING" -gt 0 ]; then
    echo "PASS: node1 container is running"
else
    echo "WARN: node1 not running — start with: docker run -d --name node1 alpine:3.19 sleep 3600"
fi

if [ "$NODE2_RUNNING" -gt 0 ]; then
    echo "PASS: node2 container is running"
else
    echo "WARN: node2 not running — start with: docker run -d --name node2 alpine:3.19 sleep 3600"
fi

# Check for inventory file
INVENTORY_PATHS=(~/ansible-lab/inventory.yml ~/ansible-lab/inventory.yaml ./inventory.yml ./inventory.yaml)
INVENTORY_FOUND=false
for inv in "${INVENTORY_PATHS[@]}"; do
    if [ -f "$inv" ]; then
        echo "PASS: Inventory file found at $inv"
        INVENTORY_FOUND=true

        # Quick syntax check
        if ansible-inventory -i "$inv" --list &>/dev/null; then
            echo "PASS: Inventory syntax is valid"
        else
            echo "WARN: Inventory file may have syntax errors"
        fi
        break
    fi
done

if ! $INVENTORY_FOUND; then
    echo "INFO: Inventory file not found in expected locations"
fi

# Check for playbook
PLAYBOOK_PATHS=(~/ansible-lab/site.yml ~/ansible-lab/playbook.yml ./site.yml ./playbook.yml)
for pb in "${PLAYBOOK_PATHS[@]}"; do
    if [ -f "$pb" ]; then
        echo "PASS: Playbook found at $pb"
        if grep -q "hosts:" "$pb"; then
            echo "PASS: Playbook has 'hosts:' directive"
        fi
        break
    fi
done

# If both nodes running and inventory found, do a live ping test
if $INVENTORY_FOUND && [ "$NODE1_RUNNING" -gt 0 ] && [ "$NODE2_RUNNING" -gt 0 ]; then
    for inv in "${INVENTORY_PATHS[@]}"; do
        if [ -f "$inv" ]; then
            if ansible all -i "$inv" -m ping 2>/dev/null | grep -q "pong"; then
                echo "PASS: ansible ping succeeds against all nodes"
            else
                echo "WARN: ansible ping did not get pong from all nodes"
            fi
            break
        fi
    done
fi

echo ""
echo "=== Validation complete ==="
