# Failure overview and trends

Apply the [mandatory guardrails](./guardrails.md) to collection, queries and
reporting. Count all transports and delegated reads against the same budget.

Produce a prioritized, evidence-backed summary across existing job history.
This is a read-only overview mode, not a tenant-wide crawler or proof that all
similar failures share a root cause.

## 1. Establish scope and collection budget

Use the current or explicitly selected workspace. Ask if workspace context is
ambiguous; do not interpret "my failures" as permission to scan the tenant.
Multiple workspaces must be explicitly selected. Read the connection preflight
linked from the skill before live access.

Unless overridden, announce these defaults:

Interpret paraphrases and explicit overrides using the intent-routing reference
linked from the skill. In particular, an explicit "no comparison" omits baseline
collection, "metadata only" omits log drill-down, and a requested ranking,
top N, calendar window, or exclusion replaces only that parameter.

- Current window: last 7 days ending at a fixed UTC collection cutoff.
- Baseline: previous 7 days, immediately before the current window.
- Top 5 items ranked by failed-run count; show failure rate and recurrence
  separately. Ties use failure rate where comparable, then stable item ID.
- UTC daily bins; use the same bin boundaries in both windows. Mark the first
  and last partial calendar-day bins. Honor a requested reporting timezone,
  convert boundaries explicitly, and account for DST rather than assuming
  every local day has 24 hours.
- Metadata-first collection: at most 50 item histories, 200 remote diagnostic requests
  including retries/pagination, and 5 minutes of collection, whichever is
  reached first. These are safety budgets, not API limits. Announce them and
  request approval to expand when they prevent adequate coverage.
- Deep diagnostics: at most 3 representative runs overall, one per leading
  signature initially; fetch additional runs only for a concrete causal question
  and with an explicitly expanded budget.

Explicit workspace-wide overview scope permits bounded item discovery/history
reads there; it does not authorize scanning other workspaces or every run's
logs. Prefer a user's workload/item filter. If more than 50 candidate histories
exist, ask for a narrower scope or increased budget before fetching a
convenient first-50 sample and calling it "top workspace failures".

## 2. Collect run metadata before logs

Use supported documented history APIs from the investigation/workload guidance.
Use the diagnostic API coverage reference linked from the skill to classify
Monitoring hub item types and separate run histories from continuous-workload
signals. Preserve unsupported or not-yet-verified types as coverage gaps rather
than silently omitting them from a claimed workspace-wide summary.
Do not invent an aggregated Monitoring hub endpoint or server-side filters.
Discover items, follow pagination, and retain continuation metadata and
collection errors. A Jobs API history call is item-scoped. Use explicit
workload history adapters for refreshes or other types only where documented.
Continuous-workload errors are a separate signal, not fabricated job runs.

Collect both successful and failed terminal runs, not only a Failed-filtered
view. Include pending/running, cancelled, deduplicated, and unknown statuses
as separate counts. Do not read item source definitions or every run's logs
to compute an overview.

Record normalized fields in memory or an approved customer-side location:

- Workspace/item ID and display name, workload type, source/API, collection time.
- Run ID, attempt identifier when exposed, parent/child mapping if known.
- Start/end UTC times and exact status with its verified normalized meaning.
- Error code and sanitized message, structured correlation IDs if returned.
- Evidence level: run-envelope only, verified inner exception, or correlated
  telemetry. Preserve the underlying source reference.

Deduplicate repeated pages/sources by workspace + item + run + attempt identity,
not message text. If attempts are not distinguishable, do not invent attempt
counts. Deduplicate telemetry events separately; ten log lines are not ten runs.
An overview based only on supplied failures cannot calculate a failure rate.

### Coverage is part of the result

For each source/item/window, track queried versus inaccessible/unsupported
histories, observed time span, oldest returned run, pagination completion,
retention/caps, request budget, result truncation, and missing fields.

The Jobs API's limited recent completed history can censor both windows:
100 returned runs is not evidence that all runs in the window were returned.
Empty history does not prove zero executions. Completed pagination does not
restore retained-out runs. Determine coverage using documented retention/caps
and returned range, not pagination alone. If coverage cannot be established,
label observed counts as lower bounds and rates as observed-sample rates or
unavailable, never as the complete workspace rate.

Do not treat a typical documented history count as a universal maximum: follow
actual continuation tokens and assess the oldest returned timestamp. Some
histories can return substantially more entries yet still fail to cover the
baseline. When an API provides a continuation token, use its documented
parameter on the verified original endpoint rather than forwarding credentials
to an unverified continuation host. Handle relative continuation URLs safely.

Semantic-model refresh history has separate Power BI authentication and
permissions requirements, including dataset Write permission for the documented
history endpoint. A successful Fabric workspace read does not prove that
refresh history is readable. Record refresh-history 403s as collection gaps,
never as failed refreshes, and do not change permissions automatically.

