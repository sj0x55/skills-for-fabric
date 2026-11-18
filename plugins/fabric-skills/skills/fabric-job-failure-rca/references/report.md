# RCA report contract

Apply the [mandatory guardrails](./guardrails.md) before presenting or saving
findings; include material blocked-gate and budget limitations in coverage.

Use progressive disclosure and the skill's customer-facing presentation rules.
Default to the compact report below; the full technical sections are available
on request or when a specific detail is necessary to explain a finding.
Maintain the evidence ledger during investigation without dumping it into chat.
Use "Unknown", "Not available", or "Not applicable" with an explanation where
appropriate. Never invent facts or hide material evidence gaps.

## Default customer report

1. **Bottom line**: identify the item, failure time/timezone, observed outcome,
   confirmed failure mechanism if known, and what remains uncertain. Keep
   this to two or three sentences; do not lead with UUIDs or backend mechanics.
2. **Key findings**: one compact table if useful:

   | Finding | Evidence / confidence | Recommended action |
   |---|---|---|

   Use Confirmed, Probable, or Undetermined, not unsupported severity labels.
   Cite the failed run or a short sanitized source reference inline.
3. **Next actions**: at most three priorities, giving the owner when known and
   a concrete verification criterion. Distinguish a recommendation from a fix
   actually executed. Do not repeat the entire table in prose.
4. **Coverage**: a brief note about evidence freshness/mode, inaccessible
   sources, sampled evidence, or unresolved cause. Say "Diagnostic reads only;
   no jobs rerun or resources changed."

For API coverage questions, distinguish a documented endpoint, an available
connector, an authorized successful read, and an error payload that actually
explains this run. Do not call a documentation audit a live test. When blocked,
name the missing evidence tier (run envelope, activity/attempt detail, inner
error/log, or correlated resource signal), not just "no logs".
Use the evidence completion checklist linked from the skill. In the compact
report, state the highest supported stage and material gap, for example
"Mechanism confirmed; deeper trigger unknown." Do not print a checklist
transcript unless requested or needed to explain a blocker.

Include a verified run/monitor link where available. Include only the minimal
sanitized error phrase needed to make the conclusion understandable, not the
full traceback. Preserve any critical idempotency warning in the default report.

## Technical details on request

Expand the sections below when requested; include only the relevant sections
for a focused follow-up. Share observed facts and evidence-based rationale,
not private internal reasoning or a deliberation transcript. Save a sanitized
report only when requested and only in an approved customer location, not this
public skills repository.

### 1. Incident summary

- Workspace/item/type, job/run/attempt, parent/child identifiers where relevant.
- Observed status, UTC failure interval, original timezone, and collection time.
- Reported or measured business impact, distinguished from unverified impact.
- Evidence mode: live, supplied logs, or mixed; optional Eventhouse coverage.
- Overall conclusion: Confirmed, Probable, or Undetermined.

### 2. UTC timeline

| UTC time | Run/activity/attempt | Event | Evidence ID |
|---|---|---|---|

Separate observed event times from inferred ordering and ingestion times.
Represent parallel branches and retries without treating every earlier event
as an upstream cause.

### 3. Evidence ledger

| ID | Source / retrieval time | Run or correlation mapping | Sanitized observation | Limits |
|---|---|---|---|---|

Use stable evidence IDs. Include accessible source references or a reproducible
query recipe and UTC window; do not publish access tokens, signed URLs, raw
customer payloads, or entire log archives. Identify partial/truncated results.

### 4. Causal analysis

| Claim or hypothesis | Classification | Supporting evidence | Contradictions / missing link |
|---|---|---|---|

Explain the dependency chain from the failing component to the reported outcome.
Distinguish failure mechanism, deeper trigger, contributing factors, and
downstream symptoms. Every causal claim must cite evidence IDs. Do not call
a hypothesis confirmed because it matches a common troubleshooting pattern.

### 5. Recommendations and verification

| Priority | Recommended action | Evidence / rationale | Suggested owner | Risk / prerequisite | Verification criterion |
|---|---|---|---|---|---|

Separate immediate mitigation, durable fix, and recurrence prevention.
Describe concrete checks: for example, after an authorized change, the same
workload/parameters complete without the observed error and relevant resource
metrics remain within the measured limit over an agreed observation period.
Do not prescribe arbitrary capacity increases or blind retries without evidence.
Note idempotency and duplicate-write risks before recommending a rerun.

**Actions executed:** diagnostic reads only. No jobs rerun, resources changed,
permissions elevated, or telemetry provisioned.

### 6. Evidence gaps and escalation

List inaccessible sources and collection errors, unsupported APIs, missing
parent/child mappings, retention limits, telemetry delay/sampling, clock/timezone
uncertainty, and unresolved alternatives.

Before saying diagnostic APIs are exhausted, account for each applicable
documented surface in the diagnostic API coverage reference linked from the
skill: used, denied, expired, unsupported for this run type, unavailable in the
host, skipped by user constraint/budget, or not yet tested. A generic wrapper
alone is not evidence that no deeper API exists. An endpoint not identified
in the reviewed public documentation is not proof that the service has no
internal capability.

For an unresolved incident, specify the smallest next evidence request.
An escalation bundle should include sanitized workspace/item/run identifiers,
UTC interval, job-side correlation IDs, diagnostic request IDs labeled separately,
exact redacted errors, relevant versions, evidence references, and steps already
checked. Keep it in an approved support channel; do not attach customer evidence
to a public contribution or issue.

Use the evidence/handoff reference linked from the skill for the concrete bundle
shape and pre-save review. Drafting a report does not authorize saving it.
Obtain approval for destination and contents before persistence; saving does
not authorize uploading or submitting a support case. Do not overwrite an
existing file without permission.

When technical detail is requested, include the four-stage completion table:

| Stage | Status | Evidence / remaining gap |
|---|---|---|
| Run verified | verified / partial / blocked / unknown / not_applicable | Actual source and identity/timing limit |
| Failing component identified | same status vocabulary | Actual parent/component mapping |
| Mechanism established | same status vocabulary | Specific error or missing inner detail |
| Deeper trigger assessed | same status vocabulary | Supported trigger or explicit unknown |

Keep mechanism and trigger classifications alongside this table. A completed
assessment with an unknown trigger is not a confirmed root cause.
