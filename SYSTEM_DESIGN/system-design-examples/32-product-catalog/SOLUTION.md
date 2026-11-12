# Complete Solution: Product Catalog

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Sellers/admins create and update products, variants/SKUs, typed category attributes,
relationships, media, and lifecycle state. Customers fetch product detail, browse
categories, and search/filter at high read volume. Bulk seller feeds, moderation,
history, localization, and reconciliation are required.

Targets: product-detail p99 below 150 ms, write p99 below 500 ms excluding media,
99.99% reads, 99.9% writes, read-model propagation below five seconds, and search
propagation below one minute. Authoritative writes are strongly consistent per
product/version. Read models/search/cache are eventual and expose source version.

## 2. Capacity estimation

Assume 100 million products, one billion variants, 10 million updates/day, 100,000
peak product reads/s, 50,000 search/browse QPS, 20 KB denormalized product document,
and five media assets/product.

- Updates average 116/s but bulk imports create 100x bursts; isolate them from
  interactive writes.
- Denormalized product documents require about 2 TB before replicas/index overhead.
- One billion compact variant records at 1 KB are about 1 TB before indexes/replicas.
- At 100,000 reads/s and 20 KB, origin payload is 2 GB/s; CDN/API/Redis caching and
  compression are critical.
- Media dominates storage/egress and belongs in object storage/CDN, never database rows.

## 3. Domain boundaries

Catalog owns descriptive identity: what an item is, variant attributes, category,
media, and publication eligibility. Pricing owns current price/promotions; inventory
owns availability/reservation; offers own seller-specific commercial terms. Catalog
may project their references/display summaries but is not authoritative for checkout.

Model `Product` (shared description), `Variant/SKU` (purchasable configuration), and
`Offer` (seller/market commercial listing) separately when a marketplace requires it.
Conflating them makes seller price/stock updates rewrite global content and creates
incorrect ownership.

## 4. APIs

```text
POST   /v1/products                         Idempotency-Key
GET    /v1/products/{productId}?locale=&market=
PATCH  /v1/products/{productId}             If-Match: version
POST   /v1/products/{productId}/variants    Idempotency-Key, If-Match
PATCH  /v1/variants/{variantId}             If-Match: version
POST   /v1/products/{productId}/media       {uploadToken, role, order}
POST   /v1/products/{productId}/publish     If-Match: version
DELETE /v1/products/{productId}             If-Match: version
POST   /v1/bulk-imports                     {objectRef, format} Idempotency-Key
GET    /v1/categories/{id}/products?filters=&sort=&cursor=
GET    /v1/search?q=&filters=&cursor=
```

Bound products/seller, variants/product, attributes/category, text/media sizes,
locales, bulk rows/bytes, filter complexity, page size, and update rates. Cursors bind
query/filter/sort/index snapshot and last stable ordering tuple.

## 5. Authoritative data model

```text
Product(id, owner_id, category_id, category_schema_version, state,
        brand_id, title_default, description_default, version,
        moderation_state, created_at, updated_at)
ProductText(product_id, locale, title, description, version)
Variant(id, product_id, sku, option_values_json, attributes_json,
        state, version, price_ref, inventory_ref)
ProductAttribute(product_id, attribute_definition_id, typed_value, version)
Category(id, parent_id, schema_id, schema_version, state)
AttributeDefinition(id, name, type, unit, cardinality, required,
                    filterable, allowed_values, validation_rules, version)
MediaAsset(id, owner_id, generation, state, object_keys, checksum, metadata)
ProductMedia(product_id, asset_id, role, position, version)
ProductRevision(product_id, version, editor, patch, created_at)
Outbox(id, aggregate_id, event_type, source_version, payload, published_at)
```

Unique constraints cover seller SKU and variant option combinations as business
policy requires. Money is not an untyped float. Attribute values retain type/unit,
and every product records the schema version under which it validated.

## 6. Read models

```text
ProductDocument(product_id, source_version, locale, state, title, description,
                category_path, brand, variants[], media_manifest, display_summaries)
SearchDocument(product_id, source_version, analyzed_text, typed_filter_fields,
               popularity_features, publication_state)
CategoryMembership(category_id, sort_key, product_id, source_version)
```

These are disposable projections. A product-detail document embeds bounded variants
or pages them separately for enormous products. Search contains only explicitly
filterable typed attributes, avoiding unbounded dynamic-field mapping explosion.

## 7. Architecture

