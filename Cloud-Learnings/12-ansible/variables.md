← [Previous: Roles](./roles.md) | [Home](../README.md) | [Next: Vault →](./vault.md)

---

# Variables

Ansible variables store values used in tasks, templates, and conditionals. Understanding precedence prevents unexpected behavior.

---

## Variable Precedence (lowest → highest)

```
1.  role defaults (roles/my-role/defaults/main.yml)
2.  inventory file or script group_vars/all
3.  inventory group_vars/*
4.  inventory file or script host_vars/*
5.  playbook group_vars/all
6.  playbook group_vars/*
7.  playbook host_vars/*
8.  host facts / cached set_facts
9.  play vars
10. play vars_prompt
11. play vars_files
12. role vars (roles/my-role/vars/main.yml)
13. block vars
14. task vars (only for that task)
15. include_vars
16. set_facts / registered vars
17. role params (argument to a role)
18. include params
19. extra vars (-e on CLI)  ← HIGHEST
```

---

## Defining Variables

```yaml
# In a play
- name: Deploy app
  hosts: webservers
  vars:
    app_version: "2.1.0"
    app_port: 8080

  vars_files:
    - vars/app.yml
    - vars/{{ env }}.yml   # Load per-environment file

  tasks:
    - name: Show version
      ansible.builtin.debug:
        msg: "Deploying {{ app_version }} on port {{ app_port }}"
```

```yaml
# group_vars/webservers.yml
app_version: "2.0.0"
app_port: 80
log_level: INFO

app_config:
  max_workers: 8
  timeout_seconds: 30
  allowed_hosts:
    - api.my-app.com
    - internal.my-app.com
```

---

## Variables in Templates (Jinja2)

```jinja2
{# templates/config.yml.j2 #}
app:
  version: {{ app_version }}
  port: {{ app_port }}
  log_level: {{ log_level | default('WARNING') }}
  debug: {{ (env == 'development') | bool }}

database:
  host: {{ db_host }}
  port: {{ db_port | default(5432) | int }}
  name: {{ db_name }}
  # Never log the password
  password: {{ db_password }}

workers: {{ ansible_processor_vcpus | default(2) * 2 }}
```

---

## Registered Variables

```yaml
- name: Check if application is installed
  ansible.builtin.command: which my-app
  register: which_result
  changed_when: false
  failed_when: false

- name: Debug result
  ansible.builtin.debug:
    var: which_result

# which_result contains:
# {
#   "cmd": "which my-app",
#   "stdout": "/usr/local/bin/my-app",
#   "stderr": "",
#   "rc": 0,
#   "changed": false
# }

- name: Install if not found
  ansible.builtin.apt:
    name: my-app
    state: present
  when: which_result.rc != 0

- name: Get current version
  ansible.builtin.command: my-app --version
  register: version_output
  changed_when: false

- name: Show version
  ansible.builtin.debug:
    msg: "Current version: {{ version_output.stdout | regex_search('[0-9]+\\.[0-9]+\\.[0-9]+') }}"
```

---

## Facts

Facts are variables automatically gathered about managed hosts.

```yaml
# Facts are gathered by default at the start of each play
- name: Use facts
  ansible.builtin.debug:
    msg: |
      OS: {{ ansible_distribution }} {{ ansible_distribution_version }}
      Arch: {{ ansible_architecture }}
      CPUs: {{ ansible_processor_vcpus }}
      Memory: {{ ansible_memtotal_mb }} MB
      Hostname: {{ ansible_hostname }}
      IP: {{ ansible_default_ipv4.address }}
      Interfaces: {{ ansible_interfaces | join(', ') }}

# Disable fact gathering (faster for playbooks that don't need them)
- name: Fast play without facts
  hosts: webservers
  gather_facts: false
  tasks:
    - name: Quick task
      ansible.builtin.ping:

# Gather only a subset of facts
- name: Minimal facts
  hosts: webservers
  gather_facts: true
  gather_subset:
    - network
    - hardware
    - min
```

```bash
# Get all facts for a host
ansible web1 -m setup

# Filter facts
ansible web1 -m setup -a "filter=ansible_memory*"
ansible web1 -m setup -a "filter=ansible_eth*"
```

---

## set_fact

```yaml
- name: Set computed facts
  ansible.builtin.set_fact:
    app_url: "http://{{ ansible_default_ipv4.address }}:{{ app_port }}"
    is_primary: "{{ inventory_hostname == groups['databases'][0] }}"
    available_memory_gb: "{{ (ansible_memtotal_mb / 1024) | round(1) }}"

# Facts set with cacheable=true persist across plays
- name: Cache facts
  ansible.builtin.set_fact:
    deployment_time: "{{ ansible_date_time.iso8601 }}"
  cacheable: true
```

---

## Lookup Plugins

```yaml
- name: Read file contents
  ansible.builtin.debug:
    msg: "{{ lookup('ansible.builtin.file', '/etc/hostname') }}"

- name: Read env variable
  ansible.builtin.debug:
    msg: "{{ lookup('ansible.builtin.env', 'HOME') }}"

- name: Read from CSV
  ansible.builtin.debug:
    msg: "{{ lookup('ansible.builtin.csvfile', 'alice file=users.csv col=2') }}"

# Use in templates or variable assignment
vars:
  ssh_public_key: "{{ lookup('ansible.builtin.file', '~/.ssh/id_rsa.pub') }}"
  api_token: "{{ lookup('ansible.builtin.env', 'API_TOKEN') }}"
  db_password: "{{ lookup('ansible.builtin.password', '/dev/null length=32 chars=ascii_letters,digits') }}"

# AWS Secrets Manager
  secret: "{{ lookup('amazon.aws.aws_secret', 'prod/my-app/db-password', region='us-east-1') }}"
```

---

## Special Variables

```yaml
# Ansible built-in special variables
- name: Special vars example
  ansible.builtin.debug:
    msg: |
      Current host: {{ inventory_hostname }}
      Short hostname: {{ inventory_hostname_short }}
      All hosts in play: {{ ansible_play_hosts }}
      All groups: {{ groups.keys() | list }}
      My groups: {{ group_names }}
      Number of hosts: {{ ansible_play_hosts | length }}
      Play name: {{ ansible_play_name }}
      Role name: {{ role_name | default('none') }}
```

---

## References

- [Variables documentation](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_variables.html)
- [Magic variables](https://docs.ansible.com/ansible/latest/reference_appendices/special_variables.html)
- [Lookup plugins](https://docs.ansible.com/ansible/latest/plugins/lookup.html)
- [Facts and set_fact](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_vars_facts.html)

---

← [Previous: Roles](./roles.md) | [Home](../README.md) | [Next: Vault →](./vault.md)
