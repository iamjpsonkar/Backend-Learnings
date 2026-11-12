← [Previous: Inventory](./inventory.md) | [Home](../README.md) | [Next: Roles →](./roles.md)

---

# Playbooks

Playbooks are Ansible's configuration and deployment language. A playbook is a YAML file containing one or more plays, each mapping a host group to a set of tasks.

---

## Playbook Structure

```yaml
---
# playbooks/deploy.yml

# Play 1: Configure load balancers
- name: Configure load balancers
  hosts: loadbalancers         # Target group from inventory
  become: true                 # Escalate privileges (sudo)
  gather_facts: true           # Collect system facts (default: true)
  serial: 1                    # Rolling update: process 1 host at a time
  any_errors_fatal: false      # Continue other hosts if one fails

  pre_tasks:
    - name: Check disk space before deploy
      ansible.builtin.shell: df -h /
      changed_when: false
      register: disk_check

    - name: Fail if low disk space
      ansible.builtin.fail:
        msg: "Insufficient disk space: {{ disk_check.stdout }}"
      when: "'100%' in disk_check.stdout"

  roles:
    - common
    - haproxy

  tasks:
    - name: Reload HAProxy
      ansible.builtin.service:
        name: haproxy
        state: reloaded

  post_tasks:
    - name: Verify HAProxy is running
      ansible.builtin.uri:
        url: "http://localhost/health"
        status_code: 200
      retries: 5
      delay: 3

  handlers:
    - name: Restart haproxy
      ansible.builtin.service:
        name: haproxy
        state: restarted

# Play 2: Deploy application
- name: Deploy application
  hosts: webservers
  become: true
  gather_facts: true

  vars:
    app_version: "{{ deploy_version | default('latest') }}"

  tasks:
    - name: Deploy app
      ansible.builtin.include_tasks: tasks/deploy-app.yml
```

---

## Tasks

```yaml
tasks:
  # Basic task
  - name: Install nginx
    ansible.builtin.apt:
      name: nginx
      state: present

  # Ignore errors for a specific task
  - name: Stop old service (may not exist)
    ansible.builtin.service:
      name: old-service
      state: stopped
    ignore_errors: true

  # Run only on specific OS
  - name: Install on Debian/Ubuntu only
    ansible.builtin.apt:
      name: build-essential
      state: present
    when: ansible_os_family == "Debian"

  # Register output and use it
  - name: Check if config exists
    ansible.builtin.stat:
      path: /etc/my-app/config.yml
    register: config_file

  - name: Create config if missing
    ansible.builtin.template:
      src: config.yml.j2
      dest: /etc/my-app/config.yml
    when: not config_file.stat.exists

  # Notify a handler
  - name: Deploy nginx config
    ansible.builtin.template:
      src: nginx.conf.j2
      dest: /etc/nginx/nginx.conf
    notify: Reload nginx   # Triggers handler at end of play

  # Block + rescue + always (try/except/finally)
  - name: Deploy with error handling
    block:
      - name: Deploy new version
        ansible.builtin.shell: /opt/deploy.sh {{ app_version }}
        args:
          chdir: /opt/my-app
    rescue:
      - name: Roll back on failure
        ansible.builtin.shell: /opt/rollback.sh
    always:
      - name: Clear temp files
        ansible.builtin.file:
          path: /tmp/deploy
          state: absent
```

---

## Handlers

Handlers are tasks triggered by `notify`. They run **once** at the end of a play, regardless of how many tasks notified them.

```yaml
handlers:
  - name: Reload nginx
    ansible.builtin.service:
      name: nginx
      state: reloaded

  - name: Restart nginx
    ansible.builtin.service:
      name: nginx
      state: restarted

  # Chain handlers
  - name: Reload nginx config
    ansible.builtin.command: nginx -s reload
    listen: "web server config changed"   # Multiple tasks can notify this

  # Force handlers to run immediately (not wait until end of play)
  # Use meta module:
  - name: Flush handlers immediately
    ansible.builtin.meta: flush_handlers
```

