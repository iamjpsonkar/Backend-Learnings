← [Previous: GitHub Workflow](./github-workflow.md) | [Home](../README.md) | [Next: AWS →](../05-aws/README.md)

---

# SSH Keys for Git and GitHub

SSH key authentication replaces passwords for Git operations. It is faster, more secure, and enables automation. This document covers key generation, GitHub/GitLab configuration, managing multiple identities, and the SSH agent.

---

## Why SSH Keys for Git

| Method | Security | Convenience | Automation |
|--------|----------|-------------|-----------|
| HTTPS + password | Low (reused passwords) | Requires password each time | Needs credential helper |
| HTTPS + PAT (Personal Access Token) | Medium | Requires token storage | Works but tokens expire |
| **SSH key** | High (asymmetric crypto) | No password after setup | Ideal for CI/CD + automation |

---

## Generate a Key Pair

```bash
# Ed25519 — recommended (smaller, faster, more secure than RSA)
ssh-keygen -t ed25519 -C "alice@example.com"

# RSA 4096 — when Ed25519 is not supported (old GitHub Enterprise, some legacy systems)
ssh-keygen -t rsa -b 4096 -C "alice@example.com"

# Flags:
# -t  key type
# -b  key size (RSA only)
# -C  comment (conventionally your email; appears in authorized_keys)
# -f  output file path (default: ~/.ssh/id_ed25519)
# -N  passphrase (use "" for no passphrase in automation; use a strong passphrase personally)

# Non-interactive (for automation scripts)
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_github -C "ci@example.com" -N ""
```

Files created:
```
~/.ssh/id_ed25519      — private key   (NEVER share, NEVER commit)
~/.ssh/id_ed25519.pub  — public key    (safe to share; goes on GitHub)
```

---

## Correct Permissions

SSH is strict about file permissions. Keys will be rejected if permissions are too open.

```bash
chmod 700 ~/.ssh                        # directory: user only
chmod 600 ~/.ssh/id_ed25519            # private key: user read/write only
chmod 644 ~/.ssh/id_ed25519.pub        # public key: readable by all (OK)
chmod 644 ~/.ssh/config                # config file
chmod 600 ~/.ssh/authorized_keys       # authorized_keys on servers
```

---

## Add Public Key to GitHub

```bash
# Print your public key
cat ~/.ssh/id_ed25519.pub
# Output: ssh-ed25519 AAAAC3Nza... alice@example.com

# Copy to clipboard (macOS)
cat ~/.ssh/id_ed25519.pub | pbcopy

# Copy to clipboard (Linux with xclip)
cat ~/.ssh/id_ed25519.pub | xclip -selection clipboard
```

On GitHub:
1. Settings → SSH and GPG keys → New SSH key
2. Title: descriptive name (e.g., "MacBook 2024" or "CI/CD pipeline")
3. Key type: Authentication Key
4. Paste the public key → Add SSH key

```bash
# Alternatively, use GitHub CLI
gh ssh-key add ~/.ssh/id_ed25519.pub --title "MacBook 2024"

# Verify the connection
ssh -T git@github.com
# Expected: Hi alice! You've successfully authenticated, but GitHub does not provide shell access.
```

---

## SSH Agent

The SSH agent holds decrypted private keys in memory, so you enter your passphrase once per session rather than on every Git operation.

```bash
# Start the agent (usually auto-started by desktop environments)
eval "$(ssh-agent -s)"
# Output: Agent pid 12345

# Add your key (will prompt for passphrase if set)
ssh-add ~/.ssh/id_ed25519

# List loaded keys (shows fingerprints)
ssh-add -l

# Remove all keys from agent
ssh-add -D

# macOS: persist in Keychain across reboots
ssh-add --apple-use-keychain ~/.ssh/id_ed25519

# List keys stored in macOS Keychain
ssh-add --apple-load-keychain
```

### Auto-start Agent in Shell Profile

Add to `~/.zshrc` or `~/.bashrc`:

```bash
# Auto-start SSH agent and add key if not already running
if [ -z "$SSH_AUTH_SOCK" ]; then
    eval "$(ssh-agent -s)" > /dev/null
    ssh-add ~/.ssh/id_ed25519 2>/dev/null
fi
```

---

## ~/.ssh/config — Multiple Identities

Use different keys for different hosts or GitHub accounts:

```
# ~/.ssh/config

# Personal GitHub account
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    AddKeysToAgent yes
    IdentitiesOnly yes          # only use the specified key (do not try others)

# Work GitHub account (different GitHub org)
Host github-work
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_work
    AddKeysToAgent yes
    IdentitiesOnly yes

# GitLab
Host gitlab.com
    HostName gitlab.com
    User git
    IdentityFile ~/.ssh/id_ed25519_gitlab
    AddKeysToAgent yes

# Self-hosted GitHub Enterprise
Host github.mycompany.com
    HostName github.mycompany.com
    User git
    IdentityFile ~/.ssh/id_ed25519_enterprise
    Port 22
```

