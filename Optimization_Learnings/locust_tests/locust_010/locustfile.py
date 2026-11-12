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
