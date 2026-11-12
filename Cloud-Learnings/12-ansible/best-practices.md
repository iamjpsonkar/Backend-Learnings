← [Previous: Modules](./modules.md) | [Home](../README.md) | [Next: CI/CD & GitOps (Batch 19) →](../13-cicd-gitops/README.md)

---

# Best Practices

---

## Project Structure

```
my-infrastructure/
├── ansible.cfg
├── requirements.yml           # Galaxy dependencies
├── site.yml                   # Master playbook (imports all others)
├── inventory/
│   ├── production/
│   │   ├── hosts.yml
│   │   ├── group_vars/
│   │   │   ├── all/
│   │   │   │   ├── vars.yml
│   │   │   │   └── vault.yml  # Encrypted
│   │   │   └── webservers.yml
│   │   └── host_vars/
│   └── staging/
│       ├── hosts.yml
│       └── group_vars/
├── playbooks/
│   ├── site.yml
│   ├── webservers.yml
│   ├── databases.yml
│   └── deploy-app.yml
└── roles/
    ├── common/
    ├── nginx/
    ├── postgresql/
    └── my-app/
```

---

## Idempotency

Every task must be safe to run multiple times — the result should be the same whether it runs once or ten times.

```yaml
# BAD — not idempotent: appends every time
- ansible.builtin.shell: echo "export PATH=/opt/my-app/bin:$PATH" >> ~/.bashrc

# GOOD — idempotent: only adds if not present
- ansible.builtin.lineinfile:
    path: ~/.bashrc
    line: 'export PATH=/opt/my-app/bin:$PATH'
    regexp: 'my-app/bin'
    state: present

# BAD — changed_when incorrectly always true
- ansible.builtin.command: /opt/my-app/bin/cache-clear
  # This task is always "changed" even if cache was empty

# GOOD — use changed_when to reflect actual change
- ansible.builtin.command: /opt/my-app/bin/cache-clear
  register: cache_result
  changed_when: "'Cleared' in cache_result.stdout"
  failed_when: cache_result.rc not in [0, 2]  # rc 2 = nothing to clear
```

---

## Naming Conventions

```yaml
# BAD — vague names
- apt:
    name: nginx
    state: present

- command: /opt/deploy.sh

# GOOD — descriptive, use FQCN (fully qualified collection names)
- name: Install nginx web server
  ansible.builtin.apt:
    name: nginx
    state: present

- name: Run application deployment script
  ansible.builtin.command:
    cmd: /opt/deploy.sh {{ app_version }}
    chdir: /opt/my-app
```

---

## Variable Naming

```yaml
# Use role-prefixed names to avoid collisions across roles
# BAD
port: 8080
user: deploy

# GOOD
my_app_port: 8080
my_app_user: deploy

# Use vault_ prefix for encrypted variables
vault_db_password: "..."
db_password: "{{ vault_db_password }}"
```

---

## Tags Strategy

```yaml
# Tag tasks by function
- name: Install packages
  ansible.builtin.apt:
    name: nginx
  tags: [nginx, install, packages]

- name: Configure nginx
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
  tags: [nginx, config]

- name: Ensure nginx is running
  ansible.builtin.service:
    name: nginx
    state: started
  tags: [nginx, service]

# Tag plays for selective runs
- name: Deploy application
  hosts: webservers
  tags: [app, deploy]

  roles:
    - role: nginx
      tags: [nginx]
    - role: my-app
      tags: [app]
```

```bash
# Common tag patterns
ansible-playbook site.yml --tags install     # Initial setup
ansible-playbook site.yml --tags config      # Config changes only
ansible-playbook site.yml --tags deploy      # App deploy only
ansible-playbook site.yml --skip-tags debug  # Skip verbose tasks in prod
```

---

## Rolling Updates

