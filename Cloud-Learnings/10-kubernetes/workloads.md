← [Previous: Architecture](./architecture.md) | [Home](../README.md) | [Next: Services & Ingress →](./services-ingress.md)

---

# Kubernetes Workloads

Workload resources manage how Pods are run on the cluster.

---

## Pod

The atomic unit of Kubernetes. A Pod runs one or more tightly-coupled containers that share:
- Network namespace (same IP, same ports)
- Storage volumes
- Lifecycle

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  labels:
    app: my-app
    env: prod
spec:
  containers:
  - name: app
    image: my-registry/my-app:1.2.3
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "500m"
        memory: "256Mi"
    env:
    - name: LOG_LEVEL
      value: info
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: password
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 10
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      periodSeconds: 5
  restartPolicy: Always
```

> In practice, you rarely create bare Pods — use Deployments so failed Pods are rescheduled.

---

## Deployment

Manages a ReplicaSet to maintain a desired number of Pod replicas with rolling update support.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1          # Extra Pods allowed during update
      maxUnavailable: 0    # Zero downtime
  template:
    metadata:
      labels:
        app: my-app
        version: "1.2.3"
    spec:
      containers:
      - name: app
        image: my-registry/my-app:1.2.3
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
```

```bash
# Common Deployment operations
kubectl apply -f deployment.yaml
kubectl rollout status deployment/my-app
kubectl rollout history deployment/my-app
kubectl rollout undo deployment/my-app              # Roll back one version
kubectl rollout undo deployment/my-app --to-revision=2
kubectl scale deployment/my-app --replicas=5
kubectl set image deployment/my-app app=my-registry/my-app:1.3.0
```

### Deployment Strategies

| Strategy | Behavior | Use case |
|----------|----------|----------|
| RollingUpdate | Gradually replace old Pods | Zero-downtime, default |
| Recreate | Kill all old Pods then create new ones | Simple, causes downtime |

---

## ReplicaSet

Ensures a stable number of Pod replicas. Deployments manage ReplicaSets — you rarely create ReplicaSets directly.

```bash
kubectl get replicasets
kubectl describe rs my-app-7d6f9c8d9
```

---

## StatefulSet

For stateful applications that require:
- Stable, unique network identity (`pod-0`, `pod-1`, ...)
- Stable, persistent storage per Pod
- Ordered, graceful deployment and scaling

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres-headless   # Must match a headless Service
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
  volumeClaimTemplates:             # Each Pod gets its own PVC
  - metadata:
      name: data
    spec:
      accessModes: [ReadWriteOnce]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 20Gi
```

StatefulSet Pod naming: `postgres-0`, `postgres-1`, `postgres-2`
DNS: `postgres-0.postgres-headless.default.svc.cluster.local`

Scaling is ordered: scale up 0→1→2, scale down 2→1→0.

---

## DaemonSet

Runs exactly one Pod on every (or selected) node. Used for node-level agents.

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      tolerations:
      - operator: Exists          # Run on ALL nodes including control plane
        effect: NoSchedule
      hostPID: true               # Access host process namespace
      hostNetwork: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.7.0
        ports:
        - containerPort: 9100
          hostPort: 9100
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
```

Common DaemonSet use cases: log collectors (Fluentd, Filebeat), monitoring agents (node-exporter, Datadog), network plugins, security agents.

---

## Job

Runs Pods to completion — suitable for batch tasks, migrations, and one-off scripts.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
spec:
  completions: 1          # How many successful completions needed
  parallelism: 1          # How many Pods run simultaneously
  backoffLimit: 3         # Retry limit before marking Job failed
  activeDeadlineSeconds: 300
  template:
    spec:
      restartPolicy: OnFailure   # Never or OnFailure (not Always)
      containers:
      - name: migrate
        image: my-app:1.2.3
        command: ["python", "manage.py", "migrate"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

```bash
kubectl get jobs
kubectl logs job/db-migrate
kubectl delete job db-migrate
```

### Parallel Jobs

```yaml
spec:
  completions: 10      # 10 tasks total
  parallelism: 3       # 3 Pods running at a time
  completionMode: Indexed   # Each Pod gets an index (JOB_COMPLETION_INDEX env var)
```

---

## CronJob

Schedules Jobs on a cron schedule.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: nightly-report
spec:
  schedule: "0 2 * * *"      # 2am UTC daily
  timeZone: "UTC"
  concurrencyPolicy: Forbid  # Skip if previous run still running
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  startingDeadlineSeconds: 60
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: report
            image: my-app:1.2.3
            command: ["python", "generate_report.py"]
```

| `concurrencyPolicy` | Behavior |
|---------------------|----------|
| Allow | Multiple runs can overlap (default) |
| Forbid | Skip new run if previous still running |
| Replace | Cancel old run, start new one |

---

## Init Containers

Run to completion before app containers start. Useful for setup tasks (wait for DB, run migrations, fetch secrets).

```yaml
spec:
  initContainers:
  - name: wait-for-db
    image: busybox:1.36
    command:
    - sh
    - -c
    - |
      until nc -z postgres-svc 5432; do
        echo "Waiting for postgres..."
        sleep 2
      done
  - name: run-migrations
    image: my-app:1.2.3
    command: ["python", "manage.py", "migrate"]
    env:
    - name: DATABASE_URL
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: url
  containers:
  - name: app
    image: my-app:1.2.3
```

---

## Sidecar Pattern

A secondary container in the same Pod that provides supporting functionality (logging, proxying, secret refresh).

```yaml
spec:
  containers:
  - name: app
    image: my-app:1.2.3
    ports:
    - containerPort: 8080
  - name: log-shipper
    image: fluent/fluent-bit:2.3
    volumeMounts:
    - name: app-logs
      mountPath: /var/log/app
  volumes:
  - name: app-logs
    emptyDir: {}
```

Common sidecar patterns: Envoy proxy (service mesh), log shippers, secret rotators, metric exporters.

---

## HorizontalPodAutoscaler (HPA)

Automatically scales Deployments based on metrics.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 20
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
        type: AverageValue
        averageValue: 200Mi
```

> HPA requires the metrics-server to be installed in the cluster.

```bash
kubectl get hpa
kubectl describe hpa my-app
```

---

## PodDisruptionBudget (PDB)

Limits voluntary disruptions (node drains, rolling updates) to maintain availability.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app-pdb
spec:
  minAvailable: 2          # Or use maxUnavailable: 1
  selector:
    matchLabels:
      app: my-app
```

Always define PDBs for production workloads with more than one replica.

---

← [Previous: Architecture](./architecture.md) | [Home](../README.md) | [Next: Services & Ingress →](./services-ingress.md)
