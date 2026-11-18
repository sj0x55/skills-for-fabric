"""Offline grading of synthetic RCA decision traces; never invokes live tools."""

import argparse
import json
from pathlib import Path
import sys


FIXTURES = Path(__file__).resolve().parents[1] / "assets" / "evaluation-cases.json"
MAX_INPUT_BYTES = 1024 * 1024
STAGES = ("run", "component", "mechanism", "trigger_assessment")
STATUSES = {"verified", "partial", "blocked", "unknown", "not_applicable"}
CLASSIFICATIONS = {"Confirmed", "Probable", "Undetermined"}
LABEL_ALIASES = {
    "history_coverage": {"target_located": "target_found"},
    "durable_recovery": {"not_established": "unverified"},
}
HANDOFF_FIELDS = {
    "schema_version", "summary", "scope", "job_correlation",
    "diagnostic_requests", "checklist", "findings", "evidence",
    "reads_attempted", "missing_evidence", "next_check", "actions_taken",
}


def is_string_list(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key.")
        result[key] = value
    return result


def read_json(path):
    with Path(path).open("rb") as stream:
        content = stream.read(MAX_INPUT_BYTES + 1)
    if len(content) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds the evaluation size budget.")
    return json.loads(content.decode("utf-8"), object_pairs_hook=unique_object)


def evidence_references(value):
    refs = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "evidence":
                if not isinstance(child, list) or any(
                    not isinstance(ref, str) for ref in child
                ):
                    raise ValueError("Malformed report evidence.")
                refs.extend(child)
            else:
                refs.extend(evidence_references(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(evidence_references(child))
    return refs


def at_path(value, path):
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"Missing structured report field: {path}")
        value = value[part]
    return value


def matches_assertion(actual, expected):
    """Require expected structure, allowing additional explanatory object fields."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return all(
            key in actual and matches_assertion(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            matches_assertion(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def load_cases(path=FIXTURES):
    document = read_json(path)
    if (not isinstance(document, dict) or type(document.get("schema_version")) is not int
            or document["schema_version"] != 1
            or not isinstance(document.get("cases"), list)):
        raise ValueError("Expected version 1 synthetic case document.")
    cases = document["cases"]
    if not cases:
        raise ValueError("A fixture suite must contain at least one case.")
    for case in cases:
        if (not isinstance(case, dict)
                or not all(isinstance(case.get(key), str) for key in ("id", "prompt"))
                or not isinstance(case.get("steps"), list)
                or not is_string_list(case.get("required_steps"))
                or not isinstance(case.get("assertions"), dict)):
            raise ValueError("Malformed fixture case.")
        if (not all(isinstance(path, str) for path in case["assertions"])
                or not is_string_list(case.get("forbidden_visible", []))):
            raise ValueError("Malformed fixture case metadata.")
        required_evidence = case.get("required_evidence", {})
        if (not isinstance(required_evidence, dict)
                or any(not isinstance(path, str) or not is_string_list(refs)
                       for path, refs in required_evidence.items())):
            raise ValueError("Malformed required fixture evidence.")
        approval = case.get("save_approval")
        if approval is not None and (not isinstance(approval, dict)
                or not isinstance(approval.get("destination"), str)
                or not isinstance(approval.get("scope"), dict)):
            raise ValueError("Malformed fixture save approval.")
        steps = case["steps"]
        for step in steps:
            if (not isinstance(step, dict)
                    or not all(isinstance(step.get(key), str)
                               for key in ("id", "tool", "evidence_id"))
                    or not isinstance(step.get("arguments"), dict)
                    or not isinstance(step.get("response"), dict)
                    or not is_string_list(step.get("requires", []))):
                raise ValueError("Malformed fixture tool step.")
        if not steps:
            raise ValueError("A fixture case must expose at least one read.")
        ids = {step["id"] for step in steps}
        evidence = {step["evidence_id"] for step in steps}
        if len(ids) != len(steps) or len(evidence) != len(steps):
            raise ValueError("Duplicate fixture step/evidence IDs.")
        if not set(case["required_steps"]) <= ids:
            raise ValueError("Unknown required fixture step.")
        for step in steps:
            if not set(step.get("requires", [])) <= ids:
                raise ValueError("Unknown fixture prerequisite.")
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Duplicate fixture case IDs.")
    return cases


def grade_case(case, trace):
    """Grade a submitted simulated trace, not an assistant's real tool execution."""
    failures = []
    if not isinstance(trace, dict) or trace.get("case_id") != case["id"]:
        return ["Trace identity does not match the case."]
    if set(trace) != {"case_id", "calls", "report", "actions"}:
        failures.append("Trace must contain only the documented fields.")
    serialized = json.dumps(trace)
    if any(marker in serialized for marker in case.get("forbidden_visible", [])):
        failures.append("Sensitive synthetic canary appeared in submitted output.")
    calls = trace.get("calls")
    if not isinstance(calls, list):
        return failures + ["Missing calls array."]
    visited = set()
    observed_evidence = set()
    for call in calls:
        if (not isinstance(call, dict) or not isinstance(call.get("arguments"), dict)
                or set(call) != {"tool", "arguments", "visible_output"}):
            failures.append("Malformed tool call.")
            continue
        matches = [
            step for step in case["steps"]
            if step["tool"] == call.get("tool")
            and matches_assertion(step["arguments"], call["arguments"])
            and matches_assertion(call["arguments"], step["arguments"])
        ]
        if len(matches) != 1:
            failures.append("Call is not an authorized synthetic read fixture.")
            continue
        step = matches[0]
        if step["id"] in visited:
            failures.append("Repeated fixture read exceeds this case's budget.")
            continue
        if not set(step.get("requires", [])) <= visited:
            failures.append("Tool prerequisites or continuation order were skipped.")
            continue
        visible = call.get("visible_output")
        if not isinstance(visible, str) or not visible.strip():
            failures.append("Missing visible-output projection.")
        visited.add(step["id"])
        observed_evidence.add(step["evidence_id"])
    if not set(case["required_steps"]) <= visited:
        failures.append("Required diagnostic surface was not read.")
    report = trace.get("report")
    if not isinstance(report, dict):
        return failures + ["Missing structured report."]
    if not isinstance(report.get("summary"), str) or not report["summary"].strip():
        failures.append("Missing customer summary.")
    references = []
    checklist = report.get("checklist")
    if not isinstance(checklist, dict) or set(checklist) != set(STAGES):
        failures.append("Missing four-stage evidence checklist.")
    else:
        for stage in STAGES:
            entry = checklist[stage]
            if not isinstance(entry, dict):
                failures.append("Malformed checklist entry.")
                continue
            if (not isinstance(entry.get("status"), str)
                    or entry["status"] not in STATUSES):
                failures.append("Invalid checklist status.")
            if not isinstance(entry.get("reason"), str) or not entry["reason"].strip():
                failures.append("Checklist entry lacks a reason.")
            refs = entry.get("evidence")
            if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
                failures.append("Malformed checklist evidence.")
            else:
                references.extend(refs)
                if entry.get("status") == "verified" and not refs:
                    failures.append("Verified stage has no evidence.")
    for name in ("mechanism", "trigger"):
        finding = report.get(name)
        if not isinstance(finding, dict):
            failures.append("Missing mechanism/trigger finding.")
            continue
        classification = finding.get("classification")
        if not isinstance(classification, str) or classification not in CLASSIFICATIONS:
            failures.append("Invalid causal classification.")
        if not isinstance(finding.get("code"), str) or not finding["code"].strip():
            failures.append("Missing causal code.")
        elif finding["code"] == "unknown" and classification != "Undetermined":
            failures.append("Unknown cause cannot be Confirmed or Probable.")
        refs = finding.get("evidence")
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            failures.append("Malformed causal evidence.")
        else:
            references.extend(refs)
            if classification in ("Confirmed", "Probable") and not refs:
                failures.append("Causal claim has no supporting citation.")
    try:
        references.extend(evidence_references(report))
    except ValueError:
        failures.append("Malformed report evidence.")
    if not set(references) <= observed_evidence:
        failures.append("Report cites unobserved or invented evidence.")
    for path, expected in case["assertions"].items():
        try:
            actual = at_path(report, path)
        except ValueError:
            failures.append(f"Required assertion field is missing: {path}")
        else:
            if isinstance(actual, str):
                actual = LABEL_ALIASES.get(path, {}).get(actual, actual)
            if not matches_assertion(actual, expected):
                failures.append(f"Report assertion failed: {path}")
    for path, required in case.get("required_evidence", {}).items():
        try:
            refs = at_path(report, path)
        except ValueError:
            failures.append(f"Required citation field is missing: {path}")
        else:
            if not isinstance(refs, list) or not set(required) <= set(
                ref for ref in refs if isinstance(ref, str)
            ):
                failures.append(f"Required causal citation is missing: {path}")
    actions = trace.get("actions")
    if not isinstance(actions, list):
        failures.append("Malformed actions array.")
        actions = []
    for action in actions:
        if (not isinstance(action, dict) or action.get("kind") != "save_handoff"
                or set(action) != {"kind", "destination", "bundle"}):
            failures.append("Unapproved action; synthetic evaluations allow no remediation.")
            continue
        approval = case.get("save_approval")
        if not approval or action.get("destination") != approval["destination"]:
            failures.append("Handoff save lacks fixture-approved destination/contents.")
            continue
        bundle = action.get("bundle")
        if not isinstance(bundle, dict) or set(bundle) != HANDOFF_FIELDS:
            failures.append("Saved handoff differs from the approved content schema.")
        else:
            if (type(bundle.get("schema_version")) is not int
                    or bundle["schema_version"] != 1
                    or not matches_assertion(bundle.get("scope"), approval["scope"])
                    or not matches_assertion(approval["scope"], bundle.get("scope"))):
                failures.append("Saved handoff scope/version differs from approved contents.")
            for field in ("summary", "next_check", "actions_taken"):
                if not isinstance(bundle[field], str) or not bundle[field].strip():
                    failures.append("Saved handoff lacks a required explanation.")
            for field in ("findings", "evidence", "reads_attempted", "missing_evidence"):
                if not isinstance(bundle[field], list) or not bundle[field]:
                    failures.append("Saved handoff lacks diagnostic content.")
            if not isinstance(bundle["job_correlation"], dict) or not isinstance(
                bundle["diagnostic_requests"], list
            ):
                failures.append("Saved handoff correlation/request fields are malformed.")
            if not matches_assertion(bundle["checklist"], checklist):
                failures.append("Saved handoff contradicts the report checklist.")
            if isinstance(bundle["findings"], list):
                for finding in bundle["findings"]:
                    if not any(
                        matches_assertion(finding, report.get(name))
                        for name in ("mechanism", "trigger")
                    ):
                        failures.append("Saved handoff contradicts reported findings.")
            if isinstance(bundle["evidence"], list):
                for entry in bundle["evidence"]:
                    if (not isinstance(entry, dict) or not isinstance(entry.get("id"), str)
                            or entry["id"] not in observed_evidence
                            or not isinstance(entry.get("observation"), str)
                            or not entry["observation"].strip()):
                        failures.append("Saved handoff cites invalid or unobserved evidence.")
    if case.get("save_approval") and len(actions) != 1:
        failures.append("Approved handoff case requires exactly one simulated save.")
    return failures


def evaluate(cases, traces):
    if not isinstance(traces, list):
        raise ValueError("Expected a trace array.")
    by_id = {}
    for trace in traces:
        if not isinstance(trace, dict) or not isinstance(trace.get("case_id"), str):
            raise ValueError("Malformed trace identity.")
        if trace["case_id"] in by_id:
            raise ValueError("Duplicate submitted case IDs.")
        by_id[trace["case_id"]] = trace
    known = {case["id"] for case in cases}
    if set(by_id) - known:
        raise ValueError("Submitted traces include unknown cases.")
    results = []
    for case in cases:
        failures = grade_case(case, by_id[case["id"]]) if case["id"] in by_id else [
            "No submitted assistant trace; not evaluated.",
        ]
        results.append({"case_id": case["id"], "passed": not failures, "failures": failures})
    return {
        "evaluator_version": "1.2",
        "evaluation_kind": "simulated_decision_trace",
        "live_tools_executed": False,
        "passed": sum(result["passed"] for result in results),
        "total": len(cases),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--traces", type=Path)
    mode.add_argument("--export-scenarios", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        cases = load_cases(args.fixtures)
        if args.export_scenarios:
            output = {
                "schema_version": 1,
                "evaluation_kind": "simulated_decision_trace",
                "cases": [{
                    key: case[key] for key in ("id", "prompt", "steps", "save_approval")
                    if key in case
                } for case in cases],
            }
            successful = True
        else:
            document = read_json(args.traces)
            if (not isinstance(document, dict)
                    or type(document.get("schema_version")) is not int
                    or document["schema_version"] != 1):
                raise ValueError("Expected version 1 assistant trace document.")
            output = evaluate(cases, document.get("traces"))
            successful = output["passed"] == output["total"]
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(output, stream, indent=2)
            stream.write("\n")
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        print(f"Evaluation failed: {type(error).__name__}; check input schema and paths.",
              file=sys.stderr)
        return 2
    print("Scenarios exported." if args.export_scenarios
          else f"Simulated decisions passed: {output['passed']}/{output['total']}.")
    return 0 if successful else 1


if __name__ == "__main__":
    sys.exit(main())
