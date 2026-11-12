← [Previous: OpenTofu](../11-terraform-opentofu/opentofu.md) | [Home](../README.md) | [Next: Getting Started →](./getting-started.md)

---

# Ansible

Ansible is an agentless configuration management, application deployment, and IT automation tool. It communicates over SSH (Linux) or WinRM (Windows) and uses YAML-based playbooks.

---

## Why Ansible?

| Feature | Description |
|---------|-------------|
| **Agentless** | Only requires SSH/Python on managed nodes |
| **Idempotent** | Running playbooks multiple times produces the same result |
| **Human-readable** | YAML playbooks are self-documenting |
| **Batteries included** | 3,000+ built-in modules for packages, files, services, cloud APIs |
| **Extensible** | Custom modules, plugins, and roles via Ansible Galaxy |

---

## Ansible vs Terraform

| | Terraform | Ansible |
|--|-----------|---------|
| Primary use | Infrastructure provisioning | Configuration management / app deployment |
| State | Stateful (state file) | Stateless (idempotent tasks) |
| Language | HCL | YAML |
| Execution model | Declarative (desired state) | Procedural (ordered tasks) |
| Agentless | Yes | Yes |
| Use together? | ✅ Provision with Terraform → configure with Ansible |

---

## How Ansible Works

```
Control Node                        Managed Nodes
   │                                      │
   ├── inventory.ini  ──────────────→  [web1, web2, web3]
   ├── playbook.yml   ── SSH/SFTP  →  [db1]
   └── roles/         ──────────────→  [cache1]

Ansible pushes tasks to managed nodes over SSH.
No agent runs on managed nodes — only Python is required.
```

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Inventory** | List of managed hosts, organized into groups |
| **Playbook** | Ordered set of plays (YAML) to run against inventory |
| **Play** | Maps a group of hosts to a set of tasks |
| **Task** | Single unit of work using a module |
| **Module** | Idempotent action: install package, copy file, restart service |
| **Role** | Reusable bundle of tasks, files, templates, and variables |
| **Handler** | Task triggered by `notify` — runs once at end of play |
| **Vault** | Encrypted storage for secrets within playbooks |
| **Fact** | Host metadata gathered automatically (OS, IPs, memory) |

---

## Topics

| File | Topics |
|------|--------|
| [Getting Started](./getting-started.md) | Install, first playbook, ad-hoc commands |
| [Inventory](./inventory.md) | Static/dynamic inventory, groups, variables |
| [Playbooks](./playbooks.md) | Plays, tasks, handlers, conditionals, loops |
| [Roles](./roles.md) | Role structure, Galaxy, dependencies |
| [Variables](./variables.md) | Variable precedence, facts, lookup plugins |
| [Vault](./vault.md) | Encrypting secrets, using vault in playbooks |
| [Modules](./modules.md) | Common built-in modules reference |
| [Best Practices](./best-practices.md) | Idempotency, tags, Molecule testing, linting |

---

## References

- [Ansible documentation](https://docs.ansible.com/)
- [Ansible Galaxy](https://galaxy.ansible.com/)
- [Molecule (testing)](https://ansible.readthedocs.io/projects/molecule/)
- [AWX / Automation Platform](https://www.ansible.com/products/awx-project/faq)

---

← [Previous: OpenTofu](../11-terraform-opentofu/opentofu.md) | [Home](../README.md) | [Next: Getting Started →](./getting-started.md)