```text
seller/admin -> write API -> catalog SQL/KV + revision/outbox
                    |                  |
            category/schema svc    ordered change log
                                       |        |         |
                                  read model  search   cache invalidation
                                       |        |
client -> product API -> CDN/cache -> document store
client -> browse/search API --------> search/category indexes

media client -> signed quarantine upload -> scan/transform -> immutable media/CDN
bulk file -> staging/validator -> bounded idempotent product commands
```

Partition products/variants by product ID and keep aggregate changes colocated.
Category/schema and seller ownership are replicated read-mostly control data with
versions. Consumers process product changes in source-version order.

## 8. Step-by-step workflow

### Create/update/publish

1. Authenticate seller/editor, validate ownership, command/idempotency, expected
   version, category state/schema version, core fields, variants, and media references.
2. In one product-shard transaction insert/update normalized rows, record revision,
   increment product version, and append outbox event.
3. Projector consumes event, reads a consistent aggregate version, builds localized
   denormalized document, and conditionally writes only if source version is newer.
4. Search/category consumers index the same version; cache keys/pointers advance.
5. Publish is a separate state transition requiring complete mandatory fields,
   unique valid variants, READY media, ownership/brand checks, and moderation approval.
6. Reads serve projected document and may batch-overlay indicative pricing/inventory;
   checkout revalidates external authorities.

### Bulk import

1. Upload immutable checksummed file, parse in sandbox, and validate row/schema limits.
2. Produce dry-run error report; approved job emits stable per-row commands keyed by
   `(job, row, normalized seller SKU)`.
3. Workers apply commands through the same write API with seller fair-share limits,
   durable checkpoints, retry/DLQ, and final reconciliation report.

## 9. Core conditional update logic

```text
function updateProduct(actor, productId, command, expectedVersion, requestKey):
    requestHash = canonicalHash(command, expectedVersion)
    transaction on shard(productId):
        prior = idempotency.get(actor.id, requestKey)
        if prior exists:
            require prior.requestHash == requestHash
            return prior.response

        product = products.getForUpdate(productId)
        require mayEdit(actor, product)
        require product.version == expectedVersion
        schema = schemas.get(product.categoryId, command.schemaVersion)
        require schema.state == ACTIVE
        normalized = validateTypedAttributesAndVariants(command, schema)

        applyPatch(product, normalized)
        product.version += 1
        revisions.insert(product.id, product.version, actor.id, normalized.patch)
        outbox.insert(ProductChanged(product.id, product.version,
                                     schema.version, affectedFields(normalized)))
        response = summarize(product)
        idempotency.insert(actor.id, requestKey, requestHash, response)
    return response
```

An `If-Match` mismatch returns 409/current version and diff hints; it never silently
overwrites another editor. For independent variants, variant-level versions can reduce
contention while product publication uses an aggregate readiness version/check.

## 10. Typed schema validation

```text
function validateAttributes(input, schema):
    result = {}
    for definition in schema.definitions:
        values = input[definition.id]
        require !definition.required or values is present
        require cardinality(values) <= definition.cardinality
        for value in values:
            typed = parseStrict(value, definition.type)
            typed = convertToCanonicalUnit(typed, definition.unit)
            require definition.validationRules.accept(typed)
            require !definition.allowedValues or typed in definition.allowedValues
            result[definition.id].add(typed)
    require no unknown attributes unless extension namespace is allowed
    return result
```

Schema evolution creates a version. Additive optional fields can coexist; breaking
type/unit/required changes trigger migration/revalidation before affected products
can update or remain published under explicit grandfathering. Never reinterpret old
stored values with new semantics silently.

## 11. Projection and ordering logic

```text
function onProductChanged(event):
    current = readStore.get(event.productId, event.locale)
    if current.sourceVersion >= event.sourceVersion: return
    aggregate = catalog.readAggregateAtLeast(event.productId, event.sourceVersion)
    document = buildProductDocument(aggregate, schemas, mediaManifests)
    readStore.putIfSourceVersionGreater(document)
    projectionOutbox.emit(ReadDocumentChanged(document.id, document.sourceVersion))
```

Do not construct a document by blindly applying possibly out-of-order partial patches.
Re-read the authoritative aggregate at or beyond the event version, then conditionally
write. Search ignores older source versions and deletes/unpublishes by tombstone.

## 12. Read, cache, and pagination

Product API resolves locale fallback, checks current publication/policy, then reads
CDN/Redis/document store. Cache keys include product/document version and locale;
an ID pointer with short TTL selects current immutable value. Old cache fill cannot
replace a newer pointer.

