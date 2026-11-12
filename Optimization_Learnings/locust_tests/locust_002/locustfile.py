from locust import HttpUser, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_data(self):
        self.client.get("/get")

    @task(1)
    def get_headers(self):
        self.client.get("/headers")
