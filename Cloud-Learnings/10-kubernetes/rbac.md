← [Previous: Storage](./storage.md) | [Home](../README.md) | [Next: Helm →](./helm.md)

---

# Kubernetes RBAC

Role-Based Access Control (RBAC) restricts who can perform which actions on which resources. It is enabled by default in all modern Kubernetes clusters.

---

## Core Objects

| Object | Scope | Purpose |
|--------|-------|---------|
| Role | Namespace | Defines permissions within one namespace |
| ClusterRole | Cluster-wide | Permissions across all namespaces or non-namespaced resources |
| RoleBinding | Namespace | Grants a Role (or ClusterRole) to subjects within a namespace |
| ClusterRoleBinding | Cluster-wide | Grants a ClusterRole to subjects cluster-wide |
| ServiceAccount | Namespace | Identity for Pods running in the cluster |

---

## Role

Grants permissions within a specific namespace.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-reader
  namespace: production
rules:
- apiGroups: [""]                # "" = core API group
  resources: ["pods", "pods/log", "services", "configmaps"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
```

### Common Verbs

| Verb | HTTP method |
|------|------------|
| get | GET (single resource) |
| list | GET (collection) |
| watch | GET with watch parameter |
| create | POST |
| update | PUT |
| patch | PATCH |
| delete | DELETE |
| deletecollection | DELETE (collection) |

---

## ClusterRole

Grants permissions across all namespaces or on cluster-scoped resources (nodes, PVs, namespaces).

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-reader
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["metrics.k8s.io"]
  resources: ["nodes", "pods"]
  verbs: ["get", "list"]
```

### Built-in ClusterRoles

| ClusterRole | Who should have it |
|-------------|-------------------|
| cluster-admin | Full cluster access — superuser |
| admin | Full namespace access |
| edit | Read/write most resources, no RBAC |
| view | Read-only access, no Secrets |
| system:node | Used by kubelets |

---

## RoleBinding

Binds a Role or ClusterRole to subjects within a namespace.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-reader-binding
  namespace: production
subjects:
- kind: User
  name: alice@example.com
  apiGroup: rbac.authorization.k8s.io
- kind: Group
  name: developers
  apiGroup: rbac.authorization.k8s.io
- kind: ServiceAccount
  name: ci-runner
  namespace: ci
roleRef:
  kind: Role             # Role or ClusterRole
  name: app-reader
  apiGroup: rbac.authorization.k8s.io
```

> A RoleBinding can reference a ClusterRole — this scopes the ClusterRole's permissions to the binding's namespace.

---

## ClusterRoleBinding

Grants a ClusterRole cluster-wide.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cluster-admin-team-platform
subjects:
- kind: Group
  name: platform-team
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io
```

---

## ServiceAccount

The identity used by Pods when communicating with the Kubernetes API. Every namespace has a `default` ServiceAccount.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api-server
  namespace: production
  annotations:
    # AWS IRSA — link to IAM role
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789:role/MyPodRole
    # GCP Workload Identity
    iam.gke.io/gcp-service-account: my-sa@my-project.iam.gserviceaccount.com
automountServiceAccountToken: false   # Opt-out if API access not needed
```

### Bind a ServiceAccount to a Role

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: api-server-role
  namespace: production
subjects:
- kind: ServiceAccount
  name: api-server
  namespace: production
roleRef:
  kind: Role
  name: app-reader
  apiGroup: rbac.authorization.k8s.io
```

### Reference in Pod

```yaml
spec:
  serviceAccountName: api-server
  automountServiceAccountToken: true
```

---

## Namespace Isolation Pattern

A common pattern: create a namespace, a dedicated ServiceAccount, and bind least-privilege roles.

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: staging

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: staging-deployer
  namespace: staging

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployer
  namespace: staging
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["services", "configmaps"]
  verbs: ["get", "list", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: staging-deployer-binding
  namespace: staging
subjects:
- kind: ServiceAccount
  name: staging-deployer
  namespace: staging
roleRef:
  kind: Role
  name: deployer
  apiGroup: rbac.authorization.k8s.io
```

---

## Verify Permissions

```bash
# Can I do this?
kubectl auth can-i create deployments --namespace=production
kubectl auth can-i delete pods --namespace=production

# Can a specific user/SA do this?
kubectl auth can-i list secrets --namespace=production \
  --as=alice@example.com

kubectl auth can-i get pods --namespace=staging \
  --as=system:serviceaccount:staging:staging-deployer

# List all permissions for current user
kubectl auth can-i --list --namespace=production

# Who can do what on a resource?
kubectl get rolebindings,clusterrolebindings -A \
  -o custom-columns='KIND:.kind,NAMESPACE:.metadata.namespace,NAME:.metadata.name,ROLE:.roleRef.name,SUBJECTS:.subjects[*].name'
```

---

## Audit Logging

Enable API server audit logging to track who did what:

```yaml
# audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
# Log Secret access at Request level
- level: Request
  resources:
  - group: ""
    resources: ["secrets"]
# Log everything else at Metadata level
- level: Metadata
  omitStages: [RequestReceived]
```

```bash
# kube-apiserver flags
--audit-log-path=/var/log/kubernetes/audit.log
--audit-policy-file=/etc/kubernetes/audit-policy.yaml
--audit-log-maxage=30
--audit-log-maxbackup=10
```

---

## Common RBAC Mistakes

| Mistake | Risk | Fix |
|---------|------|-----|
| Binding `cluster-admin` to app ServiceAccounts | Full cluster compromise if pod is exploited | Use least-privilege custom roles |
| Using `default` ServiceAccount | All pods in namespace share it | Create dedicated SAs per workload |
| `automountServiceAccountToken: true` when API not needed | Token exposed in every pod | Set to false and opt-in only |
| `*` wildcards in rules | Grants access to future resources too | List resources explicitly |
| Not auditing RBAC changes | Silent privilege escalation | Enable audit logging |

---

← [Previous: Storage](./storage.md) | [Home](../README.md) | [Next: Helm →](./helm.md)
