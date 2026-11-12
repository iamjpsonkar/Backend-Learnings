# Worked Solution: Experimentation Platform

[Design brief](README.md) | [All examples](../README.md)

## Requirements and guarantees

The platform turns a hypothesis into a versioned experiment, assigns eligible subjects consistently, records actual exposure, joins outcomes, computes reproducible metrics, detects validity failures, monitors guardrails, and preserves a decision record.

It supports A/B/n tests, holdouts, mutually exclusive layers, gradual allocation, server and trusted-client assignment, triggered analysis, segmentation, variance reduction, and fixed-horizon or approved sequential methods. It must not claim causality when sample ratio, instrumentation, interference, novelty, or metric definitions invalidate the test.

Targets: assignment p99 below 1 ms locally or 20 ms remotely, 99.999% assignment availability, durable exposure acceptance of 99.99%, results fresh within 30 minutes, and exact reproducibility from immutable inputs plus versioned code/configuration.

## Capacity estimation

Assume 100 million daily subjects, 10 billion exposures/day (116,000/s average, 5x peak), and 100 billion outcome events/day. Assignment stays local; logs batch and compress. At 200 bytes/exposure, exposures are 2 TB/day raw. Outcomes dominate storage, so retain immutable partitioned raw data and compute experiment/date aggregates. Interactive results read aggregates, not raw trillion-row joins.

## Data model and invariants

```text
Experiment(id, tenant, version, hypothesis, unit, layer, salt,
  eligibility, variants, allocation_ranges, start, stop,
  primary_metric_version, guardrails, analysis_plan, status)
Assignment(experiment, version, subject_hash, variant, assigned_at, reason)
Exposure(event_id, experiment, version, subject_hash, variant,
  exposure_time, trigger, assignment_source)
Outcome(event_id, tenant, subject_hash, event_time, name, properties, schema_version)
MetricDefinition(id, version, population, attribution_window,
  numerator, denominator, aggregation, winsorization, missing_policy)
AnalysisRun(id, experiment_version, input_snapshot, code_version,
  watermark, method, estimates, diagnostics, created_at)
```

The randomization unit (user, account, device, session, or cluster) is frozen. Identity is canonicalized before hashing. Allocation ranges are non-overlapping. Experiment versions are immutable after exposure begins; material changes create a new experiment/version and analysis population. Events are idempotent by tenant/event ID.

## API contracts

```http
POST /v1/experiments
POST /v1/experiments/{id}:validate
POST /v1/experiments/{id}:start If-Match: <version>
POST /v1/assign {experiment, subject, attributes}
POST /v1/exposures:batch
POST /v1/outcomes:batch
GET  /v1/experiments/{id}/results?analysis_run=
POST /v1/experiments/{id}:stop
```

Start validates power, allocation, layer conflicts, metrics, eligibility, dates, and approvals. Results always identify experiment/metric/code versions, event watermark, exclusion counts, method, uncertainty, and validity warnings.

## Architecture

```text
authoring -> registry/validator/approval -> signed assignment snapshots -> SDK/service
                                                                    |
                                                               exposure log
product/outcome events -> schema gateway -> immutable event log/lake -----+
                                                                        |
identity map/tokenization -> dedupe -> exposure/outcome attribution -> metric aggregates
                                                                        |
experiment UI <- result store <- statistical engine <- validity + guardrail engine

orchestrator -> start/stop decisions, sequential schedule, immutable analysis manifest
```

The registry compiles immutable assignment snapshots. SDKs assign locally; remote assignment is reserved for secrets or authoritative server context. Exposure and outcomes use separate durable streams but a common privacy-safe subject key. Stream processing provides freshness; scheduled batch recomputation from the lake is correctness authority. The statistical engine consumes frozen aggregate snapshots.

## Experiment validation

Before starting, require:

- one precise hypothesis, randomization unit, eligible population, and primary metric;
- baseline rate/variance, minimum detectable effect, power, significance level, and planned duration;
- frozen metric definitions and attribution windows;
- layer capacity and exclusion from conflicting experiments;
- guardrail thresholds and automatic-action policy;
- instrumentation A/A or shadow validation;
- explicit fixed-horizon or sequential analysis plan and maximum duration;
- owner, approver, stop conditions, privacy classification, and decision template.

