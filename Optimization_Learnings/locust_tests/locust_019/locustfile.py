from locust import HttpUser, between, task


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def view_post_author(self):
        with self.client.get(
            "/posts/1",
            name="/posts/[id]",
            catch_response=True,
        ) as response:
            try:
                user_id = response.json()["userId"]
            except (KeyError, ValueError):
                response.failure("Post response did not contain a userId")
                return

        self.client.get(f"/users/{user_id}", name="/users/[id]")
