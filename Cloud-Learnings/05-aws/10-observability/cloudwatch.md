← [Previous: AWS Observability](./README.md) | [Home](../../README.md) | [Next: CloudTrail →](./cloudtrail.md)

---

# Amazon CloudWatch

CloudWatch is the native AWS observability service. It collects metrics, logs, and traces; evaluates alarms; and generates dashboards — all in one place. It is the primary operational data plane for every AWS service.

---

## Core Components

| Component | What it does |
|-----------|-------------|
| **Metrics** | Time-series numeric data — CPU, request count, latency, custom |
| **Logs** | Structured/unstructured log events in Log Groups and Log Streams |
| **Alarms** | Evaluate metrics against thresholds; trigger actions (SNS, EC2, ASG, Lambda) |
| **Dashboards** | Visualise metrics across services and accounts |
| **Contributor Insights** | Identify top contributors from log data (top IPs, top error codes) |
| **Synthetics (Canaries)** | Scheduled scripts that monitor endpoints from outside your application |
| **Evidently** | Feature flags and A/B experiments with CloudWatch metrics |
| **Logs Insights** | Interactive query language for log analysis |
| **Metric Streams** | Real-time streaming of metrics to Kinesis Firehose / third-party tools |

---

## Metrics

### Publishing Custom Metrics

```bash
# Publish a single custom metric
aws cloudwatch put-metric-data \
    --namespace "MyApp/Orders" \
    --metric-name "OrdersProcessed" \
    --value 42 \
    --unit Count \
    --dimensions Environment=production,Service=order-service

# Publish multiple metrics in one call (more efficient — up to 20 per call)
aws cloudwatch put-metric-data \
    --namespace "MyApp/Orders" \
    --metric-data '[
        {
            "MetricName": "OrdersProcessed",
            "Dimensions": [{"Name": "Environment", "Value": "production"}],
            "Value": 42,
            "Unit": "Count"
        },
        {
            "MetricName": "OrderProcessingLatency",
            "Dimensions": [{"Name": "Environment", "Value": "production"}],
            "Value": 234.5,
            "Unit": "Milliseconds"
        }
    ]'

# Get recent metric statistics
aws cloudwatch get-metric-statistics \
    --namespace "AWS/EC2" \
    --metric-name "CPUUtilization" \
    --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
    --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Average Maximum \
    --query 'Datapoints[*].{Time:Timestamp,Avg:Average,Max:Maximum}' \
    --output table
```

### Python — Publishing Metrics from Application Code

```python
import boto3
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

# Module-level client for reuse across Lambda warm invocations
_cw = boto3.client("cloudwatch", region_name="us-east-1")

NAMESPACE = "MyApp/Orders"
ENVIRONMENT = "production"


def publish_metric(metric_name: str, value: float, unit: str = "Count", **dimensions) -> None:
    """Publish a single custom metric to CloudWatch."""
    dim_list = [{"Name": k, "Value": str(v)} for k, v in dimensions.items()]
    dim_list.append({"Name": "Environment", "Value": ENVIRONMENT})

    logger.debug(
        "Publishing metric: namespace=%s metric=%s value=%s unit=%s dimensions=%s",
        NAMESPACE, metric_name, value, unit, dimensions
    )
    try:
        _cw.put_metric_data(
            Namespace=NAMESPACE,
            MetricData=[{
                "MetricName": metric_name,
                "Dimensions": dim_list,
                "Value": value,
                "Unit": unit,
            }],
        )
    except Exception as e:
        # Log but do not raise — metric failures must not break the application
        logger.warning("Failed to publish metric: metric=%s error=%s", metric_name, str(e))


def timed(metric_name: str):
    """Decorator that records execution time as a CloudWatch metric."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                publish_metric(metric_name + "Success", 1, unit="Count", Function=func.__name__)
                return result
            except Exception as e:
                publish_metric(metric_name + "Error", 1, unit="Count", Function=func.__name__)
                logger.error("Function failed: name=%s error=%s", func.__name__, str(e))
                raise
            finally:
                elapsed_ms = (time.monotonic() - start) * 1000
                publish_metric(metric_name + "Latency", elapsed_ms, unit="Milliseconds", Function=func.__name__)
                logger.debug("Execution timed: name=%s latency_ms=%.1f", func.__name__, elapsed_ms)
        return wrapper
    return decorator


@timed("ProcessOrder")
def process_order(order_id: str) -> dict:
    logger.info("Processing order: order_id=%s", order_id)
    # ... business logic ...
    return {"order_id": order_id, "status": "processed"}
```

---

## CloudWatch Logs

