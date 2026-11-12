← [Previous: Package Managers](./package-managers.md) | [Home](../README.md) | [Next: SSH, SCP & rsync →](./ssh-scp-rsync.md)

---

# Shell Scripting for Cloud Engineers

Bash scripts are the glue of cloud automation — EC2 user data, deployment scripts, maintenance tasks, and CI/CD steps are all shell scripts in practice. This guide focuses on patterns used in production cloud environments.

---

## Script Structure and Best Practices

```bash
#!/usr/bin/env bash
# description: Brief description of what this script does
# usage: ./script.sh [options]
#
# Always start with:
set -euo pipefail
# -e: exit on any error
# -u: treat unset variables as errors
# -o pipefail: exit if any command in a pipe fails (not just the last)

# Optional: enable debug output
# set -x   # print each command before executing (useful during development)

# IFS (Internal Field Separator) — prevent word splitting on spaces in loops
IFS=$'\n\t'
```

---

## Variables

```bash
# Assign (no spaces around =)
NAME="production"
COUNT=5
MULTI_WORD="hello world"

# Use variables (quote to prevent word splitting)
echo "$NAME"
echo "Environment: $NAME"
echo "Count: ${COUNT}"    # braces allow adjacent text: ${COUNT}items

# Command substitution
CURRENT_DATE=$(date +%Y-%m-%d)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
LINES=$(wc -l < /var/log/app.log)

# Arithmetic
NUM=10
RESULT=$((NUM * 2 + 5))   # = 25
((NUM++))                  # increment in place

# Default values (critical for robust scripts)
REGION="${AWS_REGION:-us-east-1}"           # use default if unset
LOG_LEVEL="${LOG_LEVEL:-INFO}"
TIMEOUT="${TIMEOUT:-30}"

# Read-only
readonly CONFIG_FILE="/etc/myapp/config.yaml"
readonly MAX_RETRIES=3

# Arrays
SERVICES=("nginx" "redis" "postgresql")
echo "${SERVICES[0]}"           # first element: nginx
echo "${SERVICES[@]}"           # all elements
echo "${#SERVICES[@]}"          # count: 3
SERVICES+=("memcached")         # append

# Environment variables
export APP_ENV="production"     # export to child processes
printenv APP_ENV                # view value
unset APP_ENV                   # remove
```

---

## Quoting Rules

```bash
# Double quotes: allow variable expansion and command substitution
echo "Hello, $USER"              # expands $USER
echo "Date: $(date)"             # expands command substitution

# Single quotes: treat everything literally
echo 'Hello, $USER'              # prints: Hello, $USER
echo 'No $(expansion) here'

# Backticks: old command substitution (prefer $() instead)
DATE=`date`                      # works but avoid — harder to nest
DATE=$(date)                     # preferred

# When to always quote:
rm -rf "$TMPDIR"                 # if TMPDIR is empty, unquoted → rm -rf !
cp "$SOURCE_FILE" "$DEST_DIR/"   # files with spaces in names
```

---

## Conditionals

```bash
# if / elif / else
if [[ "$ENV" == "production" ]]; then
    echo "Running in production"
elif [[ "$ENV" == "staging" ]]; then
    echo "Running in staging"
else
    echo "Unknown environment: $ENV"
fi

# Test operators — [[ ]] is preferred over [ ]
[[ "$a" == "$b" ]]      # string equality
[[ "$a" != "$b" ]]      # string inequality
[[ -z "$a" ]]           # string is empty
[[ -n "$a" ]]           # string is non-empty
[[ "$a" < "$b" ]]       # string less than (alphabetical)

[[ $a -eq $b ]]         # numeric equal
[[ $a -ne $b ]]         # numeric not equal
[[ $a -lt $b ]]         # numeric less than
[[ $a -gt $b ]]         # numeric greater than
[[ $a -le $b ]]         # numeric less or equal
[[ $a -ge $b ]]         # numeric greater or equal

[[ -f "$path" ]]        # file exists and is a regular file
[[ -d "$path" ]]        # directory exists
[[ -r "$path" ]]        # file is readable
[[ -w "$path" ]]        # file is writable
[[ -x "$path" ]]        # file is executable
[[ -L "$path" ]]        # path is a symlink
[[ -s "$path" ]]        # file exists and is non-empty

# Combining conditions
[[ -f "$file" && -r "$file" ]]    # AND
[[ "$x" -gt 0 || "$y" -gt 0 ]]   # OR
[[ ! -d "$dir" ]]                 # NOT

# Inline conditionals (short-circuit)
mkdir -p /tmp/work || { echo "Failed to create dir"; exit 1; }
[[ -f "$config" ]] && source "$config"
command -v docker &>/dev/null || { echo "docker not installed"; exit 1; }
```

