← [Previous: Vault](./vault.md) | [Home](../README.md) | [Next: Best Practices →](./best-practices.md)

---

# Common Ansible Modules

Ansible ships with 3,000+ built-in modules. This page covers the most commonly used modules organized by category.

---

## Package Management

```yaml
# apt (Debian/Ubuntu)
- ansible.builtin.apt:
    name: "{{ item }}"
    state: present           # present | absent | latest
    update_cache: true
    cache_valid_time: 3600
  loop:
    - nginx
    - python3-pip
    - git

# yum / dnf (RHEL/CentOS/Amazon Linux)
- ansible.builtin.dnf:
    name: httpd
    state: latest

# Generic package (delegates to OS package manager)
- ansible.builtin.package:
    name: curl
    state: present

# pip (Python packages)
- ansible.builtin.pip:
    name:
      - flask
      - gunicorn
    state: present
    virtualenv: /opt/my-app/venv
    virtualenv_python: python3.12
```

---

## File Operations

```yaml
# Create directory
- ansible.builtin.file:
    path: /opt/my-app/logs
    state: directory
    owner: deploy
    group: deploy
    mode: "0755"
    recurse: true   # Apply recursively

# Create symlink
- ansible.builtin.file:
    src: /opt/my-app-2.1.0
    dest: /opt/my-app/current
    state: link

# Delete file or directory
- ansible.builtin.file:
    path: /tmp/old-file.txt
    state: absent

# Copy a static file to remote
- ansible.builtin.copy:
    src: files/nginx.conf           # Relative to role files/ or playbook
    dest: /etc/nginx/nginx.conf
    owner: root
    group: root
    mode: "0644"
    backup: true                    # Keep a backup of existing file

# Copy content directly
- ansible.builtin.copy:
    content: "{{ config_content }}"
    dest: /etc/my-app/config.yml
    mode: "0640"

# Render a Jinja2 template
- ansible.builtin.template:
    src: templates/app.conf.j2
    dest: /etc/my-app/app.conf
    owner: my-app
    group: my-app
    mode: "0640"
    validate: /usr/sbin/my-app --config-test %s

# Fetch file from remote to control node
- ansible.builtin.fetch:
    src: /var/log/app/error.log
    dest: logs/{{ inventory_hostname }}-error.log
    flat: true
```

---

## System Operations

```yaml
# Service management
- ansible.builtin.service:
    name: nginx
    state: started       # started | stopped | restarted | reloaded
    enabled: true

# systemd (more options than service)
- ansible.builtin.systemd:
    name: my-app
    state: started
    enabled: true
    daemon_reload: true        # Run systemctl daemon-reload first

# User management
- ansible.builtin.user:
    name: deploy
    uid: 1001
    group: deploy
    groups:
      - sudo
      - www-data
    shell: /bin/bash
    create_home: true
    home: /home/deploy
    system: false
    state: present

# Group management
- ansible.builtin.group:
    name: deploy
    gid: 1001
    state: present

# SSH authorized keys
- ansible.posix.authorized_key:
    user: deploy
    key: "{{ lookup('file', 'files/deploy.pub') }}"
    state: present
    exclusive: false    # true = replace all keys with only this one

# Cron jobs
- ansible.builtin.cron:
    name: "Backup database"
    minute: "0"
    hour: "3"
    job: "/opt/scripts/backup-db.sh >> /var/log/backup.log 2>&1"
    user: deploy
    state: present

# Set hostname
- ansible.builtin.hostname:
    name: "{{ inventory_hostname }}"

# Reboot (with wait for reconnect)
- ansible.builtin.reboot:
    reboot_timeout: 300
    connect_timeout: 10
    test_command: uptime
```

---

## Shell and Command

