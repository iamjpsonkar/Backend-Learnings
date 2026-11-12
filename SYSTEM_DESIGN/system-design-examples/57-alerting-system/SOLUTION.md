# Worked Solution: Alerting System

[Design brief](README.md) | [All examples](../README.md)

## Requirements and guarantees

Evaluate versioned metric/log rules, track durable alert state, group and deduplicate symptoms, apply silences and inhibition, route by policy, retry providers, escalate, and resolve. A rule must never resolve merely because its data source was unavailable. Configuration changes and every notification decision are auditable.

Targets: one million rule evaluations/minute, p99 evaluation start delay below one interval, critical notification p99 below 30 seconds after firing, 99.99% durable alert transitions, and no duplicate page for the same receiver/fingerprint/escalation step within its dedupe window.

## Capacity estimation

One million evaluations/minute is 16,700/s average. With 3x synchronized bursts, provision 50,000/s and jitter schedules. If 0.1% fire in a bad minute, 1,000 transitions/minute are normal; a regional outage can create hundreds of thousands. Notification capacity is therefore separately reserved by severity. Store state per rule-label instance, not per evaluation. Query sharing is permitted only for identical tenant, expression, timestamp, and data-freshness semantics.

## Data model and invariants

```text
Rule(id, tenant, version, query, interval, for_duration, keep_firing_for,
     labels, annotations, no_data_policy, error_policy)
AlertInstance(rule_id, rule_version, label_fingerprint, labels,
     state, condition_since, firing_since, last_true, last_eval, value, epoch)
Incident(fingerprint, group_labels, status, members, opened_at, resolved_at)
Silence(id, tenant, matchers, starts_at, ends_at, creator, comment, version)
NotificationAttempt(idempotency_key, receiver, incident, transition,
     escalation_step, status, attempt, next_at, provider_id)
```

Alert identity is the hash of tenant, rule ID, and canonical result labels; collisions compare full labels. States are `INACTIVE`, `PENDING`, and `FIRING`. `UNKNOWN` is evaluation health, not a transition that resolves an alert. State changes use a fenced evaluator epoch and compare-and-swap version.

## APIs

```http
PUT /v1/rules/{id} If-Match: <version>
GET /v1/alerts?state=&cursor=
POST /v1/silences
DELETE /v1/silences/{id} If-Match: <version>
POST /v1/incidents/{id}:acknowledge
GET /v1/audit?start=&end=&cursor=
```

Configuration is schema-validated, dry-run compilable, versioned, and atomically activated. Tenant identity comes from authentication. Pagination cursors bind tenant, filters, last key, and snapshot/version.

## Architecture

```text
rule/control API -> versioned config store -> schedule compiler
                                             |
                                   sharded scheduler + leases
                                             |
data sources <- query cache <- evaluators -> durable alert state/outbox
                                             |
                              grouping + silence + inhibition engine
                                             |
                                    routing/escalation tree
                                      /                  \
                         priority notification log    incident API/UI
                                      |
                         channel workers -> providers
```

Schedulers assign rule groups using leases with monotonically increasing epochs. Evaluators query sources at stable timestamps and atomically store state plus outbox events. Grouping consumes transitions, evaluates versioned silence/inhibition/routing policy, and emits idempotent notification jobs. Channel-specific workers isolate email, SMS, chat, and pager providers.

## Main evaluation state machine

```text
evaluate(instance, condition, eval_time, source_status, epoch):
  old = load_for_update(instance)
  reject_if_epoch_is_stale(epoch, old.epoch)
  if source_status != SUCCESS:
    record_eval_error(old, source_status, eval_time)
    maybe_fire_separate_meta_alert()
    return old                         # never false-resolve

  if condition == TRUE:
    if old.state == INACTIVE:
      new = PENDING(condition_since=eval_time)
    else if old.state == PENDING and eval_time-old.condition_since >= rule.for:
      new = FIRING(firing_since=eval_time)
    else:
      new = old
    new.last_true = eval_time
  else:
    if old.state == FIRING and eval_time-old.last_true < rule.keep_firing_for:
      new = old
    else:
      new = INACTIVE

  transaction:
    compare_and_swap(old.version, new.with(last_eval=eval_time, epoch=epoch))
    if transition(old,new): insert_outbox(stable_transition_id(old,new,eval_time))
```

For each successful vector evaluation, missing previous instances are treated according to the explicit no-data policy. A `for: 5m` condition uses scheduled evaluation time and requires successful true evaluations spanning five minutes; restart does not reset `condition_since`. Large evaluation gaps can invalidate continuity according to rule policy.

## Grouping, inhibition, and routing logic

