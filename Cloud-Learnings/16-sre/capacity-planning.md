← [Previous: On-Call](./on-call.md) | [Home](../README.md) | [Next: Chaos Engineering →](./chaos-engineering.md)

---

# Capacity Planning

Capacity planning ensures your systems can handle current and future load without over-provisioning. It combines load testing, metric analysis, and demand forecasting.

---

## Capacity Planning Cycle

```
1. Define headroom target
   └── "We want 40% spare capacity at peak load"

2. Measure current peak utilization
   └── CPU, memory, connections, throughput at P95 traffic

3. Project future demand
   └── Growth rate from business metrics + seasonality

4. Calculate required capacity
   └── current_peak × growth_factor / (1 - headroom_target)

5. Provision and verify
   └── Load test, adjust, set autoscaling policies

6. Review quarterly
   └── Compare projections to actuals, recalibrate
```

---

## Load Testing

### k6

```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const orderLatency = new Trend('order_latency', true);

export const options = {
  scenarios: {
    // Ramp up to steady state
    ramp_up: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },   // Ramp up
        { duration: '5m', target: 50 },   // Steady state
        { duration: '2m', target: 100 },  // Spike
        { duration: '5m', target: 100 },  // Hold spike
        { duration: '2m', target: 0 },    // Ramp down
      ],
    },
    // Constant arrival rate (more realistic)
    constant_rate: {
      executor: 'constant-arrival-rate',
      rate: 500,          // 500 requests per second
      timeUnit: '1s',
      duration: '10m',
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<300', 'p(99)<1000'],  // SLO thresholds
    errors: ['rate<0.01'],                             // < 1% error rate
  },
};

export default function () {
  const BASE_URL = __ENV.BASE_URL || 'https://staging.my-app.com';

  // Create order
  const payload = JSON.stringify({
    items: [{ sku: 'PROD-001', qty: 1 }],
    shipping_address: { zip: '10001' },
  });

  const start = Date.now();
  const res = http.post(`${BASE_URL}/api/v1/orders`, payload, {
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${__ENV.AUTH_TOKEN}` },
    tags: { endpoint: 'create_order' },
  });
  orderLatency.add(Date.now() - start);

  const success = check(res, {
    'status is 201': (r) => r.status === 201,
    'has order_id': (r) => r.json().order_id !== undefined,
  });
  errorRate.add(!success);

  sleep(1);
}
```

```bash
# Run load test
k6 run \
    --env BASE_URL=https://staging.my-app.com \
    --env AUTH_TOKEN=$AUTH_TOKEN \
    --out prometheus=http://prometheus-pushgateway:9091 \
    load-test.js

# Run with cloud execution (k6 Cloud)
k6 cloud load-test.js

# Smoke test (1 VU, brief — CI gate)
k6 run --vus 1 --duration 30s load-test.js
```

### locust (Python)

```python
# locustfile.py
import logging
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

logger = logging.getLogger(__name__)


