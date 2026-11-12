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