---

## Loops

```bash
# for loop over list
for service in nginx redis postgresql; do
    sudo systemctl restart "$service"
    echo "Restarted $service"
done

# for loop over array
SERVICES=("nginx" "redis" "postgresql")
for service in "${SERVICES[@]}"; do
    sudo systemctl status "$service" --no-pager -l
done

# for loop with range
for i in {1..5}; do
    echo "Attempt $i"
done

for i in $(seq 1 10 2); do   # seq: 1 3 5 7 9 (start step stop)
    echo "$i"
done

# while loop
RETRIES=0
MAX=5
while [[ "$RETRIES" -lt "$MAX" ]]; do
    if check_service; then
        echo "Service healthy"
        break
    fi
    ((RETRIES++))
    sleep $((RETRIES * 2))    # exponential backoff: 2 4 6 8 10s
    echo "Retry $RETRIES/$MAX"
done

# Read lines from file
while IFS= read -r line; do
    echo "Processing: $line"
done < /etc/hosts

# Read command output line by line
while IFS= read -r instance_id; do
    echo "Stopping: $instance_id"
    aws ec2 stop-instances --instance-ids "$instance_id"
done < <(aws ec2 describe-instances \
    --filters "Name=tag:Env,Values=dev" \
    --query 'Reservations[].Instances[].InstanceId' \
    --output text)
```

---

## Functions

```bash
# Define a function
log_info() {
    echo "[INFO]  $(date '+%Y-%m-%d %H:%M:%S') $*"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2
}

# Function with local variables and return value
get_instance_id() {
    local url="http://169.254.169.254/latest/meta-data/instance-id"
    local instance_id
    instance_id=$(curl -sf --max-time 2 "$url") || {
        log_error "Could not retrieve instance ID from metadata service"
        return 1
    }
    echo "$instance_id"   # "return" a value via stdout
}

# Function usage
INSTANCE_ID=$(get_instance_id) || exit 1
log_info "Instance ID: $INSTANCE_ID"

# Functions with named parameters (via positional)
deploy_service() {
    local service="$1"
    local version="$2"
    local env="${3:-staging}"    # optional, default staging
    log_info "Deploying $service version $version to $env"
}

deploy_service "api-server" "v1.2.3" "production"
```

---

## Error Handling

```bash
#!/usr/bin/env bash
set -euo pipefail

# Trap: run cleanup on exit or error
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT         # always run on exit
trap 'log_error "Script failed at line $LINENO"' ERR

# Disable exit-on-error for commands that may fail
if ! aws s3 cp backup.tar.gz s3://my-bucket/; then
    log_error "S3 upload failed, continuing anyway"
fi

# Check command exists
require_command() {
    command -v "$1" &>/dev/null || {
        log_error "Required command not found: $1"
        exit 1
    }
}
require_command aws
require_command jq
require_command docker

# Retry with exponential backoff
retry() {
    local max_attempts="$1"
    local delay="$2"
    local cmd=("${@:3}")   # all remaining args as command
    local attempt=1

    until "${cmd[@]}"; do
        if [[ "$attempt" -ge "$max_attempts" ]]; then
            log_error "Command failed after $max_attempts attempts: ${cmd[*]}"
            return 1
        fi
        log_info "Attempt $attempt failed. Retrying in ${delay}s..."
        sleep "$delay"
        delay=$((delay * 2))    # exponential backoff
        ((attempt++))
    done
}

retry 5 2 aws s3 cp large-file.tar.gz s3://my-bucket/
```

---

## Input and Arguments

```bash
# Positional parameters
script_name="$0"         # script name
first_arg="$1"           # first argument
second_arg="$2"          # second argument
all_args="$@"            # all arguments (as separate strings)
arg_count="$#"           # number of arguments

# Validate arguments
if [[ "$#" -lt 2 ]]; then
    echo "Usage: $0 <environment> <version>"
    echo "  environment: production|staging|dev"
    echo "  version: e.g. v1.2.3"
    exit 1
fi

ENV="$1"
VERSION="$2"

# Validate environment value
case "$ENV" in
    production|staging|dev) ;;
    *)
        echo "Error: invalid environment '$ENV'. Must be production, staging, or dev."
        exit 1
        ;;
esac

# Shift arguments
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --env)     ENV="$2";     shift 2 ;;
        --version) VERSION="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift   ;;
        --help|-h) usage; exit 0         ;;
        *)         echo "Unknown arg: $1"; exit 1 ;;
    esac
done
```

