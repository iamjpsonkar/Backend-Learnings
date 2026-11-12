# Complete Solution: Log Aggregation Platform

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Collect logs from hosts, containers, functions, devices and cloud streams; survive
network/backend outages with bounded local spool; authenticate/tenant-tag, parse,
redact, enrich and route; store a compressed archive and selectively indexed hot data;
support time-bounded text/field/aggregate queries, live tail, dashboards/alerts, tiered
retention, replay/reindex and auditable access/deletion.

Targets: five PB/day raw input, seconds from online source to search, p99 ingest ACK
below 500 ms, ordinary query p99 below two seconds, 99.99% read/ingest control
availability, and no silent loss after durable ACK. Delivery is at least once: source/
batch/record identities enable dedupe where affordable. Every result declares ingest/
index watermark and partial/truncated status.

## 2. Capacity estimation

Five PB/day is about 58 GB/s average and potentially 3–5x burst. With 5:1 compression:

- archive still grows about 1 PB/day before replication;
- indexing even 20% at 2x compressed-data overhead can add hundreds of TB/day;
- at 500-byte average record, ingest exceeds ten billion records/day (~116,000/s),
  but real small logs can be millions/s;
- a 15-minute regional outage at 1 GB/s/source fleet needs 900 GB aggregate spool;
- query scans must be bounded by tenant/time/index pruning; scanning one day of 5 PB
  for an interactive query is not viable;
- retention, indexing tier, sampling and cardinality are cost/product contracts, not
  afterthought cleanup.

## 3. APIs and query language

```text
POST /v1/ingest/batches                    agent mTLS, streamId, sequence, checksum
POST /v1/search
  {"from":"...", "to":"...", "query":"service=api AND level>=ERROR ...",
   "limit":100, "cursor":"..."}
POST /v1/aggregate                         bounded group-by/time histogram
GET  /v1/tail?query=&token=
POST /v1/saved-queries                     Idempotency-Key
POST /v1/reindex-jobs                      {archiveRange, parserVersion} Idempotency-Key
POST /v1/exports                           audited async export
```

Require tenant and explicit time range. Bound range by tier, query AST/regex/wildcards,
group-by cardinality, scanned bytes, results, concurrency, tail duration and export.
Cursor binds canonical query/time/index snapshot and last `(event_time, ingest_id)`.

## 4. Log envelope and storage model

```text
LogEnvelope(tenant_id, project, source_id, stream_id, source_sequence,
            event_time, receive_time, ingest_id, severity, body,
            attributes, resource, schema_id, parse_version, redaction_version)
SourceCheckpoint(agent_id, stream_id, file_identity, read_offset,
                 highest_durable_sequence, updated_at)
IngestBatch(agent_id, stream_id, first_sequence, last_sequence,
            checksum, state, broker_partition, offsets)
ArchiveObject(tenant, date_hour, shard, object_key, min_max_time,
              count, bytes, schema_versions, checksum, state)
IndexSegment(tenant, time_partition, shard, generation, min_max_time,
             postings_ref, column_ref, dictionary_ref, checksum, state)
IndexManifest(tenant, time_partition, generation, segments, watermark, state)
RetentionPolicy(tenant, stream_selector, archive_ttl, hot_ttl,
                index_fields, sampling, legal_hold_version)
```

Use server-generated `ingest_id` and source identity/sequence. Source event time may be
wrong; retain receive time and clock-quality. Archive stores sanitized canonical bytes
by default; any unredacted forensic tier needs explicit high-risk policy/key/access/TTL.

## 5. Architecture

```text
files/stdout/journal/cloud -> node/sidecar agents -> local encrypted disk spool
                                                     |
                                            regional ingest gateways
                                                     |
                                            durable partitioned buffer
                                                     |
                                      parse/redact/enrich/route stream
                                        /                |            \
                               hot index builders   archive writer   alert/live bus
                                     |                 |
                               index/object store  compressed object lake
                                     \                 /
                                      query broker/planner -> shard workers/cache

control plane -> tenants/schemas/redaction/retention/quotas/manifests
```

