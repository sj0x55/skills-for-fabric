# Read-only investigation workflow

Read and apply the [mandatory guardrails](./guardrails.md). The selected-run
request/time/child-run budgets include all delegated workload and MCP reads.

## 1. Establish the incident

For live access or a supplied URL, first read the connection and input preflight
linked from the skill. Reuse a verified connection rather than asking the user
to paste evidence that a permitted read-only tool can retrieve.

Use details already provided. Ask only for missing information needed to select
the failed run:

- Authorized tenant/environment, workspace, item name/type or ID.
- Job/run ID or a failure time range with timezone. Convert to UTC while
  preserving the original timezone; clarify ambiguous local/DST times.
- Observed impact and supplied errors, Monitoring hub details, or redacted logs.
- Whether relevant telemetry already exists in a customer Eventhouse. If known,
  obtain its workspace, KQL database, and approximate telemetry coverage.

Do not block investigation when optional Eventhouse telemetry is absent. Do not
search every tenant workspace or database for telemetry without an agreed scope.
If several runs match, show a short list with IDs, status, and UTC times and ask
which run to investigate. Do not silently choose the latest failure.

For supplied-log-only investigations, record the source and available run
identifiers; skip live discovery and label live state as unverified.

## 2. Collect the run envelope

Resolve workspace/item identity using the shared discovery guidance. Where the
workload supports the Fabric Job Scheduler, the read-only interfaces are:

```http
GET {fabricBaseUrl}/v1/workspaces/{workspaceId}/items/{itemId}/jobs/instances
GET {fabricBaseUrl}/v1/workspaces/{workspaceId}/items/{itemId}/jobs/instances/{jobInstanceId}
x-ms-fabric-skill: fabric-job-failure-rca
```

Resolve `fabricBaseUrl` from the environment, normally
`https://api.fabric.microsoft.com`. These are templates, not literal requests.
Use supplied/verified IDs and existing authentication; never use the job-trigger
POST or cancel endpoints during investigation.

- Follow documented continuation tokens/URIs until the target run is located or
  the agreed scope is exhausted. Validate continuation hosts against the
  authenticated Fabric environment before forwarding authorization.
- The list API retains limited recent history (most items expose up to 100
  recently completed instances). Pagination cannot restore expired history.
  A missing run is not proof it never executed: use a known instance ID,
  workload history, or the customer's existing export.
- Do not invent server-side status/time filters. Filter returned instances
  locally unless the current endpoint documentation supports the parameter.
- Capture `id`, `itemId`, `jobType`, `invokeType`, `status`, `rootActivityId`,
  `startTimeUtc`, `endTimeUtc`, and `failureReason` when returned. Preserve
  absent fields as unknown, not empty evidence of health.
- Retain exact status values. A cancelled, deduplicated, queued, or still-running
  instance is not automatically a failed execution. Unknown future statuses
  require verification, not coercion to Failed or Completed.
- Record the retrieval time and diagnostic request IDs separately from the
  run's correlation IDs. Do not equate a request ID, root activity ID, Spark
  application ID, and job instance ID without a documented or observed mapping.

For HTTP errors, report the failing evidence source and sanitized error:

| Diagnostic response | Action |
|---|---|
| 401 | Check environment/token audience and existing sign-in; do not expose tokens |
| 403 | Report missing read access; do not elevate permissions or infer the job's cause |
| 404 | Verify item/run/environment and retention; distinguish unavailable evidence from "no failure" |
| 429 | Honor `Retry-After`; agree on a finite retry/time budget, default at most three retries; report exhaustion |
| Unsupported API or other error | Use documented workload evidence or an existing export; preserve the collection error |

Do not poll a completed failure indefinitely. For an active run, agree on a
bounded observation period and honor any server polling interval.

## 3. Trace the failing component

Use the workload routing table in the skill. Investigate the specific run,
activity, query, refresh attempt, or Spark application, not just item health now.
Read the diagnostic API coverage reference linked from the skill and account
for the applicable deeper surfaces before declaring the run-envelope error
the best available evidence. Distinguish a documented but untested endpoint
from one actually denied or unsupported for this run. Do not call an Azure
Data Factory ARM API for a Fabric pipeline or reuse identifiers across services.

For pipelines, build a parent run -> activity run -> child run mapping from
the documented Fabric Query activity runs operation in the diagnostic API
coverage reference, existing monitoring telemetry, or exported activity details.
Do not stop at the parent wrapper when activity diagnostics are accessible.
Track activity name/type,
attempt, dependency, status, UTC interval, child item/run/application ID, and
the concrete activity error. A pipeline's generic failure wrapper is not the
underlying root cause.

