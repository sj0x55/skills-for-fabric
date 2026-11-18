# Optional customer Eventhouse telemetry

Use existing customer telemetry only with authorized read access. This workflow
does not create an Eventhouse, workspace monitoring, diagnostic settings,
mirrored database, connection, table, ingestion flow, or dashboard.

Before choosing tools, read the Eventhouse MCP integration reference linked
from the skill. Prefer a verified native Eventhouse MCP connection; use other
approved connectors or CLI/REST only with the stated fallback policy. Connector
selection never changes the authorized database, read-only boundary, or evidence
requirements below.

## Discover the actual data

1. Confirm the telemetry workspace/database and permitted investigation scope.
   It may differ from the failed job's workspace. If the customer only suspects
   telemetry exists, inspect metadata within that scope; do not scan the tenant.
2. Load `eventhouse-cli` and its `consumption` reference through the skill's
   routing table. Discover the KQL database query URI via Fabric metadata rather
   than guessing a cluster hostname. For direct Kusto access, use the Kusto
   token audience documented there, not a Fabric control-plane token. For native
   MCP, use the server/host's documented authentication; do not substitute a
   direct Kusto token or assume the two authentication contexts are shared.
3. With read-only KQL tooling, inspect `.show tables`, then the schema of
   candidate tables using `.show table <discovered-table> schema as json`,
   or equivalent metadata-only MCP tools after verifying their actual schemas.
   Resolve placeholder identifiers with the owning skill's escaping conventions.
   Do not interpolate raw log text into query identifiers.
4. Map actual columns and types for event time, workspace/item identity,
   job/activity/correlation identity, attempt, status/severity, error details,
   and ingestion time if available. Customer schemas are not standardized.
   Do not assume a table called `JobLogs`, `SparkLogs`, or `FabricTelemetry`.
5. Record which signals and time ranges the data covers. Missing tables, missing
   ID columns, access denied, expired retention, and ingestion lag are distinct
   outcomes. Continue with other evidence and include these limitations.

## Query in bounded stages

- Start with the run interval plus 15 minutes on each side. If the end is
  unknown, use an explicit bounded end such as the collection time. Specify
  UTC start/end in the report and use a half-open time range.
- Filter by the discovered event-time column before expansion or aggregation.
  Do not substitute ingestion time for event time without documenting that
  the result cannot establish precise execution chronology.
- Filter on workspace/item identity where available, then exact run,
  root-activity, activity-run, or verified child/application identifiers.
  Query both event-time and ingestion-time ranges when needed to assess lag.
- Project only necessary diagnostic columns and cap output, initially 100 rows.
  For MCP tools whose results the host may display immediately, omit sensitive
  fields in the query itself rather than relying on post-response redaction.
  A cap limits returned rows, not scan cost: retain time and identity filters.
  Check partial-result/query-status errors as well as HTTP success.
- If a cap is reached, mark results truncated. Narrow by activity/attempt or
  subdivide time ranges before fetching more. Do not conclude completeness
  from a limited sample. Respect tool query timeouts and customer query budgets.
- Expand the window only for a specific hypothesis and record the new bounds.
  Avoid `search *`, cross-database wildcards, unbounded unions, or dumping payloads.

## Schema-mapped query template

This is a template, **not an executable query against an assumed schema**.
Replace every `{{...}}` identifier with a verified table/column, quote identifiers
correctly, and supply typed parameters through supported tooling or safely
escaped literals. Omit unavailable projections; never manufacture columns.
For a GUID column, use a GUID-typed parameter or an explicitly verified
conversion instead of assuming string equality.

```kql
declare query_parameters(
    windowStart:datetime, windowEnd:datetime,
    incidentWorkspace:string, incidentItem:string, incidentRun:string
);
{{TelemetryTable}}
| where {{EventTimeColumn}} >= windowStart and {{EventTimeColumn}} < windowEnd
| where {{WorkspaceColumn}} == incidentWorkspace
| where {{ItemColumn}} == incidentItem
| where {{RunColumn}} == incidentRun
| project EventTime={{EventTimeColumn}}, RunId={{RunColumn}},
          Severity={{SeverityColumn}}, ErrorCode={{ErrorCodeColumn}},
          Message={{MessageColumn}}
| order by EventTime asc
| take 100
```

If only a verified root-activity/child ID is present, adapt the identity predicate
to that mapping. If no exact correlation field exists, constrain the event
window and item/workspace, then use a narrow indexed text predicate (`has` rather
than `contains` where appropriate) for a candidate search. Treat text matches
as weak evidence: timestamps and message similarity do not establish identity,
and token search is not exact GUID matching.

## Correlation and evidence

- Keep job instance IDs, activity IDs, Spark application IDs, and diagnostic
  request IDs separate. Record how each cross-source join was established.
- Separate attempts and deduplicate copied events using a discovered stable
  event identity when available, preserving original source attribution.
- A capacity spike near a failed run is a hypothesis until job-linked resource
  evidence supports a causal mechanism. Likewise, a downstream ingestion error
  may be an effect rather than a cause.
- An empty query means **no matching rows in this source and window**, not
  "no failure" or "telemetry does not exist." Check mapping, coverage, event
  time, ingestion delay, and retention before interpreting absence.
- Cite the database/table, redacted query or reproducible query recipe,
  UTC bounds, correlation fields, result cap, observed row count, and any partial
  result status. Share only minimal sanitized excerpts with the RCA.

If telemetry is absent, unavailable, or too delayed, say so and finish using
other evidence. Do not silently provision observability as an RCA fallback.
