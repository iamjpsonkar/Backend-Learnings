# Testing HTTP Methods with Locust

These examples use [JSONPlaceholder](https://jsonplaceholder.typicode.com), a
public API intended for examples and prototyping. Its write operations are
simulated: POST, PUT, and DELETE responses look successful, but data is not
persisted on the server.

Use a small user count and low spawn rate when running against any public demo
service.

## GET requests and query parameters

Create `locust_tests/locust_003/locustfile.py`:

```python
import random

from locust import HttpUser, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        self.client.get("/posts", name="/posts")

    @task
    def view_fixed_post(self):
        self.client.get("/posts/1", name="/posts/[id]")

    @task
    def view_random_post(self):
        post_id = random.randint(1, 100)
        self.client.get(f"/posts/{post_id}", name="/posts/[id]")

    @task
    def search_posts(self):
        user_id = random.randint(1, 10)
        self.client.get(
            "/posts",
            params={"userId": user_id},
            name="/posts?userId=[id]",
        )
```

Run the test:

```sh
locust -f locust_tests/locust_003/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

The `params` argument safely builds the query string. The `name` argument groups
dynamic IDs into stable rows in Locust's statistics.

## POST requests

Create `locust_tests/locust_004/locustfile.py`:

```python
import random

from locust import HttpUser, between, task


POST_TITLES = (
    "The Silence Between Stars",
    "Where the Wild Roads End",
    "The Last Letter at Midnight",
)

POST_BODIES = (
    "An astronomer discovers a message hidden between distant stars.",
    "Two strangers follow an abandoned road toward a town missing from every map.",
    "A midnight letter reveals a family's long-buried secret.",
)


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def create_post(self):
        self.client.post(
            "/posts",
            json={
                "title": random.choice(POST_TITLES),
                "body": random.choice(POST_BODIES),
                "userId": random.randint(1, 10),
            },
        )
```

Run the test:

```sh
locust -f locust_tests/locust_004/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

The payload choices are module-level constants so they are created once when the
file is imported, rather than rebuilt on every request.

## Validating a response

HTTP status alone may not prove that an operation succeeded. Use
`catch_response=True` to validate status and content and to mark a request as a
failure in Locust's statistics.

Create `locust_tests/locust_005/locustfile.py`:

```python
import random

from locust import HttpUser, between, task


POST_TITLES = (
    "The Silence Between Stars",
    "Where the Wild Roads End",
    "The Last Letter at Midnight",
)

POST_BODIES = (
    "An astronomer discovers a message hidden between distant stars.",
    "Two strangers follow an abandoned road toward a town missing from every map.",
    "A midnight letter reveals a family's long-buried secret.",
)


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def create_post(self):
        with self.client.post(
            "/posts",
            json={
                "title": random.choice(POST_TITLES),
                "body": random.choice(POST_BODIES),
                "userId": random.randint(1, 10),
            },
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"Expected status 201, got {response.status_code}")
                return

            try:
                response_data = response.json()
            except ValueError:
                response.failure("Response body was not valid JSON")
                return

            if "id" not in response_data:
                response.failure("Response JSON did not contain an id")
            else:
                response.success()
```

Run the test:

```sh
locust -f locust_tests/locust_005/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

Printing every response is intentionally avoided because console output can
become a load-generator bottleneck.

## PUT requests

Create `locust_tests/locust_006/locustfile.py`:

```python
import random

from locust import HttpUser, between, task


POST_TITLES = (
    "The Silence Between Stars",
    "Where the Wild Roads End",
    "The Last Letter at Midnight",
)

POST_BODIES = (
    "An astronomer discovers a message hidden between distant stars.",
    "Two strangers follow an abandoned road toward a town missing from every map.",
    "A midnight letter reveals a family's long-buried secret.",
)


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def update_post(self):
        post_id = random.randint(1, 100)
        self.client.put(
            f"/posts/{post_id}",
            name="/posts/[id]",
            json={
                "id": post_id,
                "title": random.choice(POST_TITLES),
                "body": random.choice(POST_BODIES),
                "userId": random.randint(1, 10),
            },
        )
```

Run the test:

```sh
locust -f locust_tests/locust_006/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

All IDs are grouped under `/posts/[id]` in the statistics.

## DELETE requests

Create `locust_tests/locust_007/locustfile.py`:

```python
import random

from locust import HttpUser, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def delete_post(self):
        post_id = random.randint(1, 100)
        self.client.delete(f"/posts/{post_id}", name="/posts/[id]")
```

Run the test:

```sh
locust -f locust_tests/locust_007/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

## Optional headless run

Any example can run without the web interface. Start with a small workload:

```sh
locust -f locust_tests/locust_003/locustfile.py \
  --host=https://jsonplaceholder.typicode.com \
  --headless \
  --users=2 \
  --spawn-rate=1 \
  --run-time=15s
```

See [Organizing Locust tasks](04-organizing-tasks.md) for weighted, sequential, grouped,
and nested behavior.
