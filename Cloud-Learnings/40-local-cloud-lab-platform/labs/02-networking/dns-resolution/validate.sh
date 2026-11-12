#!/usr/bin/env bash
# Validate lab: dns-resolution
set -euo pipefail

echo "=== DNS Resolution Lab Validation ==="

# Check dig is available
if command -v dig &>/dev/null; then
    echo "PASS: dig is installed"
else
    echo "WARN: dig not found — install with: brew install bind  OR  apt-get install dnsutils"
fi

# Check nslookup is available
if command -v nslookup &>/dev/null; then
    echo "PASS: nslookup is installed"
else
    echo "WARN: nslookup not found (optional)"
fi

# Check DNS resolution works (google.com A record)
if command -v dig &>/dev/null; then
    GOOGLE_IP=$(dig +short A google.com 2>/dev/null | head -1)
    if echo "$GOOGLE_IP" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
        echo "PASS: dig resolves google.com -> $GOOGLE_IP"
    else
        echo "FAIL: dig could not resolve google.com A record"
    fi

    # Check MX record lookup
    if dig MX gmail.com 2>/dev/null | grep -qi 'google.com'; then
        echo "PASS: MX records for gmail.com contain google.com"
    else
        echo "FAIL: MX lookup for gmail.com failed or unexpected result"
    fi

    # Check reverse DNS
    if dig -x 8.8.8.8 2>/dev/null | grep -qi 'dns.google'; then
        echo "PASS: Reverse DNS for 8.8.8.8 -> dns.google"
    else
        echo "FAIL: Reverse DNS for 8.8.8.8 did not return dns.google"
    fi
fi

# Check if Traefik / core stack is running
if curl -sf http://localhost:8080 &>/dev/null || curl -sf http://localhost:4567/api/v1/health &>/dev/null; then
    echo "PASS: Core stack is reachable on localhost"
else
    echo "WARN: Core stack not running — run: make start-core"
fi

# Check port reachability with bash built-in
check_port() {
    local host=$1
    local port=$2
    if bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
        echo "PASS: Port $port is open on $host"
    else
        echo "WARN: Port $port is not reachable on $host (service may not be running)"
    fi
}

check_port localhost 9000   # MinIO API
check_port localhost 9001   # MinIO Console
check_port localhost 4567   # Lab API

echo ""
echo "=== Validation complete ==="
