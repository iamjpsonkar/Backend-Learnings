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
