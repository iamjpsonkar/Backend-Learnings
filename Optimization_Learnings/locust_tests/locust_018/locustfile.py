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
