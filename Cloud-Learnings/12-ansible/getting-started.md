← [Previous: Ansible](./README.md) | [Home](../README.md) | [Next: Inventory →](./inventory.md)

---

# Getting Started with Ansible

---

## Installation

```bash
# macOS
brew install ansible

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ansible

# pip (any platform)
pip install ansible

# Verify
ansible --version
# ansible [core 2.17.x]
```

---

## Directory Layout

```
my-project/
├── ansible.cfg          # Project-level configuration
├── inventory/
│   ├── hosts.ini        # Static inventory
│   └── group_vars/
│       ├── all.yml
│       └── webservers.yml
├── playbooks/
│   ├── site.yml         # Master playbook
│   ├── webservers.yml
│   └── databases.yml
└── roles/
    ├── common/
    ├── nginx/
    └── postgres/
```

---

## ansible.cfg

```ini
[defaults]
inventory       = ./inventory/hosts.ini
roles_path      = ./roles
host_key_checking = False           # Disable for dev; enable in production
stdout_callback = yaml              # Readable output
interpreter_python = auto_silent
retry_files_enabled = False
forks           = 10                # Parallel connections

[privilege_escalation]
become          = True
become_method   = sudo
become_user     = root

[ssh_connection]
pipelining      = True              # Reduces SSH connections (~30% faster)
ssh_args        = -o ControlMaster=auto -o ControlPersist=60s
```

---

## Simple Inventory

```ini
# inventory/hosts.ini
[webservers]
web1 ansible_host=10.0.1.10
web2 ansible_host=10.0.1.11
web3 ansible_host=10.0.1.12

[databases]
db1  ansible_host=10.0.2.10
db2  ansible_host=10.0.2.11

[loadbalancers]
lb1  ansible_host=10.0.0.10

[production:children]
webservers
databases
loadbalancers

[all:vars]
ansible_user=ubuntu
ansible_ssh_private_key_file=~/.ssh/prod-key.pem
ansible_python_interpreter=/usr/bin/python3
```

---

## Ad-Hoc Commands

```bash
# Ping all hosts (connectivity check)
ansible all -m ping

# Ping a specific group
ansible webservers -m ping

# Run a shell command
ansible webservers -m shell -a "df -h"

# Get OS facts
ansible web1 -m setup -a "filter=ansible_distribution*"

# Install a package
ansible webservers -m apt -a "name=nginx state=present" --become

# Start a service
ansible webservers -m service -a "name=nginx state=started enabled=yes" --become

# Copy a file
ansible webservers -m copy -a "src=./nginx.conf dest=/etc/nginx/nginx.conf" --become

# Restart service (when file changes)
ansible webservers -m service -a "name=nginx state=restarted" --become

# Run against a subset
ansible 'webservers[0]' -m ping         # First host only
ansible 'webservers:!web3' -m ping      # All except web3
ansible 'webservers:&staging' -m ping   # Intersection
```

---

## First Playbook

```yaml
# playbooks/setup-webservers.yml
---
- name: Setup web servers
  hosts: webservers
  become: true
  gather_facts: true

  vars:
    nginx_port: 80
    app_user: deploy
    app_dir: /opt/my-app

  tasks:
    - name: Update apt cache
      ansible.builtin.apt:
        update_cache: true
        cache_valid_time: 3600

    - name: Install required packages
      ansible.builtin.apt:
        name:
          - nginx
          - python3
          - python3-pip
          - git
        state: present

    - name: Create app user
      ansible.builtin.user:
        name: "{{ app_user }}"
        shell: /bin/bash
        create_home: true
        system: true

    - name: Create application directory
      ansible.builtin.file:
        path: "{{ app_dir }}"
        state: directory
        owner: "{{ app_user }}"
        group: "{{ app_user }}"
        mode: "0755"

    - name: Deploy nginx configuration
      ansible.builtin.template:
        src: templates/nginx.conf.j2
        dest: /etc/nginx/sites-available/my-app
        owner: root
        group: root
        mode: "0644"
      notify: Reload nginx

    - name: Enable nginx site
      ansible.builtin.file:
        src: /etc/nginx/sites-available/my-app
        dest: /etc/nginx/sites-enabled/my-app
        state: link
      notify: Reload nginx

    - name: Ensure nginx is started and enabled
      ansible.builtin.service:
        name: nginx
        state: started
        enabled: true

  handlers:
    - name: Reload nginx
      ansible.builtin.service:
        name: nginx
        state: reloaded
```

---

## Running Playbooks

```bash
# Syntax check (no connection required)
ansible-playbook playbooks/setup-webservers.yml --syntax-check

# Dry run — show what would change (check mode)
ansible-playbook playbooks/setup-webservers.yml --check --diff

# Run
ansible-playbook playbooks/setup-webservers.yml

# Run with extra variables
ansible-playbook playbooks/setup-webservers.yml \
    -e "nginx_port=8080" \
    -e "environment=staging"

# Limit to specific hosts or groups
ansible-playbook playbooks/setup-webservers.yml --limit web1
ansible-playbook playbooks/setup-webservers.yml --limit "webservers:!web3"

# Run only tasks with specific tags
ansible-playbook playbooks/setup-webservers.yml --tags nginx
ansible-playbook playbooks/setup-webservers.yml --skip-tags debug

# Step-by-step confirmation
ansible-playbook playbooks/setup-webservers.yml --step

# Verbose output (up to -vvvv)
ansible-playbook playbooks/setup-webservers.yml -v
```

---

## References

- [Getting started guide](https://docs.ansible.com/ansible/latest/getting_started/index.html)
- [ansible-playbook CLI](https://docs.ansible.com/ansible/latest/cli/ansible-playbook.html)
- [Configuration settings](https://docs.ansible.com/ansible/latest/reference_appendices/config.html)

---

← [Previous: Ansible](./README.md) | [Home](../README.md) | [Next: Inventory →](./inventory.md)
