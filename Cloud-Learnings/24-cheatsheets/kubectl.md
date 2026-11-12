← [Previous: AWS CLI](./aws-cli.md) | [Home](../README.md) | [Next: Terraform →](./terraform.md)

---

# kubectl Cheatsheet

```bash
# ── CONTEXT / CLUSTER ──────────────────────────────────────────────────────────
kubectl config get-contexts                        # list all contexts
kubectl config current-context                     # active context
kubectl config use-context prod-cluster            # switch context
kubectl config set-context --current --namespace=prod  # set default namespace

# Update kubeconfig for EKS
aws eks update-kubeconfig --region us-east-1 --name prod-cluster

# ── PODS ────────────────────────────────────────────────────────────────────────
kubectl get pods -n prod                           # list pods
kubectl get pods -n prod -l app=order-api          # filter by label
kubectl get pods -n prod -o wide                   # show node and IP
kubectl get pods --all-namespaces                  # all namespaces

kubectl describe pod -n prod <pod-name>            # full details + events
kubectl logs -n prod <pod-name> --tail=100         # last 100 lines
kubectl logs -n prod <pod-name> -f                 # follow (stream)
kubectl logs -n prod <pod-name> --previous         # previous container (after crash)
kubectl logs -n prod -l app=order-api --prefix     # all pods matching label

# Exec into a running container
kubectl exec -it -n prod <pod-name> -- /bin/sh
kubectl exec -it -n prod <pod-name> -c sidecar -- /bin/bash  # specific container

# Debug: ephemeral debug container (doesn't modify the pod)
kubectl debug -it -n prod <pod-name> --image=busybox:latest --target=api

# Copy files
kubectl cp -n prod <pod-name>:/app/logs/error.log ./error.log
kubectl cp ./config.yaml -n prod <pod-name>:/tmp/config.yaml

# ── DEPLOYMENTS ────────────────────────────────────────────────────────────────
kubectl get deployments -n prod
kubectl describe deployment -n prod order-api

# Scale
kubectl scale deployment -n prod order-api --replicas=5

# Update image
kubectl set image deployment/order-api -n prod api=123456789012.dkr.ecr.us-east-1.amazonaws.com/order-api:v1.2.3

# Rollout
kubectl rollout status deployment/order-api -n prod    # watch status
kubectl rollout history deployment/order-api -n prod   # revision history
kubectl rollout undo deployment/order-api -n prod      # rollback to previous
kubectl rollout undo deployment/order-api -n prod --to-revision=3  # rollback to specific

# Restart all pods (rolling restart)
kubectl rollout restart deployment/order-api -n prod

# ── SERVICES & INGRESS ─────────────────────────────────────────────────────────
kubectl get services -n prod
kubectl get ingress -n prod
kubectl describe ingress -n prod order-api

# Port-forward for local testing
kubectl port-forward -n prod svc/order-api 8080:8080
kubectl port-forward -n prod pod/<pod-name> 5432:5432  # DB connection

# ── CONFIGMAPS & SECRETS ───────────────────────────────────────────────────────
kubectl get configmaps -n prod
kubectl get secrets -n prod
kubectl describe secret -n prod order-api-secrets

# Decode a secret value
kubectl get secret -n prod order-api-secrets \
    -o jsonpath='{.data.db-password}' | base64 -d

# Create/update
kubectl create configmap app-config -n prod \
    --from-literal=LOG_LEVEL=INFO \
    --from-literal=MAX_RETRIES=3

kubectl create secret generic db-creds -n prod \
    --from-literal=password=supersecret \
    --dry-run=client -o yaml | kubectl apply -f -

# ── NAMESPACES ─────────────────────────────────────────────────────────────────
kubectl get namespaces
kubectl create namespace staging
kubectl delete namespace staging  # deletes everything in it

# ── NODES ──────────────────────────────────────────────────────────────────────
kubectl get nodes
kubectl describe node <node-name>
kubectl top nodes                                  # CPU/memory usage
kubectl top pods -n prod                           # pod resource usage
kubectl cordon <node-name>                         # prevent new pods
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data  # evacuate node
kubectl uncordon <node-name>                       # re-enable scheduling

# ── HPA & AUTOSCALING ──────────────────────────────────────────────────────────
kubectl get hpa -n prod
kubectl describe hpa -n prod order-api

# ── APPLY / DIFF / DRY-RUN ─────────────────────────────────────────────────────
kubectl apply -f deployment.yaml                   # apply manifest
kubectl apply -k k8s/overlays/prod/                # apply kustomize overlay
kubectl diff -f deployment.yaml                    # show what would change
kubectl apply -f deployment.yaml --dry-run=server  # server-side dry run

# Delete resources
kubectl delete -f deployment.yaml
kubectl delete pod -n prod <pod-name>              # delete pod (restarts if managed by deployment)
kubectl delete pod -n prod <pod-name> --force --grace-period=0  # force delete stuck pod

# ── EVENTS ─────────────────────────────────────────────────────────────────────
kubectl get events -n prod --sort-by=.lastTimestamp | tail -20
kubectl get events -n prod --field-selector reason=BackOff

# ── RBAC ───────────────────────────────────────────────────────────────────────
kubectl auth can-i list pods -n prod
kubectl auth can-i list pods -n prod --as system:serviceaccount:prod:order-api
kubectl get rolebindings,clusterrolebindings -n prod \
    -o custom-columns='NAME:.metadata.name,ROLE:.roleRef.name,SUBJECTS:.subjects[*].name'

# ── RESOURCE INSPECTION ────────────────────────────────────────────────────────
kubectl api-resources                              # all resource types
kubectl explain deployment.spec.strategy           # field documentation

# Get all resources in a namespace
kubectl get all -n prod

# Watch changes in real time
kubectl get pods -n prod -w

# Output formats
kubectl get pods -n prod -o json
kubectl get pods -n prod -o yaml
kubectl get pods -n prod -o jsonpath='{.items[*].metadata.name}'
kubectl get pods -n prod -o custom-columns='NAME:.metadata.name,IMAGE:.spec.containers[0].image'

# ── HELM ───────────────────────────────────────────────────────────────────────
helm list -n prod                                  # installed releases
helm status order-api -n prod
helm history order-api -n prod                     # revision history
helm upgrade order-api ./chart -n prod -f values.prod.yaml
helm rollback order-api 2 -n prod                  # rollback to revision 2
helm uninstall order-api -n prod
helm template order-api ./chart -f values.prod.yaml  # render templates locally
```

---

← [Previous: AWS CLI](./aws-cli.md) | [Home](../README.md) | [Next: Terraform →](./terraform.md)
