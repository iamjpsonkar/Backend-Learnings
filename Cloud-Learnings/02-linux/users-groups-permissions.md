← [Previous: Filesystem](./filesystem.md) | [Home](../README.md) | [Next: Processes & Services →](./processes-services.md)

---

# Linux Users, Groups, and Permissions

## Users

Every process and file in Linux is owned by a user. Users are identified by a numeric **UID** (User ID). The name is a human-readable alias stored in `/etc/passwd`.

### Key Files

```bash
/etc/passwd   # User accounts: username:x:UID:GID:comment:home:shell
/etc/shadow   # Hashed passwords (root-readable only)
/etc/group    # Group definitions: groupname:x:GID:member1,member2
/etc/sudoers  # Sudo privileges (edit with visudo, never directly)
```

### /etc/passwd Format

```
ubuntu:x:1000:1000:Ubuntu:/home/ubuntu:/bin/bash
│      │ │    │    │       │            └── login shell
│      │ │    │    │       └── home directory
│      │ │    │    └── GECOS comment (full name or description)
│      │ │    └── primary GID
│      │ └── UID
│      └── password (x = stored in /etc/shadow)
└── username
```

### System vs Regular Users

| UID range | Type | Purpose |
|-----------|------|---------|
| 0 | root | Superuser — unrestricted access |
| 1–999 | System users | Services (nginx=33, www-data=33, nobody=65534) |
| 1000+ | Regular users | Human users (ubuntu=1000, ec2-user=1000) |

### User Management Commands

```bash
# View current user
whoami
id                              # UID, GID, and group memberships
id ubuntu                       # info about another user

# Create users
sudo useradd -m -s /bin/bash deploy        # create user with home dir and bash shell
sudo useradd -r -s /bin/false nginx        # create system user (no login)
sudo passwd deploy                          # set password

# Modify users
sudo usermod -aG docker ubuntu             # add ubuntu to docker group (-a = append)
sudo usermod -s /bin/bash ec2-user        # change shell
sudo usermod -L username                   # lock account
sudo usermod -U username                   # unlock account

# Delete users
sudo userdel username                      # delete user (keep home dir)
sudo userdel -r username                   # delete user and home directory

# Switch users
su - username                              # switch to user (full login shell)
sudo -u username command                   # run single command as user
sudo -i                                    # start interactive root shell
```

---

## Groups

Groups allow you to grant the same permissions to multiple users.

```bash
# View groups
groups                          # current user's groups
groups ubuntu                   # groups for specific user
cat /etc/group                  # all group definitions

# Create and manage groups
sudo groupadd developers
sudo gpasswd -a ubuntu developers          # add user to group
sudo gpasswd -d ubuntu developers          # remove user from group

# Important: group changes take effect on next login
# Force current shell to pick up new group without logout:
newgrp docker
```

### Important System Groups

| Group | Grants access to |
|-------|----------------|
| `sudo` / `wheel` | Run commands as root via sudo |
| `docker` | Manage Docker without sudo |
| `adm` | Read system log files in /var/log |
| `www-data` | Web server files |
| `ssl-cert` | TLS private keys |
| `disk` | Raw disk access (dangerous) |

---

## File Permissions

Every file and directory has three permission sets: **owner (u)**, **group (g)**, **others (o)**.

```bash
ls -la /etc/nginx/nginx.conf
-rw-r--r-- 1 root root 2656 Jan 15 10:23 nginx.conf
│││││││││
│││││││└└── Other: r-- (4+0+0 = 4)
│││││└└──── Group: r-- (4+0+0 = 4)
│││└└────── Owner: rw- (4+2+0 = 6)
││└──────── Setuid/Setgid/Sticky
│└───────── Type: - (file), d (dir), l (symlink), b (block), c (char)
└────────── (filler)
```

### Permission Bits

| Symbol | Octal | On files | On directories |
|--------|-------|---------|---------------|
| `r` | 4 | Read file contents | List directory contents |
| `w` | 2 | Write/modify file | Create/delete files inside |
| `x` | 1 | Execute file | Enter directory (cd) |
| `-` | 0 | No permission | No permission |

### chmod — Change Permissions

```bash
# Symbolic mode
chmod u+x script.sh              # add execute for owner
chmod g-w file.txt               # remove write for group
chmod o+r file.txt               # add read for others
chmod a+x script.sh              # add execute for all (a = ugo)
chmod u=rw,g=r,o= secret.conf   # set exact permissions

# Octal mode (most common in practice)
chmod 644 file.txt               # rw-r--r-- (owner rw, group r, others r)
chmod 755 script.sh              # rwxr-xr-x (owner rwx, group rx, others rx)
chmod 700 ~/.ssh                 # rwx------ (owner only)
chmod 600 ~/.ssh/id_rsa          # rw------- (owner read/write only)
chmod 777 /tmp/shared            # rwxrwxrwx (everyone — avoid in production)

# Recursive
chmod -R 755 /var/www/html       # apply to directory and all contents
```

### Common Permission Patterns

| Octal | Symbolic | Use case |
|-------|---------|---------|
| `600` | `rw-------` | SSH private keys, secrets |
| `644` | `rw-r--r--` | Config files, web content |
| `700` | `rwx------` | ~/.ssh directory |
| `750` | `rwxr-x---` | Scripts accessible to group |
| `755` | `rwxr-xr-x` | Executable programs, public directories |
| `770` | `rwxrwx---` | Shared directories for a group |
| `775` | `rwxrwxr-x` | Collaborative directories |

