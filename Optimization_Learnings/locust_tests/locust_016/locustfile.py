from locust import HttpUser, LoadTestShape, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        self.client.get("/posts")


class SpikeLoadShape(LoadTestShape):
    stages = (
        {"duration": 30, "users": 5, "spawn_rate": 2},
        {"duration": 45, "users": 30, "spawn_rate": 15},
        {"duration": 75, "users": 5, "spawn_rate": 15},
    )

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]

        return None
