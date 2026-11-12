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
