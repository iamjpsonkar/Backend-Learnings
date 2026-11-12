# Photo-Sharing Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Upload photos, create variants, publish albums/posts, enforce privacy, and serve through a CDN.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Photo(id, owner, object_version, status, visibility); Variant(photo, size, key); Post(id, photo_ids, caption). Binary media lives in object storage.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
client -> signed upload -> object store -> scan/resize queue -> variants -> CDN; metadata API -> database
```

Use multipart uploads, content hashes, asynchronous transforms, immutable versioned keys, and CDN caching. Partition metadata by owner/photo ID.

## Failure, security, and observability

Validate media, strip unsafe metadata, authorize manifest/URL issuance, purge or version on privacy changes, and monitor processing lag, failures, CDN hits, and orphan objects.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Pre-generating common sizes speeds views but costs storage; on-demand transforms reduce storage while adding cold latency and abuse risk.
