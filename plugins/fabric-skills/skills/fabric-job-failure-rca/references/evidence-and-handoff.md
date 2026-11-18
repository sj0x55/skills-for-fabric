# Evidence checklist and escalation handoff

Apply the [mandatory guardrails](./guardrails.md), including approval scope,
safe-path checks and create-only persistence. Approval for a prior incident
does not authorize a new incident, expanded contents or a different destination.

Use this checklist during each selected-run investigation. Keep detailed state
in investigation context; show only the material gap in the compact report.
An HTTP success, a tool result, and an established failure mechanism are
different milestones.

## Evidence completion checklist

| Stage | Completion criterion | Record |
|---|---|---|
| Run verified | The requested item/run/attempt, unsuccessful status and UTC interval are established by an identified source | Exact identity, source/evidence ID, collection time |
| Failing component identified | An activity/entity/statement/task/table/partition or failed session is explicitly linked to that run's outcome | Component and parent/child/attempt mapping, not an unrelated nearby error |
| Mechanism established | A specific run-linked exception or error explains how the component failed | Minimal sanitized error, evidence ID, Confirmed/Probable/Undetermined classification |
| Deeper trigger assessed | Supporting and competing explanations have been checked to the available evidence limit | Known trigger with evidence, or an explicit unknown and smallest missing check |

For each stage, record `verified`, `partial`, `blocked`, `unknown`, or
`not_applicable`, with evidence references and a short reason. A verified
assessment can conclude the deeper trigger is unknown; it does not turn that
trigger into a confirmed cause. Use `not_applicable` only with a workload-specific
reason, not to conceal missing access. Do not fill a stage from a generic wrapper.
Supplied evidence is valid when its source/identity limits remain visible.

Keep mechanism and trigger classifications separate. For example, driver
stdout can confirm an executor OOM while skew remains an unverified trigger.
A diagnostic 403 verifies an access gap, not a job-side authorization failure.
An empty advisor response is not a completed mechanism diagnosis.

Before finalizing:

1. Check the selected run and every causal citation against the evidence ledger.
2. Account for each applicable API tier using the diagnostic coverage reference.
3. Check whether other failed executions are linked consequences, unrelated
   failures, or only a suspected common-cause cluster.
4. Confirm all material gaps and any partial results remain in the report.
5. Record diagnostic reads only; distinguish recommendations from actions taken.

Never require every stage to be verified to finish a useful preliminary report.
Stop when evidence is exhausted within the approved scope/budget or the user
declines more evidence; do not repeat requests for unavailable logs.

## Optional escalation handoff

Offer a compact handoff when the cause is unresolved or support escalation is
useful. Do not create a support case, publish an issue, upload files, or save a
bundle automatically. Showing a draft in chat does not authorize persistence.
Before saving, obtain explicit approval for the **destination and contents**;
reuse an unambiguous existing approval rather than asking again. A request for
this skill feature is not approval to save current customer incident evidence.

### Handoff content contract

Use this shape for an approved JSON bundle, or the equivalent concise report:

```json
{
  "schema_version": 1,
  "summary": "<observed outcome and classification>",
  "scope": {
    "environment": "<verified service environment>",
    "workspace_id": "<workspace>",
    "item_id": "<item>",
    "item_type": "<returned type>",
    "run_id": "<run>",
    "attempt": null,
    "start_utc": "<verified timestamp or null>",
    "end_utc": "<verified timestamp or null>"
  },
  "job_correlation": {},
  "diagnostic_requests": [],
  "checklist": {},
  "findings": [],
  "evidence": [],
  "reads_attempted": [],
  "missing_evidence": [],
  "next_check": "<smallest discriminating check>",
  "actions_taken": "Diagnostic reads only; no jobs rerun or resources changed."
}
```

- Preserve unknown fields as `null` with an explanation; do not invent IDs,
  versions, owners, timestamps, impact, or activity mappings.
- Give each evidence entry an ID, source operation, retrieval time, exact
  relevant run/attempt identity, and a minimal sanitized observation.
- Record each attempted diagnostic operation, its bounded UTC range/filters
  where relevant, result, and coverage limit. Query recipes must be reproducible
  but exclude credentials, customer row payloads, sensitive literals and signed
  URLs. Prefer placeholders for unrelated resource names.
- Separate job-side correlation identifiers from diagnostic request IDs;
  preserve child links and explain which identity each refers to.
- State the confirmed mechanism and the unverified deeper trigger separately.
  Include contradictory evidence and remaining alternatives where material.
- List denied, expired, unsupported, unavailable, partial, skipped and untested
  evidence explicitly. Do not describe untried APIs as exhausted.
- Include relevant observed versions only when collected and useful.

### Pre-save review

Inspect the rendered bundle before writing. Remove tokens, cookies, passwords,
connection strings, Authorization headers, SAS signatures, personal identifiers,
raw query text/data and unnecessary logs. Review URLs and nested error/context
fields, not just obvious secret keys. If sanitization cannot be established,
omit the field and record that evidence was withheld.

Save only to the approved customer-side location, never this public skills
repository or a public issue. Preserve an existing file unless the user approved
replacement; confirm persistence after writing. Report the actual saved path.
A saved bundle is not uploaded or submitted to support without separate approval.
