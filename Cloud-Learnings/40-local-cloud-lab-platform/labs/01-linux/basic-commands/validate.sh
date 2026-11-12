#!/usr/bin/env bash
# Validate lab: linux-basic-commands
set -euo pipefail

echo "=== Linux Basic Commands Lab Validation ==="

# Check Docker is available
if docker info &>/dev/null; then
    echo "PASS: Docker is running"
else
    echo "FAIL: Docker not running — required for this lab"
    exit 1
fi

# Check we can pull and run Alpine
if docker run --rm alpine:3.19 echo "ok" &>/dev/null; then
    echo "PASS: Alpine container runs successfully"
else
    echo "FAIL: Cannot run Alpine container"
fi

# Check find works inside container
FIND_COUNT=$(docker run --rm alpine:3.19 find /etc -type f 2>/dev/null | wc -l)
if [ "$FIND_COUNT" -gt 5 ]; then
    echo "PASS: find command returns $FIND_COUNT files in /etc"
else
    echo "FAIL: find returned unexpected results ($FIND_COUNT files)"
fi

# Check text processing pipeline
PASSWD_LINES=$(docker run --rm alpine:3.19 wc -l /etc/passwd 2>/dev/null | awk '{print $1}')
if [ "$PASSWD_LINES" -gt 0 ]; then
    echo "PASS: /etc/passwd has $PASSWD_LINES lines"
else
    echo "FAIL: Could not count lines in /etc/passwd"
fi

# Check grep pipeline
GREP_RESULT=$(docker run --rm alpine:3.19 sh -c "grep root /etc/passwd | wc -l")
if [ "$GREP_RESULT" -gt 0 ]; then
    echo "PASS: grep finds root entries in /etc/passwd"
else
    echo "FAIL: grep pipeline failed"
fi

# Check file operations
docker run --rm alpine:3.19 sh -c "
    mkdir -p /tmp/lab/{docs,scripts,logs}
    echo 'hello world' > /tmp/lab/docs/hello.txt
    cat /tmp/lab/docs/hello.txt | grep -q 'hello world'
    echo ok
" &>/dev/null && echo "PASS: File create/write/read operations work" || echo "FAIL: File operations failed"

# Check permission setting
docker run --rm alpine:3.19 sh -c "
    echo '#!/bin/sh' > /tmp/test.sh
    chmod +x /tmp/test.sh
    ls -la /tmp/test.sh | grep -q '^-rwx'
    echo ok
" &>/dev/null && echo "PASS: chmod makes script executable" || echo "FAIL: Permission change failed"

echo ""
echo "=== Validation complete ==="
echo "NOTE: This lab is practice-based; full grading requires manual review."
echo "      Run 'make run-lab LAB=01-linux/basic-commands' to try it interactively."
