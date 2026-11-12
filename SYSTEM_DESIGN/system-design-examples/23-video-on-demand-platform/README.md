# Video-on-Demand Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Upload, scan, transcode, publish, search, authorize, and adaptively stream video.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Video(id, owner, source_key, status, visibility); Rendition(video, codec, bitrate, manifest_key). Store watch events separately.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
client -> object upload -> workflow -> transcoders -> object store/CDN; playback API -> signed manifest
```

Make workflow steps idempotent, create common HLS/DASH renditions, use immutable segments, and partition metadata by video ID and events by user/video.

## Failure, security, and observability

Reconcile stuck jobs, dead-letter bad inputs, enforce entitlement when signing URLs, and monitor transcode age, playback start, rebuffering, CDN hit rate, and cost/minute.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

More renditions improve device/network fit but increase compute and storage; generate rare formats on demand.
