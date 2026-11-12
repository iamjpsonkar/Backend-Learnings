# Complete Solution: Push Notification Platform

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Accept transactional and bulk notification intents, render versioned templates,
honor user preferences, resolve device tokens, deliver through APNs/FCM/Web Push,
retry transient failures, suppress invalid tokens, and expose honest status.

Targets: 1 billion notifications/day, 10x campaign bursts, transactional enqueue
p99 below 100 ms, provider submission p99 below 10 seconds for transactional
traffic, and isolation so bulk backlog cannot starve security alerts.

Provider acceptance is not proof that a device displayed a notification. Statuses
must distinguish queued, submitted, provider-accepted, failed, and device-receipt
only where a client callback exists.

## 2. Capacity estimation

```text
average intents/s = 1B / 86,400 ~= 11.6K
10x peak          ~= 116K/s
```

If each intent targets five devices, peak delivery records approach 580K/s. Keep
payloads small (provider limits are a few KB), batch provider calls where supported,
and separate intent storage from per-device attempts.

## 3. API and model

```text
POST /v1/notifications
Idempotency-Key: ...
{
  tenant, recipients | audience_ref,
  template_id, template_version, variables,
  category, priority, schedule_at, collapse_key, ttl
}
```

```text
Notification(id, tenant, idempotency_key, template_version,
             category, priority, state, schedule_at, ttl, payload_ref)
Delivery(id, notification_id, user_id, device_id, provider,
         token_version, attempt, state, next_attempt_at, provider_id, error)
DeviceToken(user_id, device_id, platform, encrypted_token,
            token_version, locale, active, last_confirmed)
Preference(user_id, category, channel, enabled, quiet_hours, timezone, version)
```

## 4. Architecture

```text
producer -> admission/idempotency API -> notification store + outbox
                                              |
                                     audience expansion
                                              |
                           priority/tenant/provider durable queues
                                      |       |       |
                              APNs workers FCM workers WebPush workers
                                      \       |       /
                                     outcome/callback processor

preference + token + template services feed expansion/rendering
retry scheduler, DLQ, audit, analytics consume durable state
```

Transactional, normal, and bulk traffic use separate queues, worker pools, quotas,
and reserved capacity.

## 5. Step-by-step workflow

1. Producer authenticates tenant and submits intent with idempotency key.
2. API validates category, template/version, variables, TTL, schedule, recipient
   count/audience reference, and tenant quota.
3. Transaction stores intent plus outbox and returns notification ID.
4. Scheduler releases due intent; audience worker pages recipient IDs.
5. For each user, preference and quiet-hour policy decides send, defer, or suppress.
6. Resolver loads active device tokens and creates deterministic delivery IDs.
7. Renderer produces provider-safe localized payload with strict byte limit.
8. Provider worker sends in bounded batch, stores result, retries transient errors,
   and disables invalid tokens.
9. Optional app receipt associates display/open with delivery ID asynchronously.

## 6. Admission and idempotency logic

```text
function createNotification(tenant, request, key):
    validate(request)
    requestHash = sha256(canonicalJson(request))

    transaction:
        old = idempotency.get(tenant.id, key)
        if old exists:
            require old.requestHash == requestHash else Conflict
            return old.notificationId

        notification = Notification(uniqueId(), tenant.id, key,
                                    pinnedTemplateVersion(request), QUEUED, ...)
        notifications.insert(notification)
        idempotency.insert(tenant.id, key, requestHash, notification.id)
        outbox.insert(NotificationReady(notification.id))
    return notification.id
```

Pin the template version at admission so a retry or delayed job does not silently
render different content.

## 7. Delivery creation

```text
function expandRecipient(notification, user):
    preference = preferences.get(user, notification.category)
    decision = evaluatePreference(preference, notification, now())
    if decision == SUPPRESS: recordSuppressed(notification,user); return
    if decision.deferUntil exists: scheduleRecipient(notification,user,decision.time); return

    for token in tokens.activeFor(user):
        deliveryId = hash(notification.id, user.id, token.deviceId, token.version)
        if deliveries.insertIfAbsent(Delivery(deliveryId, ..., READY)):
            queueFor(notification.priority, token.provider).publish(deliveryId)
```

Deterministic delivery ID prevents audience retries from duplicating device work.

## 8. Provider worker and retry logic

