# Eventhouse MCP integration

Apply the [mandatory guardrails](./guardrails.md) before connector discovery or
queries. Stop if source projection or local capture cannot prevent unsafe raw
results from being displayed by the host.

Prefer an existing, verified native Eventhouse MCP connection for authorized
customer telemetry. Keep `eventhouse-cli` consumption mode as the owner of KQL
semantics, schema discovery, and read-only workload guidance. MCP is a transport
choice, not permission to bypass that skill or expand the investigation.

This integration is optional. Installing the RCA skill does not automatically
register a customer Eventhouse, enable Copilot, grant permissions, or expose
MCP tools in a running host.

## Supported connector paths

| Priority | Connector | Capability contract |
|---|---|---|
| 1 | Native remote Eventhouse MCP (preview) | Discover the connected server's actual tools and schemas; verify database scope, metadata discovery, and bounded read-only KQL |
| 2 | Already approved Fabric RTI MCP | Discover `kusto_list_entities`, `kusto_describe_database_entity`, and `kusto_query` if advertised; inspect actual schemas before invocation |
| 3 | Already approved Azure MCP Kusto tools | Discover the router and its commands; direct `cluster-uri`, `database`, schema, and query support must be verified |
| 4 | Existing Azure CLI / Kusto REST connection | Use the documented `eventhouse-cli` consumption workflow and Kusto authentication |

The native Eventhouse MCP, Fabric RTI MCP, and Azure MCP Kusto are different
connectors. Report which one was actually used. Do not call REST a successful
MCP test, treat tool-name similarity as proof of a connector's identity, or
claim a registered server is connected before a real read succeeds.

If the user explicitly requests a particular connector or forbids fallback,
honor that restriction. On missing tools, an authentication error, access
denial, or unsupported capability, explain the gap and offer the next approved
path; do not silently switch transports. Changing transport cannot cure missing
data permissions or justify circumventing Conditional Access.

## Native remote connector setup

Microsoft documents an HTTP endpoint scoped to a KQL database:

```text
https://api.fabric.microsoft.com/v1/mcp/dataPlane/workspaces/<workspace-id>/items/<kql-database-item-id>/kqlEndpoint
```

Prefer the **MCP Server URI** copied from the selected KQL database's Overview
pane. Resolve/verify workspace and KQL database IDs first; do not substitute
the containing Eventhouse's ID or assume the database display name is its
data-plane database identifier. Validate the expected environment/tenant.

With approval, merge a server entry into the host's existing MCP configuration;
preserve unrelated entries. A VS Code example:

```json
{
  "servers": {
    "fabric-rca-eventhouse": {
      "type": "http",
      "url": "<verified-mcp-server-uri>",
      "headers": {
        "x-ms-fabric-skill": "fabric-job-failure-rca"
      }
    }
  }
}
```

Use the host's normal authentication flow and a credential authorized to query
the selected database. Do not copy tokens into configuration, request cookies,
or assume VS Code Azure/CLI sign-in automatically authenticates this server.
Restart/reload only as needed with user guidance, not automatically. A server
configuration file is not proof that the current chat exposes its tools.

Distinguish host integration from a protocol-level MCP smoke test. An authorized
test that performs MCP initialization, `tools/list`, and `tools/call` against
the native endpoint verifies that endpoint, not tool availability or sign-in in
the current chat. Ordinary Fabric/Kusto REST queries do not verify MCP. Use
protocol negotiation supported by the server/client; a rejected protocol version
is not, by itself, an authentication failure. Never copy host credential caches
or tokens to make a separate test work.

The global native endpoint is also documented:

```text
https://api.fabric.microsoft.com/v1/mcp/dataPlane/kqlEndpoint
```

It requires verified `workspaceId` and `itemId` in each tool call. Prefer the
item-scoped connection for RCA. Some tools expose alternate `clusterUrl` and
`databaseName` arguments; never use them to redirect an authorized item-scoped
investigation to an unapproved database or external cluster.

The native connector is preview. Schema discovery currently depends on Copilot
in Fabric being enabled; query execution may remain available without that
feature. Missing schema capability is not an empty schema. Do not enable
Copilot or change capacity/tenant settings automatically.

## Discover tools, then verify read access

1. Ask the host to discover the connected server's tools; inspect their real
   input schemas and descriptions. Do not invent native tool names or assume
   the native server has the same arguments as Fabric RTI or Azure MCP.
2. Confirm workspace/database scope and use least-privilege read access.
3. Use a metadata-only capability to list tables, then retrieve the schema
   of one relevant table. A dedicated schema tool can replace `.show table`
   when it returns equivalent verified columns/types.
4. Map actual event-time and correlation columns with the telemetry reference
   linked from the skill. Do not assume business tables are job telemetry.
