← [Previous: Playbooks](./playbooks.md) | [Home](../README.md) | [Next: Variables →](./variables.md)

---

# Roles

Roles are the primary way to organize and reuse Ansible content. A role bundles tasks, handlers, variables, files, templates, and defaults into a structured directory.

---

## Role Directory Structure

```
roles/
└── nginx/
    ├── tasks/
    │   ├── main.yml          # Entry point — imported automatically
    │   ├── install.yml
    │   └── configure.yml
    ├── handlers/
    │   └── main.yml          # Handlers available to this role
    ├── templates/
    │   ├── nginx.conf.j2
    │   └── vhost.conf.j2
    ├── files/
    │   └── dhparam.pem       # Static files (no templating)
    ├── vars/
    │   └── main.yml          # Role variables (high precedence)
    ├── defaults/
    │   └── main.yml          # Default values (lowest precedence)
    ├── meta/
    │   └── main.yml          # Role metadata and dependencies
    └── README.md
```

---

## Writing a Role

```yaml
# roles/nginx/defaults/main.yml
---
nginx_version: latest
nginx_port: 80
nginx_ssl_port: 443
nginx_worker_processes: auto
nginx_worker_connections: 1024
nginx_client_max_body_size: "16m"
nginx_keepalive_timeout: 65
nginx_server_name: "_"
nginx_root: /var/www/html
nginx_access_log: /var/log/nginx/access.log
nginx_error_log: /var/log/nginx/error.log
```

```yaml
# roles/nginx/tasks/main.yml
---
- name: Install nginx
  ansible.builtin.import_tasks: install.yml
  tags: [nginx, install]

- name: Configure nginx
  ansible.builtin.import_tasks: configure.yml
  tags: [nginx, config]
```

```yaml
# roles/nginx/tasks/install.yml
---
- name: Install nginx package
  ansible.builtin.package:
    name: "nginx{{ '=' + nginx_version if nginx_version != 'latest' else '' }}"
    state: "{{ 'present' if nginx_version == 'latest' else 'present' }}"

- name: Ensure nginx service is enabled
  ansible.builtin.service:
    name: nginx
    enabled: true
```

```yaml
# roles/nginx/tasks/configure.yml
---
- name: Create nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    owner: root
    group: root
    mode: "0644"
    validate: nginx -t -c %s
  notify: Reload nginx

- name: Create site configuration
  ansible.builtin.template:
    src: vhost.conf.j2
    dest: /etc/nginx/sites-available/{{ nginx_server_name }}
    owner: root
    group: root
    mode: "0644"
  notify: Reload nginx

- name: Enable site
  ansible.builtin.file:
    src: /etc/nginx/sites-available/{{ nginx_server_name }}
    dest: /etc/nginx/sites-enabled/{{ nginx_server_name }}
    state: link
  notify: Reload nginx
```

```yaml
# roles/nginx/handlers/main.yml
---
- name: Reload nginx
  ansible.builtin.service:
    name: nginx
    state: reloaded

- name: Restart nginx
  ansible.builtin.service:
    name: nginx
    state: restarted
```

```jinja2
{# roles/nginx/templates/nginx.conf.j2 #}
user www-data;
worker_processes {{ nginx_worker_processes }};
pid /run/nginx.pid;

events {
    worker_connections {{ nginx_worker_connections }};
}

http {
    sendfile on;
    keepalive_timeout {{ nginx_keepalive_timeout }};
    client_max_body_size {{ nginx_client_max_body_size }};

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    access_log {{ nginx_access_log }};
    error_log {{ nginx_error_log }};

    include /etc/nginx/sites-enabled/*;
}
```

```yaml
# roles/nginx/meta/main.yml
---
galaxy_info:
  author: my-team
  description: Nginx web server role
  license: MIT
  min_ansible_version: "2.14"
  platforms:
    - name: Ubuntu
      versions: ["22.04", "24.04"]
    - name: Debian
      versions: ["11", "12"]

dependencies:
  - role: common   # This role depends on 'common' running first
```

---

## Using Roles

```yaml
# playbooks/site.yml
---
- name: Configure web servers
  hosts: webservers
  become: true

  # Method 1: roles: block (preferred — runs before tasks)
  roles:
    - role: common
    - role: nginx
      vars:
        nginx_port: 8080
        nginx_server_name: api.my-app.com
    - role: my-app
      tags: [app, deploy]

  # Method 2: include_role in tasks (dynamic — can use conditionals/loops)
  tasks:
    - name: Install nginx only on Ubuntu
      ansible.builtin.include_role:
        name: nginx
      when: ansible_distribution == "Ubuntu"

    - name: Deploy per-service config
      ansible.builtin.include_role:
        name: service-config
      vars:
        service_name: "{{ item }}"
      loop:
        - api
        - worker
        - scheduler
```

---

## Ansible Galaxy

Ansible Galaxy is the community hub for sharing roles and collections.

```bash
# Search for a role
ansible-galaxy search nginx --author geerlingguy

# Install a role from Galaxy
ansible-galaxy role install geerlingguy.nginx

# Install from a requirements file
ansible-galaxy install -r requirements.yml

# List installed roles
ansible-galaxy list

# Install a collection
ansible-galaxy collection install amazon.aws community.postgresql

# Show role info
ansible-galaxy info geerlingguy.nginx
```

```yaml
# requirements.yml
---
roles:
  - name: geerlingguy.nginx
    version: "3.2.0"

  - name: my-org.common
    src: git+https://github.com/my-org/ansible-common.git
    version: v1.5.0

  - name: internal-db
    src: https://my-nexus.example.com/repository/ansible-roles/postgres.tar.gz

collections:
  - name: amazon.aws
    version: ">=7.0.0,<8.0.0"
  - name: community.postgresql
    version: "~=3.0"
  - name: ansible.posix
```

---

## Creating a Role with ansible-galaxy

```bash
# Scaffold a new role
ansible-galaxy role init roles/my-app

# Structure created:
# roles/my-app/
# ├── defaults/main.yml
# ├── files/
# ├── handlers/main.yml
# ├── meta/main.yml
# ├── README.md
# ├── tasks/main.yml
# ├── templates/
# ├── tests/
# │   ├── inventory
# │   └── test.yml
# └── vars/main.yml
```

---

## References

- [Roles documentation](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html)
- [Ansible Galaxy](https://galaxy.ansible.com/)
- [geerlingguy roles](https://galaxy.ansible.com/geerlingguy) (popular reference implementations)

---

← [Previous: Playbooks](./playbooks.md) | [Home](../README.md) | [Next: Variables →](./variables.md)