Separate data and control planes. Partition buffer by tenant+stream/source hash for
order/balance. Archive and index consumers checkpoint independently; searchable lag
does not block durable ingest unless contractual backlog limit is reached.

## 6. Step-by-step workflow

1. Agent discovers allowed sources, tracks stable file/container identity and byte
   offset, frames multiline messages, attaches metadata/time/sequence, applies mandatory
   early secret rules, batches/compresses/checksums and persists spool before send.
2. Gateway verifies device/tenant binding, schema/size/rate/checksum, adds trusted
   receive metadata and appends batch durably to regional buffer. Only then ACK highest
   sequence; agent deletes acknowledged spool.
3. Pipeline decompresses safely, deduplicates where configured, normalizes timestamps/
   severity/resource, parses structured or versioned patterns, applies central redaction/
   tokenization and controlled enrichment. Bad records go to bounded quarantine/raw
   sanitized route—not crash the partition.
4. Archive writer compacts records into immutable columnar compressed objects with
   checksums/min-max/catalog. Index builder indexes allowlisted fields/text into
   immutable segments and atomically publishes manifests/watermark.
5. Query planner authenticates fields, enforces time/cost, selects tenant/time manifests,
   prunes segments by min-max/Bloom/dictionary and distributes search. Workers filter/
   score/aggregate local data; broker stable-merges and marks partial/truncated.
6. Lifecycle expires hot index then archive only after legal hold/retention checks,
   manifest updates and tracked object/key deletion. Reindex reads archive under a new
   parser/redaction/schema into new generation and canaries before swap.

## 7. Agent tailing and spool correctness

```text
function pollFile(source):
    identity = (filesystemId, inodeOrPlatformFileId, creationFingerprint)
    checkpoint = state.get(source)
    if identity changed or file.size < checkpoint.readOffset:
        finish readable old file handle; start new stream generation at offset 0
    bytes = read from checkpoint.readOffset
    records, remainder = multilineFramer.feed(bytes)
    for record in records:
        sanitized = mandatoryEdgeRedact(record, policyVersion)
        sequence += 1
        spool.appendDurably(streamId, generation, sequence, sanitized, sourceOffset)
    advance local read offset only after spool durability

sender:
    batch contiguous spool records, compress and checksum
    response = send(batch)
    delete spool through response.highestDurableSequence
```

File rotation/truncation cannot rely on filename alone. Bound multiline bytes/time;
flush incomplete stack trace with marker. Spool uses quota/reserved disk and priority:
on unavoidable overflow, drop according to explicit policy and emit durable local/
remote gap counters—never pretend success.

## 8. Ingest deduplication and ACK

```text
function ingest(agent, batch):
    require certificate binds agent and allowed tenant/project
    verify checksum/compression ratio/schema/size/sequences/quota
    requestHash = hash(batch.compressedBytes, envelopeMetadata)
    prior = batchDedupe.lookup(agent.id, batch.streamId, batch.firstSequence)
    if prior exists:
        require prior.hash == requestHash
        return prior.highestDurableSequence
    offsets = buffer.appendQuorum(key=(tenant,stream), batch)
    persist/derive dedupe record and contiguous accepted sequence
    return ACK after buffer high watermark
```

If response is lost, same batch replays. Downstream may see duplicates around dedupe
retention/repartition; stable `(stream generation, sequence)` supports index/archive
dedupe or query-time suppression. Exactly-once is not required for every log if cost is
prohibitive, but duplicate rate is measured and alerts use stable IDs.

## 9. Parsing, redaction, and cardinality control

Prefer structured JSON/Protobuf/OTel-like logs with schema. Parser registry maps tenant/
service/schema to immutable parser version. Enforce max nesting/fields/string/array,
safe regex engine/timeouts and decoded bytes. Preserve original sanitized body when
parse fails with `parse_error`, never discard silently.

Redaction runs before index/archive destination using versioned rules: exact field
classification, regex detectors for tokens/credentials/PII, hash/tokenize when grouping
is allowed, drop forbidden data. Rules must avoid logging their matches. Emergency
global rule distributes fast and reprocessing/deletion addresses historical exposure.

