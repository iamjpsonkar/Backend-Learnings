# Expected Output — Observability

## Prometheus Target Status

```
State: UP
Labels: job="sample-api", instance="sample-api:8000"
```

## PromQL Query Result

Query: `rate(http_requests_total[5m])`

```json
{
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {"job": "sample-api", "method": "GET", "path": "/health", "status": "200"},
        "value": [1700000000, "0.5"]
      }
    ]
  }
}
```

## Loki Log Query

```json
{
  "streams": [
    {
      "stream": {"container": "cloud-learnings-sample-api"},
      "values": [
        ["1700000000000000000", "{\"timestamp\":\"2024-01-01T12:00:00\",\"level\":\"INFO\",\"message\":\"Request completed\",\"method\":\"GET\",\"path\":\"/health\",\"status\":200}"]
      ]
    }
  ]
}
```

## Grafana Dashboard

After completing Task 6, you should see:
- A time series graph showing request rate over time
- A stat showing current active request count
- A live log stream from the sample-api container

## Prometheus Alert

After stopping sample-api, within 2 minutes:
```
State: FIRING
Alert: ServiceDown
Labels: job="sample-api"
Annotations: summary="Service sample-api is down"
```
