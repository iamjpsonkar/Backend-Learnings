# Web Search Engine

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Crawl permitted pages, build an inverted index, rank matches, and return low-latency results.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Document(doc_id,url,version,features); TermPosting(term, shard, doc, positions); link graph and learned features are separate datasets.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
crawler -> document store -> parse/index pipeline -> immutable index shards; query -> broker -> shards -> rank/merge
```

Shard by document for balanced indexing, replicate query shards, cache frequent queries, and use tiered retrieval then expensive reranking.

## Failure, security, and observability

Use timeouts and partial results for missing shards, malware filters, versioned rollouts, and track freshness, coverage, relevance, query p99, and shard errors.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Document sharding makes ingestion balanced but queries fan out; term sharding reduces fan-out for rare terms but creates skew.
