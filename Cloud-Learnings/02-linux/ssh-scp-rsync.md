← [Previous: Shell Scripting](./shell-scripting.md) | [Home](../README.md) | [Next: Cron & Scheduling →](./cron-scheduling.md)

---

# SSH, SCP, and rsync

## SSH Overview

SSH (Secure Shell) provides encrypted remote access to Linux systems. It uses asymmetric key pairs for authentication and encrypts all traffic.

---

## Key Generation

```bash
# Generate an Ed25519 key (preferred — smaller, faster, more secure than RSA)
ssh-keygen -t ed25519 -C "deploy@company.com"

# Generate RSA 4096 (use when Ed25519 is not supported by old systems)
ssh-keygen -t rsa -b 4096 -C "deploy@company.com"

# Generate with a specific filename (non-interactive)
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_prod -C "prod-deploy" -N ""
# -N "" = empty passphrase (for automation; use a passphrase for personal keys)

# Key files created:
# ~/.ssh/id_ed25519      — private key (never share this)
# ~/.ssh/id_ed25519.pub  — public key (goes on remote servers)
```

### Copy Public Key to Remote Server

```bash
# Recommended: ssh-copy-id
ssh-copy-id -i ~/.ssh/id_ed25519.pub ubuntu@10.0.1.50

# Manual: append to authorized_keys
cat ~/.ssh/id_ed25519.pub | ssh ubuntu@10.0.1.50 \
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

---

## ~/.ssh/config — Client Configuration

The SSH config file eliminates the need to type long options every time.

```
# ~/.ssh/config

# Default settings for all hosts
Host *
    ServerAliveInterval 60          # send keepalive every 60s
    ServerAliveCountMax 3           # disconnect after 3 missed keepalives
    AddKeysToAgent yes              # add keys to ssh-agent on first use
    IdentitiesOnly yes              # use only explicitly specified keys

# Production bastion
Host bastion-prod
    HostName 54.12.34.56
    User ubuntu
    IdentityFile ~/.ssh/id_ed25519_prod
    Port 22

# Private EC2 instances via bastion (ProxyJump)
Host app-prod-*
    User ubuntu
    IdentityFile ~/.ssh/id_ed25519_prod
    ProxyJump bastion-prod          # route through bastion automatically

Host app-prod-1
    HostName 10.0.1.10

Host app-prod-2
    HostName 10.0.1.11

# Staging: shorter alias
Host staging
    HostName staging.example.com
    User ec2-user
    IdentityFile ~/.ssh/id_ed25519_staging

# Local Vagrant / development VM
Host dev
    HostName 127.0.0.1
    Port 2222
    User vagrant
    IdentityFile ~/.vagrant.d/insecure_private_key
    StrictHostKeyChecking no        # skip host key check for ephemeral VMs
    UserKnownHostsFile /dev/null    # don't add to known_hosts
```

With this config:
```bash
ssh bastion-prod              # connects to 54.12.34.56 with prod key
ssh app-prod-1                # connects via bastion → 10.0.1.10 automatically
ssh staging                   # connects with staging key
```

---

## SSH Agent

The SSH agent holds decrypted private keys in memory so you don't re-enter the passphrase each time.

```bash
# Start the agent (if not started automatically)
eval "$(ssh-agent -s)"

# Add keys
ssh-add ~/.ssh/id_ed25519           # add with passphrase prompt
ssh-add ~/.ssh/id_ed25519_prod

# List loaded keys
ssh-add -l

# Remove all keys from agent
ssh-add -D

# On macOS: use Keychain to persist across reboots
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

---

## Jump Hosts (Bastion Servers)

A bastion (jump) host is a hardened server that acts as an entry point to a private network.

```bash
# Using -J flag (preferred, available since OpenSSH 7.3)
ssh -J ubuntu@54.12.34.56 ubuntu@10.0.1.10

# Multiple jumps
ssh -J user@bastion1,user@bastion2 user@target

# Via config (ProxyJump — recommended)
# (See ~/.ssh/config example above)

# Old method: ProxyCommand (still needed for some tooling)
Host private-host
    HostName 10.0.1.10
    User ubuntu
    ProxyCommand ssh -W %h:%p ubuntu@54.12.34.56
```

---

## Port Forwarding

### Local Port Forwarding