Power calculations are metric-specific. For a two-sample mean approximation, per-arm size is proportional to `2 * variance * (z_alpha + z_power)^2 / MDE^2`; proportions use their Bernoulli variance. The UI labels this an estimate and incorporates expected eligibility, trigger, attrition, clustering, and multiple variants.

## Deterministic assignment logic

```text
assign(experiment, subject, attributes, snapshot):
  e = snapshot.exact_version(experiment)
  if e.status != RUNNING or !within_schedule(e): return NOT_ENROLLED
  if !eligible(e.eligibility, attributes): return NOT_ELIGIBLE

  unit_id = canonicalize(subject[e.randomization_unit])
  if unit_id == null: return NOT_ELIGIBLE

  layer_bucket = hash64(tenant, e.layer.salt, unit_id) mod 1_000_000
  if !e.layer.range_for(e.id).contains(layer_bucket): return LAYER_EXCLUDED

  variant_bucket = hash64(tenant, e.id, e.version, e.salt, unit_id) mod 1_000_000
  variant = e.allocation_range_containing(variant_bucket)
  return Assignment(e.id, e.version, hmac_subject(unit_id), variant, reason=ALLOCATED)
```

Layer and variant hashes use distinct salts. A layer gives each subject at most one conflicting experiment. Allocation expansion preserves existing ranges and adds previously unallocated buckets; changing weights must not silently reshuffle enrolled subjects. Cross-language golden vectors fix canonical encoding and hash behavior.

Assignment is not exposure. The product emits exposure only when the subject actually sees/executes the treatment-triggering behavior. The event copies experiment version and assigned variation so later configuration cannot reinterpret history.

## Exposure deduplication and attribution

For user-level intent-to-treat analysis, define first valid exposure per `(experiment version, subject)` and freeze its variant. Repeated exposures may be retained for dose metrics but do not multiply the analysis unit. Crossovers are diagnostics and handled by the prespecified policy, never silently reassigned.

```text
first_exposure = min_valid_exposure(subject, experiment_version)
include outcome when:
  outcome.subject == exposure.subject
  and exposure.time <= outcome.event_time
  and outcome.event_time < exposure.time + metric.attribution_window
  and outcome satisfies metric.population/filter
```

Events before exposure cannot be treatment outcomes. Late events are accepted until the published watermark passes the attribution window plus lateness allowance; then a new result revision is produced. Identity changes use a versioned effective-time mapping, and ambiguous many-to-one mappings are excluded or analyzed at the higher unit.

## Metric computation

Metric definitions compile into reusable sufficient statistics:

- mean: subject-level `count, sum, sum_of_squares`;
- conversion: one Bernoulli value per randomization unit;
- ratio: joint numerator/denominator moments, analyzed with delta method or bootstrap;
- quantile: subject-level values or mergeable sketches plus approved inference;
- retention/survival: cohort and censoring information;
- clustered tests: cluster totals and cluster-robust variance.

Compute at the randomization unit before comparing variants. Event rows are not independent samples when randomization is by user. Cap or winsorize only according to the frozen definition. Missing data, bots, internal users, and outliers use explicit prespecified rules.

For two means:

```text
effect = mean_treatment - mean_control
standard_error = sqrt(var_t/n_t + var_c/n_c)
confidence_interval = effect +/- critical_value * standard_error
```

Also report relative effect with safe handling near zero, sample sizes, raw means, interval, p-value where appropriate, and practical significance. CUPED-style variance reduction uses a pre-experiment covariate and a coefficient estimated without treatment leakage; both are versioned.

## Sequential decisions and multiple testing

Repeatedly reading a fixed-horizon p-value inflates false positives. The analysis plan chooses one of:

- fixed horizon: no significance stop before planned sample/time except safety;
- group sequential: prespecified looks and alpha-spending boundaries;
- always-valid/e-value or Bayesian rule: fully specified threshold, prior, and maximum duration.

The orchestrator runs only scheduled looks from immutable data snapshots. It records all looks, including unfavorable ones. Multiple variants/primary outcomes apply the planned family-wise or false-discovery correction. Segment results are exploratory unless powered and prespecified.

## Validity checks and guardrails

Sample-ratio mismatch compares observed assignments/exposures to planned proportions with a prespecified test and sensitivity. Diagnose by SDK version, platform, geography, time, eligibility path, and missing telemetry. SRM blocks efficacy conclusions; it is not repaired by deleting inconvenient rows.

