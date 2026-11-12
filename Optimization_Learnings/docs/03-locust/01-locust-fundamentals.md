# Locust Fundamentals

Locust is an open-source load-testing tool. Test scenarios are written in Python,
and each simulated user runs tasks that describe its behavior. Locust provides a
web interface, headless execution, real-time statistics, and distributed load
generation.

## Core concepts

- **`User`:** The base class for a simulated user.
- **`HttpUser`:** A user with an HTTP client whose requests are measured by
  Locust.
- **Task:** A unit of behavior, commonly a method decorated with `@task`.
- **Task weight:** A relative value that controls how often a random task is
  selected.
- **Wait time:** The pause between completed tasks, used to model user think
  time.
- **Spawn rate:** The number of users started per second until the target user
  count is reached.

Locust users are concurrent greenlets, not operating-system threads. The load a
single machine can generate depends on the scenario, response sizes, network,
and available CPU. Distributed mode can add worker machines when one load
generator is not enough.

## Key features

- Python-based scenarios with normal control flow and reusable code.
- Real-time request counts, failures, throughput, and response-time percentiles.
- Interactive web UI and non-interactive headless mode.
- Distributed execution across a controller and worker processes.
- HTTP support through `HttpUser`, with extension points for other protocols.
- Request grouping and custom validation for meaningful statistics.

## Typical uses

- Validate expected and peak production workloads in a test environment.
- Find a system's capacity limit and observe its failure behavior.
- Compare performance before and after a code or infrastructure change.
- Model multi-step user journeys and traffic mixes.
- Run repeatable performance checks in CI or release pipelines.

## Good practices

- Define latency, throughput, and failure-rate goals before running the test.
- Begin with one user, validate the scenario, and increase load gradually.
- Model realistic task ratios, user journeys, test data, and wait times.
- Group dynamic URLs with the `name` request argument.
- Use `catch_response=True` when success depends on response content.
- Monitor server CPU, memory, database, cache, and network metrics alongside
  Locust statistics.
- Run the load generator separately from the system under test when measuring
  meaningful capacity.
- Keep the workload and environment stable when comparing test runs.

## Common pitfalls

- Running a load test against production without explicit approval and safety
  controls.
- Increasing users before confirming that a one-user scenario is correct.
- Treating concurrent user count as equivalent to requests per second.
- Ignoring failures or relying only on average response time.
- Printing every response during a load test, which adds load-generator overhead.
- Using `time.sleep()` inside tasks instead of Locust wait times or cooperative
  scheduling.
- Generating more load than one machine can sustain and mistaking a load-generator
  bottleneck for a server bottleneck.

See the official [Locust documentation](https://docs.locust.io/en/stable/) for
architecture, configuration, and distributed-running details.
