# Calendar Service

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Manage calendars, recurring events, attendees, time zones, reminders, and free/busy queries.

Set measurable availability and latency targets, estimate peak load and retained
data, and state the ordering and consistency guarantees explicitly.

## APIs and data model

Create/update accepts recurrence rule and IANA time zone; instance APIs address one occurrence or a series; free/busy queries bounded windows.

Calendar(id, owner); Event(id, calendar, start_local, timezone, duration, recurrence, version); Exception(event, recurrence_id, override); Attendee(event, user, status).

## High-level design

```text
client -> calendar API -> transactional store -> change log -> invitation/reminder workers -> notification
```

Store recurrence rules plus exceptions rather than materializing forever, pre-expand near-term instances, index busy intervals, and cache bounded free/busy windows.

## Reliability, security, and operations

Use optimistic versions, idempotent invitation delivery, durable reminder scheduling, ACL checks, and explicit behavior for DST gaps and folds.

Track API latency, conflict failures, expansion lag, reminder lateness, invitation backlog, and time-zone conversion errors.

## Key trade-off

Rule-plus-exceptions is compact but query-heavy; materialized instances are fast but require horizon management and regeneration.
