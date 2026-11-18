# Monitoring hub diagnostic API coverage

Documentation audit: **2026-10-22**. This is a collection guide, not a claim
that every endpoint has been tested or that every workload exposes enough
evidence for a definitive RCA. Recheck linked contracts when a service changes.

## Scope and evidence tiers

The [Monitoring hub overview](https://learn.microsoft.com/en-us/fabric/admin/monitoring-hub)
describes multiple pages, including Job runs, Applications, Capacity and cost,
Agents, and Alerts. The following inventory follows the explicit item list on
the [Job runs page](https://learn.microsoft.com/en-us/fabric/admin/monitoring-hub-jobs),
not the entire Fabric item catalog. Other pages expose signals, not necessarily
discrete job executions with a public per-run error API. The new experience is
preview; visibility depends on item permissions and deployed service support.

Collect progressively, preserving exact identifier mappings:

1. **Envelope**: item, run, status, UTC interval, `failureReason`.
2. **Component**: failed activity, entity, task, table/partition, or attempt.
3. **Mechanism**: specific inner error and relevant bounded log excerpt.
4. **Trigger/context**: run-correlated dependency or resource evidence.

A generic wrapper establishes tier 1, not tier 3. Even tier 3 may not establish
the deeper trigger. Definitions describe configuration, not historical errors.
Prefer existing authorized API/telemetry reads before requesting manual logs.

## Job runs item inventory

Every item explicitly listed in the reviewed Job runs documentation has a row.
Route letters refer to the collection recipes below. "Gap" means no item-specific
public deep-error endpoint identified in reviewed documentation, not proof that
the product has no internal diagnostics. Core Job Scheduler support must still
be verified for the actual item/job type; hub visibility alone does not prove it.

| Job runs item type | Envelope route | Deeper evidence route | Important limit | Live validation |
|---|---|---|---|---|
| Copy job | A where supported | F: existing `CopyJobActivityRunDetailsLogs` | Requires previously enabled Workspace Monitoring; no dedicated deep-error REST endpoint identified | not yet tested |
| Dataflow Gen2 | A | D: existing refresh activity/table details and Mashup logs | No public detailed-log download API identified; generic `EntityUserFailure` can be all the API returns | History and generic failure read; inner error unavailable |
| Dataflow Gen2 CI/CD | A where supported | D, with generation-specific support checked | Do not assume legacy Gen1 transaction APIs apply | not yet tested separately |
| Datamart | Verify A | Gap; existing run details/support evidence | Do not substitute a semantic-model refresh ID or SQL query ID without a mapping | not yet tested |
| Data Build Tool (dbt) Job | Verify A | Gap; existing workload run/task output | No verified public per-task/log retrieval endpoint identified | not yet tested |
| Digital Twin Builder Flow | Verify A | Gap; existing flow execution details | Do not infer that a flow has Fabric pipeline activity APIs | not yet tested |
| Experiment | A read exercised | Gap; existing experiment/run diagnostics | Do not equate a hub job ID with an ML tracking run ID | History read succeeded but was empty in sampled items; failed-run RCA untested |
| Graph model | A read exercised | Gap; existing graph build/run details | Graph query errors are not automatically build-job errors | History read succeeded but was empty in sampled items; failed-run RCA untested |
| Lakehouse | A read exercised | B for Spark-backed runs; G for maintenance/MLV distinctions | A Lakehouse job is not always a Spark application | Sampled history empty; session list readable, but no failed-job mapping established |
| Map | Verify A | Gap; existing item run details | Do not invent a map-processing/log API | not yet tested |
| Notebook | A | B: mapped Livy session, driver/executor/Livy logs, Spark diagnostics | Match exact `jobInstanceId`, application and attempt; stdout may contain the actionable traceback | Failed-run/session mapping, advisor and stdout reads exercised; specific access-denial mechanism detected |
| Pipeline | A | C: Fabric Query activity runs, existing telemetry, mapped child diagnostics | ADF ARM APIs are not Fabric APIs; inspect activity `error`, not only the parent wrapper | Activity-query read succeeded on an existing failed run during this audit |
| Semantic model | E: Power BI refresh history | E: execution details, attempts, messages, objects; existing operation logs | Separate audience and access; fields vary by refresh type | Inventory read; sampled history requests denied |
| Snowflake database | Verify A | Gap; existing item/job details and explicitly mapped dependency evidence | Do not call Snowflake or change its configuration without an approved connection/scope | not yet tested |
| Spark Job Definition | A | B: item-specific Livy sessions and existing logs | Do not substitute Notebook paths or assume the same session ID | not yet tested separately |
| User data function | Verify A for a hub job | H: existing invocation diagnostics if available | Invocation identity must be mapped; do not invoke a function to obtain logs | not yet tested |

The list explicitly excludes **Dataflow Gen1**. Do not count its legacy Power BI
transactions as Gen2 runs. The generic route for a gap row is a candidate
envelope path, not verified item-specific API coverage.

## A. Core run envelope

Fabric base: `https://api.fabric.microsoft.com`. Use the environment's verified
host and include `x-ms-fabric-skill` on every call, including retries/pagination.

```http
GET /v1/workspaces/{workspaceId}/items/{itemId}/jobs/instances
GET /v1/workspaces/{workspaceId}/items/{itemId}/jobs/instances/{jobInstanceId}
```

Sources: [List Item Job Instances](https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler/list-item-job-instances),
[Get Item Job Instance](https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler/get-item-job-instance),
and the [Job Scheduler operation catalog](https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler).

Capture `id`, `itemId`, `jobType`, `invokeType`, `status`, `rootActivityId`,
`startTimeUtc`, `endTimeUtc`, and `failureReason`. Preserve any returned
`moreDetails`, `parameters`, `relatedResource`, `requestId`, and `isRetriable`;
sanitize their values before output. Do not discard nested details by
projecting only `message`. Diagnostic HTTP request IDs remain separate.

**Permissions:** documented item read scopes (or supported type-specific
scopes) and effective access to the item. Supported identities and scopes must
be checked on the operation, not assumed from a successful workspace listing.

**Retention:** most items expose only about 100 recently completed instances;
active instances have a different limit. This is not a universal hard cap.
Follow actual pagination, assess timestamps, and try a known direct run lookup
when appropriate. No generic per-activity/log operation was identified in the
reviewed Job Scheduler catalog. Never use trigger/cancel operations for RCA.

## B. Spark-backed Notebook, Spark Job Definition, Lakehouse

Load `spark-cli` operations and its existing diagnostic references first.
The [Spark monitoring API overview](https://learn.microsoft.com/en-us/fabric/data-engineering/spark-monitoring-api-overview)
catalogs the item-specific session, log, resource and Spark-history surfaces.

```http
GET /v1/workspaces/{workspaceId}/notebooks/{notebookId}/livySessions
GET /v1/workspaces/{workspaceId}/sparkJobDefinitions/{sparkJobDefinitionId}/livySessions
GET /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/livySessions
GET /v1/workspaces/{workspaceId}/{itemCollection}/{itemId}/livySessions/{livyId}
GET /v1/workspaces/{workspaceId}/{itemCollection}/{itemId}/livySessions/{livyId}/applications/{appId}/logs
```

`itemCollection` is the verified type-specific collection above, not a literal
placeholder to send. Map the exact job through returned `jobInstanceId` to
`livyId`, `sparkApplicationId`, and `attemptNumber`. Capture session state,
`cancellationReason`, timestamps and available runtime/resource metadata.
Cancellation can be a consequence of a failed statement, not the cause.

For log requests, use the specific documented type/metadata/file selectors:
[Livy logs](https://learn.microsoft.com/en-us/fabric/data-engineering/livy-log),
[driver logs](https://learn.microsoft.com/en-us/fabric/data-engineering/driver-log),
and [executor logs](https://learn.microsoft.com/en-us/fabric/data-engineering/executor-log).
Livy log examples use `applications/none` and `type=livy`; do not replace a
driver application's ID with `none`. Discover log metadata before selecting
files. Inspect bounded, sanitized stdout as well as stderr where relevant.

Use existing Spark Advisor, open-source metrics and resource usage surfaces
from the owning references for a concrete remaining causal question, not as a
mandatory full scan. Retention and partial-download behavior vary by surface;
check the actual response rather than promising indefinite logs.

**Permissions:** item/type-specific read scope and access to the source session
and logs. Do not run a diagnostic notebook, create a Livy session, or use
JobInsight `copyEventLog` to write logs into OneLake under this read-only skill.
An existing authorized export can be read without generating a new one.

## C. Pipeline orchestration and activities

Start with A. Follow actual parent -> activity -> child-run mappings; route
Notebook/Dataflow/semantic-model child failures to B/D/E rather than stopping
at the pipeline wrapper. Activity attempts, handled failures and skipped
downstream work must remain distinct.

Primary references:
[pipeline REST capabilities](https://learn.microsoft.com/en-us/fabric/data-factory/pipeline-rest-api-capabilities),
[pipeline monitoring](https://learn.microsoft.com/en-us/fabric/data-factory/monitor-pipeline-runs),
and [Data Factory Workspace Monitoring](https://learn.microsoft.com/en-us/fabric/data-factory/workspace-monitoring).

The pipeline REST capabilities document explicitly publishes this read-only
query operation and states that `jobId` is the Job Scheduler job ID:

```http
POST /v1/workspaces/{workspaceId}/datapipelines/pipelineruns/{jobId}/queryactivityruns
Content-Type: application/json
```

```json
{
  "filters": [],
  "orderBy": [{"orderBy": "ActivityRunStart", "order": "DESC"}],
  "lastUpdatedAfter": "<verified-UTC-lower-bound>",
  "lastUpdatedBefore": "<verified-UTC-upper-bound>"
}
```

Replace bounds with actual ISO 8601 timestamps bracketing the target run and
its last updates. These are last-updated filters, not start-time cohorts.
Include the acting skill header. Capture the response locally before rendering:
`input`, `output` and `userProperties` can contain sensitive values. Project
`activityRunId`, `activityName`, `activityType`, `pipelineRunId`, `status`,
`activityRunStart`, `activityRunEnd`, `retryAttempt`, and sanitized
`error.errorCode`, `error.message`, `error.failureType`, `error.target`,
`error.details`. Follow pagination if exposed by the actual documented
contract/response, without inventing continuation parameters. The documented
sample is an array; validate the returned shape rather than assuming every
history response has a `value` wrapper.

Collect explicit child IDs only when required for a failing dependency;
do not dump the entire activity input/output to find them. Preserve loops
and retry attempts. A response `id` containing an ARM-style identifier is
not an instruction to call the ARM service.

The reviewed sources also identify existing `ItemJobEventLogs` and
`FabricDataPipelinesActivityRunsLogs` telemetry. Read their current schema and
query by verified workspace/item/run and a bounded UTC interval. Collect
activity identity/type, attempt, status, timing, failure classification and
any available structured diagnostic fields. Do not infer that a failure-type
column necessarily contains the full inner exception.

Do not substitute Azure Data Factory
`management.azure.com/.../queryActivityruns` or translate paths by analogy.
HTTP POST here queries existing history; it is not permission for a rerun.

**Permissions/retention:** A for history; F for existing monitoring telemetry.
The capabilities article is not an operation-specific retention/permission
guarantee: verify the caller's effective access and returned time coverage,
and do not copy ADF's retention or RBAC contract to this Fabric operation.
If neither activity details nor child mappings are available through an
authorized documented surface, record the missing tier and use existing
activity exports/UI details as an optional fallback.

## D. Dataflow Gen2 and CI/CD variants

Use A plus `dataflows-cli` consumption guidance; retain returned `jobType`
rather than assuming `Execute` or `Refresh`. Capture all nested failure fields.
Never call `executeQuery` to recreate a historical exception.

Inventory/Get Dataflow can expose only `type: Dataflow`, without an explicit
generation/CI/CD discriminator. Do not infer the subtype from the display name,
`logicalId`, `isParametric`, or successful history reads, or count one family
test as two independently verified variant tests. Record the CI/CD subtype as
unverified until authoritative metadata or existing UI evidence establishes it.

[Refresh monitoring](https://learn.microsoft.com/en-us/fabric/data-factory/dataflows-gen2-monitor)
documents richer activity/table details, refresh CSV, and detailed-log ZIP
download. [Detailed Mashup logs](https://learn.microsoft.com/en-us/fabric/data-factory/dataflow-gen2-detailed-refresh-logs)
document JSON Lines records with `Start`, `Action`, `ActivityId`, and a
serialized `CorrelationId`; inspect all relevant engine-instance files for the
same refresh, preserving retries/parallel execution.

**Permissions:** detailed-log download requires at least workspace Viewer;
gateway-based refreshes have an additional documented diagnostic-consent
prerequisite. Do not enable it or change roles automatically. Definition reads
have separate permissions and do not supply historical errors.

**Retention:** UI history up to 50 refreshes/six months, OneLake history up to
250/six months, detailed logs up to 28 days and available a few minutes after
completion, per the monitoring documentation. These are different stores, not
interchangeable API guarantees. No documented public path for retrieving those
deep logs or the OneLake history files was identified in reviewed sources;
do not invent one from the retention statement.

No Dataflow-specific deep-error Workspace Monitoring table was identified in
the reviewed telemetry catalog. Do not assume Pipeline/Copy job tables include
Dataflow entity errors. The Power BI Gen1 transaction API is not a verified
Gen2 detailed-error adapter. If only `EntityUserFailure` is available, report
the mechanism as undetermined; if the user has no more evidence, stop cleanly.

## E. Semantic model refresh

Power BI host: `https://api.powerbi.com`; audience:
`https://analysis.windows.net/powerbi/api`. Do not use a Fabric-audience token.

```http
GET /v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/refreshes?$top=10
GET /v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/refreshes/{refreshId}
```

Sources: [refresh history](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/get-refresh-history-in-group)
and [refresh execution details in group](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/get-refresh-execution-details-in-group).
Use the refresh identity returned by the refresh API; do not substitute a hub
run ID or correlation ID without a verified mapping.

Capture history `serviceExceptionJson`, status and attempts. For the selected
refresh, the detail operation documents `status`, `extendedStatus`, `messages`,
`objects` (table/partition/status), `numberOfAttempts`, and available
`refreshAttempts`/execution metrics. Detail level varies: the reference includes
enhanced and on-demand examples, so do not assert every on-demand refresh is
unsupported or every response contains enhanced-refresh metrics. HTTP 200 can
describe a failed refresh; HTTP 202 describes in-progress execution.

**Permissions:** the history API explicitly requires dataset Write permission
despite being read-only. Documented scopes are `Dataset.Read.All` or
`Dataset.ReadWrite.All`; effective item permissions and refresh-type support
still apply. Do not assume the detail operation bypasses a known denial.
Enhanced-refresh capability/capacity prerequisites are not a blanket guarantee
that historical detail exists. A failed detail read is an evidence gap, not
the refresh's cause.

Existing semantic-model operation logs in Workspace Monitoring can provide
additional correlation; discover their actual schema and identifiers using F.
Do not turn on tracing, refresh a model, change credentials, or enable logging
as part of this investigation. Assess retained history rather than assuming
arbitrary date-range access; history excludes OneDrive refreshes per its docs.

## F. Existing Workspace Monitoring telemetry and Copy job

[Workspace Monitoring](https://learn.microsoft.com/en-us/fabric/fundamentals/workspace-monitoring-overview)
is a separate, optional telemetry source, not an aggregate historical REST API.
Resolve its verified monitoring KQL database and schema; use the Eventhouse
MCP/telemetry references linked from the skill. Do not search all Eventhouses
or assume the currently connected business database is the monitoring database.

**Permissions:** Admin to enable, Contributor to query as documented; this
skill only queries an already authorized source and never enables it.
**Retention:** default 30 days, subject to configured policies and actual
coverage. There is no retroactive backfill for activity before enablement.
Read-only monitoring data cannot be treated as a store the skill may ingest to.

[Copy job Workspace Monitoring](https://learn.microsoft.com/en-us/fabric/data-factory/copy-job-workspace-monitoring)
documents `CopyJobActivityRunDetailsLogs`. Correlate `CopyJobRunId`, `ItemId`,
workspace and UTC interval; each source/destination mapping can emit a record,
so do not count rows as separate job failures. Discover the current schema
before selecting error fields and statistics. Its documented error columns
are `ErrorCode` and `FailureType`, with `Status`, `RunId`, `StartTime`,
`EndTime`, `DurationMs` and transfer/row metrics for context. No separate
free-text error-message column is documented; do not invent one. Project only safe diagnostic
columns; do not return raw source/destination payloads.

An initial query template, after verifying the schema and actual identifiers:

```kql
CopyJobActivityRunDetailsLogs
| where Timestamp >= windowStart and Timestamp < windowEnd
| where ItemId == targetItemId and CopyJobRunId == targetRunId
| project Timestamp, CopyJobRunId, RunId, Status, StartTime, EndTime,
          ErrorCode, FailureType, DurationMs, RowsRead, RowsWritten
| take 100
```

Bind the four variables from verified incident metadata, using actual column
types; do not send unresolved identifiers. A run-level wrapper or these codes
may still be insufficient to identify the underlying connector exception.

For all monitoring tables, preserve ingestion delay, missing records, partial
query errors and schema gaps. Aggregates, metric spikes and an empty query
do not prove the cause or absence of a failed run.

## G. Lakehouse maintenance and Materialized lake view refresh

The Job runs list names Lakehouse, not Materialized lake view as a separate
item. Do not claim the latter has a separate hub row without verification.
Use A for supported historical jobs and B only with an explicit Spark mapping.

[Lakehouse background jobs](https://learn.microsoft.com/en-us/rest/api/fabric/lakehouse/background-jobs/run-on-demand-table-maintenance)
and [Materialized lake view APIs](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/materialized-lake-views-public-api)
describe workload jobs. Their run/refresh/cancel operations are not diagnostic
reads. Use only documented get/list operations and existing refresh/job
evidence through `spark-cli` MLV guidance; do not issue a refresh to obtain an ID.
No additional public historical per-table inner-error API was verified in
this audit. Do not reuse the Lakehouse maintenance contract for a Warehouse.

## H. User data function invocation diagnostics

Job-run identity and individual function-invocation identity are distinct.
Use the existing function item's invocation-log experience only with an
explicit mapping to the incident.
[View function logs](https://learn.microsoft.com/en-us/fabric/data-engineering/user-data-functions/view-function-logs)
documents the UI's historical invocation list and details: UTC date, status,
duration, Invocation ID, timestamped log levels/messages and exceptions.
An invocation response's ID header is a correlation artifact, not a log-read
endpoint. No public invocation-log REST retrieval contract was identified in
the reviewed documentation. Do not invent one, treat an invocation endpoint
as a log read, or invoke a function to test an error.

**Retention/coverage:** documented default 30 days, up to 50 entries per
function in the UI, a daily 250 MB ingestion limit, possible sampling, and
ingestion delay. Missing entries do not prove no invocation. Operation-specific
log-read permissions were not specified on that page; verify access rather
than asserting that generic item read permission guarantees it.

## Related workloads outside the documented Job runs list

These routes remain relevant to child/dependency RCA, not evidence that they
are separate supported Job runs item types:

| Workload | Existing evidence path | Boundary |
|---|---|---|
| Warehouse / SQL analytics endpoint | `sqldw-cli` operations: read-only `queryinsights`/DMVs; existing `WarehouseExecutions` monitoring data | SQL query IDs are not generic hub job IDs; completed-query telemetry is not all background work |
| SQL Database | `sqldb-cli` existing read-only operational diagnostics | Separate workload and permissions; no blanket hub job-history claim |
| Eventhouse / KQL Database | `eventhouse-cli` consumption; existing query/ingestion/command logs and metrics | Continuous-workload events are not synthetic failed job runs |
| Eventstream | `eventstream-cli` consumption and existing status/error telemetry | Never restart ingestion; correlate existing signals |
| Mirrored database | Existing mirroring monitoring logs with verified database/table mapping | Replication errors are not automatically scheduler runs |
| Apache Airflow Job | Existing DAG/task/cluster log experience | Not in reviewed Job runs item list; no verified Fabric public log-download contract identified |
| Materialized lake view | G and owning Spark MLV diagnostics | Lakehouse-associated job; separate hub-row status unverified |

Sources: [Warehouse monitoring](https://learn.microsoft.com/en-us/fabric/data-warehouse/warehouse-workspace-monitoring),
[Workspace Monitoring telemetry catalog](https://learn.microsoft.com/en-us/fabric/fundamentals/workspace-monitoring-overview),
and [Airflow logs](https://learn.microsoft.com/en-us/fabric/data-factory/access-apache-airflow-job-logs).
Use owning skill references for executable SQL/KQL recipes rather than
duplicating unverified column names or broad `SELECT *` queries here.

## Collection completion and Live validation

For a per-type test request, inventory the approved workspace completely before
classifying fixture availability. If matching items are not visible, report
**no matching visible item**, not a passed test, unsupported product, or proof
of tenant-wide absence. Do not create a fixture or induce a failure under this
read-only skill. Inventory enum mappings must be explicit: for example,
`MLExperiment` is the Experiment family, not a new unsupported item type.

Read a bounded representative history per available type, with a small expanded
sample where the first history is empty. Prefer previously selected incident
fixtures for a batch API test and label that choice; a new interactive RCA with
ambiguous targets still follows the investigation's selection rules. Empty
history verifies a read, not a failure mechanism or the absence of historical
failures. Unrelated succeeded sessions do not substitute for failed-job evidence.
For Notebook, pipeline and Dataflow, verify the deeper surface where applicable
rather than calling a successful list request an RCA pass.

For the selected item/run, record each applicable surface as **used**, **denied**,
**expired**, **unsupported for this run**, **unavailable in host**, **skipped by
constraint/budget**, or **not yet tested**. Record the source, exact IDs,
sanitized error evidence, permissions/retention limits and missing evidence tier.
Only then describe diagnostic coverage as exhausted within that scope.

During this audit, one read-only Fabric Query activity runs request against
an already selected historical pipeline run succeeded, returning a failed
Notebook activity's structured error and a succeeded activity. This verified
that endpoint/access for that run, not all pipeline activity types, retention
windows, or a deeper dependency cause. No workload was executed.

Earlier live trials covered
Notebook/Spark session/log mapping, pipeline envelope/child linkage, Dataflow
history with a generic failure, semantic-model discovery with denied history,
and native Eventhouse metadata/aggregate queries against a business database.
The latter did not verify Workspace Monitoring or job correlation.

A subsequent per-type live batch exercised the available item families.
Experiment, Graph model and sampled Lakehouse histories were readable but empty;
a Lakehouse session listing returned a succeeded session without a failed-job
mapping. Notebook run/session/advisor/stdout and pipeline activity diagnostics
were readable. Dataflow exposed only the generic failure; semantic-model history
was denied. Several other types had no visible fixture, and Dataflow CI/CD
subtype identity was not established. These are explicit inconclusive, blocked,
or unexercised outcomes, not successful RCA tests.

Other rows are documentation coverage, not live access certification. Structural
tests check packaging and routing, not endpoint validity or RCA quality.
Do not claim "all APIs available" or guarantee a root cause for the gap rows.
Unknown/new hub item types must remain visible as unverified coverage and be
checked against current primary documentation rather than dropped from reports.