### Log Groups and Streams

```bash
# Create a log group with 30-day retention
aws logs create-log-group \
    --log-group-name "/aws/myapp/production" \
    --tags Environment=production,Service=my-app

aws logs put-retention-policy \
    --log-group-name "/aws/myapp/production" \
    --retention-in-days 30

# List log groups and their retention
aws logs describe-log-groups \
    --query 'logGroups[*].{Name:logGroupName,RetentionDays:retentionInDays,StoredBytes:storedBytes}' \
    --output table

# Tail recent log events
aws logs tail "/aws/myapp/production" --follow --since 10m

# Filter logs by pattern (last 1 hour)
aws logs filter-log-events \
    --log-group-name "/aws/myapp/production" \
    --start-time $(($(date +%s) - 3600))000 \
    --filter-pattern "ERROR" \
    --query 'events[*].{Time:timestamp,Message:message}' \
    --output table
```

### Logs Insights Queries

```bash
# Run a Logs Insights query
aws logs start-query \
    --log-group-names "/aws/myapp/production" "/aws/lambda/my-function" \
    --start-time $(($(date +%s) - 3600)) \
    --end-time $(date +%s) \
    --query-string '
        fields @timestamp, @message, @logStream
        | filter @message like /ERROR/
        | stats count(*) as errorCount by bin(5m)
        | sort @timestamp desc
        | limit 50
    '

# Useful Logs Insights query patterns:
# Top error messages:
#   fields @message
#   | filter level = "ERROR"
#   | stats count(*) as cnt by @message
#   | sort cnt desc
#   | limit 20

# P99 latency per endpoint:
#   fields endpoint, duration_ms
#   | stats pct(duration_ms, 99) as p99 by endpoint
#   | sort p99 desc

# Lambda cold start rate:
#   filter @type = "REPORT"
#   | stats count(initDuration) as coldStarts, count(*) as total by bin(5m)
#   | fields (coldStarts / total) * 100 as coldStartPct
```

### Metric Filters (Logs → Metrics)

```bash
# Create a metric filter: count ERROR log lines as a custom metric
aws logs put-metric-filter \
    --log-group-name "/aws/myapp/production" \
    --filter-name "error-count" \
    --filter-pattern "[timestamp, level=\"ERROR\", ...]" \
    --metric-transformations \
        metricName=ErrorCount,metricNamespace=MyApp/Logs,metricValue=1,unit=Count,defaultValue=0

# JSON-structured logs — extract a numeric field
aws logs put-metric-filter \
    --log-group-name "/aws/myapp/production" \
    --filter-name "order-latency" \
    --filter-pattern '{ $.level = "INFO" && $.event = "order.processed" }' \
    --metric-transformations \
        metricName=OrderLatency,metricNamespace=MyApp/Performance,metricValue='$.duration_ms',unit=Milliseconds
```

---

## Alarms

```bash
# Alarm: high CPU on an EC2 instance — notify SNS and stop instance
aws cloudwatch put-metric-alarm \
    --alarm-name "ec2-high-cpu-i-1234567890abcdef0" \
    --alarm-description "CPU > 80% for 10 minutes" \
    --namespace "AWS/EC2" \
    --metric-name "CPUUtilization" \
    --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 80 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --alarm-actions \
        arn:aws:sns:us-east-1:123456789012:ops-alerts \
        arn:aws:automate:us-east-1:ec2:stop \
    --ok-actions arn:aws:sns:us-east-1:123456789012:ops-alerts \
    --treat-missing-data breaching

# Alarm: ALB 5xx error rate > 1% over 5 minutes
aws cloudwatch put-metric-alarm \
    --alarm-name "alb-5xx-error-rate" \
    --alarm-description "ALB HTTP 5xx error rate above 1%" \
    --metrics '[
        {
            "Id": "e1",
            "Expression": "m2/m1*100",
            "Label": "5xx Error Rate %"
        },
        {
            "Id": "m1",
            "MetricStat": {
                "Metric": {
                    "Namespace": "AWS/ApplicationELB",
                    "MetricName": "RequestCount",
                    "Dimensions": [{"Name": "LoadBalancer", "Value": "app/my-alb/abc123"}]
                },
                "Period": 300,
                "Stat": "Sum"
            },
            "ReturnData": false
        },
        {
            "Id": "m2",
            "MetricStat": {
                "Metric": {
                    "Namespace": "AWS/ApplicationELB",
                    "MetricName": "HTTPCode_Target_5XX_Count",
                    "Dimensions": [{"Name": "LoadBalancer", "Value": "app/my-alb/abc123"}]
                },
                "Period": 300,
                "Stat": "Sum"
            },
            "ReturnData": false
        }
    ]' \
    --threshold 1 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts \
    --treat-missing-data notBreaching

# Composite alarm (alarm fires only if BOTH sub-alarms fire — reduces noise)
aws cloudwatch put-composite-alarm \
    --alarm-name "service-degraded" \
    --alarm-description "Service degraded — high error rate AND high latency" \
    --alarm-rule "ALARM(alb-5xx-error-rate) AND ALARM(alb-p99-latency-high)" \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts
```