class OrderUser(HttpUser):
    wait_time = between(1, 3)
    host = "https://staging.my-app.com"

    def on_start(self) -> None:
        """Authenticate before running tasks."""
        resp = self.client.post("/api/v1/auth/token", json={
            "username": "loadtest@my-app.com",
            "password": "loadtest-password",
        })
        self.token = resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        logger.info("User authenticated for load test")

    @task(10)
    def browse_products(self) -> None:
        with self.client.get("/api/v1/products", headers=self.headers, catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Expected 200, got {resp.status_code}")

    @task(3)
    def create_order(self) -> None:
        with self.client.post(
            "/api/v1/orders",
            json={"items": [{"sku": "PROD-001", "qty": 1}]},
            headers=self.headers,
            catch_response=True,
            name="/api/v1/orders [POST]",
        ) as resp:
            if resp.status_code == 201:
                resp.success()
            else:
                resp.failure(f"Order creation failed: {resp.status_code}")

    @task(1)
    def checkout(self) -> None:
        self.client.post("/api/v1/checkout", headers=self.headers)
```

```bash
locust -f locustfile.py \
    --headless \
    --users 100 \
    --spawn-rate 10 \
    --run-time 10m \
    --csv results
```

---

## Resource Sizing Guidelines

```bash
# Kubernetes: check actual resource usage vs requests/limits
kubectl top pods -n production --containers | sort -k4 -rn | head -20

# Find pods with >80% CPU throttling
kubectl get pod -n production -o json | \
    jq -r '.items[] | .metadata.name + " " + (.spec.containers[].resources.limits.cpu // "no-limit")'

# Prometheus: CPU throttle ratio
rate(container_cpu_throttled_seconds_total{namespace="production"}[5m])
/
rate(container_cpu_usage_seconds_total{namespace="production"}[5m])

# Right-sizing recommendation
# For a service using 400m CPU at p95 load:
# - Request: 500m (25% headroom over p95)
# - Limit: 1000m (2x request — allow burst, prevent noisy-neighbor)
# - Memory request ≈ Memory limit (no burst for memory — OOM kills immediately)
```

### VPA (Vertical Pod Autoscaler) for Automated Sizing

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: order-api-vpa
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-api
  updatePolicy:
    updateMode: "Off"     # "Off" = recommendations only, "Auto" = apply automatically
  resourcePolicy:
    containerPolicies:
      - containerName: order-api
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: 2000m
          memory: 2Gi
```

```bash
# View VPA recommendations
kubectl describe vpa order-api-vpa -n production | grep -A 20 "Recommendation:"
```

---

## Demand Forecasting

```python
# Simple linear regression on request volume for capacity forecast
import logging
import numpy as np
from datetime import datetime, timedelta

import boto3

logger = logging.getLogger(__name__)
cw = boto3.client("cloudwatch")


def forecast_capacity(
    service: str,
    days_historical: int = 90,
    days_ahead: int = 30,
    headroom_factor: float = 1.4,
) -> dict:
    """
    Forecast required capacity using linear regression on CloudWatch metrics.
    Returns current_peak, projected_peak, required_capacity.
    """
    logger.info(
        "Forecasting capacity",
        extra={"service": service, "days_historical": days_historical},
    )

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days_historical)

    response = cw.get_metric_statistics(
        Namespace="MyApp/Production",
        MetricName="RequestCount",
        Dimensions=[{"Name": "ServiceName", "Value": service}],
        StartTime=start_time,
        EndTime=end_time,
        Period=86400,  # Daily datapoints
        Statistics=["Maximum"],
    )

    datapoints = sorted(response["Datapoints"], key=lambda x: x["Timestamp"])
    if len(datapoints) < 7:
        logger.warning("Insufficient data for forecast", extra={"service": service})
        return {}

    y = np.array([dp["Maximum"] for dp in datapoints])
    x = np.arange(len(y))

    # Linear regression: y = slope * x + intercept
    slope, intercept = np.polyfit(x, y, 1)
    projected = slope * (len(y) + days_ahead) + intercept

    current_peak = float(y[-7:].max())  # Last week's peak
    required_capacity = projected * headroom_factor

    result = {
        "service": service,
        "current_peak_rps": round(current_peak / 86400, 1),
        "projected_peak_rps": round(projected / 86400, 1),
        "required_capacity_rps": round(required_capacity / 86400, 1),
        "growth_rate_pct": round((projected / current_peak - 1) * 100, 1),
    }
    logger.info("Forecast complete", extra=result)
    return result
```

---

## References

- [k6 load testing](https://k6.io/docs/)
- [Locust](https://docs.locust.io/)
- [Google SRE Book — Software Engineering in SRE](https://sre.google/sre-book/software-engineering-in-sre/)
- [Kubernetes VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)

---

← [Previous: On-Call](./on-call.md) | [Home](../README.md) | [Next: Chaos Engineering →](./chaos-engineering.md)
