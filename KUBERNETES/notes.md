# Kubernetes --- A Practical Learning Guide

**Primary learning source:** [Kubernetes Tutorial for Beginners ---
TechWorld with Nana](https://www.youtube.com/watch?v=X48VuDVv0do)\
**Course length:** Approximately 4 hours\
**Approach in this document:** The video supplies the topics, examples,
and demonstrations. The material is reorganized into a practical
learning path: understand the problem, build a local cluster, deploy an
application, learn how Kubernetes connects and configures it, then
handle persistence and packaging.

> These are original study notes, not a word-for-word transcript. The
> order below is intentionally different from the video's chapter order
> so that each concept is introduced when you need it in a hands-on
> workflow.

------------------------------------------------------------------------

# 0. How to study this guide

Do not try to memorize every Kubernetes object before using Kubernetes.
Work through the guide in stages:

1.  Understand the purpose and mental model.
2.  Start a local cluster and learn the CLI.
3.  Deploy a simple application.
4.  Understand the objects created behind the scenes.
5.  Connect application components.
6.  Add configuration and external access.
7.  Learn persistence and stateful workloads.
8.  Organize and package resources.

For each stage:

-   Watch the relevant video segment.
-   Read the corresponding section here.
-   Run the commands yourself.
-   Inspect the objects Kubernetes created.
-   Write down what surprised you and what failed.

## Video-to-guide map

  Video segment                                Where it appears in this guide
  -------------------------------------------- --------------------------------
  02:18 --- What is Kubernetes?                Sections 1--2
  05:20 --- Main components                    Sections 3--5
  22:29 --- Architecture                       Section 4
  34:47 --- Minikube and kubectl setup         Section 6
  44:52 --- kubectl commands                   Section 7
  1:02:03 --- YAML configuration               Sections 8--9
  1:16:16 --- MongoDB and Mongo Express demo   Sections 10--12
  1:46:16 --- Namespaces                       Section 13
  2:01:52 --- Ingress                          Section 14
  2:24:17 --- Helm                             Section 17
  2:38:07 --- Volumes                          Section 15
  2:58:38 --- StatefulSet                      Section 16
  3:13:43 --- Services                         Sections 11--12

------------------------------------------------------------------------

# 1. Start with the problem Kubernetes solves

## 1.1 From one container to an application platform

Docker helps you package an application and run it as a container. That
works well when you have a small number of containers.

Now imagine a backend system containing:

-   A frontend application.
-   Several backend APIs.
-   A database.
-   A cache.
-   Background workers.
-   A message broker.

These components may each run in multiple container instances. They may
need to be restarted, scaled, updated, connected to each other, and
scheduled across multiple machines.

Doing all of that manually becomes difficult.

**Kubernetes is a container orchestration platform.** It coordinates
containerized workloads across a cluster of machines and continuously
works to keep them in the state you declared.

## 1.2 What Kubernetes helps with

  -----------------------------------------------------------------------
  Problem                             Kubernetes mechanism
  ----------------------------------- -----------------------------------
  A workload instance disappears      Controllers recreate the required
                                      Pods.

  An application needs more instances Change the replica count or use
                                      autoscaling.

  Pod IP addresses change             Services provide stable access to
                                      selected Pods.

  A new version must be deployed      Deployments support rolling updates
                                      and rollbacks.

  Application settings differ by      ConfigMaps and Secrets provide
  environment                         configuration separately from
                                      images.

  Data must outlive a Pod             Persistent storage abstractions
                                      attach storage to workloads.

  Many resources need organizing      Namespaces group namespaced
                                      resources.

  Many YAML resources need packaging  Helm Charts package and template
                                      Kubernetes resources.
  -----------------------------------------------------------------------

Kubernetes does not automatically guarantee that an application is
highly available, secure, or backed up. Those outcomes depend on the
application, cluster setup, storage, networking, and operational
practices.

## 1.3 Docker and Kubernetes have different jobs

  -----------------------------------------------------------------------
  Docker                              Kubernetes
  ----------------------------------- -----------------------------------
  Builds container images and runs    Orchestrates containerized
  containers.                         workloads across a cluster.

  Packages application code and       Schedules, scales, connects, and
  dependencies.                       manages workloads.

  Commonly used during development    Commonly used to operate workloads
  and image builds.                   across multiple nodes.

  Docker Compose describes a          Kubernetes uses API resources such
  multi-container setup.              as Pods, Deployments, and Services.
  -----------------------------------------------------------------------

Kubernetes does not require Docker Engine on its nodes. It communicates
with container runtimes through the Container Runtime Interface (CRI).
Docker-built images remain usable when they follow supported OCI image
formats.

**Mental model:** Docker packages and runs a container; Kubernetes
manages the desired state of containerized applications across a
cluster.

------------------------------------------------------------------------

# 2. Build the mental model before learning commands

Start with five ideas. Almost everything in this beginner course
connects back to them.

## 2.1 Cluster

A **cluster** is the Kubernetes environment. It consists of machines
called nodes and the Kubernetes components that manage workloads on
them.

## 2.2 Node

A **node** is a physical or virtual machine in the cluster.

-   Control plane components manage the cluster.
-   Worker node components run application workloads.
-   In a small learning cluster, one machine may perform both roles.

## 2.3 Pod

A **Pod** is the smallest deployable unit in Kubernetes. It wraps one or
more containers.

A Pod:

-   Is scheduled onto one node.
-   Has its own cluster IP address.
-   Shares its network namespace among its containers.
-   Can provide shared volumes to its containers.
-   Is replaceable; a replacement Pod may have a different IP.

Most application Pods contain one main application container.

## 2.4 Deployment

A **Deployment** describes the desired state for a stateless
application:

-   Which image should run.
-   How many replicas should exist.
-   Which labels identify the Pods.
-   How updates should be rolled out.

You normally create a Deployment rather than managing application Pods
directly.

## 2.5 Service

A **Service** gives a stable network endpoint to a changing set of Pods.

Pods may be replaced and receive new IP addresses. Other applications
should not need to keep updating their connection details every time
that happens. A Service selects Pods using labels and provides a stable
endpoint.

## 2.6 The first relationship to remember

``` text
Deployment
    |
    | manages
    v
ReplicaSet
    |
    | maintains
    v
Pods
    |
    | run
    v
Containers
```

And for networking:

``` text
Client
  |
  v
Service
  |
  | selects Pods using labels
  v
Pod A     Pod B     Pod C
```

A ReplicaSet is the object that maintains the desired number of matching
Pods. In normal application work, you manage the Deployment and let it
manage the ReplicaSet.

------------------------------------------------------------------------

# 3. Understand the cluster architecture

The video introduces the architecture after the main objects. Learn it
now as the explanation of *who does the work* when you create a
Deployment.

## 3.1 Control plane and worker nodes

A Kubernetes cluster has two broad functional areas:

-   **Control plane:** Exposes the Kubernetes API, makes scheduling
    decisions, and runs controllers.
-   **Worker nodes:** Run application Pods.

The video uses the term *Master Node*. Modern Kubernetes documentation
generally uses *Control Plane*.

``` text
                         KUBERNETES CLUSTER
+-------------------------------------------------------------+
|                         CONTROL PLANE                       |
|                                                             |
|  +----------------+  +----------------+  +----------------+ |
|  | API Server     |  | Scheduler      |  | Controller     | |
|  |                |  |                |  | Manager        | |
|  +----------------+  +----------------+  +----------------+ |
|                                                             |
|                    +------------------+                     |
|                    |       etcd       |                     |
|                    |  Cluster state   |                     |
|                    +------------------+                     |
+-------------------------------------------------------------+
                              |
                       Kubernetes API
                              |
              +---------------+---------------+
              |                               |
+-----------------------------+ +-----------------------------+
|         WORKER NODE 1       | |         WORKER NODE 2       |
|                             | |                             |
|  kubelet                    | |  kubelet                    |
|  Container Runtime          | |  Container Runtime          |
|  kube-proxy (if used)       | |  kube-proxy (if used)       |
|                             | |                             |
|  Pod A       Pod B          | |  Pod C       Pod D          |
+-----------------------------+ +-----------------------------+
```

## 3.2 Control plane components

### API Server --- the entry point

The `kube-apiserver` exposes the Kubernetes API.

-   `kubectl` sends requests to it.
-   Dashboards and automation tools use it.
-   It authenticates and authorizes requests.
-   It validates resource definitions and applies admission control.
-   It reads and writes cluster state through the storage layer.

When you run:

``` bash
kubectl get pods
```

`kubectl` sends a request to the API server.

### Scheduler --- chooses where a Pod runs

The `kube-scheduler` assigns newly created, unscheduled Pods to suitable
nodes.

It considers resource requests and scheduling constraints, including
CPU, memory, node selectors, affinity, taints, and tolerations.

The scheduler chooses the node. It does not directly start the
container.

### Controller Manager --- keeps the desired state

The `kube-controller-manager` runs controllers. Controllers observe
cluster state and take action to move actual state towards desired
state.

Example:

-   Desired state: three replicas.
-   Actual state: two Pods exist.
-   A controller works through the API to create the missing Pod.

This repeated process is called a **reconciliation loop**.

### etcd --- stores cluster state

`etcd` is the consistent key-value store used to persist Kubernetes
cluster data.

-   It stores Kubernetes API data.
-   It is critical to the control plane.
-   Access must be protected.
-   Backups are important for recovery.

It is not the database for your application's business records.

## 3.3 Worker node components

### kubelet --- node-level agent

The kubelet:

-   Watches for Pods assigned to its node.
-   Works with the container runtime to ensure required containers are
    running.
-   Reports node and Pod status.
-   Runs configured container health probes.

### Container runtime --- runs containers

The runtime pulls images and creates, starts, and stops containers.

Examples include `containerd` and `CRI-O`. Kubernetes communicates with
the runtime through the Container Runtime Interface (CRI).

**Version note:** Kubernetes removed its built-in dockershim integration
in Kubernetes 1.24. Docker-built OCI-compatible images can still be
used. A Kubernetes node does not need Docker Engine just to run those
images.

### kube-proxy --- helps implement Service networking

`kube-proxy` is commonly used to configure network forwarding so Service
traffic reaches eligible backend endpoints. Some networking
implementations provide Service forwarding without kube-proxy.

It is not an HTTP reverse proxy like NGINX.

------------------------------------------------------------------------

# 4. Create a local Kubernetes lab

Now that you know what a cluster is, create one. The video uses
Minikube.

## 4.1 Minikube

**Minikube** runs a local Kubernetes cluster for learning and
development. A one-node setup is enough to learn the beginner concepts.
Control-plane and workload functions can run on the same machine.

Other local options include:

-   kind
-   Kubernetes in Docker Desktop
-   k3d

## 4.2 Install the tools

You need:

-   A local Kubernetes environment such as Minikube.
-   `kubectl`, the Kubernetes CLI.

Use the current installation instructions for your operating system:

-   [Minikube installation](https://minikube.sigs.k8s.io/docs/start/)
-   [kubectl installation](https://kubernetes.io/docs/tasks/tools/)

The video was recorded with an older setup. Driver names and commands
can change. Follow the current Minikube documentation for your machine.

## 4.3 Start and verify the cluster

``` bash
minikube start
minikube status
kubectl get nodes
kubectl cluster-info
```

Wait until the node reports `Ready`.

**Checkpoint:** You have a working Kubernetes cluster and a CLI that can
communicate with it.

------------------------------------------------------------------------

# 5. Learn kubectl by doing real operations

`kubectl` is the command-line client used to communicate with the
Kubernetes API.

Do not memorize commands in isolation. Learn them as a workflow:
inspect, create, examine, debug, update, and delete.

## 5.1 Inspect the cluster

``` bash
kubectl version
kubectl cluster-info
kubectl get nodes
```

## 5.2 List resources

``` bash
kubectl get pods
kubectl get deployments
kubectl get replicasets
kubectl get services
kubectl get namespaces
```

Show Pod IPs and node placement:

``` bash
kubectl get pods -o wide
```

## 5.3 Create your first Deployment

``` bash
kubectl create deployment nginx --image=nginx
```

Inspect what Kubernetes created:

``` bash
kubectl get deployments
kubectl get replicasets
kubectl get pods
```

Notice the relationship:

``` text
Deployment -> ReplicaSet -> Pod
```

## 5.4 Inspect and debug

``` bash
kubectl describe deployment nginx
kubectl describe pod <pod-name>
kubectl logs <pod-name>
kubectl logs -f <pod-name>
```

For a Pod with multiple containers:

``` bash
kubectl logs <pod-name> -c <container-name>
```

The Events section in `kubectl describe` is especially useful for errors
such as image-pull failures and scheduling problems.

## 5.5 Execute a command inside a Pod

``` bash
kubectl exec -it <pod-name> -- /bin/sh
```

The image must contain the requested shell. Minimal images may not
include Bash.

## 5.6 Change and remove resources

``` bash
kubectl edit deployment nginx
kubectl scale deployment nginx --replicas=3
kubectl delete deployment nginx
```

## 5.7 Watch changes

``` bash
kubectl get pods -w
```

**Checkpoint:** You can create a workload, inspect the objects behind
it, read logs, and remove it.

------------------------------------------------------------------------

# 6. Move from imperative commands to declarative YAML

CLI commands are excellent for learning and quick experiments. For
repeatable application deployments, define resources in YAML files and
keep them in Git.

## 6.1 The three important parts of a resource definition

A typical Kubernetes manifest contains:

-   `apiVersion`: API group and version.
-   `kind`: Type of object, such as Deployment or Service.
-   `metadata`: Name, labels, annotations, and other identity
    information.
-   `spec`: Desired configuration.
-   `status`: Observed state, populated and updated by Kubernetes.

You normally write `metadata` and `spec`. Kubernetes updates `status`.

## 6.2 First Deployment manifest

Create `nginx-deployment.yaml`:

``` yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          ports:
            - containerPort: 80
```

Apply it:

``` bash
kubectl apply -f nginx-deployment.yaml
kubectl get deployment
kubectl get replicasets
kubectl get pods
```

## 6.3 Understand the manifest from the inside out

  -----------------------------------------------------------------------
  Field                               Meaning
  ----------------------------------- -----------------------------------
  `apiVersion`                        API group and version.

  `kind`                              Resource type.

  `metadata.name`                     Resource name.

  `metadata.labels`                   Key-value metadata used to identify
                                      objects.

  `spec.replicas`                     Desired number of replicas.

  `spec.selector`                     Which Pods the Deployment manages.

  `spec.template`                     Blueprint for the Pods it creates.

  `containers[].name`                 Container name.

  `containers[].image`                Image to run.

  `containerPort`                     Documents a port the container is
                                      expected to listen on.
  -----------------------------------------------------------------------

## 6.4 Labels and selectors: the connection mechanism

Labels are key-value pairs attached to Kubernetes objects:

``` yaml
labels:
  app: nginx
```

A selector matches those labels:

``` yaml
selector:
  matchLabels:
    app: nginx
```

The Deployment selector must match the labels in its Pod template.
Services also use selectors to find the Pods to which they send traffic.

## 6.5 Apply and delete declaratively

``` bash
kubectl apply -f nginx-deployment.yaml
kubectl delete -f nginx-deployment.yaml
```

`apply` creates the object if it does not exist and updates it when the
declared configuration changes.

Multiple YAML documents can be stored in one file, separated by `---`.

**Checkpoint:** You can explain the difference between a Deployment's
selector and its Pod template labels.

------------------------------------------------------------------------

# 7. Connect workloads with Services

This topic appears near the end of the video, but it is fundamental to
understanding the demo project. Learn the basic Service idea before
deploying MongoDB and Mongo Express.

## 7.1 Why a Service is needed

Pods are ephemeral. When a Pod is replaced, its IP address can change.

A Service:

-   Selects Pods using labels.
-   Provides a stable virtual IP and DNS name.
-   Routes traffic to eligible backend endpoints.

Example:

``` yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
```

Apply and inspect:

``` bash
kubectl apply -f nginx-service.yaml
kubectl get services
kubectl describe service nginx-service
```

### Understand the ports

-   `port`: Port exposed by the Service.
-   `targetPort`: Port on the selected Pod to which traffic is
    forwarded.
-   `containerPort`: A descriptive declaration in the Pod spec; it does
    not itself publish the port.

## 7.2 Service types

  -----------------------------------------------------------------------
  Type                    Purpose                 Typical use
  ----------------------- ----------------------- -----------------------
  `ClusterIP`             Stable internal         Service-to-service
                          endpoint.               communication.

  Headless                DNS discovery of        StatefulSet peer
                          individual Pod          discovery.
                          endpoints.              

  `NodePort`              Exposes a port on each  Local testing or
                          node's IP.              specific network
                                                  setups.

  `LoadBalancer`          Requests an external    External access in
                          load balancer           supported environments.
                          integration.            
  -----------------------------------------------------------------------

### ClusterIP

This is the default Service type. It is normally reachable only from
inside the cluster.

### Headless Service

A Headless Service sets:

``` yaml
spec:
  clusterIP: None
```

It does not allocate a normal virtual ClusterIP. DNS can return
individual Pod addresses. This is useful for workloads that need to
discover specific Pods.

### NodePort

A NodePort exposes a port on each node's IP address. The usual default
range is `30000`--`32767`.

``` yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-nodeport
spec:
  type: NodePort
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 8080
      nodePort: 30080
```

### LoadBalancer

A LoadBalancer Service requests an external load-balancer integration
where the infrastructure supports it.

``` yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-lb
spec:
  type: LoadBalancer
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 8080
```

## 7.3 Multi-port Services

A Service can expose multiple ports. Name ports when there is more than
one:

``` yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-service
spec:
  selector:
    app: backend
  ports:
    - name: http
      port: 80
      targetPort: 8080
    - name: metrics
      port: 9090
      targetPort: 9090
```

**Checkpoint:** You can explain why clients should connect to a Service
rather than depend on an individual Pod IP.

------------------------------------------------------------------------

# 8. Configure applications with ConfigMaps and Secrets

The video introduces these components early and then uses them in the
MongoDB/Mongo Express demo.

## 8.1 The problem: configuration should not be baked into an image

An application image should not need to be rebuilt just because the
database hostname or an environment-specific setting changes.

Kubernetes provides two useful resources:

-   **ConfigMap:** Non-sensitive configuration.
-   **Secret:** Sensitive configuration such as passwords and tokens.

## 8.2 ConfigMap example

`mongodb-configmap.yaml`:

``` yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mongodb-configmap
data:
  database_url: mongodb-service
```

Apply:

``` bash
kubectl apply -f mongodb-configmap.yaml
kubectl get configmap
```

## 8.3 Secret example

`mongodb-secret.yaml`:

``` yaml
apiVersion: v1
kind: Secret
metadata:
  name: mongodb-secret
type: Opaque
stringData:
  mongo-root-username: root
  mongo-root-password: change-this-example-password
```

Apply:

``` bash
kubectl apply -f mongodb-secret.yaml
kubectl get secrets
```

`stringData` accepts plain strings and Kubernetes converts them for the
Secret representation.

**Security warning:** Secret values are commonly base64-encoded in
API/YAML representations. Base64 is encoding, not encryption. Restrict
access with RBAC, configure encryption at rest, and do not commit real
credentials to Git.

## 8.4 Inject values into a container

A Pod can read ConfigMap and Secret keys as environment variables:

``` yaml
env:
  - name: ME_CONFIG_MONGODB_SERVER
    valueFrom:
      configMapKeyRef:
        name: mongodb-configmap
        key: database_url

  - name: ME_CONFIG_MONGODB_ADMINUSERNAME
    valueFrom:
      secretKeyRef:
        name: mongodb-secret
        key: mongo-root-username
```

The referenced ConfigMap and Secret must exist in the same Namespace as
the Pod.

They can also be mounted as files. This is useful when an application
expects configuration files rather than environment variables.

**Checkpoint:** You can distinguish application configuration from the
container image and explain why passwords belong in a Secret rather than
a ConfigMap.

------------------------------------------------------------------------

# 9. Put the concepts together: MongoDB + Mongo Express

This is the main application demonstration in the video. It is a useful
project because it combines Deployments, Pods, Services, ConfigMaps,
Secrets, and external access.

## 9.1 What are we building?

-   **MongoDB:** Database.
-   **Mongo Express:** Web UI that connects to MongoDB.

Conceptual request and data flow:

``` text
Browser
   |
   v
External access to Mongo Express
   |
   v
Mongo Express Service
   |
   v
Mongo Express Pod
   |
   v
MongoDB Service (internal)
   |
   v
MongoDB Pod
```

## 9.2 Why two Services?

Mongo Express needs to be reachable from outside the cluster for the
demo.

MongoDB should be reachable by Mongo Express inside the cluster, but it
does not need to be exposed to the public internet.

So:

-   MongoDB gets an internal `ClusterIP` Service.
-   Mongo Express gets an external access mechanism for the local demo,
    such as `NodePort`.

## 9.3 MongoDB Deployment

Conceptual `mongodb-deployment.yaml`:

``` yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mongodb-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mongodb
  template:
    metadata:
      labels:
        app: mongodb
    spec:
      containers:
        - name: mongodb
          image: mongo:7
          ports:
            - containerPort: 27017
          env:
            - name: MONGO_INITDB_ROOT_USERNAME
              valueFrom:
                secretKeyRef:
                  name: mongodb-secret
                  key: mongo-root-username
            - name: MONGO_INITDB_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mongodb-secret
                  key: mongo-root-password
```

## 9.4 MongoDB internal Service

`mongodb-service.yaml`:

``` yaml
apiVersion: v1
kind: Service
metadata:
  name: mongodb-service
spec:
  selector:
    app: mongodb
  ports:
    - protocol: TCP
      port: 27017
      targetPort: 27017
  type: ClusterIP
```

Mongo Express can use this DNS name inside the same Namespace:

``` text
mongodb-service:27017
```

## 9.5 Mongo Express Deployment

The Mongo Express container needs:

-   MongoDB Service hostname from the ConfigMap.
-   MongoDB username from the Secret.
-   MongoDB password from the Secret.

Example environment configuration:

``` yaml
env:
  - name: ME_CONFIG_MONGODB_SERVER
    valueFrom:
      configMapKeyRef:
        name: mongodb-configmap
        key: database_url

  - name: ME_CONFIG_MONGODB_ADMINUSERNAME
    valueFrom:
      secretKeyRef:
        name: mongodb-secret
        key: mongo-root-username

  - name: ME_CONFIG_MONGODB_ADMINPASSWORD
    valueFrom:
      secretKeyRef:
        name: mongodb-secret
        key: mongo-root-password
```

The Mongo Express container commonly listens on port `8081`.

## 9.6 Mongo Express external Service

For a local learning cluster, a NodePort Service can expose the UI:

``` yaml
apiVersion: v1
kind: Service
metadata:
  name: mongo-express-service
spec:
  selector:
    app: mongo-express
  ports:
    - protocol: TCP
      port: 8081
      targetPort: 8081
      nodePort: 30000
  type: NodePort
```

The Service selector must match the labels in the Mongo Express
Deployment's Pod template.

## 9.7 Apply resources in dependency order

Create the configuration before the Deployments that reference it:

``` bash
kubectl apply -f mongodb-secret.yaml
kubectl apply -f mongodb-configmap.yaml
kubectl apply -f mongodb-deployment.yaml
kubectl apply -f mongodb-service.yaml
kubectl apply -f mongo-express-deployment.yaml
kubectl apply -f mongo-express-service.yaml
```

Inspect:

``` bash
kubectl get all
kubectl get pods -o wide
kubectl get services
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

Open the Service with Minikube:

``` bash
minikube service mongo-express-service
```

## 9.8 What you should understand after the demo

You should be able to explain:

1.  Why MongoDB and Mongo Express run as separate workloads.
2.  Why MongoDB needs an internal Service.
3.  Why Mongo Express needs external access in this demo.
4.  How the Service selector finds the correct Pods.
5.  How the ConfigMap supplies the database hostname.
6.  How the Secret supplies credentials.
7.  Why the database needs persistent storage if its data must survive
    Pod replacement.

> This is a learning demo, not a production database deployment. It uses
> a simple database workload to teach Kubernetes resources. Production
> databases need persistent storage, backup and restore, security
> hardening, resource planning, and an appropriate availability design.

------------------------------------------------------------------------

# 10. Organize resources with Namespaces

Namespaces are easier to understand after you have created several
related resources.

## 10.1 What is a Namespace?

A **Namespace** is a logical grouping and naming scope for namespaced
Kubernetes resources. It helps organize resources within one cluster.

It is not a separate physical cluster and is not, by itself, a strong
security boundary.

## 10.2 Default Namespaces

A typical cluster includes:

  -----------------------------------------------------------------------
  Namespace                           Purpose
  ----------------------------------- -----------------------------------
  `default`                           Used when no Namespace is
                                      specified.

  `kube-system`                       Kubernetes system components. Avoid
                                      changing it without a clear reason.

  `kube-public`                       Intended for publicly readable
                                      cluster information.

  `kube-node-lease`                   Holds node lease objects used for
                                      heartbeat information.
  -----------------------------------------------------------------------

Local distributions may add their own Namespaces.

## 10.3 Why use Namespaces?

The video highlights these practical uses:

-   Group resources, for example `database`, `monitoring`, and
    `logging`.
-   Separate teams and avoid resource-name collisions.
-   Separate environments such as development and staging.
-   Apply RBAC permissions and resource quotas within a logical scope.

## 10.4 Create and use a Namespace

``` bash
kubectl get namespaces
kubectl create namespace development
kubectl get namespaces
```

Create resources in it:

``` bash
kubectl apply -f app.yaml -n development
kubectl get pods -n development
```

Or specify it in a manifest:

``` yaml
metadata:
  name: my-app
  namespace: development
```

Change the current context's default Namespace:

``` bash
kubectl config set-context --current --namespace=development
```

Inspect the current context:

``` bash
kubectl config view --minify
```

## 10.5 Important Namespace behavior

-   Most application resources are namespaced.
-   Nodes and PersistentVolumes are cluster-scoped.
-   ConfigMaps and Secrets are Namespace-scoped. A Pod cannot directly
    reference one in another Namespace.
-   Services can be reached across Namespaces through DNS, for example
    `service-name.namespace-name`.

------------------------------------------------------------------------

# 11. Expose HTTP applications with Ingress

The Mongo Express demo exposed a Service using a NodePort. That is
useful for learning, but real applications often need a hostname and
HTTP path routing.

## 11.1 What Ingress solves

Instead of asking users to visit an IP address and port, you may want:

``` text
https://example.com/          -> frontend Service
https://example.com/api       -> backend Service
https://admin.example.com/    -> admin Service
```

**Ingress** is an API object that defines HTTP/HTTPS routing rules from
outside the cluster to Services.

## 11.2 Ingress resource vs Ingress controller

-   **Ingress resource:** The routing rules stored in the Kubernetes
    API.
-   **Ingress controller:** The software that watches those rules and
    implements the routing.

Creating an Ingress resource alone does not make routing work. A
compatible Ingress controller must be installed and configured.

## 11.3 Example Ingress manifest

``` yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp-service
                port:
                  number: 8080
```

The Service `myapp-service` must exist and expose port `8080`.

## 11.4 Route by path

``` yaml
rules:
  - host: example.com
    http:
      paths:
        - path: /shop
          pathType: Prefix
          backend:
            service:
              name: shop-service
              port:
                number: 80
        - path: /api
          pathType: Prefix
          backend:
            service:
              name: api-service
              port:
                number: 8080
```

## 11.5 TLS / HTTPS

Ingress can use a TLS Secret containing a certificate and private key:

``` yaml
spec:
  tls:
    - hosts:
        - myapp.example.com
      secretName: myapp-tls
```

The TLS Secret must exist in the same Namespace as the Ingress.

## 11.6 Try Ingress with Minikube

The video demonstrates the Minikube Ingress add-on:

``` bash
minikube addons enable ingress
kubectl get pods -n ingress-nginx
```

The exact controller and setup can vary by Minikube version and
platform. Check the current Minikube documentation if the add-on
behavior changes.

**Checkpoint:** You can explain why an Ingress object needs a controller
and how host/path rules select backend Services.

------------------------------------------------------------------------

# 12. Persist data with Volumes

A database container may run successfully, but what happens to its data
when its Pod is removed and replaced?

That is the problem this section solves.

## 12.1 Why persistent storage is needed

A Pod is replaceable. Data written only to a container's writable layer
is not a reliable persistence strategy.

Kubernetes storage abstractions let workloads use storage whose
lifecycle is not tied to one specific container instance.

## 12.2 Volume

A **Volume** makes storage available to containers in a Pod. Its
lifecycle and persistence depend on the volume type.

Examples:

-   `emptyDir`: Temporary storage tied to the Pod's lifetime.
-   `hostPath`: A path from the node's filesystem; use carefully.
-   PersistentVolume-backed storage: Storage managed independently of an
    individual Pod.

## 12.3 PersistentVolume (PV)

A **PersistentVolume** represents storage available to the cluster.

It may be backed by local, network, or cloud-provider storage. A PV is
cluster-scoped.

## 12.4 PersistentVolumeClaim (PVC)

A **PersistentVolumeClaim** is a request for storage made by a workload
owner.

It can specify:

-   Requested capacity.
-   Access mode.
-   StorageClass.

A Pod references the PVC rather than managing the underlying storage
details itself.

## 12.5 StorageClass

A **StorageClass** describes a class of storage and its provisioner. It
can support dynamic provisioning: when a PVC requests storage, the
provisioner can create a matching volume.

## 12.6 Understand the storage relationship

``` text
Pod
 |
 | references
 v
PersistentVolumeClaim (PVC)
 |
 | binds to or requests
 v
PersistentVolume (PV)
 |
 | backed by
 v
Actual storage (disk / network / cloud storage)
```

With dynamic provisioning, the StorageClass and provisioner can create a
PV to satisfy the PVC.

## 12.7 Example PVC

``` yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

The cluster needs a suitable StorageClass or a matching PV for the claim
to bind.

## 12.8 Mount a PVC into a Pod

``` yaml
spec:
  containers:
    - name: app
      image: nginx
      volumeMounts:
        - name: app-storage
          mountPath: /data
  volumes:
    - name: app-storage
      persistentVolumeClaim:
        claimName: app-data
```

The PVC must exist in the same Namespace as the Pod.

## 12.9 ConfigMap and Secret as volumes

ConfigMaps and Secrets can also be mounted as files in a container. This
is useful when an application expects configuration files instead of
environment variables.

**Important:** A PVC is not a backup. Database backup, restore testing,
and storage failure planning are separate responsibilities.

------------------------------------------------------------------------

# 13. Run stateful applications with StatefulSets

A Deployment is a good fit for interchangeable stateless application
replicas. Some workloads need more predictable identity and storage
association.

## 13.1 Stateless vs stateful

**Stateless application:**

-   Does not depend on a particular Pod retaining local state between
    requests.
-   Replicas are usually interchangeable.
-   Example: a typical API server that stores data in an external
    database.

**Stateful application:**

-   May need stable identity.
-   May need stable storage association.
-   May need ordered startup and shutdown.
-   Examples include certain databases and clustered systems.

## 13.2 What is a StatefulSet?

A **StatefulSet** manages stateful Pods that need stable identities
and/or persistent storage associations.

Key characteristics:

-   Predictable Pod names such as `mysql-0`, `mysql-1`, `mysql-2`.
-   Stable identity across rescheduling.
-   Persistent storage can be provisioned per Pod through
    `volumeClaimTemplates`.
-   Ordered creation and termination by default.
-   Commonly paired with a Headless Service for stable per-Pod DNS.

## 13.3 Deployment vs StatefulSet

  -----------------------------------------------------------------------
  Deployment                          StatefulSet
  ----------------------------------- -----------------------------------
  Commonly used for stateless         Used when stable identity and/or
  workloads.                          storage association is required.

  Pods are generally interchangeable. Pods have stable ordinal
                                      identities.

  Pod names are generated and may     Pod names follow predictable
  change.                             ordinals.

  Commonly paired with a regular      Often paired with a Headless
  Service.                            Service for per-Pod DNS.

  Does not provide per-replica        Can create a PVC for each Pod using
  storage identity by itself.         `volumeClaimTemplates`.
  -----------------------------------------------------------------------

## 13.4 Pod identity

For a StatefulSet named `mysql` with three replicas:

``` text
mysql-0
mysql-1
mysql-2
```

Each ordinal represents a stable identity.

## 13.5 Headless Service and StatefulSet

A Headless Service sets:

``` yaml
spec:
  clusterIP: None
```

It can provide DNS records for individual Pods, helping clustered
applications discover specific members.

## 13.6 Scaling databases

The video discusses database master/worker or primary/replica-style
arrangements. Remember that StatefulSet only provides stable identity
and storage association. It does not automatically configure database
replication, primary election, failover, consistency, or backups.

Those behaviors must be implemented by the database system and its
operational configuration.

**Checkpoint:** You can explain why a database may need a StatefulSet
and why StatefulSet alone does not make a database highly available.

------------------------------------------------------------------------

# 14. Package Kubernetes applications with Helm

By now, an application may have several YAML files: Deployment,
Services, ConfigMaps, Secrets references, Ingress, and storage
resources.

Helm helps package and configure those resources.

## 14.1 What is Helm?

**Helm** is a package manager for Kubernetes. It installs and manages
applications using **Charts**.

A Chart is a package containing templates and default configuration for
Kubernetes resources.

## 14.2 Important Helm terms

-   **Chart:** The package containing templates and defaults.
-   **Release:** An installed instance of a Chart.
-   **values.yaml:** Default configuration values that can be
    overridden.
-   **Templates:** YAML templates rendered into Kubernetes manifests.

## 14.3 Typical Chart structure

``` text
my-chart/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    └── configmap.yaml
```

## 14.4 Example values.yaml

``` yaml
replicaCount: 2

image:
  repository: nginx
  tag: "1.27"

service:
  port: 80
```

A template can use a value:

``` yaml
spec:
  replicas: {{ .Values.replicaCount }}
```

The same Chart can be configured differently for development, staging,
and production.

## 14.5 Common Helm commands

``` bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm search repo nginx
```

Install a local Chart:

``` bash
helm install my-release ./my-chart
helm list
helm upgrade my-release ./my-chart
helm uninstall my-release
```

## 14.6 Important version note: Tiller

The video discusses **Tiller**, the server-side component used by Helm
2. Helm 3 removed Tiller. Do not design a new setup around Tiller. The
Chart and templating concepts remain relevant, but use current Helm 3
documentation.

Official documentation: [Helm](https://helm.sh/docs/).

------------------------------------------------------------------------

# 15. Put all the concepts into one application architecture

The video introduces components separately and then demonstrates them.
This diagram shows how the concepts fit together.

``` text
                          USER / BROWSER
                                |
                                v
                         Ingress Controller
                                |
                         Ingress routing rules
                                |
                                v
                        Frontend Service
                                |
                                v
                         Frontend Deployment
                                |
                             Frontend
                                |
                                v
                         Backend Service
                                |
                                v
                         Backend Deployment
                                |
                           Backend Pods
                                |
                   +------------+------------+
                   |                         |
                   v                         v
            Database Service            Cache Service
                   |                         |
                   v                         v
             Database Pod                Cache Pod
                   |
                   v
             Persistent Storage

Configuration:
  ConfigMaps -> non-sensitive settings
  Secrets    -> sensitive values

Organization:
  Namespaces -> logical grouping of resources

Packaging:
  Helm Chart -> templates and configuration for resources
```

This is a conceptual architecture for learning, not a complete
production design. The exact resources depend on the application and
cluster.

------------------------------------------------------------------------

# 16. Practical lab plan

Work through these milestones in order. Do not move on until you can
explain what happened at each stage.

## Lab 1 --- Start a cluster

-   [ ] Install Minikube.
-   [ ] Install kubectl.
-   [ ] Start the local cluster.
-   [ ] Confirm the node is `Ready`.

``` bash
minikube start
kubectl get nodes
kubectl cluster-info
```

## Lab 2 --- Create your first workload

-   [ ] Create an NGINX Deployment.
-   [ ] Inspect its Deployment, ReplicaSet, and Pod.
-   [ ] Read the Pod logs.
-   [ ] Describe the Pod.
-   [ ] Delete one Pod and observe the replacement.

``` bash
kubectl create deployment nginx --image=nginx
kubectl get deployments,replicasets,pods
kubectl describe pod <pod-name>
kubectl logs <pod-name>
kubectl delete pod <pod-name>
kubectl get pods -w
```

## Lab 3 --- Write YAML

-   [ ] Write a Deployment manifest.
-   [ ] Set replicas to two.
-   [ ] Add labels and selectors.
-   [ ] Apply the manifest.
-   [ ] Change the replica count and apply again.

``` bash
kubectl apply -f deployment.yaml
kubectl get deployments,pods
```

## Lab 4 --- Expose the application

-   [ ] Create a ClusterIP Service.
-   [ ] Verify that its selector matches the Pod labels.
-   [ ] Inspect the Service and its endpoints.
-   [ ] Try NodePort access in the local cluster.

``` bash
kubectl apply -f service.yaml
kubectl get services
kubectl describe service <service-name>
```

## Lab 5 --- MongoDB and Mongo Express

-   [ ] Create a Secret for credentials.
-   [ ] Create a ConfigMap for the database Service name.
-   [ ] Deploy MongoDB.
-   [ ] Create the internal MongoDB Service.
-   [ ] Deploy Mongo Express using the ConfigMap and Secret.
-   [ ] Expose Mongo Express externally.
-   [ ] Verify that Mongo Express can connect to MongoDB.

## Lab 6 --- Namespaces

-   [ ] Create a Namespace named `development`.
-   [ ] Deploy your application into it.
-   [ ] List resources in that Namespace.
-   [ ] Change your current context's default Namespace.
-   [ ] Explain which resources are cluster-scoped.

## Lab 7 --- Ingress

-   [ ] Enable or install an Ingress controller.
-   [ ] Create an Ingress resource.
-   [ ] Route a hostname or path to a Service.
-   [ ] Test the route.
-   [ ] Understand where TLS configuration belongs.

## Lab 8 --- Persistent storage and StatefulSet

-   [ ] Inspect available StorageClasses.
-   [ ] Create a PVC.
-   [ ] Mount it into a Pod.
-   [ ] Write data and recreate the Pod.
-   [ ] Verify the data persists.
-   [ ] Study StatefulSet Pod names and stable identity.
-   [ ] Understand the Headless Service relationship.

## Lab 9 --- Helm

-   [ ] Install Helm 3.
-   [ ] Add a chart repository.
-   [ ] Search for a Chart.
-   [ ] Install a Chart.
-   [ ] Inspect the release.
-   [ ] Upgrade and uninstall it.
-   [ ] Create a tiny Chart for your own NGINX Deployment.

------------------------------------------------------------------------

# 17. kubectl and Helm quick reference

## kubectl

  Task                          Command
  ----------------------------- ------------------------------------------------
  Cluster information           `kubectl cluster-info`
  List nodes                    `kubectl get nodes`
  List Pods                     `kubectl get pods`
  List Pods in all Namespaces   `kubectl get pods -A`
  List Deployments              `kubectl get deployments`
  List Services                 `kubectl get services`
  Show Pod details              `kubectl describe pod <pod>`
  Show logs                     `kubectl logs <pod>`
  Follow logs                   `kubectl logs -f <pod>`
  Open shell                    `kubectl exec -it <pod> -- /bin/sh`
  Apply YAML                    `kubectl apply -f file.yaml`
  Delete YAML resources         `kubectl delete -f file.yaml`
  Scale Deployment              `kubectl scale deployment <name> --replicas=3`
  Create Namespace              `kubectl create namespace <name>`
  Get resources in Namespace    `kubectl get all -n <namespace>`
  Watch Pods                    `kubectl get pods -w`
  Rollout status                `kubectl rollout status deployment/<name>`
  Rollout history               `kubectl rollout history deployment/<name>`
  Undo rollout                  `kubectl rollout undo deployment/<name>`

`kubectl get all` does not literally list every Kubernetes resource
type.

## Helm

  Task                  Command
  --------------------- ----------------------------------
  Add repository        `helm repo add <name> <url>`
  Update repositories   `helm repo update`
  Search repository     `helm search repo <keyword>`
  Install Chart         `helm install <release> <chart>`
  List releases         `helm list`
  Upgrade release       `helm upgrade <release> <chart>`
  Uninstall release     `helm uninstall <release>`

------------------------------------------------------------------------

# 18. Modern-version notes while following the video

The course was published in 2020. Its conceptual foundation remains
useful, but some implementation details have changed.

1.  **Master Node terminology:** Modern Kubernetes documentation
    generally says *control plane*.
2.  **Docker runtime integration:** Kubernetes removed dockershim in
    v1.24. Docker-built OCI-compatible images remain usable.
3.  **Helm Tiller:** Tiller belongs to Helm 2. Helm 3 removed it.
4.  **Ingress API:** Use `networking.k8s.io/v1` for current Ingress
    manifests and install a compatible Ingress controller.
5.  **Minikube drivers:** Follow current Minikube installation
    instructions; older driver flags may no longer be suitable.
6.  **Secrets:** Base64 is not encryption. Protect access and configure
    encryption at rest where appropriate.
7.  **Database persistence:** A simple MongoDB Deployment is a teaching
    demo. Real database workloads need persistent storage, backups,
    recovery, security, and availability planning.
8.  **NodePort:** Useful for learning and some network setups.
    Production exposure often uses a load balancer and/or Ingress,
    depending on the environment.
9.  **Service forwarding:** kube-proxy is common, but some networking
    implementations provide Service forwarding without it.

------------------------------------------------------------------------

# 19. What to learn after this video

This video establishes the beginner foundation. Once you can deploy and
connect a small application, continue with:

1.  Resource requests and limits.
2.  Liveness, readiness, and startup probes.
3.  Rolling updates and rollbacks in more depth.
4.  RBAC and ServiceAccounts.
5.  NetworkPolicies.
6.  Autoscaling with HPA.
7.  Monitoring and logging.
8.  Helm Charts for your own backend.
9.  Managed Kubernetes platforms and cloud load balancers.

These are follow-on topics, not prerequisites for understanding the
material in this guide.

------------------------------------------------------------------------

# 20. Official references

Use the video as the teaching walkthrough and current official
documentation when commands or APIs differ:

-   [Video --- Kubernetes Tutorial for Beginners, TechWorld with
    Nana](https://www.youtube.com/watch?v=X48VuDVv0do)
-   [TechWorld with Nana --- Written Kubernetes
    guide](https://www.techworld-with-nana.com/guides/kubernetes-tutorial)
-   [Kubernetes documentation ---
    Concepts](https://kubernetes.io/docs/concepts/)
-   [Kubernetes --- Cluster
    Architecture](https://kubernetes.io/docs/concepts/architecture/)
-   [Kubernetes ---
    Workloads](https://kubernetes.io/docs/concepts/workloads/)
-   [Kubernetes --- Services, Load Balancing, and
    Networking](https://kubernetes.io/docs/concepts/services-networking/)
-   [Kubernetes ---
    Storage](https://kubernetes.io/docs/concepts/storage/)
-   [Minikube --- Getting
    Started](https://minikube.sigs.k8s.io/docs/start/)
-   [Helm documentation](https://helm.sh/docs/)

------------------------------------------------------------------------

# Final self-assessment

You are ready to move beyond this beginner course when you can do the
following without copying every command:

-   [ ] Explain the problem Kubernetes solves and how it differs from
    Docker.
-   [ ] Explain Cluster, Node, Pod, Deployment, ReplicaSet, and Service.
-   [ ] Draw the control plane and worker node architecture.
-   [ ] Explain the roles of API Server, Scheduler, Controller Manager,
    and etcd.
-   [ ] Explain the roles of kubelet, container runtime, and kube-proxy.
-   [ ] Start a local cluster and use kubectl.
-   [ ] Deploy an application using YAML.
-   [ ] Explain labels, selectors, and Pod templates.
-   [ ] Connect two workloads through a Service.
-   [ ] Supply configuration through ConfigMaps and Secrets.
-   [ ] Deploy the MongoDB + Mongo Express demo and explain its traffic
    flow.
-   [ ] Organize resources using Namespaces.
-   [ ] Explain Ingress and why it needs a controller.
-   [ ] Explain PV, PVC, and StorageClass.
-   [ ] Explain why a StatefulSet is different from a Deployment.
-   [ ] Explain what Helm Charts and Releases are.

**The central idea:** Kubernetes is declarative. You describe the state
you want, and Kubernetes components continuously work to make the actual
cluster state match it.
