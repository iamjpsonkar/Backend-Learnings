← [Previous: Services & Ingress](./services-ingress.md) | [Home](../README.md) | [Next: Storage →](./storage.md)

---

# Kubernetes ConfigMaps & Secrets

ConfigMaps and Secrets decouple configuration from container images, following the twelve-factor app principle.

---

## ConfigMap

Stores non-sensitive configuration as key-value pairs or files.

### Create a ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: production
data:
  # Key-value pairs
  LOG_LEVEL: "info"
  APP_PORT: "8080"
  FEATURE_FLAGS: "new-ui=true,dark-mode=false"
  # Multi-line file content
  app.properties: |
    server.port=8080
    spring.datasource.url=jdbc:postgresql://postgres:5432/mydb
    cache.ttl=300
  nginx.conf: |
    server {
        listen 80;
        location / {
            proxy_pass http://localhost:8080;
        }
    }
```

```bash
# Imperative creation
kubectl create configmap app-config \
  --from-literal=LOG_LEVEL=info \
  --from-literal=APP_PORT=8080

kubectl create configmap nginx-config --from-file=nginx.conf
kubectl create configmap app-props --from-env-file=.env
```

### Consume as Environment Variables

```yaml
spec:
  containers:
  - name: app
    image: my-app:1.2.3
    # Inject individual keys
    env:
    - name: LOG_LEVEL
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: LOG_LEVEL
    # Inject ALL keys as env vars
    envFrom:
    - configMapRef:
        name: app-config
```

### Consume as Volume Mount

```yaml
spec:
  containers:
  - name: app
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config      # Each key becomes a file
    - name: nginx-config
      mountPath: /etc/nginx/nginx.conf
      subPath: nginx.conf         # Mount single key as a file
  volumes:
  - name: config-volume
    configMap:
      name: app-config
  - name: nginx-config
    configMap:
      name: nginx-config
```

> ConfigMap volume mounts update automatically when the ConfigMap changes (with ~1 minute delay). Environment variable injection does NOT update — requires Pod restart.

---

## Secret

Stores sensitive data. Values are **base64-encoded** (not encrypted) by default. Enable encryption at rest in etcd for real security.

### Secret Types

| Type | Use case |
|------|----------|
| Opaque | Generic key-value secrets (default) |
| kubernetes.io/dockerconfigjson | Docker registry credentials |
| kubernetes.io/tls | TLS certificate and key |
| kubernetes.io/service-account-token | Service account tokens |
| kubernetes.io/ssh-auth | SSH credentials |
| kubernetes.io/basic-auth | Basic authentication |

### Create an Opaque Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
  namespace: production
type: Opaque
stringData:                # Plaintext — kubectl encodes to base64
  password: "super-secret-password"
  url: "postgresql://user:super-secret-password@postgres:5432/mydb"
```

```bash
# Imperative
kubectl create secret generic db-secret \
  --from-literal=password=super-secret-password \
  --from-literal=url=postgresql://user:super-secret-password@postgres:5432/mydb

# From file
kubectl create secret generic tls-secret \
  --from-file=tls.crt --from-file=tls.key

# TLS type
kubectl create secret tls app-tls \
  --cert=tls.crt --key=tls.key

# Docker registry
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com \
  --docker-username=user \
  --docker-password=token
```

### Consume as Environment Variables

```yaml
spec:
  containers:
  - name: app
    env:
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: password
    envFrom:
    - secretRef:
        name: db-secret
```

### Consume as Volume Mount

```yaml
spec:
  containers:
  - name: app
    volumeMounts:
    - name: secrets-volume
      mountPath: /etc/secrets
      readOnly: true
  volumes:
  - name: secrets-volume
    secret:
      secretName: db-secret
      defaultMode: 0400     # Restrict file permissions
```

Files appear at `/etc/secrets/password`, `/etc/secrets/url`.

### Pull from Private Registry

```yaml
spec:
  imagePullSecrets:
  - name: regcred
  containers:
  - name: app
    image: registry.example.com/my-app:1.2.3
```

---

## Encryption at Rest

By default, Secrets are stored in etcd unencrypted (only base64). Enable encryption:

```yaml
# /etc/kubernetes/enc/encryption-config.yaml (on control plane)
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
- resources:
  - secrets
  providers:
  - aescbc:
      keys:
      - name: key1
        secret: <base64-encoded-32-byte-key>
  - identity: {}    # Fallback for reading unencrypted existing secrets
```

```bash
# kube-apiserver flag
--encryption-provider-config=/etc/kubernetes/enc/encryption-config.yaml

# Encrypt all existing secrets
kubectl get secrets --all-namespaces -o json | kubectl replace -f -
```

---

## External Secrets Operator

For production, sync secrets from external stores (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager, Azure Key Vault) into Kubernetes Secrets automatically.

```yaml
# ExternalSecret syncs from AWS Secrets Manager
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: db-secret           # Creates/updates this k8s Secret
    creationPolicy: Owner
  data:
  - secretKey: password       # k8s Secret key
    remoteRef:
      key: prod/myapp/db      # AWS Secrets Manager path
      property: password      # JSON property within the secret
```

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace
```

---

## Sealed Secrets (GitOps pattern)

Encrypt Secrets into `SealedSecret` objects that are safe to commit to Git. Only the in-cluster controller can decrypt them.

```bash
# Install
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets-controller sealed-secrets/sealed-secrets \
  --namespace kube-system

# Install kubeseal CLI
brew install kubeseal

# Seal a secret
kubectl create secret generic db-secret \
  --from-literal=password=my-password \
  --dry-run=client -o yaml | \
  kubeseal --format yaml > sealed-db-secret.yaml

# Commit sealed-db-secret.yaml to Git — safe to do
kubectl apply -f sealed-db-secret.yaml
```

---

## Best Practices

| Practice | Why |
|----------|-----|
| Never commit plain Secrets to Git | They are only base64-encoded, not encrypted |
| Use External Secrets Operator or Sealed Secrets | Real secret management with rotation |
| Enable etcd encryption at rest | Protects secrets if etcd is compromised |
| Set `defaultMode: 0400` on secret volume mounts | Restrict file-level access |
| Use RBAC to limit who can `get`/`list` Secrets | Listing Secrets leaks all values |
| Prefer volume mounts over env vars for secrets | Env vars appear in logs, process listings |
| Rotate secrets regularly | Limit blast radius of exposure |

---

← [Previous: Services & Ingress](./services-ingress.md) | [Home](../README.md) | [Next: Storage →](./storage.md)
