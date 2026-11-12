← [Previous: Storage Optimization](./storage-optimization.md) | [Home](../README.md) | [Next: FinOps Culture →](./finops-culture.md)

---

# Kubernetes Cost Management

Kubernetes abstracts infrastructure from workloads — which also hides costs. Without tooling you cannot answer "how much does the order-api namespace cost?" or "which team is wasting the most."

---

## Kubecost

Kubecost is the most widely used Kubernetes cost visibility tool. It allocates cluster costs to namespaces, deployments, labels, and teams.

```bash
# Install Kubecost with Helm
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm repo update

helm upgrade --install kubecost kubecost/cost-analyzer \
    --namespace kubecost \
    --create-namespace \
    --set kubecostToken="<token>" \
    --set prometheus.server.persistentVolume.enabled=true \
    --set global.prometheus.enabled=true \
    --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::123456789012:role/KubecostRole

# Port-forward Kubecost UI
kubectl port-forward svc/kubecost-cost-analyzer 9090:9090 -n kubecost
# Open: http://localhost:9090

# Query Kubecost API: cost by namespace (last 30 days)
curl "http://localhost:9090/model/allocation?window=30d&aggregate=namespace&shareIdle=true" \
    | jq '.data[0] | to_entries | sort_by(-.value.totalCost) | .[:10][] | {ns: .key, cost: .value.totalCost}'
```

### Kubecost Allocation Report

```bash
# Cost by team label (last 7 days)
curl "http://localhost:9090/model/allocation?window=7d&aggregate=label:team&shareIdle=false" \
    | jq -r '.data[0] | to_entries[] | [.key, (.value.totalCost | . * 100 | round / 100)] | @csv'

# Cost by deployment in production namespace
curl "http://localhost:9090/model/allocation?window=7d&aggregate=deployment&namespace=production" \
    | jq -r '.data[0] | to_entries | sort_by(-.value.totalCost) | .[] | "\(.key): $\(.value.totalCost | . * 100 | round / 100)"'

# Efficiency: idle CPU + memory costs
curl "http://localhost:9090/model/clusterInfo" | j
    jq '{cpu_efficiency: .cpuEfficiency, memory_efficiency: .ramEfficiency, idle_cost: .idleCost}'
```

---

## AWS Cost Allocation (EKS)

```bash
# EKS cost allocation tags: tag node groups so costs flow to teams
aws eks update-nodegroup-config \
    --cluster-name my-cluster \
    --nodegroup-name backend-workers \
    --labels addOrUpdateLabels='{"team":"backend","cost-center":"CC-1042"}'

# Karpenter: tag nodes with workload labels for cost allocation
# In Karpenter NodePool spec
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: backend
spec:
  template:
    metadata:
      labels:
        team: backend
        cost-center: CC-1042
    spec:
      taints:
        - key: team
          value: backend
          effect: NoSchedule
```

---

## Spot Nodes for Cost Reduction

```yaml
# Karpenter NodePool with mixed On-Demand + Spot
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: general
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["2"]
  disruption:
    consolidationPolicy: WhenUnderutilized
    consolidateAfter: 30s
---
# EC2NodeClass: preferSpot with fallback
apiVersion: karpenter.k8s.aws/v1beta1
kind: EC2NodeClass
metadata:
  name: general
spec:
  amiFamily: AL2
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```

```bash
# AWS managed node group with Spot
aws eks create-nodegroup \
    --cluster-name my-cluster \
    --nodegroup-name spot-general \
    --capacity-type SPOT \
    --instance-types t3.large t3.xlarge t3a.large m5.large m5a.large \
    --scaling-config minSize=0,maxSize=30,desiredSize=5 \
    --labels team=general,lifecycle=spot
```

---

## Pod Resource Request Tuning

Overly conservative requests waste money. Kubernetes schedules based on requests, not actual usage.

```bash
# Find pods where actual CPU is < 20% of requested CPU
kubectl get pod -n production -o json | \
    jq -r '[.items[] | {
        name: .metadata.name,
        requested_cpu: .spec.containers[0].resources.requests.cpu,
        requested_mem: .spec.containers[0].resources.requests.memory
    }] | sort_by(.name)[] | [.name, .requested_cpu, .requested_mem] | @tsv'

# Compare with actual (requires metrics-server)
kubectl top pods -n production --containers --sort-by=cpu

# Namespace resource quota: cap what a team can request
apiVersion: v1
kind: ResourceQuota
metadata:
  name: backend-quota
  namespace: backend
spec:
  hard:
    requests.cpu: "20"          # Max 20 CPU cores across all pods
    requests.memory: "40Gi"
    limits.cpu: "40"
    limits.memory: "80Gi"
    count/deployments.apps: "20"
    count/pods: "100"
    persistentvolumeclaims: "20"
    requests.storage: "500Gi"
```

---

## Cluster Consolidation

```bash
# Find underutilized nodes (< 30% CPU requested)
kubectl get nodes -o json | jq -r '.items[] | {
    name: .metadata.name,
    cpu_allocatable: .status.allocatable.cpu,
    instance_type: .metadata.labels["node.kubernetes.io/instance-type"]
} | [.name, .instance_type, .cpu_allocatable] | @tsv'

kubectl top nodes --sort-by=cpu

# Karpenter consolidation: drain and terminate idle nodes automatically
# Set in NodePool:
spec:
  disruption:
    consolidationPolicy: WhenUnderutilized
    consolidateAfter: 60s    # Terminate node 60s after becoming underutilized
    expireAfter: 720h        # Force rotate nodes every 30 days (fresh AMIs)
    budgets:
      - nodes: "10%"         # Max 10% of nodes disrupted at once
```

---

## Cost Showback via Labels

```yaml
# Standardize cost allocation labels on all deployments
# Team is responsible for adding these to their workloads

apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-api
  namespace: production
  labels:
    app: order-api
    team: backend
    cost-center: CC-1042
    service: order-api
    environment: production
spec:
  template:
    metadata:
      labels:
        app: order-api
        team: backend
        cost-center: CC-1042
        service: order-api
```

```bash
# Kubecost: weekly cost report by team (send to Slack)
curl -s "http://kubecost:9090/model/allocation?window=7d&aggregate=label:team" | \
    python3 -c "
import sys, json
data = json.load(sys.stdin)['data'][0]
for team, info in sorted(data.items(), key=lambda x: -x[1]['totalCost']):
    print(f'{team:<25} \${info[\"totalCost\"]:.2f}/week  CPU eff: {info[\"cpuEfficiency\"]*100:.0f}%  Mem eff: {info[\"ramEfficiency\"]*100:.0f}%')
"
```

---

## References

- [Kubecost](https://www.kubecost.com/install.html)
- [Karpenter consolidation](https://karpenter.sh/docs/concepts/disruption/)
- [AWS EKS cost optimization](https://aws.github.io/aws-eks-best-practices/cost_optimization/)
- [GCP GKE cost optimization](https://cloud.google.com/architecture/best-practices-for-running-cost-effective-kubernetes-applications-on-gke)

---

← [Previous: Storage Optimization](./storage-optimization.md) | [Home](../README.md) | [Next: FinOps Culture →](./finops-culture.md)
