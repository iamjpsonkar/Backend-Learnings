import logging

from locust import HttpUser, between, events, task


MAX_FAILURE_RATIO = 0.01
MAX_AVERAGE_RESPONSE_TIME = 1_000
MAX_P95_RESPONSE_TIME = 2_000


@events.quitting.add_listener
def enforce_performance_thresholds(environment, **_kwargs):
    stats = environment.stats.total

    if stats.fail_ratio > MAX_FAILURE_RATIO:
        logging.error("Failure ratio exceeded 1%%")
        environment.process_exit_code = 1
    elif stats.avg_response_time > MAX_AVERAGE_RESPONSE_TIME:
        logging.error("Average response time exceeded 1000 ms")
        environment.process_exit_code = 1
    elif stats.get_response_time_percentile(0.95) > MAX_P95_RESPONSE_TIME:
        logging.error("p95 response time exceeded 2000 ms")
        environment.process_exit_code = 1
    else:
        environment.process_exit_code = 0


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        self.client.get("/posts")
