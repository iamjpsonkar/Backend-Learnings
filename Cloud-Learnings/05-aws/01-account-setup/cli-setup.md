← [Previous: Billing & Budgets](./billing-budgets.md) | [Home](../../README.md) | [Next: AWS IAM →](../02-iam/README.md)

---

# AWS CLI Setup and Configuration

The AWS CLI is the primary tool for interacting with AWS from a terminal, scripts, and CI/CD pipelines. This document covers installation, authentication, named profiles, and the credential resolution chain.

---

## Installation

### AWS CLI v2 (Current — Use This)

```bash
# macOS (using the official installer)
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
aws --version
# aws-cli/2.x.x Python/3.x.x Darwin/...

# macOS with Homebrew
brew install awscli

# Linux (x86_64)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version

# Linux (ARM64 — for Graviton instances)
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Windows (PowerShell)
# Download and run: https://awscli.amazonaws.com/AWSCLIV2.msi

# Verify installation
aws --version
which aws
```

### Useful Companion Tools

```bash
# jq — JSON processor (essential for parsing CLI output)
brew install jq          # macOS
sudo apt install jq      # Ubuntu
sudo dnf install jq      # Amazon Linux

# AWS Session Manager Plugin (for SSM Session Manager)
# macOS:
brew install --cask session-manager-plugin

# Ubuntu:
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb"
sudo dpkg -i session-manager-plugin.deb
```

---

## Initial Configuration

```bash
# Configure default profile (interactive)
aws configure
# AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
# AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
# Default region name [None]: us-east-1
# Default output format [None]: json    # json | yaml | table | text

# Configuration is stored in:
#   ~/.aws/credentials  — access keys
#   ~/.aws/config       — region, output, profiles, SSO settings

cat ~/.aws/credentials
cat ~/.aws/config
```

---

## Named Profiles

Use named profiles to switch between different accounts, roles, or regions without re-configuring.

### ~/.aws/credentials

```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

[dev]
aws_access_key_id = AKIAIOSFODNN7DEVKEY
aws_secret_access_key = devSecretKey

[production]
aws_access_key_id = AKIAIOSFODNN7PRODKEY
aws_secret_access_key = prodSecretKey
```

### ~/.aws/config

```ini
[default]
region = us-east-1
output = json

[profile dev]
region = us-west-2
output = json

[profile production]
region = us-east-1
output = json
cli_pager =          # disable pager for scripting

# Role assumption profile (assumes a role in another account)
[profile prod-admin]
role_arn = arn:aws:iam::123456789012:role/AdminRole
source_profile = default
region = us-east-1

# SSO profile (see SSO section below)
[profile sso-dev]
sso_start_url = https://myorg.awsapps.com/start
sso_region = us-east-1
sso_account_id = 111122223333
sso_role_name = DeveloperAccess
region = us-east-1
output = json
```

### Using Profiles

```bash
# Use a named profile for a single command
aws s3 ls --profile dev
aws ec2 describe-instances --profile production

# Set profile for the current shell session
export AWS_PROFILE=dev
aws s3 ls   # now uses dev profile

# Unset (revert to default)
unset AWS_PROFILE

# Check which identity is currently in use
aws sts get-caller-identity
# Returns: Account, UserId, Arn
```

---

## AWS SSO / IAM Identity Center (Recommended)

SSO provides temporary credentials via browser-based login. No long-lived access keys to rotate or accidentally commit.

```bash
# Configure an SSO profile (one-time setup)
aws configure sso

# Prompts:
# SSO session name: myorg
# SSO start URL: https://myorg.awsapps.com/start
# SSO region: us-east-1
# Registered scopes: sso:account:access
# (browser opens for login)
# Account: 111122223333 — Development
# Role: DeveloperAccess

# Login (opens browser for MFA/SSO)
aws sso login --profile sso-dev

# Now use the profile
aws s3 ls --profile sso-dev

# Set as active profile
export AWS_PROFILE=sso-dev

# Logout
aws sso logout

# Refresh credentials (re-login if expired)
aws sso login --profile sso-dev
```

### ~/.aws/config for SSO Sessions

```ini
[sso-session myorg]
sso_start_url = https://myorg.awsapps.com/start
sso_region = us-east-1
sso_registration_scopes = sso:account:access

[profile dev]
sso_session = myorg
sso_account_id = 111122223333
sso_role_name = DeveloperAccess
region = us-east-1

[profile staging]
sso_session = myorg
sso_account_id = 444455556666
sso_role_name = DeveloperAccess
region = us-east-1

[profile production]
sso_session = myorg
sso_account_id = 777788889999
sso_role_name = ReadOnlyAccess
region = us-east-1
```

