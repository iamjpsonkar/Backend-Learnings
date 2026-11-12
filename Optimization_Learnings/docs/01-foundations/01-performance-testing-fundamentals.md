# Performance Testing Fundamentals

Performance testing measures how a system behaves under a defined workload. It
helps determine whether the system meets its response-time, throughput,
reliability, and resource-usage goals.

Performance testing is not simply “sending many requests.” A useful test has a
representative workload, measurable acceptance criteria, controlled test data,
and monitoring on both the load generator and the system under test.

## Why performance testing matters

- Find slow endpoints and resource bottlenecks before production.
- Verify that the system meets service-level objectives under expected load.
- Estimate capacity and identify when scaling is required.
- Detect performance regressions between releases.
- Understand failure behavior and recovery at unusually high load.
- Protect user experience and operational reliability.

## Important measurements

- **Response time:** How long a request takes, usually reported with percentiles
  such as the median, p95, and p99.
- **Throughput:** The amount of work completed per unit of time, such as requests
  per second (RPS).
- **Error rate:** The percentage or rate of requests that fail.
- **Concurrency:** The number of users or operations active at the same time.
- **Resource utilization:** CPU, memory, disk, network, connection-pool, and
  database usage on the system under test.

An average alone can hide slow outliers. Percentiles are usually more useful: a
p95 response time of 800 ms means 95% of measured responses completed in 800 ms
or less.

## Types of performance testing

- **Load testing:** Verifies behavior under expected and peak workloads.
- **Stress testing:** Increases load until the system reaches or passes its
  capacity limit.
- **Spike testing:** Applies sudden increases and decreases in traffic.
- **Soak (endurance) testing:** Runs for an extended period to reveal leaks,
  resource exhaustion, or gradual degradation.
- **Volume testing:** Evaluates behavior with large amounts of stored or
  transferred data.
- **Scalability testing:** Measures how performance changes as resources or
  workload increase.

## A practical testing workflow

1. Define the question the test must answer.
2. Set measurable success criteria, such as p95 latency and maximum error rate.
3. Model realistic user journeys, traffic ratios, and wait times.
4. Prepare representative test data and an isolated environment when possible.
5. Establish a baseline with a small workload.
6. Increase load gradually while monitoring application and infrastructure
   metrics.
7. Analyze bottlenecks, make one controlled change, and rerun the same test.

Results are only comparable when the workload, environment, data, and test
duration are controlled and recorded.
