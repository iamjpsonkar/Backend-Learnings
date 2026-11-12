← [Previous: Variables](./variables.md) | [Home](../README.md) | [Next: Modules →](./modules.md)

---

# Ansible Vault

Ansible Vault encrypts sensitive data (passwords, API keys, certificates) at rest using AES-256. Encrypted files can be safely committed to version control.

---

## Encrypting Files

```bash
# Encrypt a new file (prompts for vault password)
ansible-vault create group_vars/production/vault.yml

# Encrypt an existing file
ansible-vault encrypt group_vars/production/secrets.yml

# Decrypt a file in place (careful — writes plaintext to disk)
ansible-vault decrypt group_vars/production/secrets.yml

# View encrypted file without decrypting to disk
ansible-vault view group_vars/production/vault.yml

# Edit an encrypted file
ansible-vault edit group_vars/production/vault.yml

# Re-key (change the vault password)
ansible-vault rekey group_vars/production/vault.yml

# Encrypt a single string (for embedding in YAML)
ansible-vault encrypt_string 'super-secret-password' --name db_password
# Output:
# db_password: !vault |
#   $ANSIBLE_VAULT;1.1;AES256
#   3961363134...
```

---

## Vault Variables in Playbooks

```yaml
# group_vars/production/vars.yml — plain variables
---
db_host: 10.0.2.10
db_name: my_app
db_user: my_app
app_port: 8080
log_level: WARNING
```

```yaml
# group_vars/production/vault.yml — encrypted with ansible-vault
---
vault_db_password: "super-secret-db-pass"
vault_api_key: "sk-prod-abc123xyz"
vault_ssl_key: |
  -----BEGIN PRIVATE KEY-----
  MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...
  -----END PRIVATE KEY-----
```

```yaml
# group_vars/production/vars.yml — reference vault vars
---
db_password: "{{ vault_db_password }}"     # Indirection: plain var → vault var
api_key: "{{ vault_api_key }}"
ssl_key: "{{ vault_ssl_key }}"
```

This pattern keeps vault-prefixed names as the encrypted source and exposes clean names elsewhere.

---

## Running Playbooks with Vault

```bash
# Prompt for vault password at runtime
ansible-playbook site.yml --ask-vault-pass

# Use a password file (for CI/CD — file contains only the password)
ansible-playbook site.yml --vault-password-file ~/.vault_pass

# Use an environment variable for the password file path
ANSIBLE_VAULT_PASSWORD_FILE=~/.vault_pass ansible-playbook site.yml

# Or in ansible.cfg:
# [defaults]
# vault_password_file = ~/.vault_pass
```

---

## Multiple Vault IDs

Use multiple vault IDs when different teams own different secrets.

```bash
# Create secrets with a specific vault ID
ansible-vault create --vault-id dev@prompt group_vars/dev/vault.yml
ansible-vault create --vault-id prod@prompt group_vars/production/vault.yml

# Create with a password file
ansible-vault create --vault-id prod@~/.vault_pass_prod group_vars/production/vault.yml

# Encrypt a string with a vault ID
ansible-vault encrypt_string --vault-id prod@~/.vault_pass_prod \
    'secret123' --name db_password

# Run playbook supplying both vault IDs
ansible-playbook site.yml \
    --vault-id dev@~/.vault_pass_dev \
    --vault-id prod@~/.vault_pass_prod
```

---

## Vault in CI/CD

```bash
# Store vault password as a CI secret
# GitHub Actions example — vault password in GitHub Secrets

# .github/workflows/deploy.yml
# - name: Run Ansible
#   env:
#     VAULT_PASSWORD: ${{ secrets.ANSIBLE_VAULT_PASSWORD }}
#   run: |
#     echo "$VAULT_PASSWORD" > /tmp/vault-pass
#     chmod 600 /tmp/vault-pass
#     ansible-playbook site.yml --vault-password-file /tmp/vault-pass
#     rm -f /tmp/vault-pass
```

```yaml
# .github/workflows/deploy.yml
- name: Create vault password file
  run: |
    echo "${{ secrets.ANSIBLE_VAULT_PASSWORD }}" > /tmp/.vault_pass
    chmod 600 /tmp/.vault_pass

- name: Deploy with Ansible
  run: |
    ansible-playbook -i inventory/hosts.ini \
        site.yml \
        --vault-password-file /tmp/.vault_pass \
        -e "env=production"

- name: Remove vault password file
  if: always()
  run: rm -f /tmp/.vault_pass
```

---

## ansible.cfg Integration

```ini
[defaults]
vault_password_file = ~/.ansible_vault_pass

# Multiple vault IDs
# vault_identity_list = dev@~/.vault_pass_dev, prod@~/.vault_pass_prod
```

---

## Best Practices

- **Never commit plaintext secrets** — always encrypt with vault before committing
- **Use the indirection pattern**: `vault_` prefixed vars in vault files, clean names in vars files
- **Separate vault files per environment**: `group_vars/production/vault.yml`, `group_vars/dev/vault.yml`
- **Rotate vault passwords** when team members leave (`ansible-vault rekey`)
- **Use a secrets manager** (HashiCorp Vault, AWS Secrets Manager) with lookup plugins for production — Ansible Vault is for bootstrapping and simpler setups
- **Protect vault password files**: `chmod 600 ~/.vault_pass`, add to `.gitignore`

---

## References

- [Ansible Vault documentation](https://docs.ansible.com/ansible/latest/vault_guide/index.html)
- [Vault best practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
- [HashiCorp Vault lookup plugin](https://docs.ansible.com/ansible/latest/collections/community/hashi_vault/hashi_vault_lookup.html)

---

← [Previous: Variables](./variables.md) | [Home](../README.md) | [Next: Modules →](./modules.md)
