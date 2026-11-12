← [Previous: Workloads](./workloads.md) | [Home](../README.md) | [Next: ConfigMaps & Secrets →](./configmaps-secrets.md)

---

# Kubernetes Services & Ingress

Services provide stable network endpoints for Pods. Ingress manages HTTP/HTTPS routing into the cluster.

---

## Service Types

### ClusterIP (default)

Exposes the Service on an internal cluster IP. Only reachable from within the cluster.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: production
spec:
  type: ClusterIP
  selector:
    app: my-app          # Routes to Pods with this label
  ports:
  - name: http
    port: 80             # Service port (what clients connect to)
    targetPort: 8080     # Container port
    protocol: TCP
```

```bash
# DNS: my-app.production.svc.cluster.local
curl http://my-app.production.svc.cluster.local
curl http://my-app              # Same namespace shorthand
```

### NodePort

Exposes the Service on each Node's IP at a static port (30000–32767). Accessible from outside the cluster.

```yaml
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
    nodePort: 30080      # Optional — auto-assigned if omitted
```

Access: `http://<any-node-ip>:30080`

> NodePort is rarely used in production. Prefer LoadBalancer or Ingress.

### LoadBalancer

Provisions a cloud provider load balancer. The cloud controller manager creates the LB and routes traffic to NodePorts.

```yaml
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - port: 443
    targetPort: 8443
  annotations:
    # AWS NLB
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
    # GCP
    cloud.google.com/load-balancer-type: "External"
    # Azure
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
```

```bash
kubectl get svc my-app
# EXTERNAL-IP shows the provisioned LB address
```

### ExternalName

Maps a Service to an external DNS name. Useful for referencing external services with a cluster-internal name.

```yaml
spec:
  type: ExternalName
  externalName: my-database.rds.amazonaws.com
```

Cluster Pods resolve `my-db.default.svc.cluster.local` → CNAME → `my-database.rds.amazonaws.com`.

### Headless Service

A ClusterIP Service with `clusterIP: None`. Returns the individual Pod IPs directly from DNS instead of a virtual IP. Required by StatefulSets.

```yaml
spec:
  clusterIP: None
  selector:
    app: postgres
  ports:
  - port: 5432
```

DNS resolves `postgres-headless` to all Pod IPs. Individual Pods addressable as `postgres-0.postgres-headless.default.svc.cluster.local`.

---

## Endpoints and EndpointSlices

The controller automatically creates EndpointSlices listing the Pod IPs backing a Service. You can inspect them to debug routing issues.

```bash
kubectl get endpointslices -l kubernetes.io/service-name=my-app
kubectl describe endpointslices my-app-xxxxx
```

---

## Ingress

Ingress manages external HTTP/HTTPS access to Services. It provides:
- Host-based routing (`api.example.com`, `app.example.com`)
- Path-based routing (`/api/`, `/admin/`)
- TLS termination
- Rewrite rules, rate limiting, authentication (depends on controller)

An **Ingress Controller** must be deployed — the Ingress resource is just a configuration object.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - app.example.com
    secretName: app-tls-cert      # TLS secret (cert + key)
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
  - host: admin.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: admin-service
            port:
              number: 80
```

### Path Types

| pathType | Behavior |
|----------|----------|
| Exact | Only `/api` matches, not `/api/` |
| Prefix | `/api` matches `/api`, `/api/`, `/api/v1` |
| ImplementationSpecific | Controller-defined behaviour |

---

## Ingress Controllers

| Controller | Notes |
|------------|-------|
| ingress-nginx | Most widely used, feature-rich |
| Traefik | Dynamic config, good for microservices |
| AWS ALB Ingress Controller | Creates real ALBs per Ingress |
| GCE Ingress Controller | GCP HTTP(S) LB (GKE default) |
| Kong | API gateway capabilities |
| Istio Gateway | Service mesh integration |

### Install ingress-nginx (Helm)

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2
```

---

## TLS / HTTPS

### Manual TLS Secret

```bash
# Create secret from cert and key files
kubectl create secret tls app-tls-cert \
  --cert=tls.crt \
  --key=tls.key \
  -n production
```

### cert-manager (automatic TLS from Let's Encrypt)

```yaml
# ClusterIssuer for Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx

---
# Ingress references the issuer
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - app.example.com
    secretName: app-tls-cert    # cert-manager auto-creates this
```

```bash
# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

---

## NetworkPolicy

Controls which Pods can communicate with which. Default: all Pods can reach all other Pods.

```yaml
# Deny all ingress to Pods in the production namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: production
spec:
  podSelector: {}           # Applies to ALL Pods in namespace
  policyTypes:
  - Ingress

---
# Allow only api Pods to reach db Pods on port 5432
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-db
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: db
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432
```

> NetworkPolicy requires a CNI that supports it (Calico, Cilium, Weave). Flannel does not enforce NetworkPolicy.

---

## Service Discovery

```bash
# Within the same namespace
curl http://my-svc
curl http://my-svc:8080

# Cross-namespace
curl http://my-svc.other-namespace
curl http://my-svc.other-namespace.svc.cluster.local

# From a Pod — check DNS resolution
kubectl exec -it my-pod -- nslookup my-svc
kubectl exec -it my-pod -- curl -v http://my-svc/healthz
```

---

← [Previous: Workloads](./workloads.md) | [Home](../README.md) | [Next: ConfigMaps & Secrets →](./configmaps-secrets.md)
