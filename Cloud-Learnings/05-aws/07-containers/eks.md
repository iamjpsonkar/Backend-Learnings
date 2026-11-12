← [Previous: ECS](./ecs.md) | [Home](../../README.md) | [Next: AWS Serverless →](../08-serverless/README.md)

---

# Amazon EKS (Elastic Kubernetes Service)

EKS is a managed Kubernetes service. AWS runs the control plane (API server, etcd, scheduler) across multiple AZs. You choose how to run worker nodes: managed node groups (EC2 ASGs managed by AWS), self-managed nodes, or Fargate profiles (serverless pods).

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Cluster** | The Kubernetes control plane managed by AWS |
| **Managed node group** | EC2 ASG managed by EKS — AWS handles AMI updates and draining |
| **Self-managed node group** | You manage the ASG, AMI, and patching |
| **Fargate profile** | Pods matching a namespace/label selector run serverless on Fargate |
| **IRSA** | IAM Roles for Service Accounts — pods assume IAM roles without node-level credentials |
| **EKS add-ons** | Managed plugins: vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver, etc. |
| **eksctl** | CLI tool for EKS cluster management (wraps CloudFormation) |

---

## Creating a Cluster

```bash
# Using eksctl (recommended — handles VPC, node group, OIDC, and add-ons)
eksctl create cluster \
    --name production \
    --region us-east-1 \
    --version 1.29 \
    --node-type m6i.large \
    --nodes-min 2 \
    --nodes-max 10 \
    --managed \
    --with-oidc \
    --ssh-access \
    --ssh-public-key my-key \
    --asg-access \
    --external-dns-access \
    --full-ecr-access \
    --alb-ingress-access \
    --node-private-networking

# Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name production
kubectl get nodes
```

### Using AWS CLI (without eksctl)

```bash
# Create the cluster (control plane only)
CLUSTER_ROLE_ARN="arn:aws:iam::123456789012:role/EKSClusterRole"
VPC_SUBNET_IDS="subnet-aaa,subnet-bbb,subnet-ccc"
CLUSTER_SG="sg-0123456789abcdef0"

aws eks create-cluster \
    --name production \
    --kubernetes-version "1.29" \
    --role-arn $CLUSTER_ROLE_ARN \
    --resources-vpc-config "subnetIds=$VPC_SUBNET_IDS,securityGroupIds=$CLUSTER_SG,endpointPublicAccess=false,endpointPrivateAccess=true" \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
    --tags Environment=production

aws eks wait cluster-active --name production
echo "Cluster is active"

# Enable the OIDC identity provider (required for IRSA)
OIDC_URL=$(aws eks describe-cluster --name production \
    --query "cluster.identity.oidc.issuer" --output text)
aws iam create-open-id-connect-provider \
    --url $OIDC_URL \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list $(echo | openssl s_client -connect $(echo $OIDC_URL | sed 's|https://||'):443 2>/dev/null | openssl x509 -fingerprint -sha1 -noout | sed 's/://g' | cut -d= -f2 | tr '[:upper:]' '[:lower:]')
```

---

## Managed Node Groups

```bash
NODE_ROLE_ARN="arn:aws:iam::123456789012:role/EKSNodeRole"

# General purpose nodes
aws eks create-nodegroup \
    --cluster-name production \
    --nodegroup-name general \
    --scaling-config minSize=2,maxSize=10,desiredSize=3 \
    --instance-types m6i.large m6i.xlarge \
    --ami-type AL2_x86_64 \
    --node-role $NODE_ROLE_ARN \
    --subnets subnet-aaa subnet-bbb \
    --capacity-type ON_DEMAND \
    --disk-size 50 \
    --labels role=general \
    --tags Environment=production

# Spot nodes for non-critical workloads (significant cost savings)
aws eks create-nodegroup \
    --cluster-name production \
    --nodegroup-name spot-workers \
    --scaling-config minSize=0,maxSize=20,desiredSize=0 \
    --instance-types m6i.large m6i.xlarge m5.large m5.xlarge \
    --ami-type AL2_x86_64 \
    --node-role $NODE_ROLE_ARN \
    --subnets subnet-aaa subnet-bbb \
    --capacity-type SPOT \
    --labels role=spot \
    --taints key=spot,value=true,effect=NO_SCHEDULE

# List node groups
aws eks list-nodegroups --cluster-name production
aws eks describe-nodegroup --cluster-name production --nodegroup-name general \
    --query 'nodegroup.{Status:status,Desired:scalingConfig.desiredSize,Min:scalingConfig.minSize,Max:scalingConfig.maxSize,InstanceTypes:instanceTypes}'
```

---

## Fargate Profiles

```bash
FARGATE_ROLE_ARN="arn:aws:iam::123456789012:role/EKSFargatePodExecutionRole"

# Run all pods in the "serverless" namespace on Fargate
aws eks create-fargate-profile \
    --cluster-name production \
    --fargate-profile-name serverless \
    --pod-execution-role-arn $FARGATE_ROLE_ARN \
    --subnets subnet-aaa subnet-bbb \
    --selectors namespace=serverless namespace=kube-system

kubectl create namespace serverless

# Deploy a pod to Fargate
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello-fargate
  namespace: serverless
spec:
  replicas: 2
  selector:
    matchLabels:
      app: hello-fargate
  template:
    metadata:
      labels:
        app: hello-fargate
    spec:
      containers:
      - name: hello
        image: public.ecr.aws/nginx/nginx:1.25-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "256m"
            memory: "512Mi"
          limits:
            cpu: "256m"
            memory: "512Mi"
EOF
```

