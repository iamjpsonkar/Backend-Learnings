import random

from locust import HttpUser, between, task


POST_TITLES = (
    "The Silence Between Stars",
    "Where the Wild Roads End",
    "The Last Letter at Midnight",
)

POST_BODIES = (
    "An astronomer discovers a message hidden between distant stars.",
    "Two strangers follow an abandoned road toward a town missing from every map.",
    "A midnight letter reveals a family's long-buried secret.",
)


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def create_post(self):
        with self.client.post(
            "/posts",
            json={
                "title": random.choice(POST_TITLES),
                "body": random.choice(POST_BODIES),
                "userId": random.randint(1, 10),
            },
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"Expected status 201, got {response.status_code}")
                return

            try:
                response_data = response.json()
            except ValueError:
                response.failure("Response body was not valid JSON")
                return

            if "id" not in response_data:
                response.failure("Response JSON did not contain an id")
            else:
                response.success()
