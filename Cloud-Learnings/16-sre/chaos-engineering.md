← [Previous: Capacity Planning](./capacity-planning.md) | [Home](../README.md) | [Next: Postmortems →](./postmortems.md)

---

# Chaos Engineering

Chaos engineering deliberately injects failures into production-like systems to uncover weaknesses before they cause real incidents. The goal is not to break things — it's to build confidence in the system's resilience.

---

## Principles

1. **Form a hypothesis** — "The system will continue serving requests if pod X is killed"
2. **Define the blast radius** — start small; run in staging before production
3. **Measure steady state** — establish baseline metrics before injecting failure
4. **Run the experiment** — inject the failure
5. **Observe and compare** — did the system behave as hypothesized?
6. **Fix or document** — if hypothesis was wrong, fix the weakness

---

## LitmusChaos (Kubernetes)

```bash
# Install LitmusChaos
helm repo add litmuschaos https://litmuschaos.github.io/litmus-helm/
helm install chaos litmuschaos/litmus \
    --namespace litmus \
    --create-namespace \
    --set portal.frontend.service.type=ClusterIP

# Port-forward Litmus UI
kubectl port-forward svc/chaos-litmus-frontend-service 9091:9091 -n litmus
# Open: http://localhost:9091
```

### Pod Failure Experiment

```yaml
# Experiment: kill one pod and verify service continues
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: order-api-pod-failure
  namespace: production
spec:
  appinfo:
    appns: production
    applabel: "app=order-api"
    appkind: deployment
  chaosServiceAccount: litmus-admin
  jobCleanUpPolicy: retain
  engineState: "active"
  annotationCheck: "false"
  experiments:
    - name: pod-delete
      spec:
        components:
          env:
            - name: TOTAL_CHAOS_DURATION
              value: "60"   # seconds
            - name: CHAOS_INTERVAL
              value: "10"   # kill a pod every 10 seconds
            - name: FORCE
              value: "false"
            - name: PODS_AFFECTED_PERC
              value: "50"   # kill 50% of pods
  # Steady-state hypothesis: error rate remains < 1%
  # (verify via Prometheus probe)
---
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: order-api-network-latency
  namespace: production
spec:
  appinfo:
    appns: production
    applabel: "app=order-api"
    appkind: deployment
  experiments:
    - name: pod-network-latency
      spec:
        components:
          env:
            - name: NETWORK_LATENCY
              value: "200"    # ms of latency to inject
            - name: JITTER
              value: "50"     # ms of jitter
            - name: TOTAL_CHAOS_DURATION
              value: "120"
            - name: TARGET_CONTAINER
              value: "order-api"
```

---

## AWS Fault Injection Service (FIS)

```bash
# Create FIS experiment template: stop random EC2 instances
aws fis create-experiment-template \
    --description "Stop 20% of production ECS tasks" \
    --targets '{"ecsTaskTargets": {
        "resourceType": "aws:ecs:task",
        "resourceArns": [],
        "selectionMode": "PERCENT(20)",
        "filters": [{"path": "cluster", "values": ["my-app-production"]}]
    }}' \
    --actions '{"stopTasks": {
        "actionId": "aws:ecs:stop-task",
        "targets": {"Tasks": "ecsTaskTargets"}
    }}' \
    --stopConditions '[{
        "source": "aws:cloudwatch:alarm",
        "value": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:CriticalErrorRate"
    }]' \
    --roleArn arn:aws:iam::123456789012:role/FISRole \
    --tags Purpose=ChaosExperiment
```

```json
// FIS experiment template: inject network latency via SSM
{
    "description": "Inject 200ms network latency on app servers",
    "targets": {
        "appInstances": {
            "resourceType": "aws:ec2:instance",
            "resourceTags": {"tier": "application"},
            "selectionMode": "PERCENT(25)"
        }
    },
    "actions": {
        "addLatency": {
            "actionId": "aws:ssm:send-command",
            "parameters": {
                "documentArn": "arn:aws:ssm:::document/AWSFIS-Run-Network-Latency",
                "documentParameters": "{\"DelayMilliseconds\": \"200\", \"DurationSeconds\": \"120\"}",
                "maxErrors": "0",
                "maxConcurrency": "1",
                "targets": "appInstances"
            }
        }
    },
    "stopConditions": [
        {
            "source": "aws:cloudwatch:alarm",
            "value": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:StopFIS"
        }
    ]
}
```

---

## Chaos Experiments Catalog

| Experiment | What it tests | Expected behavior |
|------------|--------------|------------------|
| Pod kill (50%) | Kubernetes restarts + load balancing | No user-visible downtime |
| Database failover | Primary → replica promotion | < 30s disruption, reconnect |
| Network partition (inject latency) | Timeout handling, retries | Graceful degradation |
| Dependency failure (kill inventory svc) | Circuit breaker, fallback | Orders queue, not fail |
| Node drain | Pod rescheduling, PDB compliance | No SLO breach |
| Memory exhaustion (OOM) | OOM kill + restart | Service recovers automatically |
| DNS failure | DNS timeout handling | Cache + retry works |
| Clock skew | Token expiry, timestamp handling | No auth failures |
| High CPU (stress test) | Throttling behavior | Latency increase but no errors |
| Secret rotation | Live rotation without restart | No auth failures during rotation |

---

## Game Day

A game day is a planned chaos experiment run with the full team present — operations, engineering, and sometimes management.

```markdown
## Game Day Plan: Order API Resilience

**Date:** YYYY-MM-DD 14:00 UTC
**Duration:** 2 hours
**Environment:** Production (traffic split 10% to chaos target)

### Objectives
1. Verify pod kill does not breach SLO
2. Verify circuit breaker activates when inventory service fails
3. Measure MTTR when database connection pool is exhausted

### Participants
- Incident commander: @name
- Chaos engineer (runs experiments): @name
- Observer (metrics + dashboards): @name
- Customer support liaison: @name

### Steady-State Hypothesis
- Availability SLO: > 99.9% (error rate < 0.1%)
- p99 latency < 500ms
- No P0/P1 alerts firing

### Experiment 1: Pod Kill (14:05)
1. Baseline: measure error rate for 5 min
2. Kill 50% of order-api pods via LitmusChaos
3. Observe for 10 min
4. Stop experiment
5. Compare to baseline

### Roll-back Criteria
- Error rate > 5% for > 2 min → stop experiment, restore
- Any PagerDuty P0 page → stop immediately

### Post-Game-Day
- Write findings document within 24h
- File reliability improvement tickets for any failures
```

---

## References

- [LitmusChaos](https://litmuschaos.io/)
- [AWS Fault Injection Service](https://docs.aws.amazon.com/fis/latest/userguide/)
- [Chaos Engineering Principles](https://principlesofchaos.org/)
- [Netflix Chaos Monkey](https://github.com/Netflix/chaosmonkey)

---

← [Previous: Capacity Planning](./capacity-planning.md) | [Home](../README.md) | [Next: Postmortems →](./postmortems.md)
