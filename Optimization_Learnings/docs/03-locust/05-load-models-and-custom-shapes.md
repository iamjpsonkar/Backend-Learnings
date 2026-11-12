# Load Models and Custom Shapes

A workload model describes how simulated traffic changes over time. Choosing the
right model matters because a constant number of users, a constant task rate,
and a constant request rate are different goals.

## Concurrency and throughput

- **Concurrent users:** The number of active simulated users.
- **Spawn rate:** How quickly Locust starts or stops users to reach a target.
- **Task throughput:** The number of task iterations started per second.
- **Request throughput (RPS):** The number of HTTP requests completed per second.

One task can make multiple requests, and each user waits between tasks. Therefore,
ten users do not imply ten RPS, and one task per second does not imply one RPS
when that task sends multiple requests.

## How custom shapes work

A class derived from `LoadTestShape` controls concurrent users over time. Locust
calls its `tick()` method approximately once per second. The method returns:

```text
(target_user_count, spawn_rate)
```

Returning `None` stops the test. When a locustfile contains a custom shape, the
shape controls user count, spawn rate, and duration instead of the corresponding
web UI or command-line values.

## Constant concurrent-user load

This shape ramps to ten users, maintains ten concurrent users, and stops after
60 seconds. The ramp takes approximately five seconds at two users per second.

Create `locust_tests/locust_013/locustfile.py`:

```python
from locust import HttpUser, LoadTestShape, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        self.client.get("/posts")


class ConstantLoadShape(LoadTestShape):
    users = 10
    spawn_rate = 2
    duration = 60

    def tick(self):
        if self.get_run_time() < self.duration:
            return self.users, self.spawn_rate

        return None
```

Run the test:

```sh
locust -f locust_tests/locust_013/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --headless
```

Constant users do not produce constant RPS. Response time, task complexity, and
wait time still affect throughput.

## Constant task throughput

`constant_throughput(rate)` adjusts each user's wait time to target a number of
task runs per second. This example targets one task per second per user.

Create `locust_tests/locust_014/locustfile.py`:

```python
from locust import HttpUser, constant_throughput, task


class WebsiteUser(HttpUser):
    wait_time = constant_throughput(1)

    @task
    def list_posts(self):
        self.client.get("/posts")
```

Run five users for one minute:

```sh
locust -f locust_tests/locust_014/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --headless \
  --users=5 \
  --spawn-rate=1 \
  --run-time=1m
```

With one request in the task, five users target approximately five RPS after
ramp-up. This is not a strict global rate limiter. If a task takes longer than
the target interval, Locust cannot maintain the requested rate and waits zero
seconds before the next iteration.

## Step load

A step test raises concurrency at fixed intervals. It helps reveal the point at
which latency, error rate, or resource utilization begins to degrade.

This example starts with five users and adds five users every 30 seconds. It
reaches 20 users in the final stage and stops after two minutes.

Create `locust_tests/locust_015/locustfile.py`:

```python
from locust import HttpUser, LoadTestShape, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        self.client.get("/posts")


class StepLoadShape(LoadTestShape):
    step_duration = 30
    users_per_step = 5
    spawn_rate = 2
    duration = 120

    def tick(self):
        run_time = self.get_run_time()

        if run_time >= self.duration:
            return None

        step = int(run_time // self.step_duration) + 1
        return step * self.users_per_step, self.spawn_rate
```

Run the test:

```sh
locust -f locust_tests/locust_015/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --headless
```

The stages are:

| Elapsed time | Target users |
| --- | ---: |
| 0–29 seconds | 5 |
| 30–59 seconds | 10 |
| 60–89 seconds | 15 |
| 90–119 seconds | 20 |

## Spike load

A spike test applies a rapid traffic increase and then returns to the baseline.
It measures how the system handles sudden demand and whether it recovers after
the spike.

Create `locust_tests/locust_016/locustfile.py`:

```python
from locust import HttpUser, LoadTestShape, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        self.client.get("/posts")


class SpikeLoadShape(LoadTestShape):
    stages = (
        {"duration": 30, "users": 5, "spawn_rate": 2},
        {"duration": 45, "users": 30, "spawn_rate": 15},
        {"duration": 75, "users": 5, "spawn_rate": 15},
    )

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]

        return None
```

Run the test:

```sh
locust -f locust_tests/locust_016/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --headless
```

The `duration` values are cumulative stage end times:

| Elapsed time | Target users | Behavior |
| --- | ---: | --- |
| 0–29 seconds | 5 | Baseline |
| 30–44 seconds | 30 | Rapid spike |
| 45–74 seconds | 5 | Recovery |
| 75 seconds | 0 | Test stops |

## Choosing a workload model

| Goal | Recommended model |
| --- | --- |
| Observe behavior at a stable concurrency | Constant-user shape |
| Approximate a task rate per user | `constant_throughput()` |
| Find where degradation begins | Step load |
| Test sudden demand and recovery | Spike load |
| Reproduce a production traffic profile | Custom staged shape |

Start with small values, validate the scenario, and monitor the load generator as
well as the target system. A requested shape is not useful if the load generator
lacks the CPU or network capacity to produce it.

See the official
[custom load shape documentation](https://docs.locust.io/en/stable/custom-load-shape.html)
and [Locust API reference](https://docs.locust.io/en/stable/api.html) for details.
