from locust import HttpUser, constant_pacing, task


class WebsiteUser(HttpUser):
    wait_time = constant_pacing(2)

    @task
    def list_posts(self):
        self.client.get("/posts")
