← [Previous: Getting Started](./getting-started.md) | [Home](../README.md) | [Next: Playbooks →](./playbooks.md)

---

# Inventory

Inventory tells Ansible which hosts to manage and how to connect to them.

---

## Static Inventory (INI)

```ini
# inventory/hosts.ini

# Ungrouped hosts
standalone.example.com

# Named group
[webservers]
web1.example.com
web2.example.com ansible_host=192.168.1.12 ansible_port=2222

# Group with connection vars inline
[databases]
db1 ansible_host=10.0.2.10 ansible_user=ec2-user ansible_ssh_private_key_file=~/.ssh/db-key.pem
db2 ansible_host=10.0.2.11

# Children groups — a group of groups
[production:children]
webservers
databases

# Variables for a group
[webservers:vars]
nginx_port=80
app_version=2.1.0

[all:vars]
ansible_python_interpreter=/usr/bin/python3
```

---

## Static Inventory (YAML)

```yaml
# inventory/hosts.yml
all:
  vars:
    ansible_user: ubuntu
    ansible_ssh_private_key_file: ~/.ssh/prod-key.pem
    ansible_python_interpreter: /usr/bin/python3

  children:
    webservers:
      hosts:
        web1:
          ansible_host: 10.0.1.10
          weight: 10
        web2:
          ansible_host: 10.0.1.11
          weight: 20
      vars:
        nginx_port: 80
        app_dir: /opt/my-app

    databases:
      hosts:
        db1:
          ansible_host: 10.0.2.10
        db2:
          ansible_host: 10.0.2.11
          db_role: replica

    production:
      children:
        webservers:
        databases:
```

---

## Group Variables (group_vars/)

Variables in `group_vars/` are automatically loaded based on group membership.

```
inventory/
├── hosts.ini
├── group_vars/
│   ├── all.yml           # Applied to every host
│   ├── all/
│   │   ├── vars.yml
│   │   └── vault.yml     # Encrypted with ansible-vault
│   ├── webservers.yml
│   ├── databases.yml
│   └── production.yml
└── host_vars/
    ├── web1.yml           # Variables for specific host
    └── db1.yml
```

```yaml
# inventory/group_vars/all.yml
---
ntp_servers:
  - 0.pool.ntp.org
  - 1.pool.ntp.org

log_dir: /var/log/my-app
timezone: America/New_York

common_packages:
  - curl
  - wget
  - htop
  - vim
  - python3
```

```yaml
# inventory/group_vars/webservers.yml
---
nginx_port: 80
nginx_worker_processes: auto
app_dir: /opt/my-app
app_user: deploy

ssl_certificate: /etc/ssl/certs/my-app.crt
ssl_certificate_key: /etc/ssl/private/my-app.key
```

```yaml
# inventory/host_vars/db1.yml
---
db_role: primary
db_max_connections: 500
db_shared_buffers: "4GB"
```

---

## Dynamic Inventory

Dynamic inventory scripts/plugins query APIs (AWS, GCP, Azure, etc.) to generate host lists at runtime.

### AWS EC2 Plugin

```yaml
# inventory/aws_ec2.yml
plugin: amazon.aws.aws_ec2
regions:
  - us-east-1
  - us-west-2
filters:
  instance-state-name: running
  tag:Environment: production
keyed_groups:
  - key: tags.Role
    prefix: role
  - key: placement.region
    prefix: region
  - key: instance_type
    prefix: type
compose:
  ansible_host: public_ip_address
  ansible_user: "'ec2-user'"  # or ubuntu for Ubuntu AMIs
hostnames:
  - tag:Name
  - dns-name
```

```bash
# Use dynamic inventory
ansible-inventory -i inventory/aws_ec2.yml --list
ansible-inventory -i inventory/aws_ec2.yml --graph

# Run playbook with dynamic inventory
ansible-playbook -i inventory/aws_ec2.yml playbooks/deploy.yml
```

### GCP Plugin

```yaml
# inventory/gcp_compute.yml
plugin: google.cloud.gcp_compute
projects:
  - my-app-prod-123456
filters:
  - status = RUNNING
  - labels.environment = production
keyed_groups:
  - key: labels.role
    prefix: role
  - key: zone
    prefix: zone
auth_kind: application
```

---

## Multiple Inventory Sources

```bash
# Pass multiple inventory files/directories
ansible-playbook -i inventory/hosts.ini -i inventory/aws_ec2.yml playbooks/deploy.yml

# Or configure in ansible.cfg
# [defaults]
# inventory = inventory/

# Ansible auto-loads all files in a directory (YAML, INI, and plugins)
```

---

## Patterns and Limits

```bash
# Run against all hosts
ansible all -m ping

# Specific group
ansible webservers -m ping

# Specific host
ansible web1 -m ping

# Multiple groups (union)
ansible 'webservers:databases' -m ping

# Intersection (hosts in both groups)
ansible 'webservers:&production' -m ping

# Exclusion
ansible 'webservers:!web1' -m ping

# Wildcard
ansible 'web*' -m ping

# Regex (prefix with ~)
ansible '~web[12].example.com' -m ping

# Range
ansible 'web[1:3]' -m ping   # web1, web2, web3
```

---

## References

- [Inventory documentation](https://docs.ansible.com/ansible/latest/inventory_guide/intro_inventory.html)
- [Dynamic inventory](https://docs.ansible.com/ansible/latest/inventory_guide/intro_dynamic_inventory.html)
- [aws_ec2 plugin](https://docs.ansible.com/ansible/latest/collections/amazon/aws/aws_ec2_inventory.html)
- [gcp_compute plugin](https://docs.ansible.com/ansible/latest/collections/google/cloud/gcp_compute_inventory.html)

---

← [Previous: Getting Started](./getting-started.md) | [Home](../README.md) | [Next: Playbooks →](./playbooks.md)