Other checks include pre-experiment covariate balance, assignment/exposure mismatch, crossover, duplicate IDs, event delays, invariant metrics, bot rates, novelty/weekday coverage, concurrent layer violations, and treatment-dependent missingness.

Guardrails monitor errors, latency, crashes, revenue loss, abuse, and support load. Automatic stop needs a versioned, conservative threshold sustained across enough volume; it freezes further allocation and records the reason. It does not erase exposures or declare the primary metric a loss.

## Step-by-step workflow

1. The owner registers the hypothesis, unit, population, metrics, power assumptions, guardrails, and analysis plan.
2. Validation compiles eligibility and allocation, checks layer conflicts, runs golden assignments, and obtains approval.
3. A signed immutable version reaches SDKs; the orchestrator activates it at the declared instant.
4. Eligible subjects receive stable layer and variant buckets; actual treatment triggers emit idempotent exposure events.
5. Outcome events are schema-validated, deduplicated, tokenized, archived, and joined only after exposure inside metric windows.
6. Pipelines aggregate at the randomization unit and publish versioned, watermarked sufficient statistics.
7. The engine runs validity checks and the prespecified statistical method on an immutable snapshot.
8. Owners record ship, iterate, or stop with effect, uncertainty, guardrails, warnings, and follow-up; the experiment is archived reproducibly.

## Failure handling

- **Registry unavailable:** SDKs use verified last-known-good snapshots; no subject is reassigned.
- **Exposure pipeline lag:** product behavior continues, results watermark stalls, and decisions are disabled until caught up.
- **Duplicate/replayed events:** event IDs and first-exposure rules make processing idempotent.
- **Bad schema/instrumentation:** quarantine invalid events, raise invariant alerts, and mark affected runs invalid.
- **Processor failure:** restore checkpoint and replay immutable logs; revisioned upserts prevent double counting.
- **Late outcomes:** publish higher result revisions until the declared finalization deadline.
- **Identity join outage:** buffer tokenized events and expose join coverage; never treat missing joins as zero outcomes.
- **Guardrail breach:** freeze allocation via an audited higher config version; retain data for diagnosis.
- **Region loss:** fail over signed configuration and replicated logs while fencing stale publishers.
- **Analysis bug:** issue a new code/metric version and recompute; never overwrite the historical run.

## Security, privacy, and governance

Use tenant-scoped RBAC, separation of author/approver/analyst roles, encryption, signed configurations, immutable audit logs, and reviewed service credentials. Assignment does not grant authorization. Tokenize subject IDs with tenant-specific HMAC keys, minimize attributes, separate re-identification access, enforce consent/residency/retention/deletion, and apply minimum cohort sizes to result slices.

Prevent p-hacking operationally: preregister primary metrics and analysis, log every edit/look/exclusion, label post-hoc slices, and preserve negative results. Raw exports and experiment overrides require additional audited privileges.

## Observability and SLOs

Track snapshot propagation/version age, assignment reason and allocation balance, exposure accepted/duplicate/late/dropped, outcome schema errors, join coverage, stream/batch watermark, metric revision lag, SRM and invariant results, guardrail state, scheduled-look execution, query latency, and raw-versus-aggregate reconciliation.

Continuous A/A tests and synthetic subjects validate allocation, exposure, joins, attribution boundaries, late corrections, and false-positive calibration. Alert on integrity/freshness error budgets and validity failures before infrastructure saturation alone.

## Implementation path

1. Implement an immutable registry, deterministic A/B hashing, golden vectors, and server-side exposure logging.
2. Add schema-controlled outcome ingestion, raw archive, dedupe, post-exposure attribution, and simple mean/conversion metrics.
3. Add randomization-unit aggregates, reproducible analysis manifests, confidence intervals, SRM, and invariant checks.
4. Add layers, holdouts, allocation expansion, client SDKs, signed snapshots, and identity coverage diagnostics.
5. Add guardrails, variance reduction, ratios/clusters, late revisions, and fixed/group-sequential governance.
6. Add privacy workflows, automated A/A calibration, batch reconciliation, regional recovery, and decision archives.

## Final design

Immutable experiment semantics and deterministic hashing make assignment stable; actual exposure, not assignment lookup, anchors analysis. Immutable raw events and versioned metric/code manifests make every result reproducible. Randomization-unit aggregation, temporal attribution, SRM/invariant checks, and prespecified sequential rules protect causal validity. The platform reports uncertainty and invalidity as first-class outputs instead of manufacturing a confident answer from compromised data.