With the `github-work` alias, use it in Git remotes:

```bash
# Clone using the work alias
git clone git@github-work:myorg/repo.git

# Add remote using the alias
git remote add origin git@github-work:myorg/repo.git

# Verify which identity will be used
ssh -T git@github-work
# Expected: Hi workuser! You've successfully authenticated...
```

---

## Per-Repository Git Configuration

When using multiple GitHub accounts, configure the correct email per repository:

```bash
# Inside a work repository
git config user.email "alice@mycompany.com"
git config user.name "Alice Smith"

# Inside a personal project
git config user.email "alice@personal.com"

# Verify
git config user.email
```

Or use conditional includes in `~/.gitconfig`:

```ini
# ~/.gitconfig
[includeIf "gitdir:~/work/"]
    path = ~/.gitconfig-work

# ~/.gitconfig-work
[user]
    email = alice@mycompany.com
    name = Alice Smith (Work)
```

---

## Deploy Keys (Repository-Specific Keys)

Deploy keys are SSH keys scoped to a single repository. Use them for CI/CD pipelines or automated read-only access.

```bash
# Generate a dedicated deploy key (no passphrase for automation)
ssh-keygen -t ed25519 -f ~/.ssh/deploy_myrepo -C "deploy@ci" -N ""

# Print the public key — add to GitHub
cat ~/.ssh/deploy_myrepo.pub
```

On GitHub: Repository → Settings → Deploy keys → Add deploy key
- Title: `CI/CD Pipeline`
- Key: paste public key
- Allow write access: only if the pipeline needs to push

```bash
# Use deploy key in CI: set private key as a GitHub Secret
# In GitHub Actions:
- name: Set up SSH key
  env:
    SSH_KEY: ${{ secrets.DEPLOY_PRIVATE_KEY }}
  run: |
    mkdir -p ~/.ssh
    echo "$SSH_KEY" > ~/.ssh/id_ed25519
    chmod 600 ~/.ssh/id_ed25519
    ssh-keyscan github.com >> ~/.ssh/known_hosts
```

---

## GitHub Actions — SSH Key Best Practices

In CI/CD, prefer OIDC (see [github-workflow.md](github-workflow.md)) over SSH keys where possible. When SSH is needed (e.g., cloning private dependencies):

```yaml
# .github/workflows/ci.yml
- name: Configure SSH for private dependencies
  uses: webfactory/ssh-agent@v0.9.0
  with:
    ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}

# The action starts the agent, adds the key, and sets SSH_AUTH_SOCK
# Subsequent git operations in the workflow can clone private repos
```

---

## Signing Commits with SSH Keys

GitHub supports using your SSH key to sign commits (proves authorship cryptographically):

```bash
# Configure Git to sign commits with your SSH key
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true

# Sign a single commit
git commit -S -m "feat: add secure endpoint"

# Verify signature on a commit
git verify-commit HEAD
git log --show-signature
```

On GitHub: add the same public key as a **Signing Key** (Settings → SSH and GPG keys → New SSH key → Signing Key type).

Signed commits display a "Verified" badge on GitHub.

---

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| `Permission denied (publickey)` | Key not loaded in agent, or wrong key for host | `ssh-add ~/.ssh/id_ed25519`; verify with `ssh -T git@github.com` |
| `WARNING: UNPROTECTED PRIVATE KEY FILE!` | Key file permissions too open | `chmod 600 ~/.ssh/id_ed25519` |
| `Host key verification failed` | GitHub's host key changed or not in known_hosts | `ssh-keyscan github.com >> ~/.ssh/known_hosts` |
| Commits using wrong email | No per-repo config; global config used | `git config user.email "correct@email.com"` in the repo |
| Two GitHub accounts interfere | Both match `github.com` | Use SSH config Host alias (`github-work`) |
| `ssh-add -l` shows nothing | Agent not running | `eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519` |

---

## Debugging SSH

```bash
# Verbose connection — shows which key is tried and why
ssh -vT git@github.com 2>&1 | head -50

# Even more verbose
ssh -vvT git@github.com 2>&1 | grep -E "debug1|Offering|Authentications"

# Verify the remote URL is SSH (not HTTPS)
git remote -v
# Should show: git@github.com:org/repo.git (not https://)

# Switch from HTTPS to SSH
git remote set-url origin git@github.com:org/repo.git

# Test a specific SSH config host
ssh -vT git@github-work 2>&1 | grep -E "IdentityFile|Authentications|Hi"
```

---

## References

- [GitHub: connecting with SSH](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [OpenSSH man page](https://man.openbsd.org/ssh)
- [SSH config reference](https://man.openbsd.org/ssh_config)
- [GitHub signed commits with SSH](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits)
---

← [Previous: GitHub Workflow](./github-workflow.md) | [Home](../README.md) | [Next: AWS →](../05-aws/README.md)
