#!/usr/bin/env bash
# Validate lab: hybrid-cloud-onprem-bridge
set -euo pipefail

echo "=== Hybrid Cloud On-Premises Bridge Validation ==="

# Check Docker is running
if docker info &>/dev/null; then
    echo "PASS: Docker is running"
else
    echo "FAIL: Docker not running"
    exit 1
fi

# Check onprem-net exists
if docker network ls 2>/dev/null | grep -q "onprem-net"; then
    SUBNET=$(docker network inspect onprem-net 2>/dev/null | python3 -c "
import sys, json
n = json.load(sys.stdin)
subnet = n[0]['IPAM']['Config'][0].get('Subnet','?')
print(subnet)
" 2>/dev/null || echo "?")
    echo "PASS: onprem-net network exists (subnet: $SUBNET)"
else
    echo "WARN: onprem-net network not found"
    echo "      Create: docker network create --subnet=192.168.100.0/24 onprem-net"
fi

# Check cloud-net exists
if docker network ls 2>/dev/null | grep -q "cloud-net"; then
    SUBNET=$(docker network inspect cloud-net 2>/dev/null | python3 -c "
import sys, json
n = json.load(sys.stdin)
subnet = n[0]['IPAM']['Config'][0].get('Subnet','?')
print(subnet)
" 2>/dev/null || echo "?")
    echo "PASS: cloud-net network exists (subnet: $SUBNET)"
else
    echo "WARN: cloud-net network not found"
fi

# Check gateway container
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^gateway$"; then
    # Check gateway spans both networks
    NETWORKS=$(docker inspect gateway 2>/dev/null | python3 -c "
import sys, json
c = json.load(sys.stdin)
nets = list(c[0]['NetworkSettings']['Networks'].keys())
print(f'Connected networks: {nets}')
has_both = 'onprem-net' in nets and 'cloud-net' in nets
exit(0 if has_both else 1)
" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "PASS: gateway container spans both networks"
        echo "  $NETWORKS"
    else
        echo "WARN: gateway exists but is not connected to both networks"
        echo "  Connect: docker network connect cloud-net gateway"
    fi
else
    echo "WARN: gateway container not running"
    echo "      Start: docker run -d --name gateway --network onprem-net --cap-add=NET_ADMIN alpine:3.19 sleep 3600"
    echo "      Then: docker network connect cloud-net gateway"
fi

# Check on-prem services
for svc in onprem-app onprem-db; do
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^$svc$"; then
        echo "PASS: $svc is running"
    else
        echo "INFO: $svc not running (optional)"
    fi
done

# Check cloud services
for svc in cloud-app cloud-api; do
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^$svc$"; then
        echo "PASS: $svc is running"
    else
        echo "INFO: $svc not running (optional)"
    fi
done

# Test gateway connectivity
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^gateway$"; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^onprem-app$"; then
        if docker exec gateway ping -c 1 -W 2 onprem-app &>/dev/null; then
            echo "PASS: gateway can reach onprem-app"
        else
            echo "WARN: gateway cannot reach onprem-app"
        fi
    fi
fi

echo ""
echo "=== Validation complete ==="