---

## Text Processing Patterns

```bash
# Extract fields from JSON (requires jq)
CLUSTER=$(aws ecs list-clusters | jq -r '.clusterArns[0]')
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query 'Vpcs[0].VpcId' \
    --output text)

# Parse CSV/TSV
while IFS=',' read -r name ip port; do
    echo "Host: $name  IP: $ip  Port: $port"
done < hosts.csv

# String operations
path="/var/log/app/error.log"
echo "${path##*/}"        # basename: error.log
echo "${path%/*}"         # dirname: /var/log/app
echo "${path%.log}"       # strip suffix: /var/log/app/error
echo "${path^^}"          # uppercase: /VAR/LOG/APP/ERROR.LOG
echo "${path,,}"          # lowercase

VERSION="v1.2.3"
echo "${VERSION#v}"       # strip leading v: 1.2.3

# Check if string contains substring
if [[ "$output" == *"ERROR"* ]]; then
    echo "Error found in output"
fi

# Heredoc (multi-line strings)
cat > /etc/myapp/config.yaml << EOF
environment: $ENV
version: $VERSION
log_level: ${LOG_LEVEL:-INFO}
database:
  host: ${DB_HOST}
  port: 5432
EOF
```

---

## Cloud Automation Patterns

### EC2 User Data Script

```bash
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee /var/log/user-data.log) 2>&1    # log all output

log() { echo "$(date '+%Y-%m-%dT%H:%M:%SZ') $*"; }

log "Starting user data initialization"

# Update packages
log "Updating packages"
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# Install dependencies
log "Installing dependencies"
apt-get install -y nginx curl awscli jq

# Fetch config from SSM Parameter Store
log "Fetching configuration"
DB_PASSWORD=$(aws ssm get-parameter \
    --name "/prod/db/password" \
    --with-decryption \
    --query 'Parameter.Value' \
    --output text)

# Write config
cat > /etc/myapp/env << ENVFILE
DB_PASSWORD=${DB_PASSWORD}
ENVFILE
chmod 600 /etc/myapp/env

# Start service
systemctl enable --now nginx

log "Initialization complete"
```

### Wait for Resource with Timeout

```bash
wait_for_service() {
    local host="$1"
    local port="$2"
    local timeout="${3:-60}"
    local elapsed=0

    log_info "Waiting for $host:$port (timeout: ${timeout}s)"
    until nc -z "$host" "$port" 2>/dev/null; do
        if [[ "$elapsed" -ge "$timeout" ]]; then
            log_error "Timeout waiting for $host:$port after ${timeout}s"
            return 1
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    log_info "$host:$port is ready (${elapsed}s)"
}

wait_for_service db.internal 5432 120
```

---

## Useful One-Liners

```bash
# Parse and display JSON output from AWS CLI
aws ec2 describe-instances --output json | jq '.Reservations[].Instances[] | {id: .InstanceId, state: .State.Name, ip: .PublicIpAddress}'

# Get all running instance IDs in a region
aws ec2 describe-instances \
    --filters "Name=instance-state-name,Values=running" \
    --query "Reservations[].Instances[].InstanceId" \
    --output text | tr '\t' '\n'

# Count log lines per minute (rate monitoring)
awk '{print $4}' /var/log/nginx/access.log | cut -c2-18 | sort | uniq -c | sort -rn | head -20

# Find and replace in multiple files
find /etc/nginx -name "*.conf" -exec sed -i 's/old.domain.com/new.domain.com/g' {} +

# Watch a command every 2 seconds
watch -n2 'ss -tuln | grep :443'
watch -n5 'systemctl status nginx'

# Measure command execution time
time ./backup.sh
```

---

## References

- [Bash manual](https://www.gnu.org/software/bash/manual/bash.html)
- [ShellCheck — static analysis tool](https://www.shellcheck.net/)
- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
- [Bash pitfalls](https://mywiki.wooledge.org/BashPitfalls)
---

← [Previous: Package Managers](./package-managers.md) | [Home](../README.md) | [Next: SSH, SCP & rsync →](./ssh-scp-rsync.md)