---

## Conditionals

```yaml
# when: — skip task if condition is false
- name: Install on Ubuntu only
  ansible.builtin.apt:
    name: nginx
    state: present
  when: ansible_distribution == "Ubuntu"

# Multiple conditions (AND)
- name: Install on Ubuntu 22.04 in production
  ansible.builtin.apt:
    name: nginx
    state: present
  when:
    - ansible_distribution == "Ubuntu"
    - ansible_distribution_major_version | int >= 22
    - env == "production"

# OR condition
- name: Install on Debian or Ubuntu
  ansible.builtin.apt:
    name: nginx
    state: present
  when: ansible_distribution == "Ubuntu" or ansible_distribution == "Debian"

# Check registered result
- name: Check if app is running
  ansible.builtin.shell: systemctl is-active my-app
  register: app_status
  changed_when: false
  failed_when: false

- name: Start app if not running
  ansible.builtin.service:
    name: my-app
    state: started
  when: app_status.rc != 0
```

---

## Loops

```yaml
# Simple list loop
- name: Install packages
  ansible.builtin.apt:
    name: "{{ item }}"
    state: present
  loop:
    - nginx
    - python3
    - git
    - curl

# Loop over dicts
- name: Create users
  ansible.builtin.user:
    name: "{{ item.name }}"
    groups: "{{ item.groups }}"
    shell: "{{ item.shell | default('/bin/bash') }}"
  loop:
    - { name: alice, groups: sudo }
    - { name: bob,   groups: www-data }
    - { name: carol, groups: sudo, shell: /bin/zsh }

# Loop with index
- name: Create numbered files
  ansible.builtin.file:
    path: "/tmp/file_{{ index }}"
    state: touch
  loop: "{{ ['a', 'b', 'c'] }}"
  loop_control:
    index_var: index
    label: "{{ item }}"   # Cleaner output

# Loop until (retry)
- name: Wait for service to be ready
  ansible.builtin.uri:
    url: http://localhost:8080/health
    status_code: 200
  register: result
  until: result.status == 200
  retries: 12
  delay: 5

# Loop over dict items
- name: Set sysctl values
  ansible.posix.sysctl:
    name: "{{ item.key }}"
    value: "{{ item.value }}"
    sysctl_set: true
  loop: "{{ sysctl_params | dict2items }}"
```

---

## Include and Import

```yaml
# Static import (parsed at playbook load time)
- ansible.builtin.import_tasks: tasks/common.yml

# Dynamic include (evaluated at runtime — can use variables)
- ansible.builtin.include_tasks: "tasks/{{ ansible_os_family | lower }}.yml"

# Import a full playbook
- ansible.builtin.import_playbook: playbooks/common.yml

# Import a role
- name: Deploy nginx
  ansible.builtin.import_role:
    name: nginx

# Include a role with variables
- name: Deploy app
  ansible.builtin.include_role:
    name: my-app
  vars:
    app_version: "2.0.1"
    app_port: 8080
```

---

## Tags

```yaml
- name: Install nginx
  ansible.builtin.apt:
    name: nginx
    state: present
  tags:
    - nginx
    - install
    - packages

- name: Deploy nginx config
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
  tags:
    - nginx
    - config
```

```bash
# Run only tasks with 'nginx' tag
ansible-playbook site.yml --tags nginx

# Skip tasks with 'packages' tag
ansible-playbook site.yml --skip-tags packages

# Special tags
ansible-playbook site.yml --tags always    # Runs regardless of --tags filter
ansible-playbook site.yml --tags never     # Only runs when explicitly requested
```

---

## References

- [Playbooks guide](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_intro.html)
- [Conditionals](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_conditionals.html)
- [Loops](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_loops.html)
- [Handlers](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_handlers.html)

---

← [Previous: Inventory](./inventory.md) | [Home](../README.md) | [Next: Roles →](./roles.md)
