import random

from locust import HttpUser, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def delete_post(self):
        post_id = random.randint(1, 100)
        self.client.delete(f"/posts/{post_id}", name="/posts/[id]")
