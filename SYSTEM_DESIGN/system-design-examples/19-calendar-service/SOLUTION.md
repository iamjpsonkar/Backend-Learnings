# Complete Solution: Calendar Service

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Users create private/shared calendars, single or recurring events, invite attendees,
edit one occurrence or a whole series, answer invitations, configure reminders, and
query free/busy time. Events retain their wall-clock intent in an IANA time zone.

Targets: 99.99% read and 99.9% write availability, p99 event read below 200 ms,
p99 write below 400 ms, and 99.99% of reminders dispatched within 30 seconds of
their due time. A successful write is strongly consistent for that event and emits
changes at least once. Notifications may be delayed or duplicated but never replace
the authoritative calendar state.

## 2. Capacity estimation

Assume 100 million users, 20 created events/user/month, ten reads per write, five
attendees/event, and two reminders/attendee/event.

- Writes average about 770/s and can peak above 8,000/s.
- Reads average about 7,700/s and can peak near 80,000/s.
- Two billion event series/month at roughly 2 KB is 4 TB/month before indexes and
  replication.
- Reminder delivery can spike on five-minute boundaries; partition scheduling and
  provision for at least 10x average.

Pre-expand a rolling 12-month horizon, but preserve rules indefinitely so the
horizon can advance.

## 3. API design

```text
POST   /v1/calendars/{calendarId}/events       Idempotency-Key
GET    /v1/calendars/{calendarId}/events?from=&to=&pageToken=
GET    /v1/events/{eventId}
PATCH  /v1/events/{eventId}?scope=single|future|series   If-Match: version
DELETE /v1/events/{eventId}?scope=single|future|series   If-Match: version
POST   /v1/events/{eventId}/responses          {status, comment}
POST   /v1/free-busy                           {principals, from, to, timezone}
POST   /v1/calendars/{calendarId}/share        {principal, role}
GET    /v1/changes?syncToken=
```

Create accepts local start, IANA zone, duration, RFC 5545-like recurrence rule,
attendees, reminders, and a client event ID. Free/busy windows and attendee counts
are bounded. A sync token is an opaque per-principal change-log cursor.

## 4. Data model

```text
Calendar(id, owner_id, name, default_tz, acl_version, change_sequence)
CalendarACL(calendar_id, principal_id, role, version)
Event(id, calendar_id, organizer_id, title_ciphertext,
      start_local, timezone, duration_seconds, recurrence_rule,
      recurrence_end, status, version, series_generation, created_at)
EventException(event_id, recurrence_id_local, kind, override_json, version)
Attendee(event_id, principal_or_email, response, response_version)
Reminder(event_id, attendee_id, recurrence_id_local, offset_seconds, method)
Occurrence(event_id, recurrence_id_local, start_utc, end_utc,
           effective_version, state)
BusyInterval(principal_id, start_utc, end_utc, visibility, source_key, version)
Change(calendar_id, sequence, entity_key, operation, version)
Outbox(id, aggregate_id, event_type, payload, created_at, published_at)
```

`recurrence_id_local` identifies an occurrence by the series' original local date
and time, not by UTC. This keeps exceptions attached when DST changes UTC offsets.
Unique keys on `(event_id, recurrence_id_local)` and idempotency keys prevent
duplicate exceptions and creates.

## 5. Architecture

```text
clients -> API/auth -> calendar service -> partitioned SQL
                           |                    |
                           |                 outbox/change log
                           |                    |
                    recurrence reader      event stream
                           |              /       |        \
                   occurrence cache   expander  invites  reminder planner
                           |              |                   |
                     free/busy API <- interval index     due-time buckets
                                                               |
                                                        notification service
```

Partition primary data by calendar ID, with a home region per calendar. Cross-user
effects (attendee copies, busy intervals, email, reminders) are asynchronous
projections from a transactional outbox. The organizer's event is canonical.

## 6. Step-by-step workflow

1. Authenticate, authorize editor role, validate zone/rule/window/attendees, and
   resolve local time under the explicit DST policy.
2. In one database transaction insert event, attendees/reminders, increment the
   calendar change sequence, and append `EventChanged` to outbox.
