# Installation and Basic commands

## Install minikube

https://minikube.sigs.k8s.io/docs/start/?arch=%2Flinux%2Fx86-64%2Fstable%2Fdebian+package

```sh
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube_latest_amd64.deb

sudo dpkg -i minikube_latest_amd64.deb
```

### verify installation
```sh
minikube version
```
```txt
minikube version: v1.39.0
commit: 7a9f6a841470a207de8cf4bafcccee0969d8ba10
```

## Install kubernetes

https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/

### verify installation
```sh
kubectl version
```
```txt
Client Version: v1.37.2
Kustomize Version: v5.8.1
Server Version: v1.37.0
```

## Start the minikube
```sh
minikube start
```

## Status
```sh
minikube status
```
```txt
minikube
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured
```

## get nodes
```sh
kubectl get nodes
```
```txt
NAME       STATUS   ROLES           AGE    VERSION
minikube   Ready    control-plane   2m2s   v1.37.0
```

## get pods
```sh
kubectl get pods
```

## get services
```sh
kubectl get services
```

## get deployment
```sh
kubectl get deployment
```

## get replicase
```sh
kubectl get replicaset
```

# Creating first Deployment

## nginx deployment
```sh
kubectl create deployment nginx-depl --image=nginx
```
```txt
deployment.apps/nginx-depl created
```

### verify deployment creation
```sh
kubectl get deployment
```
```txt
NAME         READY   UP-TO-DATE   AVAILABLE   AGE
nginx-depl   1/1     1            1           46s
```

### verify replicase
```sh
kubectl get replicaset
```
```txt
NAME                    DESIRED   CURRENT   READY   AGE
nginx-depl-7fc6847dd8   1         1         1       23m
```

### veify pod
```sh
kubectl get pods
```
```txt
NAME                          READY   STATUS    RESTARTS   AGE
nginx-depl-7fc6847dd8-b87kg   1/1     Running   0          24m
```




