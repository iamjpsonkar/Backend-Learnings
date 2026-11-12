# Recommendation Service

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Generate candidates, retrieve fresh features, rank, experiment, and learn from exposure and feedback.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Item/user embeddings and features are versioned; CandidateSet(request,user,items); Exposure(request,item,model) joins later outcomes.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
events -> feature/embedding pipelines -> online stores; request -> candidates -> feature fetch -> ranker -> policy -> response
```

Use multiple candidate sources, approximate-nearest-neighbor indexes, bounded feature deadlines, fallback rankings, and cache anonymous results.

## Failure, security, and observability

Validate model/features, canary by cohort, prevent leakage, protect user data, and monitor latency, coverage, diversity, drift, business metrics, and fallback rate.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

More complex models can improve relevance but increase latency, opacity, feature freshness requirements, and rollback risk.
