← [Previous: Observability Stack](./observability-stack.md) | [Home](../README.md) | [Next: Data Pipeline →](./data-pipeline.md)

---

# Project: Kubernetes App on EKS

Deploy a multi-service application on Amazon EKS with Helm, horizontal pod autoscaling, ingress with TLS, and GitOps-style deployment using Kustomize overlays.

**Estimated cost:** ~$100–150/month (EKS cluster + worker nodes + ALB)
**Time to complete:** 3–4 hours

---

## Architecture

```
Internet
  │  HTTPS (443)
  ▼
AWS ALB Ingress Controller
  │
  ├── /api/*  → order-api Service (ClusterIP)
  │               └── 3 replicas → HPA (3-10 based on CPU)
  └── /      → frontend Service (ClusterIP)
                  └── 2 replicas

order-api Pod
  ├── app container (FastAPI)
  └── OTel sidecar container

Amazon RDS PostgreSQL (private — accessed via Service ExternalName)
AWS Secrets Manager → External Secrets Operator → Kubernetes Secret
```

---

## Step 1: Create EKS Cluster

```bash
export CLUSTER_NAME="myapp-prod"
export REGION="us-east-1"
export K8S_VERSION="1.29"

# Install eksctl
brew install eksctl  # or download from GitHub releases

# Create cluster (managed node group)
cat > cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: $CLUSTER_NAME
  region: $REGION
  version: "$K8S_VERSION"

iam:
  withOIDC: true  # Required for IRSA (IAM Roles for Service Accounts)

managedNodeGroups:
  - name: workers
    instanceType: t3.medium
    minSize: 2
    maxSize: 10
    desiredCapacity: 3
    privateNetworking: true
    volumeSize: 50
    volumeEncrypted: true
    labels:
      role: worker
    tags:
      project: myapp
      managed_by: eksctl

addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest
    wellKnownPolicies:
      ebsCSIController: true
EOF

eksctl create cluster -f cluster.yaml
aws eks update-kubeconfig --region $REGION --name $CLUSTER_NAME
kubectl get nodes
```

---

## Step 2: Install Core Add-ons

```bash
# ── AWS Load Balancer Controller ───────────────────────────────────────────
# Create IAM policy
curl -o alb-policy.json \
    https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.1/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://alb-policy.json

eksctl create iamserviceaccount \
    --cluster=$CLUSTER_NAME \
    --namespace=kube-system \
    --name=aws-load-balancer-controller \
    --attach-policy-arn=arn:aws:iam::$ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy \
    --approve

helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
    -n kube-system \
    --set clusterName=$CLUSTER_NAME \
    --set serviceAccount.create=false \
    --set serviceAccount.name=aws-load-balancer-controller

# ── External Secrets Operator ──────────────────────────────────────────────
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
    -n external-secrets \
    --create-namespace

# Create IRSA for External Secrets
eksctl create iamserviceaccount \
    --name external-secrets \
    --namespace external-secrets \
    --cluster $CLUSTER_NAME \
    --attach-policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite \
    --approve

# ── Metrics Server (required for HPA) ──────────────────────────────────────
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

---

## Step 3: Application Manifests

```yaml
# k8s/base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-api
  labels:
    app: order-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: order-api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    metadata:
      labels:
        app: order-api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: order-api
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: api
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/order-api:latest
          ports:
            - containerPort: 8080
              name: http
          env:
            - name: DB_HOST
              valueFrom:
                secretKeyRef:
                  name: order-api-secrets
                  key: db-host
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: order-api-secrets
                  key: db-password
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: "http://otel-collector.monitoring.svc.cluster.local:4317"
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 5
            failureThreshold: 3
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: order-api
```

```yaml
# k8s/base/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: order-api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300  # 5 min cool-down
```

```yaml
# k8s/base/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: order-api
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/abc123
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /health/ready
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: "30"
spec:
  rules:
    - host: api.myapp.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: order-api
                port:
                  number: 8080
```

```yaml
# k8s/base/external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: order-api-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-store
    kind: ClusterSecretStore
  target:
    name: order-api-secrets
    creationPolicy: Owner
  data:
    - secretKey: db-host
      remoteRef:
        key: /prod/order-api/db-host
    - secretKey: db-password
      remoteRef:
        key: /prod/order-api/db-password
```

---

## Step 4: Kustomize Overlays

```
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── hpa.yaml
│   ├── ingress.yaml
│   └── external-secret.yaml
└── overlays/
    ├── staging/
    │   ├── kustomization.yaml  (replicas=1, staging ingress host)
    │   └── patch-replicas.yaml
    └── prod/
        ├── kustomization.yaml  (replicas=3, prod ingress host)
        └── patch-resources.yaml
```

```yaml
# k8s/overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: prod
namePrefix: ""

resources:
  - ../../base

images:
  - name: 123456789012.dkr.ecr.us-east-1.amazonaws.com/order-api
    newTag: "$(IMAGE_TAG)"   # replaced by CI/CD

patches:
  - path: patch-resources.yaml
    target:
      kind: Deployment
      name: order-api
```

```bash
# Deploy with kustomize
kubectl apply -k k8s/overlays/prod/

# Or with image tag replacement
IMAGE_TAG=$(git rev-parse --short HEAD)
cd k8s/overlays/prod
kustomize edit set image \
    123456789012.dkr.ecr.us-east-1.amazonaws.com/order-api:$IMAGE_TAG
kubectl apply -k .
```

---

## Step 5: Verify the Deployment

```bash
# Check pods
kubectl get pods -n prod -l app=order-api

# Check HPA
kubectl get hpa -n prod order-api
# NAME        REFERENCE               TARGETS   MINPODS   MAXPODS   REPLICAS
# order-api   Deployment/order-api   18%/70%   3         10        3

# Get ALB address
kubectl get ingress -n prod order-api \
    -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Rollout history
kubectl rollout history deployment/order-api -n prod

# Rollback if needed
kubectl rollout undo deployment/order-api -n prod

# Watch rolling update
kubectl rollout status deployment/order-api -n prod
```

---

## Teardown

```bash
# Delete application resources
kubectl delete -k k8s/overlays/prod/

# Delete cluster (also removes node groups)
eksctl delete cluster --name $CLUSTER_NAME --region $REGION
```

---

← [Previous: Observability Stack](./observability-stack.md) | [Home](../README.md) | [Next: Data Pipeline →](./data-pipeline.md)
