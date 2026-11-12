# Organizing Locust Tasks

A Locust task represents an action performed by a simulated user. A task is usually
a method decorated with `@task`, but it can also be a `TaskSet` or
`SequentialTaskSet` class.

Tasks declared directly on a user or a regular `TaskSet` are selected randomly.
Use weights to control how often each task is selected. Use a
`SequentialTaskSet` when the actions must run in a fixed order.

## Task organization options

- `@task`: Define a simple task.
- `@task(weight)`: Select tasks randomly according to relative weights.
- `TaskSet`: Group related tasks that are selected randomly.
- `SequentialTaskSet`: Group tasks that must run in declaration order.
- Nested task sets: Model sections and subsections of a larger application.

## Prerequisites

Install Locust and verify the installation:

```sh
pip install locust
locust --version
```

The examples use [JSONPlaceholder](https://jsonplaceholder.typicode.com), a test
API that supports the routes used below.

## Weighted tasks

Weights define relative execution frequency; they do not define task order. In
this example, the four tasks have a `5:4:3:2` ratio. The total weight is 14, so
`view_posts` is selected approximately `5/14` of the time.

Create `locust_tests/locust_008/locustfile.py`:

```python
import random

from locust import HttpUser, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task(5)
    def view_posts(self):
        self.client.get("/posts", name="/posts")

    @task(4)
    def view_post(self):
        self.client.get("/posts/1", name="/posts/[id]")

    @task(3)
    def view_random_post(self):
        post_id = random.randint(1, 100)
        self.client.get(f"/posts/{post_id}", name="/posts/[id]")

    @task(2)
    def search_posts(self):
        user_id = random.randint(1, 10)
        self.client.get("/posts", params={"userId": user_id}, name="/posts?userId=[id]")
```

Run the test:

```sh
locust -f locust_tests/locust_008/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

The `name` argument groups requests with different IDs under one row in Locust's
statistics.

## Ordered tasks with `SequentialTaskSet`

A `SequentialTaskSet` executes tasks in declaration order and repeats the
sequence. It must be assigned to a `User`; a `SequentialTaskSet` is not a user by
itself.

Create `locust_tests/locust_009/locustfile.py`:

```python
import random

from locust import HttpUser, SequentialTaskSet, between, task


class BrowseSequence(SequentialTaskSet):
    @task
    def view_posts(self):
        self.client.get("/posts", name="/posts")

    @task
    def view_post(self):
        self.client.get("/posts/1", name="/posts/[id]")

    @task
    def view_random_post(self):
        post_id = random.randint(1, 100)
        self.client.get(f"/posts/{post_id}", name="/posts/[id]")

    @task
    def search_posts(self):
        user_id = random.randint(1, 10)
        self.client.get("/posts", params={"userId": user_id}, name="/posts?userId=[id]")


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    tasks = [BrowseSequence]
```

Run the test:

```sh
locust -f locust_tests/locust_009/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

The sequence runs from top to bottom and then starts again. In a
`SequentialTaskSet`, `@task(2)` repeats that step twice at its declared position;
it does not give the step a random selection probability.

## Grouped tasks with `TaskSet`

A `TaskSet` groups related behavior. Tasks inside each group are selected
randomly according to their weights. The user below enters read behavior three
times as often as write behavior.

Create `locust_tests/locust_010/locustfile.py`:

```python
import random

from locust import HttpUser, TaskSet, between, task


class ReadPosts(TaskSet):
    @task(3)
    def list_posts(self):
        self.client.get("/posts", name="/posts")

    @task(2)
    def view_post(self):
        post_id = random.randint(1, 100)
        self.client.get(f"/posts/{post_id}", name="/posts/[id]")

    @task(1)
    def leave_read_section(self):
        self.interrupt()


class WritePosts(TaskSet):
    @task(2)
    def create_post(self):
        self.client.post(
            "/posts",
            json={
                "title": "A Locust test post",
                "body": "Created during a load test",
                "userId": random.randint(1, 10),
            },
        )

    @task(1)
    def delete_post(self):
        post_id = random.randint(1, 100)
        self.client.delete(f"/posts/{post_id}", name="/posts/[id]")

    @task(1)
    def leave_write_section(self):
        self.interrupt()


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    tasks = {ReadPosts: 3, WritePosts: 1}
```

Run the test:

```sh
locust -f locust_tests/locust_010/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

A `TaskSet` does not return to its parent automatically. Its exit task must call
`self.interrupt()` so the parent can select another task or task set.

## A complete sequential user journey

Use a `SequentialTaskSet` when several requests form one business journey. This
example initializes per-user state, performs three ordered requests, and then
returns control to the parent user.

Create `locust_tests/locust_011/locustfile.py`:

```python
import random

from locust import HttpUser, SequentialTaskSet, between, task


class PostJourney(SequentialTaskSet):
    def on_start(self):
        self.post_id = random.randint(1, 100)

    @task
    def list_posts(self):
        self.client.get("/posts", name="/posts")

    @task
    def view_post(self):
        self.client.get(f"/posts/{self.post_id}", name="/posts/[id]")

    @task
    def view_comments(self):
        self.client.get(
            f"/posts/{self.post_id}/comments",
            name="/posts/[id]/comments",
        )

    @task
    def finish_journey(self):
        self.interrupt()


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    tasks = [PostJourney]
```

Run the test:

```sh
locust -f locust_tests/locust_011/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

`on_start()` runs each time the task set begins. Here it selects one post ID that
is shared by the related steps in that journey.

## Nested task sets

Task sets can contain other task sets. This is useful when an application has a
hierarchy, such as a posts section containing a comments subsection.

Create `locust_tests/locust_012/locustfile.py`:

```python
import random

from locust import HttpUser, TaskSet, between, task


class CommentTasks(TaskSet):
    @task(3)
    def list_comments(self):
        self.client.get("/comments", name="/comments")

    @task(1)
    def view_comment(self):
        comment_id = random.randint(1, 100)
        self.client.get(f"/comments/{comment_id}", name="/comments/[id]")

    @task(1)
    def leave_comments(self):
        self.interrupt()


class PostTasks(TaskSet):
    tasks = {CommentTasks: 2}

    @task(3)
    def list_posts(self):
        self.client.get("/posts", name="/posts")

    @task(2)
    def view_post(self):
        post_id = random.randint(1, 100)
        self.client.get(f"/posts/{post_id}", name="/posts/[id]")

    @task(1)
    def leave_posts(self):
        self.interrupt()


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    tasks = [PostTasks]
```

Run the test:

```sh
locust -f locust_tests/locust_012/locustfile.py \
  --host=https://jsonplaceholder.typicode.com
```

When `CommentTasks` calls `interrupt()`, execution returns to `PostTasks`. When
`PostTasks` calls it, execution returns to `WebsiteUser`.

## Choosing the right approach

| Requirement | Recommended approach |
| --- | --- |
| Independent user actions | Methods decorated with `@task` |
| Different action frequencies | Weighted `@task(weight)` methods |
| Related actions selected randomly | `TaskSet` |
| A fixed, repeatable user journey | `SequentialTaskSet` |
| Hierarchical application behavior | Nested task sets |

For a short ordered flow, a single `@task` method containing several requests is
often simpler than a `SequentialTaskSet`. Use task sets when grouping, reuse, or
nested behavior makes the test easier to understand.

## Common mistakes

- Defining a `TaskSet` or `SequentialTaskSet` without assigning it to an
  `HttpUser`.
- Expecting weighted tasks to run in a predictable order.
- Forgetting `self.interrupt()` when a nested task set should return to its
  parent.
- Using dynamic URLs as separate statistics names, which creates one row per ID.
- Sending load to a service without permission. Use a test environment or an API
  intended for testing.

See the official [Locust TaskSet documentation](https://docs.locust.io/en/stable/tasksets.html)
for more details.