---

## EKS Add-ons

```bash
# Install EBS CSI driver (required for PersistentVolumes on EBS)
aws eks create-addon \
    --cluster-name production \
    --addon-name aws-ebs-csi-driver \
    --service-account-role-arn arn:aws:iam::123456789012:role/EBSCSIDriverRole \
    --addon-version v1.26.0-eksbuild.1

# Install ALB Ingress Controller (AWS Load Balancer Controller)
aws eks create-addon \
    --cluster-name production \
    --addon-name aws-load-balancer-controller \
    --service-account-role-arn arn:aws:iam::123456789012:role/AWSLoadBalancerControllerRole

# List installed add-ons
aws eks list-addons --cluster-name production --query 'addons' --output table

# Update CoreDNS
aws eks update-addon \
    --cluster-name production \
    --addon-name coredns \
    --resolve-conflicts OVERWRITE
```

---

## IRSA — IAM Roles for Service Accounts

Allows pods to assume IAM roles without node-level credentials. The pod's service account is annotated with the role ARN; the OIDC provider exchanges the Kubernetes token for temporary AWS credentials.

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
OIDC_PROVIDER=$(aws eks describe-cluster --name production \
    --query "cluster.identity.oidc.issuer" --output text | sed 's|https://||')

# Create the trust policy
cat > /tmp/trust-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Federated": "arn:aws:iam::$ACCOUNT_ID:oidc-provider/$OIDC_PROVIDER"},
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
            "StringEquals": {
                "$OIDC_PROVIDER:aud": "sts.amazonaws.com",
                "$OIDC_PROVIDER:sub": "system:serviceaccount:my-app:my-app-sa"
            }
        }
    }]
}
EOF

# Create the IAM role
ROLE_ARN=$(aws iam create-role \
    --role-name eks-my-app-role \
    --assume-role-policy-document file:///tmp/trust-policy.json \
    --query 'Role.Arn' --output text)

# Attach permissions (e.g., read from S3)
aws iam attach-role-policy \
    --role-name eks-my-app-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Create a Kubernetes service account annotated with the role ARN
kubectl create serviceaccount my-app-sa -n my-app
kubectl annotate serviceaccount my-app-sa -n my-app \
    eks.amazonaws.com/role-arn=$ROLE_ARN

# Pods using this service account automatically get IAM credentials
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: aws-cli-test
  namespace: my-app
spec:
  serviceAccountName: my-app-sa
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command: ["aws", "s3", "ls"]
EOF
```

---

## Cluster Access — aws-auth ConfigMap

```bash
# Grant an IAM role admin access to the cluster
kubectl -n kube-system edit configmap aws-auth

# Add under mapRoles:
# - rolearn: arn:aws:iam::123456789012:role/DevOpsRole
#   username: devops
#   groups:
#   - system:masters

# Or using eksctl
eksctl create iamidentitymapping \
    --cluster production \
    --arn arn:aws:iam::123456789012:role/DevOpsRole \
    --group system:masters \
    --username devops

eksctl get iamidentitymapping --cluster production
```

---

## Deploying a Sample Application

```bash
# Full deployment: Deployment + Service + HPA + PodDisruptionBudget
cat <<'EOF' | kubectl apply -f -
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: my-app-sa
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: my-app
      containers:
      - name: app
        image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app/backend:v1.2.3
        ports:
        - containerPort: 8080
        env:
        - name: APP_ENV
          value: production
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app
  namespace: my-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app
  namespace: my-app
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
EOF
```

---

## Cluster Upgrades

```bash
# Check current version and available updates
aws eks describe-cluster --name production \
    --query 'cluster.{Version:version,Status:status,PlatformVersion:platformVersion}'

# Upgrade control plane (one minor version at a time)
aws eks update-cluster-version \
    --name production \
    --kubernetes-version "1.30"

aws eks wait cluster-active --name production

# Upgrade managed node group (triggers rolling AMI replacement)
aws eks update-nodegroup-version \
    --cluster-name production \
    --nodegroup-name general \
    --kubernetes-version "1.30" \
    --force

# Upgrade add-ons after cluster upgrade
aws eks update-addon \
    --cluster-name production \
    --addon-name vpc-cni \
    --resolve-conflicts OVERWRITE
```

---

## References

- [EKS documentation](https://docs.aws.amazon.com/eks/latest/userguide/)
- [eksctl](https://eksctl.io/)
- [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS best practices guide](https://aws.github.io/aws-eks-best-practices/)
- [EKS pricing](https://aws.amazon.com/eks/pricing/)
---

← [Previous: ECS](./ecs.md) | [Home](../../README.md) | [Next: AWS Serverless →](../08-serverless/README.md)
