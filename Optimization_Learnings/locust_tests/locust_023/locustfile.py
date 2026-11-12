from locust import HttpUser, between, events, task


@events.init_command_line_parser.add_listener
def add_custom_arguments(parser):
    parser.add_argument(
        "--post-limit",
        type=int,
        default=10,
        env_var="LOCUST_POST_LIMIT",
        help="Number of posts requested by each task",
    )


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_posts(self):
        post_limit = self.environment.parsed_options.post_limit
        self.client.get(
            "/posts",
            params={"_limit": post_limit},
            name="/posts?_limit=[value]",
        )
