from locust import HttpUser, constant_throughput, task


class WebsiteUser(HttpUser):
    wait_time = constant_throughput(1)

    @task
    def list_posts(self):
        self.client.get("/posts")