3. Return event ID and version after commit. A repeated idempotency key returns the
   original result.
4. Relay publishes the outbox record. Expansion worker materializes near-term
   occurrences and busy intervals; invitation worker creates recipient copies and
   sends notifications idempotently.
5. Reminder planner creates jobs only for concrete occurrences within its rolling
   scheduling horizon.

## 7. Core recurrence expansion logic

```text
function instances(event, exceptions, rangeUtc, tzdataVersion):
    localRange = widenAndConvert(rangeUtc, event.timezone)
    candidates = recurrenceLibrary.expand(
        event.startLocal, event.recurrenceRule, localRange)
    result = []

    for localId in candidates:
        exception = exceptions.get(localId)
        if exception.kind == CANCELLED: continue

        effective = applyOverride(event, exception)
        resolved = resolveLocal(effective.startLocal, effective.timezone,
                                effective.dstPolicy)
        if resolved.invalid: continueOrReport(effective.dstPolicy)
        startUtc = resolved.instant
        endUtc = startUtc + effective.duration

        if overlaps(startUtc, endUtc, rangeUtc):
            result.add(Occurrence(event.id, localId, startUtc, endUtc,
                                  effective.version, tzdataVersion))
    return sortByStartThenId(result)
```

Use a mature recurrence library, cap candidate count and CPU, and reject unbounded
queries. Expansion is deterministic for `(event version, tzdata version, range)`.

### DST policy

- Store `start_local + IANA timezone + duration`, never only a UTC timestamp for a
  recurring wall-clock event.
- In a spring-forward gap, default to the first valid instant after the gap or use
  the caller's explicit reject/shift policy.
- In a fall-back fold, persist whether the earlier or later offset was chosen.
- Record the tzdata version. When rules change, invalidate and regenerate affected
  future occurrences; historical instants remain immutable unless explicitly
  migrated.

## 8. Edit semantics and optimistic concurrency

```text
function updateEvent(actor, eventId, scope, recurrenceId, patch, expectedVersion):
    transaction:
        event = events.getForUpdate(eventId)
        require canEdit(actor, event.calendarId)
        require event.version == expectedVersion

        if scope == SINGLE:
            upsert exception(eventId, recurrenceId, OVERRIDE, patch)
        else if scope == SERIES:
            validate patch
            update event with patch and version + 1
        else if scope == FUTURE:
            oldRule = truncateBefore(event.rule, recurrenceId)
            update old event rule = oldRule
            create new series beginning at recurrenceId with inherited exceptions

        append calendar change and outbox EventChanged
    return newVersion
```

An `If-Match` mismatch returns 409 with current version; it never silently loses an
edit. “This and following” splits the series because one recurrence rule cannot
cleanly represent two histories. Moving a single occurrence preserves its original
recurrence ID in the exception.

## 9. Attendees and invitation consistency

The organizer record owns time/title/recurrence. Each attendee has a response on
the canonical event plus a local projected calendar entry. An invitation command
uses `(event_id, attendee, event_version)` as its idempotency key.

An RSVP transaction conditionally advances `response_version` and emits an outbox
event. Concurrent organizer changes do not overwrite the response. If delivery is
late, the recipient sync feed still obtains authoritative state. Removing an
attendee revokes the projected copy and pending reminders.

## 10. Free/busy query

```text
function freeBusy(requester, principals, window):
    require duration(window) <= MAX_WINDOW
    for principal in principals:
        if !maySeeAvailability(requester, principal): markUnknown()
        else:
            intervals = busyIndex.rangeScan(principal, window)
            output[principal] = mergeOverlapping(redactDetails(intervals))
    return output
```

The projection expands visible occurrences into an interval index partitioned by
principal and time bucket. Cache only bounded `(principal ACL version, window,
change sequence)` results. If projection lag exceeds a small threshold, read the
event change tail or mark the response stale; never claim a slot is free from an
unknown/incomplete partition.

## 11. Durable reminder scheduling

1. Planner expands occurrences through a rolling horizon and computes
   `due_at = occurrence_start - offset`.