---

## chown — Change Ownership

```bash
# Change owner
sudo chown ubuntu file.txt
sudo chown ubuntu:developers file.txt    # change owner and group
sudo chown :www-data /var/www/html       # change group only

# Recursive
sudo chown -R www-data:www-data /var/www/html
sudo chown -R ubuntu:ubuntu /home/ubuntu/.ssh
```

---

## umask — Default Permissions

`umask` defines which permissions are subtracted from the default when creating new files and directories.

```bash
umask              # view current umask (commonly 022 or 027)
umask 022          # set umask for current session
```

**Calculation:**
- New files default: `666` (rw-rw-rw-)
- New directories default: `777` (rwxrwxrwx)
- Subtract umask: `666 - 022 = 644`, `777 - 022 = 755`

| umask | New files | New directories | Suitable for |
|-------|----------|-----------------|-------------|
| `022` | `644` | `755` | Public servers (default) |
| `027` | `640` | `750` | Shared team environments |
| `077` | `600` | `700` | Sensitive personal files |

---

## sudo — Privilege Escalation

`sudo` allows permitted users to run commands as root (or another user). Configuration is in `/etc/sudoers`, always edited via `visudo` to prevent syntax errors.

```bash
# Basic usage
sudo command                     # run as root
sudo -u postgres psql            # run as postgres user
sudo -i                          # interactive root shell
sudo !!                          # re-run last command with sudo (bash trick)

# View sudo privileges
sudo -l                          # list what current user can do
sudo -l -U username              # check another user's sudo rights

# /etc/sudoers format
# user  host=(run-as)  commands
ubuntu  ALL=(ALL:ALL)  ALL       # full sudo (typical for admin user)
deploy  ALL=(ALL)  NOPASSWD: /bin/systemctl restart nginx   # specific command no password
%developers  ALL=(ALL)  NOPASSWD: /usr/bin/docker           # group-based
```

### /etc/sudoers.d/ Drop-in Files

Instead of editing `/etc/sudoers` directly, add files to `/etc/sudoers.d/`:

```bash
# Create a drop-in for the deploy user
sudo bash -c 'cat > /etc/sudoers.d/deploy << EOF
deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart myapp, /bin/systemctl status myapp
EOF'
sudo chmod 440 /etc/sudoers.d/deploy
```

---

## Special Permission Bits

### SUID (Set User ID) — Octal 4xxx

When set on an executable, the file runs with the **owner's** UID, not the caller's.

```bash
ls -l /usr/bin/passwd
-rwsr-xr-x 1 root root 68208 /usr/bin/passwd
     ^
     s = SUID set (runs as root even when called by regular user)

# Set/remove SUID
chmod u+s /usr/bin/myapp
chmod 4755 /usr/bin/myapp
chmod u-s /usr/bin/myapp       # remove SUID

# Find all SUID files (security audit)
find / -perm /4000 -type f 2>/dev/null
```

### SGID (Set Group ID) — Octal 2xxx

On executables: runs with the **group's** GID.
On directories: new files inherit the directory's group (useful for shared dirs).

```bash
chmod g+s /shared/project       # new files in this dir get 'project' group
chmod 2775 /shared/project

# Find SGID files
find / -perm /2000 -type f 2>/dev/null
```

### Sticky Bit — Octal 1xxx

On directories: users can only delete files they own, even if they have write permission on the directory.

```bash
ls -ld /tmp
drwxrwxrwt 12 root root 4096 /tmp
         ^
         t = sticky bit set

chmod +t /shared/uploads         # enable sticky bit
chmod 1777 /tmp                  # standard /tmp permissions
```

---

## Cloud-Specific Patterns

### EC2 Default Users

| AMI | Default user | Notes |
|-----|-------------|-------|
| Amazon Linux 2 / 2023 | `ec2-user` | Has passwordless sudo |
| Ubuntu | `ubuntu` | Has passwordless sudo |
| RHEL / CentOS | `ec2-user` | Has passwordless sudo |
| Debian | `admin` | Has passwordless sudo |
| SUSE | `ec2-user` | Has passwordless sudo |

### Adding Authorized Keys for Automation

```bash
# Create deploy user with SSH access (no password login)
sudo useradd -m -s /bin/bash -G sudo deploy
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
echo "ssh-rsa AAAA... deploy-key" | sudo tee /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh
```

### Locking Down SSH (Post-Deployment)

```bash
# In /etc/ssh/sshd_config — restrict access
PermitRootLogin no
PasswordAuthentication no
AllowUsers ubuntu deploy
MaxAuthTries 3
```

---

## References

- [Linux man pages: chmod(1)](https://man7.org/linux/man-pages/man1/chmod.1.html)
- [Linux man pages: useradd(8)](https://man7.org/linux/man-pages/man8/useradd.8.html)
- [sudoers(5) manual](https://man7.org/linux/man-pages/man5/sudoers.5.html)
- [SSH hardening guide](https://www.ssh.com/academy/ssh/config)
---

← [Previous: Filesystem](./filesystem.md) | [Home](../README.md) | [Next: Processes & Services →](./processes-services.md)