```yaml
# command module (no shell — safer, no pipes/redirects)
- ansible.builtin.command:
    cmd: /opt/my-app/bin/migrate
    chdir: /opt/my-app
  register: migrate_result
  changed_when: "'Applied 0 migrations' not in migrate_result.stdout"

# shell module (full shell — supports pipes, env, etc.)
- ansible.builtin.shell:
    cmd: |
      set -e
      source /opt/my-app/venv/bin/activate
      python manage.py collectstatic --noinput
    chdir: /opt/my-app
  environment:
    DJANGO_SETTINGS_MODULE: my_app.settings.production
    SECRET_KEY: "{{ vault_secret_key }}"

# raw module (no Python required — runs raw SSH command)
- ansible.builtin.raw: apt-get install -y python3

# script module (run local script on remote host)
- ansible.builtin.script:
    cmd: scripts/install-agent.sh
    creates: /usr/local/bin/my-agent   # Skip if this file exists
```

---

## Git and Archives

```yaml
# Clone/update git repo
- ansible.builtin.git:
    repo: https://github.com/my-org/my-app.git
    dest: /opt/my-app
    version: "v2.1.0"      # branch, tag, or commit SHA
    force: false
    depth: 1               # Shallow clone
  become_user: deploy

# Extract archive
- ansible.builtin.unarchive:
    src: https://releases.my-app.com/my-app-2.1.0.tar.gz
    dest: /opt/
    remote_src: true       # true = URL/path on remote host; false = local path
    creates: /opt/my-app-2.1.0
    owner: deploy
    group: deploy
```

---

## Network

```yaml
# HTTP requests (check URLs, download files)
- ansible.builtin.uri:
    url: https://api.example.com/health
    method: GET
    status_code: 200
    return_content: true
    timeout: 10
    headers:
      Authorization: "Bearer {{ api_token }}"
  register: health_response

# Wait for a port to open
- ansible.builtin.wait_for:
    host: "{{ ansible_host }}"
    port: 5432
    timeout: 60
    state: started

# Wait for file to exist
- ansible.builtin.wait_for:
    path: /var/run/my-app.pid
    state: present
    timeout: 30

# Firewalld
- ansible.posix.firewalld:
    service: http
    permanent: true
    state: enabled
    immediate: true
```

---

## Lineinfile and Blockinfile

```yaml
# Ensure a line is present in a file
- ansible.builtin.lineinfile:
    path: /etc/ssh/sshd_config
    regexp: '^PermitRootLogin'
    line: 'PermitRootLogin no'
    state: present
    backup: true
  notify: Restart sshd

# Ensure a block is present
- ansible.builtin.blockinfile:
    path: /etc/hosts
    marker: "# {mark} ANSIBLE MANAGED BLOCK"
    block: |
      10.0.1.10 web1.internal
      10.0.1.11 web2.internal
      10.0.2.10 db1.internal
    state: present
```

---

## Debug and Assertions

```yaml
# Print a message or variable
- ansible.builtin.debug:
    msg: "Deploying {{ app_version }} to {{ inventory_hostname }}"

- ansible.builtin.debug:
    var: hostvars[inventory_hostname]

# Fail with a custom message
- ansible.builtin.fail:
    msg: "App version {{ app_version }} is not supported on {{ ansible_distribution }}"
  when: app_version is version('2.0', '<')

# Assert conditions
- ansible.builtin.assert:
    that:
      - app_port | int > 0
      - app_port | int < 65535
      - app_version is defined
    fail_msg: "Invalid app configuration"
    success_msg: "Configuration validated"
```

---

## References

- [Module index](https://docs.ansible.com/ansible/latest/collections/index_module.html)
- [ansible.builtin modules](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/index.html)
- [amazon.aws collection](https://docs.ansible.com/ansible/latest/collections/amazon/aws/index.html)
- [community.general collection](https://docs.ansible.com/ansible/latest/collections/community/general/index.html)

---

← [Previous: Vault](./vault.md) | [Home](../README.md) | [Next: Best Practices →](./best-practices.md)
