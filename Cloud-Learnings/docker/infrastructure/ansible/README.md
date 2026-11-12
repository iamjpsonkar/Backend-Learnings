# Ansible Infrastructure

Ansible playbooks for the Cloud-Learnings Lab Platform.

## Quick Start

```bash
# Start iac profile
./run.sh start iac

# Enter Ansible container
docker exec -it cloud-learnings-ansible bash

# Inside container, run playbook
ansible-playbook -i /workspace/inventory /workspace/playbooks/setup.yml

# Run with verbose output
ansible-playbook -i /workspace/inventory /workspace/playbooks/setup.yml -v
```

## Inventory

The inventory uses Docker connection (not SSH) to target running containers.

```bash
# Ping all hosts
ansible -i inventory all -m ping

# Run ad-hoc command
ansible -i inventory postgres -m shell -a "pg_isready"
```

## Idempotency

All playbooks are idempotent — running them multiple times produces the same result.

Run a playbook twice and verify no changes on second run:
```bash
ansible-playbook -i inventory playbooks/setup.yml
# Should show: ok=X changed=X
ansible-playbook -i inventory playbooks/setup.yml
# Should show: ok=X changed=0  (no changes)
```