Report current and baseline coverage independently. If the baseline is
incomplete or differently scoped, suppress improvement/regression claims for
that comparison and explain why. A newly visible item is not necessarily a
newly failing item.

## 3. Calculate metrics with explicit denominators

Use start-time cohorts: include runs with `start >= windowStart` and
`start < windowEnd`, based on the selected reporting timezone's converted UTC
boundaries. Label runs that started before the window and failed during it
separately; do not silently mix end-time and start-time cohorts. If a workload
lacks a comparable start timestamp, report its metric separately and explain.
State that recent cohorts may still be in progress at collection time.

For each item and each window:

```text
failed = distinct terminal failed runs in the start-time cohort
succeeded = distinct terminal successful runs in the same cohort
eligible = failed + succeeded
failure_rate = failed / eligible, only when eligible > 0
failure_share = item failed / total observed item-level failed runs,
                only when that observed total > 0
rate_change_pp = 100 * (current_rate - baseline_rate)
```

Map statuses through the source's documented contract; for core Jobs API,
`Completed` maps to successful and `Failed` to failed. Exclude Cancelled,
Deduped, active, and unmapped statuses from `eligible`, showing their counts.
Do not compute success as "anything that isn't Failed". Zero eligible runs
means N/A, not 0% failure. Clearly label observed-sample denominators.

Show counts and rates together. A count increase with an unchanged rate may
reflect higher run volume, not worsening reliability. When baseline failed
count is zero, show "no failures observed in baseline" and the absolute change,
not infinite growth or a fabricated percentage increase. Only call it a new
failure pattern if baseline coverage is comparable.

Do not average per-item rates for a portfolio rate: sum failed and eligible
over the same covered cohort. Do not compare a changed workload mix without
showing per-item changes or a matched-item comparison. Items missing from a
window remain unavailable, not zeros.

Pipeline parents and child runs can both be real failed runs. Label the primary
ranking as **item-level run failures**, not independent incident count.
Where explicit parent/child links exist, additionally group failure cascades
and show their linked runs. Do not sum both views together; when mappings are
missing, state that incident deduplication is unavailable.

### Verified incidents versus suspected clusters

Maintain three separate views; do not replace the existing execution ranking:

| View | Membership rule | Count meaning |
|---|---|---|
| Failed executions | Distinct failed execution identities in the covered cohort | The existing failed-run numerator, not an incident count |
| Linked incidents | Connected groups of at least two failed executions joined by verified causal propagation links | Observed linked failure cascades, not a count of all independent incidents |
| Suspected common-cause clusters | Runs sharing a specific signature, dependency or time pattern without verified propagation | Hypotheses for investigation; they do not deduplicate executions or incidents |

Use workspace + item + run identity, retaining source-qualified attempt metadata
and the primary metric's execution unit. Do not split a single failed execution
into new counted executions merely because its logs contain retries.
Each linkage must cite source evidence explicitly showing both identities and
that the child's failure contributed to the parent's unsuccessful outcome.
A child invocation alone, a shared root activity value, matching text, shared
resource, or temporal overlap is not enough. Do not treat handled child errors
as causes of a later independent parent failure.

For verified links, compute connected groups transitively without counting
a shared child or an execution twice. Report linked-group count, group members,
and **unlinked failed executions** separately. If links cross the selected time
window, retain outside-window context but do not add it to cohort counts. Report
incomplete mappings, identity conflicts or cycles rather than forcing a count.

Suspected clusters can overlap linked groups; label overlap and evidence
strength, never add these populations together. A cluster needs its own
supporting evidence and smallest validating check. It must not inherit a
representative run's confirmed cause for all members.

## 4. Rank, group, and detect patterns

Produce two complementary views:

1. Top items by observed failed-run count (default), with eligible count,
   failure rate, baseline count/rate, percentage-point change where valid,
   first/last failure, and failing days.
2. Top error signatures by distinct failed runs and affected items, with
   evidence level, representative runs, and current/baseline counts.

Build signatures from workload + structured error code + verified inner
exception where available. Normalize volatile IDs/timestamps only in a derived
sanitized signature; retain source references and meaningful operation/error
differences. Missing causes stay Unknown. Generic cancellation/statement-failed
wrappers are **symptom groups**, not confirmed shared causes. Do not merge
unrelated failures because they share `Py4JJavaError` or "timeout".

Describe observed patterns with counts and evidence:

- Recurrence: failing days, consecutive failed executions, or repeated scheduled
  failures when the ordered history and schedule evidence support that claim.
  Missing executions break confidence in a streak; do not infer schedule misses
  from sparse logs.