Index only allowlisted typed fields. Unknown/dynamic keys remain in archive/nonindexed
map; cap unique field names/values, truncate/hash selected IDs, and reject user/session/
request IDs as indexed labels unless designed. One random UUID field can explode index.

## 10. Hot index construction

Micro-batch records by tenant/time/shard into immutable segment containing:

- compressed columnar values for timestamp, severity and selected fields;
- inverted postings for tokens and exact fields;
- dictionaries/finite-state structures for terms;
- min/max, Bloom/zone maps and sparse time index;
- stored body/attributes or archive pointers;
- count/checksum/schema/parser/redaction metadata.

Write all objects, verify, then atomically add segment to manifest. Background compaction
merges small segments, applies tombstones/retention and swaps manifest; queries pin a
generation. Late logs go to delta segments for original event-time partition within
allowed horizon, otherwise late archive/search tier per policy.

## 11. Query planning and execution

```text
function search(principal, request):
    require authorized tenant/projects/fields and bounded time range
    ast = parseAndTypeCheck(request.query, tenantSchema)
    estimate = cost(ast, timeRange, shardStats)
    require estimate within interactive budget or route async
    snapshot = pinIndexManifests(tenant, intersectingTimePartitions)
    shards = prune(snapshot, ast.time, exactFilters, minMax, bloom, dictionaries)
    partials = parallelWithDeadline(shards, s => s.execute(ast, localTopNOrAggregate))
    result = stableMerge(partials, order=(eventTime DESC, ingestId DESC))
    return authorizedFieldMask(result), signedCursor(snapshot, lastConsumed),
           coverage/watermark/truncation
```

Push selective indexed predicates before body regex. Regex scans only candidate rows
and uses safe engine. For aggregations, local combine then global merge; approximate
distinct/top K are explicit. A missing shard yields `partial=true`, never an unlabeled
complete answer.

## 12. Query cursor and live tail

Cursor pins query hash, manifest generations/shard continuations and last ordering key.
New logs do not reshuffle current pages. If segments retire/TTL expires, return cursor-
expired/data-gone. Deep result paging is capped; large extraction uses asynchronous export.

Live tail first captures index/buffer watermark, queries a short historical range
through that watermark, then subscribes to post-watermark sanitized stream. Deduplicate
overlap by ingest ID. Gateway applies query filter/authorization, bounded buffers and
coalescing/drop notices to slow viewers. Tail is best effort; reconnect uses last
watermark/history query.

## 13. Archive and reindex

Archive writer creates immutable Parquet-like objects sorted/clustered by time/source,
with catalog manifest/checksum and encryption. Commit catalog only after object exists;
input checkpoint advances after catalog commit. Compaction replaces objects through
new manifest then retires old after query/readers/reference grace.

Reindex job pins archive objects, parser/redaction/index schema version and target
generation, reads under strict quotas, writes independent index, compares counts/time/
golden queries, canaries then swaps. Reindex cannot restore data redacted/dropped before
archive—intentional privacy trade-off.

## 14. Retention and deletion

Policy chooses per stream/severity: discard/sample debug before expensive ingest,
hot searchable duration, archive duration, legal hold and allowed fields. Lifecycle
marks manifest entries deleting, waits for queries, removes objects/segments/replicas/
caches and records proof. Encryption-key destruction can assist cryptographic erase but
must not violate shared-key/legal retention.

Tenant/user deletion locates data only if indexed provenance permits; design tenant/
subject partition/tombstone strategy beforehand. Immutable archive is not exemption
from privacy obligations. Backups/object versions follow the same expiry schedule.

## 15. Sampling and overload policy

Sampling before archive saves most cost but loses forensic detail. Policies can keep
all errors/security/audit, deterministic sample debug by trace/request ID, rate-limit
repeated templates, and aggregate drop counts. Adaptive sampling decisions/version are
attached so analytics can interpret bias; never sample regulated audit logs unintentionally.

On overload, enforce tenant/service priority/bytes quotas at agents/gateways/buffer;
slow low-priority sources, increase batch/compression, delay indexing, preserve archive,
and expose dropped/spooled/lag metrics. Reserve capacity for platform's own critical
logs so the system remains diagnosable without recursive log storms.