---

## Dashboards

```bash
# Create a dashboard with key application metrics
aws cloudwatch put-dashboard \
    --dashboard-name "MyApp-Production" \
    --dashboard-body '{
        "widgets": [
            {
                "type": "metric",
                "x": 0, "y": 0, "width": 12, "height": 6,
                "properties": {
                    "title": "Request Rate and Error Rate",
                    "view": "timeSeries",
                    "stacked": false,
                    "metrics": [
                        ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/my-alb/abc123", {"stat": "Sum", "period": 60, "label": "Requests/min"}],
                        ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", "app/my-alb/abc123", {"stat": "Sum", "period": 60, "color": "#d62728", "label": "5xx Errors/min"}]
                    ],
                    "period": 60,
                    "region": "us-east-1"
                }
            },
            {
                "type": "metric",
                "x": 12, "y": 0, "width": 12, "height": 6,
                "properties": {
                    "title": "Target Response Time P50/P99",
                    "view": "timeSeries",
                    "metrics": [
                        ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "app/my-alb/abc123", {"stat": "p50", "period": 60, "label": "P50"}],
                        ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "app/my-alb/abc123", {"stat": "p99", "period": 60, "label": "P99", "color": "#ff7f0e"}]
                    ],
                    "period": 60
                }
            },
            {
                "type": "alarm",
                "x": 0, "y": 6, "width": 6, "height": 3,
                "properties": {
                    "title": "Active Alarms",
                    "alarms": ["arn:aws:cloudwatch:us-east-1:123456789012:alarm:alb-5xx-error-rate"]
                }
            }
        ]
    }'
```

---

## CloudWatch Synthetics (Canaries)

```bash
# Create a canary to heartbeat-check an HTTP endpoint every 5 minutes
aws synthetics create-canary \
    --name my-app-heartbeat \
    --code Handler=index.handler,S3Bucket=my-canary-bucket,S3Key=canary-code.zip \
    --artifact-s3-location s3://my-canary-artifacts/my-app-heartbeat/ \
    --execution-role-arn arn:aws:iam::123456789012:role/CloudWatchSyntheticsRole \
    --schedule Expression="rate(5 minutes)" \
    --run-config TimeoutInSeconds=30,MemoryInMB=960,ActiveTracing=true \
    --runtime-version syn-nodejs-puppeteer-6.2 \
    --tags Environment=production

# Minimal Node.js canary (inline — for simple URL checks)
# Place this in a zip as index.js with handler: index.handler
# const synthetics = require('Synthetics');
# const log = require('SyntheticsLogger');
# exports.handler = async () => {
#     await synthetics.executeHttpStep('Homepage check', {
#         hostname: 'example.com', path: '/', port: 443, protocol: 'https:'
#     });
# };
```

---

## Key Metrics by Service

| Service | Important Metrics | Alarm Threshold |
|---------|------------------|-----------------|
| EC2 | `CPUUtilization`, `NetworkIn/Out`, `StatusCheckFailed` | CPU >80% for 10m |
| ALB | `RequestCount`, `TargetResponseTime`, `HTTPCode_Target_5XX_Count` | 5xx rate >1% |
| Lambda | `Errors`, `Duration`, `Throttles`, `ConcurrentExecutions` | Error rate >1%, p99 duration near timeout |
| RDS | `CPUUtilization`, `FreeStorageSpace`, `DatabaseConnections`, `ReadLatency` | CPU >80%, storage <10% |
| SQS | `ApproximateNumberOfMessagesVisible`, `ApproximateAgeOfOldestMessage` | Age >5min = backlog |
| DynamoDB | `SystemErrors`, `SuccessfulRequestLatency`, `ThrottledRequests` | Throttles >0 |
| ECS | `CPUUtilization`, `MemoryUtilization`, `RunningTaskCount` | Memory >85% |

---

## References

- [CloudWatch documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/)
- [Logs Insights query syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [CloudWatch Synthetics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html)
- [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
---

← [Previous: AWS Observability](./README.md) | [Home](../../README.md) | [Next: CloudTrail →](./cloudtrail.md)
