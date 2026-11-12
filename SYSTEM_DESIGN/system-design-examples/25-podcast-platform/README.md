# Podcast Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Ingest publisher feeds, store episodes, serve audio, synchronize progress, and calculate analytics.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Show(feed_url, etag, poll_at); Episode(show, guid, media_key, published_at); Progress(user, episode, position, version).

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
scheduler -> conditional feed fetch -> parser/deduper -> metadata/media -> CDN; clients -> progress API/events
```

Use adaptive polling, GUID plus enclosure hashes for deduplication, object storage/CDN for cached media, and batched analytics streams.

## Failure, security, and observability

Sandbox parsing, prevent SSRF, honor takedowns, use optimistic progress updates, and measure poll lag, duplicate rate, playback errors, CDN hit ratio, and analytics delay.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Proxying audio improves reliability and analytics but adds bandwidth/copyright obligations; direct URLs reduce cost but reduce control.