Browse/search uses `(sort_value, product_id)` cursor pinned to index generation/query
hash. Over-fetch and recheck current product state to remove recently unpublished
items; advance based on consumed candidates. Product-detail fallback may rebuild from
primary under a strict rate limit when projection is missing, but search does not scan SQL.

## 13. Media workflow

Issue signed upload to quarantine for exact key/size/type/checksum. Scanner and
sandboxed decoder validate magic bytes, malware, pixel limits, strip unsafe metadata,
and generate immutable generation-scoped variants. Only READY assets owned by the
seller may be attached. Product documents contain a media manifest, never mutable
binary URLs. Reordering changes metadata; replacement creates a generation.

## 14. Moderation and lifecycle

Draft content can be edited freely within policy. Automated checks examine text,
images, prohibited products, brands, duplicates, and seller risk; uncertain/high-risk
items enter human review. Decisions and appeals are versioned/audited. Publish checks
the latest approved content hash so an edit cannot reuse approval for different content.

Unpublish/delete commits authoritative state/tombstone first, immediately makes API
policy deny it, then removes search/category/cache and schedules media cleanup under
retention/legal hold. Retain product ID/history so delayed events cannot republish it.

## 15. Sharding, bulk fairness, and backpressure

- Hash by product ID and colocate variants/revisions/outbox; maintain seller-to-product
  index separately for management listing.
- Isolate bulk queues from interactive commands and use per-seller weighted quotas.
- Cap aggregate/variant/media/attribute sizes; extremely large variation sets use
  paged variant storage/read models.
- Under projection lag, preserve authoritative writes and product-detail fallbacks,
  slow bulk ingestion, and report search freshness instead of unsafe partial mutation.
- Rebuild read/search generations from primary snapshots plus change-log tail.

## 16. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client/bulk row retries | Idempotency returns same product/version |
| Concurrent editors | Optimistic version returns 409; no lost update |
| Outbox event duplicates/reorders | Conditional source version prevents regression |
| Read model is missing | Rate-limited primary aggregate fallback for detail |
| Search lags/fails | Detail remains available; browse fallback only if designed/indexed |
| Cache stale after unpublish | Authoritative policy/tombstone check denies response |
| Schema changes | Existing version remains interpretable; migration is explicit |
| Media transform fails | Asset stays non-READY and cannot publish |
| Shard region fails | Fenced replica promotion prevents two product writers |

## 17. Security and privacy

Enforce seller/brand/category/editor/moderator roles on every mutation and asset.
Protect against mass assignment, IDOR, XSS/HTML injection, malicious URLs/media,
counterfeit/prohibited goods, feed bombs, formula/CSV injection, scraping, and SKU
enumeration. Encrypt data, sign artifacts/events, audit changes/moderation/imports/
exports/admin access, and apply retention, deletion, legal hold, consent, residency,
and seller offboarding to primary/history, projections, indexes, media, logs, and backups.

## 18. Observability

Track write/read/search/browse latency/errors, version conflicts/idempotency, updates
and products/seller, validation failures by schema/field, interactive versus bulk queue
age, outbox/read/search propagation lag, source-version skew, cache/CDN hit and stale
denials, missing documents/media, moderation age/results/appeals, publish failures,
index/rebuild divergence, storage growth, and checkout failures caused by catalog drift.

Contract tests run every category schema and migration. Projection tests duplicate/
reorder events and require monotonic documents. Golden product/search tests cover
locales, variants, typed filters, unpublish, and moderation. Chaos/load tests kill
cache/projectors/search/shards and flood bulk imports; reconciliation compares primary
versions with read/search/media generations.

## 19. Implementation path

1. **MVP:** normalized product/variant SQL, one category schema, optimistic writes,
   revisions, publication checks, product-detail read, and safe media references.
2. **Read scale:** outbox, denormalized documents, versioned cache/CDN, search/category
   indexes, typed filters, localization, and reconciliation.
3. **Seller scale:** bulk staging/dry-run, quotas/fair queues, flexible schema versions,
   offers/references, moderation/appeals, and generation rebuilds.
4. **Hardening:** regional read/write routing/failover, security/compliance lifecycle,
   load/chaos/migration tests, restore drills, dashboards, and SLOs.

## 20. Final design

Keep normalized, typed, versioned product/variant data as the authoritative write
model and separate commercial price/inventory/offer ownership. Transactional outbox
events build immutable-version denormalized detail, category, search, and cache views.
Schema-versioned validation makes flexible attributes safe; conditional projections
make duplicate/out-of-order delivery harmless. Current publication/moderation policy
guards reads while asynchronous indexes provide scale and rebuildability.