2. Upsert job keyed by `(event, occurrence, attendee, reminder, event_version)` into
   day/hour partitions.
3. Dispatchers claim due rows using leases/`SKIP LOCKED`, publish notification, and
   record completion.
4. A retry reuses the same notification idempotency key. Obsolete versions are
   ignored after reading current event state.
5. Sweepers recover expired leases and compare planned coverage with the event
   horizon.

Wall-clock boundary spikes are absorbed by partitioned due buckets and queues.
Editing or cancelling an event advances its version, making old jobs harmless even
before cleanup.

## 12. Read path, sync, and caching

Range reads fetch single events and pre-expanded occurrences, then expand any
missing or stale series on demand and populate cache. Cache keys include event and
tzdata versions. Pagination orders by `(start_utc, event_id, recurrence_id)`.

Every committed calendar mutation increments its sequence. Incremental sync reads
changes after a token and returns a new token; tombstones are retained longer than
the offline-client guarantee. If a token is too old, return `FULL_SYNC_REQUIRED`.

## 13. Partitioning and scaling

- Partition event writes by calendar ID for local transactions and ordered change
  sequences; isolate unusually large shared calendars.
- Partition occurrences/busy intervals by principal and month for bounded scans.
- Replicate read-only history and serve cacheable calendar ranges regionally.
- Keep writes in the calendar home region; fail over with fencing to prevent two
  primaries assigning versions.
- Apply per-calendar/user attendee, recurrence, reminder, and query-cost quotas.

## 14. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client retries create | Idempotency record returns the same event |
| Outbox relay crashes | Unpublished row is retried; consumers deduplicate |
| Expander lags | Read expands stale/missing range on demand; alert on lag |
| Reminder worker dies | Lease expires and another worker claims job |
| Duplicate notification | Provider/idempotency key suppresses duplicate effect |
| tzdata changes | Invalidate future projections and re-plan reminders |
| Cache is stale | Version/change-sequence mismatch forces refresh |
| Home region fails | Promote fenced replica; reject writes until single leader |
| Attendee calendar unavailable | Retry projection; canonical organizer state remains committed |

## 15. Security and privacy

Enforce owner/editor/reader/free-busy ACLs on every event, change feed, attachment,
and interval query. Redact title and attendees from availability-only responses.
Use short-lived share links, audit share/export/admin access, encrypt content and
tokens, sanitize text/links, and rate-limit enumeration. Apply retention, deletion,
legal hold, residency, and private-event rules to primary data, indexes, caches,
notifications, and backups.

## 16. Observability

Track read/write latency and errors, optimistic conflicts, outbox/expansion/index
lag, cache staleness, recurrence CPU/candidate limits, invitation age, reminder
planning coverage/lateness/duplicates, sync-token expiry, and tzdata-version
mismatch. Alert on correctness SLOs, not only host health.

Test recurrence against standard conformance cases and property-test range
boundaries. Maintain a DST suite for gaps, folds, leap years, month ends, and rule
changes. Chaos tests kill relays/dispatchers/region leaders; reconciliation tests
prove every committed event produces projected occurrences, attendee changes, and
the expected reminder jobs.

## 17. Implementation path

1. **MVP:** single events, calendar ACLs, SQL transactions, versioned edits, bounded
   range reads, and change log.
2. **Scheduling:** recurrence library, exceptions, DST policy/tests, invitations,
   and durable reminders.
3. **Scale:** rolling expansion, interval index, caching, partitioning, quotas, and
   reconciliation.
4. **Global hardening:** home-region failover, privacy lifecycle, tzdata migration,
   load/chaos tests, restore drills, and SLOs.

## 18. Final design

Keep the recurrence rule and local-time intent as source of truth, represent edits
as explicit exceptions or series splits, and materialize only bounded future
occurrences. SQL transactions plus an outbox protect authoritative changes;
idempotent projections power free/busy, invitations, and reminders. The central
invariant is that each occurrence has one stable local recurrence identity and all
derived work is tied to an event version, so retries and stale jobs cannot recreate
cancelled or superseded behavior.