```text
function deliver(deliveryId):
    delivery = deliveries.lease(deliveryId, owner=workerId, ttl=30s)
    if not acquired: return
    notification = notifications.get(delivery.notificationId)

    if now() >= notification.createdAt + notification.ttl:
        deliveries.finish(deliveryId, EXPIRED); return

    token = tokens.getVersion(delivery.userId, delivery.deviceId,
                              delivery.tokenVersion)
    if token missing or not active:
        deliveries.finish(deliveryId, TOKEN_INACTIVE); return

    payload = renderBounded(notification, token.locale, providerLimit(token))
    result = provider(token.provider).send(token, payload, delivery.id)

    if result.accepted:
        deliveries.finish(deliveryId, SUBMITTED, result.providerId)
    else if result.invalidToken:
        tokens.deactivateIfVersion(token)
        deliveries.finish(deliveryId, INVALID_TOKEN)
    else if result.transient and delivery.attempt < retryPolicy.max:
        deliveries.retryAt(deliveryId, backoffWithJitter(delivery.attempt))
    else:
        deliveries.finish(deliveryId, FAILED, result.code)
        maybeDeadLetter(deliveryId)
```

Retries keep the same logical delivery ID. Provider-specific idempotency support is
used when available, but duplicate device display remains possible and payload
actions must be idempotent.

## 9. Preferences, quiet hours, and collapse

- Transactional security categories may be legally/product exempt from marketing
  opt-out but still follow explicit policy.
- Evaluate quiet hours in the user's IANA time zone; defer only if TTL permits.
- Preference version is recorded for audit.
- Collapse key lets provider keep latest state update (for example latest score),
  but must never collapse independent security or payment events.
- Coalesce bursts per conversation/order before device fan-out where semantics allow.

## 10. Token lifecycle

Apps register tokens with authenticated user/device and monotonically increasing
token version. Provider invalid-token response deactivates only that version so a
delayed callback cannot disable a newly rotated token. Log token hash, never raw
token. Periodically expire tokens not confirmed by active clients.

## 11. Scheduling and cancellation

Scheduled notifications use a durable time-bucket scheduler. Cancellation changes
intent state and prevents unleased deliveries; already submitted provider messages
usually cannot be recalled. API reports this distinction honestly.

## 12. Failure handling

| Failure | Behavior |
| --- | --- |
| Admission DB fails | Request fails/retries with same idempotency key |
| Queue unavailable | Outbox retains work until publisher recovers |
| Expansion worker crashes | Deterministic delivery IDs make replay safe |
| Provider throttles/outage | Circuit, provider-specific retry/backoff, queue isolation |
| Preference service fails | Use fresh validated cache; marketing fails closed/suppresses |
| Template/render fails | Mark explicit failure; never send malformed fallback content |
| Callback duplicated/out of order | Versioned monotonic delivery state ignores regression |
| Bulk campaign overload | Tenant admission and separate pools preserve transactional capacity |

## 13. Security and privacy

- Encrypt device tokens with restricted key access; TLS/mTLS internally.
- Tenant-scoped auth, quotas, templates, audiences, and delivery visibility.
- No secrets/regulated data in lock-screen payloads; send opaque reference and let
  authenticated app fetch details.
- Escape and bound template variables; prohibit arbitrary provider fields.
- Audit preference changes, audience access, sends, token access, and DLQ replay.
- Enforce consent, data deletion, retention, and regional messaging rules.

## 14. Observability

Measure admission p99, intents and deliveries by priority/tenant/provider, queue
age, expansion/render latency, preference suppression/defer, submitted/failed/
invalid-token rates, provider throttle/latency, retries/DLQ, token churn, receipt/
open delay, bulk-versus-transactional SLO, and notification cost.

Synthetic tests create an idempotent intent, apply preference/quiet hours, rotate a
token during retry, simulate provider throttle/outage, expire TTL, and verify bulk
traffic cannot delay a transactional probe.

## 15. Implementation path

1. **MVP:** one provider, direct recipients, durable intent/delivery records,
   idempotency, one transactional queue, bounded retries, and token invalidation.
2. **Product correctness:** versioned templates, preferences/quiet hours, scheduler,
   collapse/coalescing, receipts, audit, and DLQ/replay.
3. **Scale/isolation:** paged audiences, deterministic delivery IDs, separate
   priority/tenant pools, batching, quotas, and backpressure.
4. **Provider/global resilience:** multiple adapters/regions, reserved capacity,
   chaos/load tests, compliance, and disaster recovery.

## 16. Final design

Use a transactional idempotent admission service, outbox, deterministic per-device
delivery records, priority-isolated durable queues, provider-specific workers, and
versioned preferences/tokens/templates. The central invariant is that one logical
notification creates at most one delivery record per token version, while retries
may submit it more than once and therefore remain explicitly idempotent and
observable.
