← [Previous: FluxCD](./fluxcd.md) | [Home](../README.md) | [Next: Production Pipelines →](./production-pipelines.md)

---

# Deployment Strategies

Choosing the right deployment strategy balances risk, speed, and resource cost.

---

## Strategy Comparison

| Strategy | Downtime | Risk | Rollback | Resource cost |
|----------|----------|------|----------|---------------|
| Recreate | Yes | High | Redeploy old | Low |
| Rolling update | No | Medium | Gradual re-rollout | Low |
| Blue/Green | No | Low | Instant (DNS/LB switch) | 2× during deploy |
| Canary | No | Low (% exposure) | Instant | Slight overhead |
| Shadow | No | None | N/A | 2× (shadow receives traffic) |
| A/B testing | No | Low | Instant | Slight overhead |

---

## Recreate

Stop all old pods, then start all new pods. Simple but causes downtime.

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  strategy:
    type: Recreate
```

---

## Rolling Update (Kubernetes Default)

Replace pods incrementally. No downtime, but both versions serve traffic briefly.

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2          # Create up to 2 extra pods during update
      maxUnavailable: 0    # Never reduce below desired count (zero-downtime)
```

```bash
# kubectl rollout commands
kubectl rollout status deployment/my-app -n production
kubectl rollout history deployment/my-app -n production
kubectl rollout undo deployment/my-app -n production          # Rollback one step
kubectl rollout undo deployment/my-app --to-revision=3       # Rollback to specific revision
kubectl rollout pause deployment/my-app -n production        # Pause mid-rollout
kubectl rollout resume deployment/my-app -n production
```

---

## Blue/Green

Run two identical environments. Switch load balancer to promote green. Rollback = switch back.

### AWS (ALB Weighted Target Groups)

```bash
# Create two target groups: blue (current) and green (new)
BLUE_TG_ARN="arn:aws:elasticloadbalancing:..."
GREEN_TG_ARN="arn:aws:elasticloadbalancing:..."
LISTENER_ARN="arn:aws:elasticloadbalancing:..."

# Initial: 100% blue
aws elbv2 modify-listener \
    --listener-arn $LISTENER_ARN \
    --default-actions '[
        {"Type":"forward","ForwardConfig":{"TargetGroups":[
            {"TargetGroupArn":"'$BLUE_TG_ARN'","Weight":100},
            {"TargetGroupArn":"'$GREEN_TG_ARN'","Weight":0}
        ]}}
    ]'

# Deploy new version to green ECS service / ASG
# Run smoke tests against green target group directly

# Switch traffic to green
aws elbv2 modify-listener \
    --listener-arn $LISTENER_ARN \
    --default-actions '[
        {"Type":"forward","ForwardConfig":{"TargetGroups":[
            {"TargetGroupArn":"'$BLUE_TG_ARN'","Weight":0},
            {"TargetGroupArn":"'$GREEN_TG_ARN'","Weight":100}
        ]}}
    ]'
```

### Kubernetes (Service Selector Switch)

```yaml
# Blue deployment (current)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-blue
spec:
  replicas: 5
  selector:
    matchLabels:
      app: my-app
      version: blue
  template:
    metadata:
      labels:
        app: my-app
        version: blue
    spec:
      containers:
        - name: api
          image: my-app/api:1.0.0
---
# Green deployment (new)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-green
spec:
  replicas: 5
  selector:
    matchLabels:
      app: my-app
      version: green
  template:
    metadata:
      labels:
        app: my-app
        version: green
    spec:
      containers:
        - name: api
          image: my-app/api:2.0.0
---
# Service selector switches from blue to green
apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  selector:
    app: my-app
    version: blue    # Change to 'green' to switch traffic
  ports:
    - port: 80
      targetPort: 8080
```

```bash
# Promote green (zero-downtime)
kubectl patch service my-app \
    -n production \
    -p '{"spec":{"selector":{"version":"green"}}}'

# Rollback
kubectl patch service my-app \
    -n production \
    -p '{"spec":{"selector":{"version":"blue"}}}'
```

---

## Canary

Route a small percentage of traffic to the new version. Gradually increase if metrics are healthy.

### Kubernetes + Argo Rollouts

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
  namespace: production
spec:
  replicas: 10
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: api
          image: my-app/api:2.0.0
          ports:
            - containerPort: 8080
  strategy:
    canary:
      canaryService: my-app-canary     # Service routing to canary pods
      stableService: my-app-stable     # Service routing to stable pods
      trafficRouting:
        nginx:
          stableIngress: my-app-ingress
      steps:
        - setWeight: 5               # 5% canary
        - pause: {duration: 5m}      # Observe for 5 min
        - analysis:                  # Run automated analysis
            templates:
              - templateName: success-rate
        - setWeight: 25              # 25% canary
        - pause: {duration: 10m}
        - analysis:
            templates:
              - templateName: success-rate
        - setWeight: 50
        - pause: {duration: 10m}
        - setWeight: 100             # Full rollout
      autoPromotionEnabled: false    # Require manual promotion after analysis
```

```yaml
# AnalysisTemplate — query Prometheus for error rate
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: production
spec:
  metrics:
    - name: success-rate
      interval: 1m
      count: 5
      successCondition: result[0] >= 0.95
      failureLimit: 2
      provider:
        prometheus:
          address: http://prometheus-server.monitoring.svc.cluster.local
          query: |
            sum(rate(http_requests_total{app="my-app",status!~"5.."}[2m]))
            /
            sum(rate(http_requests_total{app="my-app"}[2m]))
```

```bash
# Promote canary manually
kubectl argo rollouts promote my-app -n production

# Abort and rollback
kubectl argo rollouts abort my-app -n production

# Watch rollout progress
kubectl argo rollouts get rollout my-app -n production --watch
```

---

## Feature Flags

Feature flags decouple deployment from release — ship code dark, enable for users gradually.

```python
# Python with LaunchDarkly SDK
import ldclient
from ldclient.config import Config

ldclient.set_config(Config(sdk_key=os.environ["LAUNCHDARKLY_SDK_KEY"]))
client = ldclient.get()

def get_user_context(user_id: str) -> ldclient.Context:
    return ldclient.Context.create(user_id)

def new_checkout_flow_enabled(user_id: str) -> bool:
    context = get_user_context(user_id)
    return client.variation("new-checkout-flow", context, default=False)

# In route handler
@app.route("/checkout")
def checkout():
    user_id = get_current_user_id()
    if new_checkout_flow_enabled(user_id):
        return new_checkout_handler()
    return legacy_checkout_handler()
```

---

## Cloud Run Traffic Splitting (Canary)

```bash
# Cloud Run built-in traffic splitting
gcloud run services update-traffic my-app-api \
    --region=us-central1 \
    --to-revisions=my-app-api-00010-xyz=90,LATEST=10

# Gradually increase
gcloud run services update-traffic my-app-api \
    --region=us-central1 \
    --to-revisions=my-app-api-00010-xyz=50,LATEST=50

# Promote
gcloud run services update-traffic my-app-api \
    --region=us-central1 \
    --to-latest
```

---

## References

- [Argo Rollouts documentation](https://argoproj.github.io/argo-rollouts/)
- [Flagger (alternative)](https://flagger.app/)
- [AWS CodeDeploy deployment strategies](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html)
- [LaunchDarkly](https://launchdarkly.com/)

---

← [Previous: FluxCD](./fluxcd.md) | [Home](../README.md) | [Next: Production Pipelines →](./production-pipelines.md)
