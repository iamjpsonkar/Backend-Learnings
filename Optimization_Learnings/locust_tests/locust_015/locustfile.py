from locust import HttpUser, LoadTestShape, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        self.client.get("/posts")


class StepLoadShape(LoadTestShape):
    step_duration = 30
    users_per_step = 5
    spawn_rate = 2
    duration = 120

    def tick(self):
        run_time = self.get_run_time()

        if run_time >= self.duration:
            return None

        step = int(run_time // self.step_duration) + 1
        return step * self.users_per_step, self.spawn_rate
