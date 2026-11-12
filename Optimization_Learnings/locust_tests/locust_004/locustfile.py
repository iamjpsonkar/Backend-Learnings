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
        self.client.post(
            "/posts",
            json={
                "title": random.choice(POST_TITLES),
                "body": random.choice(POST_BODIES),
                "userId": random.randint(1, 10),
            },
        )