Distinguish retries, parallel branches, handled errors, and downstream skipped
or cancelled activities. The earliest timestamp alone is not a causal chain.
Trace the first evidenced failure on the dependency path that caused the
observed unsuccessful outcome. If no child mapping is available, say so.

Collect only relevant redacted exception excerpts, error codes, existing
driver/executor logs, refresh details, query/ingestion errors, and observed
resource signals. Do not download entire data payloads or create a notebook,
Livy session, SQL workload, or test refresh to reproduce the issue.

### Semantic model refresh failures

Use the documented Power BI refresh-history endpoint, not a refresh trigger:

```http
GET https://api.powerbi.com/v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/refreshes?$top=10
GET https://api.powerbi.com/v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/refreshes/{refreshId}
```

Use the Power BI audience `https://analysis.windows.net/powerbi/api`, not the
Fabric audience. Verify model IDs through authorized item/dataset discovery.
The [refresh-history API documentation](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/get-refresh-history-in-group)
requires dataset Write permission even though this is a read-only request.
An accepted token or successful model listing does not establish that access;
the documented OAuth scope alone does not establish item permissions either.
Do not change permissions automatically or infer the precise missing entitlement
from a Forbidden response alone.

- If the target is unspecified, collect bounded history only within the approved
  workspace and present candidate failed runs for selection. If history access
  is already known to be denied, recheck a small sample rather than probing every
  model again. Report sampled coverage, not an assertion that every model is
  inaccessible.
- Do not classify a history-request denial as a refresh failure, or choose an
  inventory item and claim it has failed. Model metadata, a missing
  `isRefreshable` field, and an empty history do not establish storage mode,
  refresh eligibility, or health.
- For an accessible selected failure, retain status, refresh/request ID,
  start/end times, refresh type, `serviceExceptionJson`, and available attempt
  details. Sanitize exception fields before output. Distinguish attempt failures
  from the final refresh outcome. Use the selected refresh's execution-detail
  read for returned messages, table/partition objects and attempts where
  supported; do not assume every refresh type exposes the same detail. The
  diagnostic API coverage reference has the exact contract and limitations.
- If access remains blocked, request the existing failed row's model name,
  UTC time, and **Refresh history -> Show details** error or an existing export.
  Reuse identifiers already provided. This is a fallback, not a requirement for
  users whose history is accessible. Do not repeat a blocked browser sign-in
  without a meaningful authentication-context change.
- Stop at an access-blocked preliminary report if no failed-run evidence is
  available. State that the cause is undetermined, rather than diagnosing
  credentials, capacity, a gateway, or a data source without job-side evidence.

### Dataflow Gen2 generic failures

Use existing job history and the selected job-instance read under `dataflows-cli`
consumption guidance. Preserve the returned `jobType`: do not replace it with
an expected value from an example. Do not evaluate M, trigger a refresh, or
change diagnostic settings to reproduce a failure.

`EntityUserFailure` with only a generic "Something went wrong" message confirms
an unsuccessful run, not a specific user mistake, failing query, source,
destination, credential problem, or capacity issue. Preserve `isRetriable`
separately from message text that suggests trying again; neither authorizes
a rerun.

