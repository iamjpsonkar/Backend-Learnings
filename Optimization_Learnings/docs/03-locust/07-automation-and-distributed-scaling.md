# Locust Automation and Distributed Scaling

A useful performance test must be repeatable, produce actionable artifacts, and
fail automatically when agreed performance criteria are violated. This guide
covers thresholds, parameterization, faster load generation, configuration,
distributed execution, and CI usage.

## Automated performance thresholds

Locust exits nonzero when requests fail, but a test can also fail when latency or
failure-rate objectives are exceeded. The `quitting` event runs before process
exit and can set `environment.process_exit_code`.

Create `locust_tests/locust_022/locustfile.py`:

```python
import logging

from locust import HttpUser, between, events, task


MAX_FAILURE_RATIO = 0.01
MAX_AVERAGE_RESPONSE_TIME = 1_000
MAX_P95_RESPONSE_TIME = 2_000


@events.quitting.add_listener
def enforce_performance_thresholds(environment, **_kwargs):
    stats = environment.stats.total

    if stats.fail_ratio > MAX_FAILURE_RATIO:
        logging.error("Failure ratio exceeded 1%%")
        environment.process_exit_code = 1
    elif stats.avg_response_time > MAX_AVERAGE_RESPONSE_TIME:
        logging.error("Average response time exceeded 1000 ms")
        environment.process_exit_code = 1
    elif stats.get_response_time_percentile(0.95) > MAX_P95_RESPONSE_TIME:
        logging.error("p95 response time exceeded 2000 ms")
        environment.process_exit_code = 1
    else:
        environment.process_exit_code = 0


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        self.client.get("/posts")
```

Run it headlessly so the exit code can gate automation:

```sh
locust -f locust_tests/locust_022/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --headless \
  --users=5 \
  --spawn-rate=1 \
  --run-time=1m
```

Thresholds must come from service-level objectives or a controlled baseline, not
arbitrary universal values. Average latency is included for demonstration, but
percentile objectives are usually more informative.

## Custom command-line arguments

Custom arguments make a locustfile reusable without editing code. They also
appear in the web UI and are forwarded to workers when a distributed test starts.

Create `locust_tests/locust_023/locustfile.py`:

```python
from locust import HttpUser, between, events, task


@events.init_command_line_parser.add_listener
def add_custom_arguments(parser):
    parser.add_argument(
        "--post-limit",
        type=int,
        default=10,
        env_var="LOCUST_POST_LIMIT",
        help="Number of posts requested by each task",
    )


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        post_limit = self.environment.parsed_options.post_limit
        self.client.get(
            "/posts",
            params={"_limit": post_limit},
            name="/posts?_limit=[value]",
        )
```

Set the value on the command line:

```sh
locust -f locust_tests/locust_023/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --post-limit=5
```

Or use its environment variable:

```sh
LOCUST_POST_LIMIT=5 locust \
  -f locust_tests/locust_023/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

Do not put secrets directly in commands because they may appear in shell history
or process listings. Use a secret manager or protected environment variables.

## Faster load generation with `FastHttpUser`

`FastHttpUser` uses `geventhttpclient` and generally consumes less CPU than the
default requests-based `HttpUser`. It can increase generator throughput, but it
does not make the target service respond faster.

Create `locust_tests/locust_024/locustfile.py`:

```python
from locust import FastHttpUser, between, task


class WebsiteUser(FastHttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        self.client.get("/posts")
```

Run it like any other locustfile:

```sh
locust -f locust_tests/locust_024/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

Benchmark both clients with your real scenario. `FastHttpUser` has a very similar
API, but code that relies on requests internals may need changes.

## Configuration files

Repeated command options can live in a configuration file. This repository
includes `locust.conf.example`:

```ini
locustfile = locust_tests/locust_003/locustfile.py
host = https://jsonplaceholder.typicode.com
headless = true
users = 5
spawn-rate = 1
run-time = 30s
html = report.html
```

Run with the example configuration:

```sh
locust --config=locust.conf.example
```

Locust loads configuration in this order, with later sources overriding earlier
ones: configuration files, environment variables, then command-line arguments.
Keep environment-specific values and credentials out of version control.

## Result artifacts

Create an HTML report and CSV files during a headless run:

```sh
mkdir -p results
locust -f locust_tests/locust_003/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --headless \
  --users=5 \
  --spawn-rate=1 \
  --run-time=1m \
  --html=results/report.html \
  --csv=results/run
```

Store workload parameters, code revision, environment details, and server-side
metrics with the results. A report without test context is difficult to compare
or reproduce.

## Distributed execution

The master coordinates the test and aggregates statistics. Workers generate the
load; the master does not run simulated users itself.

Start a headless master that waits for two workers:

```sh
locust -f locust_tests/locust_003/locustfile.py \
  --master \
  --headless \
  --expect-workers=2 \
  --users=100 \
  --spawn-rate=10 \
  --run-time=5m \
  --host=https://target.example.test
```

Start the same locustfile on each worker machine:

```sh
locust -f locust_tests/locust_003/locustfile.py \
  --worker \
  --master-host=MASTER_IP
```

Requirements for a distributed run:

- Every worker must use the same locustfile and compatible dependencies.
- Workers must reach the target service and the master's communication port.
- Test data must be safe for concurrent use across processes and machines.
- Server and generator clocks should be synchronized.
- Monitor CPU and network utilization on every load generator.

On supported Unix-like systems, `--processes` can use multiple local CPU cores.
Separate machines are still preferable when generator and target resources could
interfere with each other.

## Continuous integration

The repository's validation workflow checks formatting, links, code-to-guide
synchronization, Python syntax, and Locust user discovery without contacting
public targets. A real CI performance test should run against an isolated,
stable environment and archive its reports.

Use short smoke performance tests on frequent changes. Run longer load, stress,
and soak tests on scheduled or release workflows so CI feedback remains useful.

See the official [event hook documentation](https://docs.locust.io/en/stable/extending-locust.html),
[distributed execution guide](https://docs.locust.io/en/stable/running-distributed.html),
and [performance guide](https://docs.locust.io/en/stable/increase-performance.html).
