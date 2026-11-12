from locust import FastHttpUser, between, task


class WebsiteUser(FastHttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        self.client.get("/posts")