Forward a local port to a remote host. Access remote services locally.

```bash
# Access a remote database (port 5432) via local port 15432
ssh -L 15432:rds.endpoint.us-east-1.rds.amazonaws.com:5432 ubuntu@bastion-prod

# Now connect locally:
psql -h 127.0.0.1 -p 15432 -U dbuser mydb

# Access a private web server
ssh -L 8080:10.0.1.10:80 ubuntu@bastion-prod
# Open: http://localhost:8080
```

### Remote Port Forwarding

Expose a local port on the remote server. Useful for sharing local dev work.

```bash
# Expose local port 3000 on remote server's port 8080
ssh -R 8080:localhost:3000 ubuntu@server
```

### Dynamic (SOCKS) Proxy

Turn the SSH connection into a SOCKS proxy — route arbitrary traffic through it.

```bash
ssh -D 1080 ubuntu@bastion-prod
# Configure browser/tools to use SOCKS5 proxy at 127.0.0.1:1080
```

### Persistent tunnels (background)

```bash
# Run in background (-f), don't execute remote command (-N)
ssh -fN -L 15432:rds.endpoint:5432 ubuntu@bastion-prod

# Kill it later
kill $(lsof -ti:15432)
# or
pkill -f "ssh.*15432"
```

---

## SSH Server Hardening (/etc/ssh/sshd_config)

```bash
# Core hardening settings
PermitRootLogin no              # never allow root login
PasswordAuthentication no       # key-based auth only
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
MaxAuthTries 3                  # disconnect after 3 failed attempts
LoginGraceTime 20               # 20s to complete auth before disconnect
ClientAliveInterval 300         # 5-minute keepalive
ClientAliveCountMax 2           # disconnect after 2 missed responses

# Restrict which users can log in
AllowUsers ubuntu deploy        # whitelist specific users
AllowGroups ssh-users           # or restrict by group

# Change default port (security through obscurity — minor benefit)
Port 2222

# Apply changes
sudo systemctl reload sshd

# Test config syntax before reloading
sudo sshd -t
```

> **Always keep a second terminal session open** when editing sshd_config — a syntax error will lock you out.

---

## SCP — Secure Copy

SCP copies files over SSH. It uses SSH for authentication and encryption.

```bash
# Copy local file to remote
scp file.txt ubuntu@server:/home/ubuntu/

# Copy remote file to local
scp ubuntu@server:/var/log/app.log ./

# Copy directory recursively
scp -r ./deploy/ ubuntu@server:/opt/myapp/

# Copy via bastion (using SSH config alias)
scp -J bastion-prod file.tar.gz ubuntu@10.0.1.10:/tmp/

# Specify port
scp -P 2222 file.txt ubuntu@server:/tmp/

# Preserve timestamps and permissions
scp -p file.txt ubuntu@server:/tmp/

# Limit bandwidth (in Kbit/s)
scp -l 1024 large-file.tar.gz ubuntu@server:/tmp/
```

> **Note:** SCP is deprecated in OpenSSH 9.0+ in favour of SFTP. Use `rsync` for large transfers.

---

## rsync — Efficient File Synchronisation

rsync transfers only changed blocks, making it far more efficient than SCP for large or repeated transfers.

```bash
# Basic syntax
rsync [options] source destination

# Common flags
# -a  archive mode (recursive, preserves permissions, times, symlinks, owner)
# -v  verbose
# -z  compress during transfer
# -P  show progress + resume partial transfers
# -n  dry run (simulate without copying)
# --delete  delete files in destination not present in source

# Sync local directory to remote
rsync -avz ./dist/ ubuntu@server:/var/www/html/

# Sync remote directory to local
rsync -avz ubuntu@server:/var/log/app/ ./logs/

# Dry run first — always recommended for --delete operations
rsync -avzn --delete ./dist/ ubuntu@server:/var/www/html/

# Mirror local directory to remote (exact copy, removes extra files)
rsync -avz --delete ./dist/ ubuntu@server:/var/www/html/

# Via bastion jump host
rsync -avz -e "ssh -J bastion-prod" ./app/ ubuntu@10.0.1.10:/opt/app/

# Exclude patterns
rsync -avz --exclude='*.log' --exclude='.git/' ./src/ ubuntu@server:/app/src/

# Bandwidth limit (1 MB/s)
rsync -avz --bwlimit=1024 large-file.tar.gz ubuntu@server:/tmp/

# Resume an interrupted transfer
rsync -avzP large-file.tar.gz ubuntu@server:/tmp/
```

