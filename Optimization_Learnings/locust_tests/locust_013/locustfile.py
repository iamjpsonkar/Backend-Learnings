from locust import HttpUser, LoadTestShape, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        self.client.get("/posts")


class ConstantLoadShape(LoadTestShape):
    users = 10
    spawn_rate = 2
    duration = 60

    def tick(self):
        if self.get_run_time() < self.duration:
            return self.users, self.spawn_rate

        return None