5. Execute one narrow, authorized diagnostic KQL query with explicit UTC and
  item/run filters and `take 100` or a smaller cap. Prefer aggregate counts
   or a projection excluding sensitive payloads. Check query status and partial
   results, not just whether the MCP call returned successfully.
6. Record separately: configuration added, tool discovery succeeded, metadata
   read succeeded, and bounded correlation query succeeded. If a stage cannot
   run, report exactly that; do not label the integration fully tested.

Metadata-only reads are useful connection tests but are not proof that telemetry
exists or that job correlation works. A host tool can expose generic queries
that also accept management operations: review the operation, not its name.

## Connector-specific mapping

### Native remote Eventhouse MCP

A development trial discovered `executeQuery`, `getSchema`,
`getGeneralKQLExamples`, and `getSpecificKQLExamples`. These are observed names,
not a substitute for discovering the connected version's actual tools.

- `executeQuery` advertised required `kqlQuery` and `maxRecords` arguments.
  Its `maxRecords` limits returned records, not query execution. Apply time,
  identity, projection, and result bounds inside KQL as well.
- Omit alternate `clusterUrl`/`databaseName` for the verified item-scoped endpoint;
  the server resolves its bound database. A missing Fabric `databaseName` does
  not require guessing a name for this path.
- `getSchema` advertised cached, partial context including column samples,
  values, and statistics. It is not metadata-only. Do not use it as a safe
  schema-only read when those values could expose sensitive data. Prefer an
  authorized `.show tables` or `.show database schema` query with an explicit
  metadata projection through `executeQuery` when supported. This is metadata
  access, not proof that the Copilot-backed schema helper is available.
- Do not fetch user-specific query examples by default: they may contain
  customer literals and are unnecessary for basic connectivity.
- Query content may contain nested JSON `Tables`. Select the named
  `PrimaryResult`, or use the result-table mapping when supplied; do not assume
  the first table contains data. Metadata and data queries can use different
  envelopes. Inspect `isError`, JSON-RPC errors, query status/partial indicators,
  and completion information separately. Some responses expose completion
  row counts without a detailed status table: report that limitation instead
  of inventing a status or discarding a returned result as a failed query.

### Fabric RTI MCP

The official project documents `kusto_list_entities`,
`kusto_describe_database_entity`, and `kusto_query`. Use them only if actually
advertised by the connected version. `kusto_command` can mutate state:
permit only an explicitly reviewed metadata `.show` operation when a dedicated
read-only tool is unavailable. Do not invoke ingestion, Eventstream creation,
Activator creation, or other writes bundled in the same server.

### Azure MCP Kusto

Discover the Kusto router's schema first. Known read-only capabilities include:

- `kusto_table_list`: verified `cluster-uri` and `database`.
- `kusto_table_schema`: the same scope plus a discovered `table`.
- `kusto_query`: the same scope plus explicit read-only `query`.

The router may require `command` and a nested `parameters` object. Use the
actual discovered shape, not a copied tool call from another connector.
Use a verified Fabric query URI rather than subscription/ARM cluster discovery
to find a Fabric Eventhouse. Verify the actual data-plane database name; if
Fabric metadata omits it, use authorized database metadata discovery or ask.
Do not guess a database name from a display name.

Avoid generic sampling tools for RCA unless they can enforce incident-time,
identity, projection, and row-limit constraints. `sample 10` without a time
filter is not a bounded incident investigation.

## Read-only and output enforcement

- No `.create`, `.alter`, `.drop`, `.ingest`, `.set`, `.append`, `.export`,
  `.execute`, role assignments, management batches, or provisioning. Review
  indirect operations as well; an operator/tool named query does not guarantee
  no side effects. Do not invoke unknown stored functions or plugins whose
  effects or data destinations are unverified.
- Do not rely on an MCP tool annotation such as read-only as the only check.
  Validate actual KQL and explicit workspace/database scope before invocation.
- Respect the same finite request/time budgets and coverage rules as REST.
  Do not rerun all successful queries through a second transport for comparison.
- Raw MCP results may be displayed by the host before the assistant can redact
  them. Restrict projected fields at the query itself. Never request secrets,
  auth headers, raw payloads, or wide row samples and promise to redact later.
- Preserve server/query errors, sampling, ingestion delay, schema limitations,
  and truncation as evidence gaps. An empty MCP result is not proof of health.
- Keep server names, capability checks, and query recipes in requested technical
  details; ordinary reports should lead with findings and material coverage.

## Official references

- [Remote MCP server for eventhouses (preview)](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/mcp-remote-eventhouse)
- [Microsoft Fabric RTI MCP and available tools](https://github.com/microsoft/fabric-rti-mcp#available-tools)

Treat documentation examples as capability guidance, not proof that the current
host has a connected server, valid permissions, or useful customer telemetry.