## 16. Multi-tenancy and sharding

Partition buffer by tenant+source hash, archive by tenant/time/shard, index by tenant/
time/logical shard. Large tenants get dedicated shards/quotas; small tenants share but
query always injects tenant predicate at storage layer. Split hot time shards by source
hash and merge in broker. Regional ingest respects residency; cross-region search fans
to authorized catalogs or asynchronously replicates approved archive/index.

## 17. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Agent/network outage | Encrypted bounded spool and retry same sequences |
| Gateway dies after buffer append | Agent retry/batch dedupe; no loss |
| Parser crashes/poison log | Sandbox/restart then bounded quarantine with sanitized body |
| Index builder fails | Archive/buffer remains; retry from checkpoint |
| Segment object written but manifest fails | Orphan sweeper removes/reuses checksummed object |
| Query shard times out | Retry replica or return explicit partial coverage |
| Object archive unavailable | Hot search works; archive/reindex backpressure explicitly |
| One tenant floods | Hierarchical quotas/fair partitions isolate it |
| Region fails | Agents spool/reroute by residency; query uses replicated verified data |

## 18. Security and privacy

Use mTLS workload/device identity, tenant/project/source/query/export/admin RBAC,
encrypted spool/transport/storage, per-tenant keys where required, secret vault,
signed agents/config/parsers, network segmentation, tamper-evident audit and break-
glass field access. Prevent forged tenant metadata, cross-tenant query, query/regex DoS,
log injection/XSS/terminal escapes, parser/deserialization bombs, archive path traversal,
connector SSRF, agent takeover, retention override and malicious logs causing alerts.

Redact secrets/PII early, mask fields by role, avoid raw samples in errors/metrics,
audit every query/export, detect bulk exfiltration, and enforce consent/purpose,
retention/deletion/legal hold/residency. Security/audit logs may require WORM/tamper
evidence and separation from application-admin control.

## 19. Observability

Track source/agent discovered/read/spooled/sent/ACK/dropped bytes and spool age/disk,
gateway QPS/bytes/duplicates/quota/compression, buffer partitions/lag/retention risk,
parse/redact errors/matches/schema/cardinality, archive/index input/output/count/checksum/
watermark/segment/compaction/orphans, event-to-search latency, query latency/scanned bytes/
shards/cache/partial/timeout/cardinality, tail drops, retention/deletion/reindex/export,
tenant cost and platform self-log health.

Golden fixtures cover rotation/truncation/multiline, schemas, secrets, Unicode, huge/
malformed logs and late timestamps. Property-test agent ACK/retry and manifest swaps.
Load-test small logs, high cardinality, regex scans and one noisy tenant. Chaos agents/
network/buffer/pipeline/index/object/query/region; reconcile ACK ranges to buffer,
buffer to archive/index counts/checksums, manifests to objects and retention proofs.

## 20. Implementation path

1. **MVP:** authenticated agent/file tail, disk spool, durable regional ingest, structured
   parse, one hot time index, bounded tenant/time search and simple retention.
2. **Durability/cost:** compressed object archive/catalog, redaction/schema registry,
   immutable index segments/manifests, replay/reindex, quotas and source checkpoints.
3. **Scale/product:** distributed planner/shards/aggregations, live tail, tiered index,
   cardinality controls, sampling, exports, regional residency and large-tenant cells.
4. **Hardening:** security/privacy/WORM/audit controls, property/golden/cardinality/load/
   chaos tests, deletion/reindex/restore/key drills, runbooks, dashboards, and SLOs.

## 21. Final design

Agents durably spool source-sequenced, early-redacted batches and delete only after the
regional replicated buffer ACK. A versioned sandboxed pipeline produces sanitized
canonical envelopes; one branch writes immutable compressed archive, while another
builds selective immutable time-sharded index segments and atomically published
manifests. Query planning enforces tenant/time/cost, prunes before scanning and labels
partial coverage. Replayable archive, bounded cardinality/retention/quotas and tracked
deletion make massive logs searchable and affordable without letting retries, outages,
secrets or one noisy tenant destroy the platform.
