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