### rsync Trailing Slash Rule

The trailing slash on the **source** controls what gets copied:

```bash
# WITH trailing slash: copies contents of dir/ into dest/
rsync -av dir/ ubuntu@server:/dest/
# Result: /dest/file1, /dest/file2

# WITHOUT trailing slash: copies dir itself into dest/
rsync -av dir ubuntu@server:/dest/
# Result: /dest/dir/file1, /dest/dir/file2
```

---

## Cloud-Specific Patterns

### EC2 Key Pair Authentication

```bash
# Download the key pair from EC2 console (or create during launch)
chmod 400 ~/Downloads/my-key.pem    # required: SSH rejects keys with loose permissions

# Connect to Amazon Linux 2/2023
ssh -i ~/Downloads/my-key.pem ec2-user@54.12.34.56

# Connect to Ubuntu AMI
ssh -i ~/Downloads/my-key.pem ubuntu@54.12.34.56

# Add to ~/.ssh/config for convenience
Host my-ec2
    HostName 54.12.34.56
    User ec2-user
    IdentityFile ~/Downloads/my-key.pem
```

### EC2 Instance Connect (No Pre-existing Keys)

EC2 Instance Connect pushes a temporary one-time SSH public key to the instance for 60 seconds.

```bash
# Push your public key (valid for 60 seconds)
aws ec2-instance-connect send-ssh-public-key \
    --instance-id i-0abcdef1234567890 \
    --availability-zone us-east-1a \
    --instance-os-user ec2-user \
    --ssh-public-key file://~/.ssh/id_ed25519.pub

# Connect immediately after
ssh ec2-user@54.12.34.56
```

### AWS Systems Manager Session Manager (No SSH Required)

SSM Session Manager provides shell access without opening port 22, without key pairs, and logs all commands to CloudWatch or S3.

```bash
# Prerequisites: SSM Agent must be running on the instance
#                Instance role must have AmazonSSMManagedInstanceCore policy

# Start a session (requires aws CLI and session-manager-plugin installed)
aws ssm start-session --target i-0abcdef1234567890

# Port forwarding via SSM (no open ports needed)
aws ssm start-session \
    --target i-0abcdef1234567890 \
    --document-name AWS-StartPortForwardingSession \
    --parameters '{"portNumber":["5432"],"localPortNumber":["15432"]}'

# SSH over SSM (configure ~/.ssh/config)
Host i-* mi-*
    ProxyCommand sh -c \
      "aws ssm start-session --target %h \
       --document-name AWS-StartSSHSession \
       --parameters 'portNumber=%p'"

# Then use normal SSH
ssh -i my-key.pem ec2-user@i-0abcdef1234567890
```

### Copying Files to S3 Instead of SCP

For large files or when instances are in private subnets, use S3 as an intermediary:

```bash
# Upload locally, download on instance
aws s3 cp large-file.tar.gz s3://my-deploy-bucket/transfers/
aws ssm start-session --target i-0abc...
# On instance:
aws s3 cp s3://my-deploy-bucket/transfers/large-file.tar.gz /tmp/
```

---

## Known Hosts and Host Key Verification

```bash
# View known hosts
cat ~/.ssh/known_hosts

# Remove a stale host key (e.g., after instance rebuild)
ssh-keygen -R 54.12.34.56          # remove by IP
ssh-keygen -R my-server.example.com # remove by hostname

# Scan a host's public key fingerprint before connecting
ssh-keyscan -H 54.12.34.56 >> ~/.ssh/known_hosts

# Disable host checking for ephemeral hosts (automation only — not production)
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ubuntu@host
```

---

## References

- [OpenSSH manual](https://man.openbsd.org/ssh)
- [SSH config file reference](https://man.openbsd.org/ssh_config)
- [rsync documentation](https://rsync.samba.org/documentation.html)
- [AWS EC2 Instance Connect](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-methods.html)
- [AWS SSM Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
---

← [Previous: Shell Scripting](./shell-scripting.md) | [Home](../README.md) | [Next: Cron & Scheduling →](./cron-scheduling.md)
