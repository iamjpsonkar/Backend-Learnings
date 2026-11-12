# Advanced Locust Patterns

This guide builds on the basic HTTP, task, and load-shape examples. It covers
precise pacing, per-user state, request correlation, task filtering, and traffic
mixes with multiple user classes.

## Fixed iteration pacing

`constant_pacing(seconds)` targets a fixed interval between the start of task
iterations for each user. If a task takes 300 ms and pacing is two seconds, the
user waits about 1.7 seconds before starting again. If the task takes longer than
two seconds, Locust waits zero seconds.

Create `locust_tests/locust_017/locustfile.py`:

```python
from locust import HttpUser, constant_pacing, task


class WebsiteUser(HttpUser):
    wait_time = constant_pacing(2)

    @task
    def list_posts(self):
        self.client.get("/posts")
```

Run the test:

```sh
locust -f locust_tests/locust_017/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --headless \
  --users=2 \
  --spawn-rate=1 \
  --run-time=30s
```

Use `constant_pacing(2)` for one iteration every two seconds per user. Use
`constant_throughput(2)` for two iterations per second per user.

## User lifecycle and per-user state

`on_start()` runs once when each simulated user starts. It is useful for login,
test-data allocation, or loading per-user state. `on_stop()` runs when that user
stops and can release resources or reset local state.

Create `locust_tests/locust_018/locustfile.py`:

```python
import random

from locust import HttpUser, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.user_id = random.randint(1, 10)
        self.client.get(f"/users/{self.user_id}", name="/users/[id]")

    @task
    def view_my_posts(self):
        self.client.get(
            "/posts",
            params={"userId": self.user_id},
            name="/posts?userId=[id]",
        )

    def on_stop(self):
        self.user_id = None
```

Run the test:

```sh
locust -f locust_tests/locust_018/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

Each user receives its own `WebsiteUser` instance and therefore its own
`user_id`. For an authenticated API, `on_start()` can send a login request and
store a token in `self.client.headers`.

Avoid putting shared mutable state in module globals unless access is
intentionally coordinated.

## Correlating requests

Correlation extracts a value from one response and uses it in a later request.
This is essential for realistic workflows involving IDs, tokens, pagination,
and server-generated references.

Create `locust_tests/locust_019/locustfile.py`:

```python
from locust import HttpUser, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def view_post_author(self):
        with self.client.get(
            "/posts/1",
            name="/posts/[id]",
            catch_response=True,
        ) as response:
            try:
                user_id = response.json()["userId"]
            except (KeyError, ValueError):
                response.failure("Post response did not contain a userId")
                return

        self.client.get(f"/users/{user_id}", name="/users/[id]")
```

Run the test:

```sh
locust -f locust_tests/locust_019/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

The first response is validated before its `userId` is used. Returning after
`response.failure()` prevents a misleading second request with invalid data.

## Filtering tasks with tags

Tags let one locustfile support focused test suites such as read-only, write,
smoke, or critical-path tests.

Create `locust_tests/locust_020/locustfile.py`:

```python
import random

from locust import HttpUser, between, tag, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @tag("read")
    @task(3)
    def list_posts(self):
        self.client.get("/posts")

    @tag("read", "detail")
    @task(2)
    def view_post(self):
        post_id = random.randint(1, 100)
        self.client.get(f"/posts/{post_id}", name="/posts/[id]")

    @tag("write")
    @task(1)
    def create_post(self):
        self.client.post(
            "/posts",
            json={"title": "Tagged task", "body": "Example", "userId": 1},
        )
```

Run only read tasks:

```sh
locust -f locust_tests/locust_020/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --tags=read
```

Run everything except write tasks:

```sh
locust -f locust_tests/locust_020/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --exclude-tags=write
```

When more than one included tag is provided, a task runs if it has any included
tag. Excluded tags take precedence.

## Multiple user classes

Separate user classes model populations with different behavior and wait times.
The `weight` attribute controls their relative population. `fixed_count` reserves
an exact number of users and takes precedence over weight.

Create `locust_tests/locust_021/locustfile.py`:

```python
import random

from locust import HttpUser, between, constant, task


class BrowserUser(HttpUser):
    weight = 3
    wait_time = between(1, 3)

    @task
    def browse_posts(self):
        post_id = random.randint(1, 100)
        self.client.get(f"/posts/{post_id}", name="/posts/[id]")


class AuthorUser(HttpUser):
    weight = 1
    wait_time = between(2, 5)

    @task
    def create_post(self):
        self.client.post(
            "/posts",
            json={"title": "New post", "body": "Example", "userId": 1},
        )


class MonitorUser(HttpUser):
    fixed_count = 1
    wait_time = constant(10)

    @task
    def check_service(self):
        self.client.get("/posts/1", name="/posts/[id]")
```

Run nine total users:

```sh
locust -f locust_tests/locust_021/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --headless \
  --users=9 \
  --spawn-rate=2 \
  --run-time=1m
```

Locust first creates one `MonitorUser`. The remaining users are divided between
`BrowserUser` and `AuthorUser` using the `3:1` weight ratio.

To run only selected classes, pass their names after the command options:

```sh
locust -f locust_tests/locust_021/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  BrowserUser AuthorUser
```

## Pattern selection guide

| Requirement | Pattern |
| --- | --- |
| Fixed time between iteration starts | `constant_pacing()` |
| Initialize state once per user | `on_start()` |
| Clean up when a user exits | `on_stop()` |
| Reuse response data in later requests | Correlation |
| Run a subset of tasks | Tags |
| Model different user populations | Multiple user classes |

Keep tasks focused on user behavior. Move large data-generation, setup, and
cleanup operations outside timed request paths when possible.