```yaml
# serial controls how many hosts run at once
- name: Rolling deploy to web servers
  hosts: webservers
  serial: "25%"     # Update 25% of hosts at a time
  # serial: 2       # Exactly 2 hosts at a time
  # serial: [1, 5, "100%"]  # 1 first, then 5, then rest

  max_fail_percentage: 20   # Abort if >20% of hosts fail

  tasks:
    - name: Remove from load balancer
      ansible.builtin.uri:
        url: "http://{{ lb_host }}/deregister/{{ inventory_hostname }}"
        method: POST

    - name: Deploy new version
      ansible.builtin.include_tasks: tasks/deploy.yml

    - name: Health check
      ansible.builtin.uri:
        url: "http://{{ ansible_host }}:{{ app_port }}/health"
        status_code: 200
      retries: 5
      delay: 5

    - name: Re-add to load balancer
      ansible.builtin.uri:
        url: "http://{{ lb_host }}/register/{{ inventory_hostname }}"
        method: POST
```

---

## Testing with Molecule

Molecule is the standard tool for testing Ansible roles.

```bash
# Install
pip install molecule molecule-docker

# Initialize Molecule for a role
cd roles/nginx
molecule init scenario

# Role structure after init:
# roles/nginx/molecule/default/
# ├── converge.yml    # Playbook to apply the role
# ├── molecule.yml    # Molecule configuration
# └── verify.yml      # Tests to run after converge
```

```yaml
# roles/nginx/molecule/default/molecule.yml
---
dependency:
  name: galaxy

driver:
  name: docker

platforms:
  - name: instance-ubuntu
    image: geerlingguy/docker-ubuntu2204-ansible:latest
    pre_build_image: true

  - name: instance-debian
    image: geerlingguy/docker-debian12-ansible:latest
    pre_build_image: true

provisioner:
  name: ansible
  inventory:
    host_vars:
      instance-ubuntu:
        nginx_port: 8080

verifier:
  name: ansible
```

```yaml
# roles/nginx/molecule/default/converge.yml
---
- name: Converge
  hosts: all
  become: true

  roles:
    - role: nginx
      vars:
        nginx_port: 8080
```

```yaml
# roles/nginx/molecule/default/verify.yml
---
- name: Verify
  hosts: all
  gather_facts: false

  tasks:
    - name: Check nginx is running
      ansible.builtin.service_facts:

    - name: Assert nginx is active
      ansible.builtin.assert:
        that:
          - "'nginx' in services"
          - "services['nginx'].state == 'running'"
        fail_msg: "nginx is not running"

    - name: Check nginx responds on port 8080
      ansible.builtin.uri:
        url: http://localhost:8080/
        status_code: [200, 301, 302]
```

```bash
# Run full test cycle: create → converge → verify → destroy
molecule test

# Individual stages
molecule create
molecule converge
molecule verify
molecule destroy

# Enter instance for debugging
molecule login --host instance-ubuntu
```

---

## Linting with ansible-lint

```bash
# Install
pip install ansible-lint

# Lint a playbook
ansible-lint playbooks/site.yml

# Lint all playbooks and roles
ansible-lint

# Custom rules via .ansible-lint
```

```yaml
# .ansible-lint
---
exclude_paths:
  - .cache/
  - molecule/

warn_list:
  - yaml[line-length]

skip_list:
  - no-changed-when   # Allow on legacy tasks

rules:
  yaml:
    line-length:
      max: 160
```

---

## Key Rules

1. **Always use FQCN** — `ansible.builtin.apt` not just `apt`
2. **Always set `name:`** on every task and play
3. **Use `become: false` as default** — only escalate where needed
4. **Never store plaintext secrets** — use Ansible Vault or a secrets manager
5. **Test with `--check --diff` before applying to production**
6. **Pin Galaxy role versions** in `requirements.yml`
7. **Tag everything** for selective runs
8. **Use `block/rescue/always`** for error handling in critical tasks

---

## References

- [Best practices guide](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
- [Molecule documentation](https://ansible.readthedocs.io/projects/molecule/)
- [ansible-lint](https://ansible.readthedocs.io/projects/lint/)
- [Ansible style guide](https://docs.ansible.com/ansible/latest/dev_guide/style_guide/index.html)

---

← [Previous: Modules](./modules.md) | [Home](../README.md) | [Next: CI/CD & GitOps (Batch 19) →](../13-cicd-gitops/README.md)