If the existing API response lacks entity/step details, use an already
authorized diagnostic source if available. Otherwise, offer the selected run's
existing activity/table error, refresh CSV, or detailed Mashup logs as an
optional fallback. Follow the documented
[refresh monitoring guidance](https://learn.microsoft.com/en-us/fabric/data-factory/dataflows-gen2-monitor)
for availability, permissions, retention, and gateway prerequisites. Do not
invent a log-download endpoint or enable gateway diagnostics automatically.
Logs can contain query expressions and endpoint information: inspect locally
and sanitize before any output.

If the user has no additional evidence, finish a preliminary report without
repeating the request. Keep the cause **Undetermined**, identify the smallest
missing evidence, and make any support escalation optional. A subsequent
completed run establishes a later successful execution, not a confirmed
transient cause, a durable fix, or complete rollback of partial writes.

### Notebook statement failures

Map the requested job to its session using the session listing's explicit
`jobInstanceId` match, then use the returned `livyId` and `sparkApplicationId`.
Do not use the job ID as the session ID or select the newest application.
Preserve attempt numbers. If timestamps differ between session infrastructure
startup and job submission, label each clock/event separately; calculate job
duration from job start/end, not unrelated session fields.

`System_Cancelled_Session_Statements_Failed` is a terminal wrapper: the system
cancellation is a consequence of a statement error, not evidence of a manual
cancellation. After reading the owning Spark references:

1. Check Spark Advisor. An empty result means no advice returned, not no error.
2. Inspect relevant driver log metadata and bounded sanitized excerpts. Driver
   stderr may contain only JVM/framework messages; **driver stdout can contain
   the Python cell traceback and the actual failing call**. Use both as needed,
   not repeated speculative requests against the same surface.
3. Preserve the cell/line, failing operation, nested exception, structured error
   code, and retry indicator. A `Py4JJavaError` is a bridge wrapper; a nested
   `SocketTimeoutException` identifies a more specific failure mechanism.
4. Stop additional log collection once the evidence supports an actionable
   mechanism. Optional telemetry is useful only for a remaining causal question.

For a token-acquisition timeout, distinguish the requested token audience from
the remote endpoint that actually timed out. A request for a Graph token does
not establish a Graph API outage, invalid audience, missing permission, or
Conditional Access failure. The token library may contact another dependency.
Do not print token values while investigating.

Keep retry semantics separate: a nested error marked retriable, a notebook's
retry helper, and a job envelope marked non-retriable describe different layers.
None authorizes rerunning the notebook. Before recommending retry changes,
check existing retry behavior and evidence for a transient dependency problem.
Earlier runs with the same generic cancellation wrapper establish a recurring
symptom only; compare their specific exceptions before asserting a common cause.

A notebook may intentionally sanitize a dependency exception into a safe
application error. Preserve that error and mark the underlying cause unknown;
do not try to bypass a sanitizer, print credentials, or infer an outage from a
generic transport label. Preserve exact HTTP statuses, including nonstandard
ones; a service-side 520 is not evidence of a permission problem or necessarily
equivalent to 500.

Pipeline errors may say that the Notebook service returned HTTP 200 while also
embedding a failed notebook state. Distinguish successful transport/status
retrieval from unsuccessful notebook execution, and follow explicit child run
IDs to avoid counting the wrapper and child as independent causes.

Check later outcomes without triggering a run. A later success establishes
successful execution for that attempt, not a durable recovery. If successes
occur between repeated source-authorization failures, compare effective
execution identity, source, parameters, and path before assuming access was
permanently revoked. Recommend a bounded comparison rather than blind retries.

## 4. Correlate optional customer telemetry

If authorized telemetry exists, read the Eventhouse reference linked from the
skill and query the incident window using discovered schema and identifiers.
Telemetry supplements run evidence; it is neither assumed present nor required
for every conclusion. Record ingestion delay, retention, sampling, query
failures, and coverage limits.

## 5. Test competing explanations

Maintain the four-stage evidence completion checklist in the evidence/handoff
reference linked from the skill: run, failing component, mechanism, and deeper
trigger assessment. Record status and evidence for each; never interpret a
successful API response as all four stages completed.

Create an evidence ledger with stable IDs (`E1`, `E2`, ...), source, UTC event
time, collection time, run/correlation identifiers, and a minimal sanitized
excerpt. Reference those IDs in every causal claim.

For each hypothesis, record supporting evidence, contradicting evidence, and
the smallest next read-only check. Use these categories as a checklist, not
an automatic diagnosis:

| Candidate | Evidence needed beyond a generic failure message |
|---|---|
| Code, expression, schema, or data | Specific failing statement/exception, schema mismatch, or redacted record validation tied to this attempt |
| Identity or connectivity | Job-side authentication, authorization, DNS, gateway, or network error for the relevant dependency; diagnostic access errors do not qualify |
| Capacity, memory, concurrency, or throttling | Workload limits, resource metrics, OOM/termination details, or throttle events correlated to this execution |
| Timeout or dependency outage | Observed timeout/dependency failure with matching identity and interval; separate timeout symptom from its trigger |
| Configuration or deployment regression | Verified configuration/version difference and a causal link; temporal proximity alone is insufficient |
| Cancellation or service-side incident | Actual cancellation/termination record or authoritative incident evidence affecting this run |

Compare an existing successful attempt only if the workload, parameters, data
scope, configuration, and time window are sufficiently comparable. Do not run
a new job. State confounders rather than interpreting correlation as proof.

Classify conclusions as **Confirmed**, **Probable**, or **Undetermined**:

- Confirmed: direct run-linked evidence explains the failure mechanism and the
  dependency path; relevant alternatives have been checked.
- Probable: supporting evidence exists but an important causal link is missing.
- Undetermined: evidence cannot discriminate between plausible causes.

A log entry may confirm the failure mechanism (for example executor OOM)
without confirming its deeper trigger (for example skew). Label them separately.
Keep multiple independent root causes when the evidence warrants them.

## 6. Report and hand off

Use the report contract linked from the skill. Include evidence-backed
remediation recommendations, owners, risks, and a verification plan. Do not
claim remediation or recovery: a later successful run does not prove the cause
was removed. For unresolved incidents provide a minimal escalation bundle,
not a fabricated definitive RCA.

## API sources

- [List Item Job Instances](https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler/list-item-job-instances)
- [Get Item Job Instance](https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler/get-item-job-instance)

Check the current workload documentation for support and identity requirements.