An incident fingerprint hashes configured group labels such as `(tenant,alertname,cluster)`. New firing members wait `group_wait` so related symptoms arrive together. Subsequent changes wait `group_interval`; unchanged firing groups repeat after `repeat_interval`.

Silences match the full canonical alert labels and an active time interval. Inhibition suppresses a target only when a source alert is currently firing, source/target matchers pass, and configured equality labels match exactly. Suppression prevents notification, not state persistence. Every decision records policy version and matching silence/source IDs.

```text
route(alert, node):
  if !node.matchers.match(alert.labels): return []
  receivers = node.receivers
  for child in node.children:
    child_receivers = route(alert, child)
    receivers += child_receivers
    if child_receivers and !child.continue: break
  return unique(receivers)
```

The notification key is `(receiver, incident_fingerprint, transition, escalation_step, policy_version)`. Insert it uniquely before sending. Provider timeouts are ambiguous, so retries reuse the provider idempotency key where supported; otherwise the attempt ledger prevents concurrent duplicates but documents at-least-once delivery.

## Step-by-step workflow

1. A rule update is validated, compiled, versioned, audited, and atomically activated.
2. The scheduler assigns its group a stable timestamp and jittered slot under a fenced lease.
3. An evaluator queries the source with tenant/time bounds and classifies success, no-data, or error.
4. It advances each instance through inactive, pending, or firing in a transaction with an outbox event.
5. The grouping engine maps firing instances to stable incidents and evaluates silences and inhibition.
6. The routing tree chooses receivers and escalation steps using the recorded policy version.
7. Priority workers send idempotent jobs, retry transient failures, and record definitive outcomes.
8. A successful false evaluation resolves the instance; grouped resolve notifications follow policy.

## Notification retry and escalation

Classify provider responses as success, permanent failure, throttling, or ambiguous/transient. Retry transient failures with exponential backoff, jitter, `Retry-After`, and a deadline. Permanent failures go to a review queue. Critical jobs have reserved partitions/concurrency and may fail over to a secondary provider. Escalation timers are durable jobs canceled by a matching acknowledgment or resolution version; stale timers verify incident state before sending.

## Failure handling

- **Evaluator crash:** another owner acquires a higher epoch and resumes persisted state; stale writers are fenced.
- **Data-source timeout:** retain state, record unknown health, and optionally fire an independent datasource alert.
- **Duplicate transition:** unique outbox and notification keys collapse replay.
- **Notification provider outage:** retry within deadline, fail over by policy, preserve attempt history.
- **Alert storm:** severity reservations, tenant quotas, grouping, inhibition, and digest fallback protect critical pages.
- **Scheduler delay:** evaluate at the declared timestamp or mark missed; never pretend a late wall-clock sample was on time.
- **Config-store outage:** use last verified version for a bounded period; reject unversioned changes.
- **Region loss:** a standby takes leases with higher epochs; replicated state/outbox prevents transition loss.

## Security and abuse controls

Use tenant-scoped RBAC, mTLS, encryption, secret references rather than webhook secrets in rule text, and immutable audits for rules, routes, silences, acknowledgments, and manual sends. Sanitize templates, restrict outbound destinations, prevent SSRF, cap query/rule cost, and redact sensitive labels in notifications. Break-glass actions expire and are separately reviewed.

## Observability and SLOs

Measure scheduled-versus-start delay, evaluation duration/errors/no-data, state transitions, pending age, firing cardinality, incident group size, suppression by reason, outbox/notification lag, attempts/provider response, duplicate suppression, escalation lateness, and end-to-end fire-to-page latency.

Synthetic rules continuously exercise pending, firing, silence, inhibition, retry, acknowledgment, escalation, and resolution. Reconcile alert state against notification jobs and page on critical notification error-budget burn or durable-state risk.

## Implementation path

1. Implement versioned rules, one evaluator, durable state, one receiver, and state-machine tests.
2. Add transactional outbox, idempotent workers, retry classification, and complete audit history.
3. Add grouping, silence matching, routing, inhibition, templates, and preview/dry-run APIs.
4. Shard schedules with leases/epochs, persist checkpoints, and test failover during transitions.
5. Add multi-provider escalation, priority reservations, tenant quotas, and storm exercises.
6. Add cross-region recovery, reconciliation, canary alerts, restore drills, and policy simulation.

## Final design

Durable, fenced state transitions are the source of truth; notifications are replayable consequences carried by an outbox. Source failure is explicitly different from a false condition. Stable fingerprints and idempotency keys control duplicates, while grouping, inhibition, and silences reduce noise without erasing alert state. Reserved critical capacity and auditable policy decisions keep the system useful during the outage it is meant to report.