---

## Credential Resolution Chain

When you run an AWS CLI command, the SDK checks for credentials in this order (first match wins):

```
1. Command-line options       --aws-access-key-id, --aws-secret-access-key
2. Environment variables      AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
3. AWS_PROFILE environment    export AWS_PROFILE=myprofile
4. ~/.aws/credentials file    [default] or [profile-name]
5. ~/.aws/config file         [profile profile-name]
6. Container credentials      ECS task role (via metadata endpoint)
7. EC2 instance metadata      Instance profile role (http://169.254.169.254/...)
```

**In production on EC2/ECS/Lambda**: credentials come from the instance/task/function role automatically (step 6 or 7). Never put access keys in environment variables on production systems.

---

## Environment Variables

```bash
# Override any profile for a single command or session
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_DEFAULT_REGION=us-east-1
export AWS_SESSION_TOKEN=AQoXnyc4lcK4w...   # for temporary credentials

# Check active credentials
aws sts get-caller-identity

# Useful env vars
export AWS_PAGER=""              # disable automatic pager (good for scripting)
export AWS_MAX_ATTEMPTS=3        # retry limit
export AWS_RETRY_MODE=standard   # standard | adaptive

# Unset when done
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
```

---

## Role Assumption

```bash
# Assume a role and export credentials
CREDS=$(aws sts assume-role \
    --role-arn arn:aws:iam::123456789012:role/DeployRole \
    --role-session-name deploy-session-$(date +%s) \
    --query 'Credentials' \
    --output json)

export AWS_ACCESS_KEY_ID=$(echo $CREDS | jq -r '.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo $CREDS | jq -r '.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo $CREDS | jq -r '.SessionToken')

# Verify
aws sts get-caller-identity

# Use a profile that assumes a role automatically
# (configure role_arn + source_profile in ~/.aws/config — see above)
aws s3 ls --profile prod-admin
```

---

## Useful CLI Patterns

```bash
# Output formats
aws ec2 describe-instances --output table    # human-readable table
aws ec2 describe-instances --output json     # full JSON (default)
aws ec2 describe-instances --output yaml     # YAML
aws ec2 describe-instances --output text     # tab-separated (good for shell parsing)

# JMESPath queries (--query flag)
# Get only instance IDs and states
aws ec2 describe-instances \
    --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType]' \
    --output table

# Filter by tag
aws ec2 describe-instances \
    --filters 'Name=tag:Environment,Values=production' 'Name=instance-state-name,Values=running' \
    --query 'Reservations[*].Instances[*].InstanceId' \
    --output text

# Pagination (automatically handles large result sets)
aws s3api list-objects-v2 \
    --bucket my-bucket \
    --query 'Contents[*].Key' \
    --output text

# Wait for a resource state
aws ec2 wait instance-running --instance-ids i-0abc1234
aws ec2 wait instance-stopped --instance-ids i-0abc1234

# Dry run (check permissions without taking action)
aws ec2 run-instances \
    --image-id ami-0abcdef1234567890 \
    --instance-type t3.micro \
    --dry-run
# If you have permission: "DryRunOperation" error (good)
# If you lack permission: "UnauthorizedOperation" error

# Get current region
aws configure get region
aws ec2 describe-availability-zones --query 'AvailabilityZones[0].RegionName' --output text

# Get current account ID
aws sts get-caller-identity --query Account --output text
```

---

## Auto-Completion

```bash
# bash
complete -C aws_completer aws
echo 'complete -C aws_completer aws' >> ~/.bashrc

# zsh
autoload bashcompinit && bashcompinit
complete -C aws_completer aws
echo 'autoload bashcompinit && bashcompinit; complete -C aws_completer aws' >> ~/.zshrc

# Reload shell
source ~/.zshrc
```

---

## References

- [AWS CLI v2 installation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [Named profiles documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html)
- [AWS SSO CLI integration](https://docs.aws.amazon.com/cli/latest/userguide/sso-configure-profile-token.html)
- [CLI configuration reference](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
---

← [Previous: Billing & Budgets](./billing-budgets.md) | [Home](../../README.md) | [Next: AWS IAM →](../02-iam/README.md)
