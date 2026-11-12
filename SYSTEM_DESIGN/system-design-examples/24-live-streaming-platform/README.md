# Live-Streaming Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Ingest live media, transcode renditions, distribute low-latency segments, provide chat, and archive streams.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Stream(id, creator, state, ingest_region); Segment(stream, sequence, rendition, key); chat and viewer counts are independent services.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
broadcaster -> regional ingest -> transcode -> packager -> origin shield -> CDN -> viewers
```

Assign redundant ingest endpoints, produce short CMAF/HLS segments, cascade distribution, and aggregate viewer counts rather than writing per view.

## Failure, security, and observability

Fail over ingest with discontinuity markers, isolate chat from media, authorize publish/play tokens, and track end-to-end latency, dropped frames, segment gaps, and CDN misses.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Short segments lower latency but increase request/encoding overhead and reduce recovery buffer.
