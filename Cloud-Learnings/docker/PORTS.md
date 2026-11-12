# Port Reference

All ports used by the Cloud-Learnings Lab Platform. All ports are on `localhost` and only accessible from your machine.

## Core Profile

| Port | Service | Protocol | URL |
|---|---|---|---|
| 80 | Traefik (HTTP entrypoint) | HTTP | http://localhost:80 |
| 443 | Traefik (HTTPS entrypoint) | HTTPS | https://localhost:443 |
| 3000 | Homepage Dashboard | HTTP | http://localhost:3000 |
| 8080 | Traefik Dashboard | HTTP | http://localhost:8080/dashboard/ |

## Dashboard Profile

| Port | Service | Protocol | URL |
|---|---|---|---|
| 9000 | Portainer Docker UI | HTTP | http://localhost:9000 |

## Data Profile

| Port | Service | Protocol | Notes |
|---|---|---|---|
| 5432 | PostgreSQL | TCP | `psql -h localhost -U labuser -d labdb` |
| 3306 | MySQL | TCP | `mysql -h 127.0.0.1 -u labuser -p labdb` |
| 27017 | MongoDB | TCP | `mongosh localhost:27017` |
| 6379 | Redis | TCP | `redis-cli -h localhost -a redispassword123` |
| 8081 | Adminer (DB UI) | HTTP | http://localhost:8081 |
| 8082 | Redis Commander | HTTP | http://localhost:8082 |

## Messaging Profile

| Port | Service | Protocol | Notes |
|---|---|---|---|
| 5672 | RabbitMQ AMQP | AMQP | `amqp://admin:adminpassword123@localhost:5672/` |
| 15672 | RabbitMQ Management | HTTP | http://localhost:15672 |
| 9092 | Redpanda (Kafka API) | TCP | `kafka://localhost:9092` |
| 9644 | Redpanda Admin | HTTP | http://localhost:9644 |
| 8083 | Redpanda Console | HTTP | http://localhost:8083 |
| 8084 | Redpanda Schema Registry | HTTP | http://localhost:8084 |

## AWS Profile

| Port | Service | Protocol | Notes |
|---|---|---|---|
| 4566 | LocalStack (all AWS services) | HTTP | `aws --endpoint-url=http://localhost:4566` |
| 4510-4559 | LocalStack internal | TCP | Reserved range |
| 9001 | MinIO S3 API | HTTP | `aws --endpoint-url=http://localhost:9001` |
| 9002 | MinIO Console | HTTP | http://localhost:9002 |

## Azure Profile

| Port | Service | Protocol | Notes |
|---|---|---|---|
| 10000 | Azurite Blob Storage | HTTP | `DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;...` |
| 10001 | Azurite Queue Storage | HTTP | See .env.example for full connection string |
| 10002 | Azurite Table Storage | HTTP | See .env.example for full connection string |

## GCP Profile

| Port | Service | Protocol | Notes |
|---|---|---|---|
| 8085 | GCP Pub/Sub Emulator | HTTP | `PUBSUB_EMULATOR_HOST=localhost:8085` |
| 8086 | GCP Firestore Emulator | HTTP | `FIRESTORE_EMULATOR_HOST=localhost:8086` |

## Observability Profile

| Port | Service | Protocol | URL |
|---|---|---|---|
| 9090 | Prometheus | HTTP | http://localhost:9090 |
| 3001 | Grafana | HTTP | http://localhost:3001 (admin/admin) |
| 3100 | Loki | HTTP | http://localhost:3100 |
| 3200 | Tempo | HTTP | http://localhost:3200 |
| 4317 | OTel Collector / Tempo OTLP gRPC | gRPC | `grpc://localhost:4317` |
| 4318 | OTel Collector / Tempo OTLP HTTP | HTTP | http://localhost:4318 |
| 8889 | OTel Collector Prometheus metrics | HTTP | http://localhost:8889/metrics |

## Security Profile

| Port | Service | Protocol | URL |
|---|---|---|---|
| 8200 | Vault | HTTP | http://localhost:8200 (token: dev-root-token) |
| 8180 | Keycloak | HTTP | http://localhost:8180/admin (admin/adminpassword123) |

## CI/CD Profile

| Port | Service | Protocol | URL |
|---|---|---|---|
| 3002 | Gitea | HTTP | http://localhost:3002 (gitadmin/gitpassword123) |
| 2222 | Gitea SSH | SSH | `git clone git@localhost:2222/org/repo.git` |
| 8090 | Jenkins | HTTP | http://localhost:8090 |
| 50000 | Jenkins Agent | TCP | Jenkins agent protocol |
| 5000 | Docker Registry | HTTP | http://localhost:5000 |

## Apps Profile

| Port | Service | Protocol | URL |
|---|---|---|---|
| 8000 | Sample API | HTTP | http://localhost:8000/health |
| 8100 | Sample Frontend | HTTP | http://localhost:8100 |
| 8001 | Event Producer | HTTP | http://localhost:8001 |

---

## Changing Ports

All ports are configurable in `.env`. Example:

```env
POSTGRES_PORT=5433
GRAFANA_PORT=3005
```

After changing `.env`, restart the affected services:

```bash
./run.sh restart
```

## Port Conflict Detection

Run `./run.sh doctor` to check for port conflicts before starting.

Manual check:

```bash
# macOS/Linux
lsof -i :4566   # Check if LocalStack port is free
lsof -i :5432   # Check if Postgres port is free
```

## Security Note

All ports are bound to `127.0.0.1` by default (localhost only). They are not accessible from the network. If you need to access them from another machine, use SSH tunneling — do not bind to `0.0.0.0` in production environments.