- Burst: failures clustered in an explicit time bin, listing affected
  workloads/items and distinct runs. Show source coverage and run volume.
- Deterioration/recovery: comparable same-item rate/count changes; a later
  successful run is not proof of a durable fix.
- Spread: the number of distinct items/workspaces exhibiting the same verified
  signature. Temporal overlap alone does not prove a shared dependency outage.

Small samples must remain visible. Use "observed increase", not "statistically
significant", "anomaly", or a quantified probability without a stated, justified
method and sufficient data. Do not invent business impact, capacity saturation,
deployments, or owners.

## 5. Explain what might be going on

Pick up to 3 representative failures across the leading signatures, preferring
an unresolved high-volume symptom, an emerging pattern with comparable
baseline, or a cross-item pattern. Record the selection rule. These samples
are explanatory examples, not a random sample or proof of every group's cause.

For each selected run, load the investigation workflow and relevant workload
skill, use exact identifiers, and collect only the evidence needed. Distinguish
Confirmed mechanisms from Probable hypotheses and Undetermined deeper causes.
A timeout in token acquisition does not establish an outage of the requested
audience, and matching cancellation wrappers do not establish matching causes.
Do not extrapolate a sampled inner exception to uninspected failures.

Use optional authorized Eventhouse telemetry to validate a specific pattern or
hypothesis; read its reference from the skill. Discover schema, filter both
windows, and aggregate by verified distinct run identity rather than log count.
If run identities, success signals, or coverage are absent, report telemetry
event counts separately, not a job failure rate. Sampling/ingestion lag and
query limits apply to aggregates as well as returned rows.

Recommend prioritized next actions by observed frequency, breadth, and known
impact, with supporting evidence and the smallest confirming check. Unknown
impact stays unknown. Do not automatically remediate or expand into all logs.

## 6. Overview report contract

Use progressive disclosure and the skill's customer-facing presentation rules.
Do not narrate the collection procedure or print the complete evidence ledger
by default.

### Default customer report

1. **Bottom line**: workspace, current time window/timezone, observed failure
   count/rate with denominator where valid, and the most important pattern.
   State partial coverage up front when applicable. Use two or three sentences,
   not an inventory or a list of API operations.
2. **Top failures**: one compact table, default five items:

   | Item / workload | Failed / terminal runs | Observed failure rate | Main finding |
   |---|---|---|---|

   Link items/runs where supported and verified. Keep counts and denominators
   visible; use N/A where a rate is unavailable. Include a short comparison in
   the finding column only when comparable. Do not assign business severity
   without measured or user-provided impact.
3. **What might be going on**: up to three evidence-backed bullets combining
   the main trends and explanations. Explicitly label Confirmed findings,
   Probable hypotheses, and Undetermined causes. State which samples were
   verified, without extrapolating their cause to the full group. Use short
   inline source references or verified drill-down links.
4. **Next actions**: up to three prioritized recommendations with known owner,
   rationale, and verification criterion. Avoid repeating every table row.
5. **Coverage**: a short, explicit note on excluded workloads, incomplete
   baseline/current history, partial-day bins where relevant, and observed-only
   rates. State that parent/child run counts may overlap when incident
   deduplication is unavailable. End with "Diagnostic reads only; no jobs
   rerun or resources changed."

When linkage materially changes interpretation, add one short statement such as
"Four failed executions include one verified two-run cascade and two unlinked
failures; the shared-timeout hypothesis is not a confirmed common cause."
Keep the detailed group membership/evidence ledger on request.

Omit unchanged or irrelevant detail rather than manufacturing findings to fill
each section. Keep material caveats visible even when the user asks for a
three-bullet executive summary.

### Technical details on request

Provide relevant measured facts, not internal deliberations:

- **Scope and coverage**: exact current/baseline half-open UTC intervals,
  timezone and cutoff; item/source counts, budgets, retention and pagination
  limits, excluded statuses, and source-specific collection errors.
- **Patterns and trends**: daily counts and denominators, signature rankings,
  failing days, baseline count/rate and percentage-point changes only where
  comparable; linked cascades separately from item-level counts.
- **Evidence and limitations**: stable evidence IDs, source retrieval times,
  representative run/attempt IDs, sanitized exceptions, reproducible query
  recipes, and the precise extent each proposed cause was verified.
- **Recommendations and verification**: detailed owner/risk/prerequisite,
  evidence rationale, and verification plan; unresolved escalation needs.

Preserve technical evidence in investigation context, not necessarily a saved
file. A request for technical detail is not permission to save a report,
publish customer evidence, expose credentials, or expand collection scope.

If only partial data is available, title the result "Observed failure overview
(partial coverage)" and do not present a global top ranking. If no failures
were returned, say "No failures observed in the queried sources and window",
not "all jobs are healthy".
