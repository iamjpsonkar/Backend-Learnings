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
