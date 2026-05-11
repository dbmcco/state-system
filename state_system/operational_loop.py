from __future__ import annotations

import json
from pathlib import Path

from state_system.contracts import JsonObject, load_json
from state_system.trace_runner import run_trace_manifest


def run_operational_loop(
    *,
    project_root: Path,
    manifest_path: Path,
    output_dir: Path,
) -> JsonObject:
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_dir = output_dir / "trace"
    report = run_trace_manifest(
        project_root=project_root,
        manifest_path=manifest_path,
        output_dir=trace_dir,
    )
    summary = _operator_summary(report)
    summary_path = output_dir / "operator-summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def _operator_summary(report: JsonObject) -> JsonObject:
    source_event = _step_payload(report, "trigger")
    review_packet = _step_payload(report, "review-packet")
    commit = _step_payload(report, "commit")
    recent_change = _step_payload(report, "recent-change")
    context_package = _step_payload(report, "laura-package")
    activation = _step_payload(report, "agent-activation")
    response = _step_payload(report, "agent-response")

    evidence_refs = sorted(
        {
            *source_event.get("evidence_context", {}).get("source_refs", []),
            *review_packet.get("evidence_packet", {}).get("evidence_refs", []),
            *activation.get("evidence_refs", []),
            *response.get("evidence_refs", []),
        }
    )

    summary = {
        "id": "operational_loop.southern-abrasives",
        "trace_id": report["trace_id"],
        "status": report["status"],
        "trace_report_path": str(Path(report["output_dir"]) / "trace-report.json"),
        "operator_report_path": str(Path(report["output_dir"]) / "index.html"),
        "source": {
            "source_event_id": source_event.get("source_event_id"),
            "trigger_id": source_event.get("trigger", {}).get("id"),
            "created": source_event.get("created"),
        },
        "review": {
            "packet_id": review_packet["id"],
            "allowed_outputs": review_packet.get("allowed_outputs", []),
            "unresolved_evidence_refs": review_packet.get(
                "evidence_packet",
                {},
            ).get("unresolved_evidence_refs", []),
        },
        "commit": {
            "id": commit["id"],
            "status": commit["status"],
            "accepted_journal_entry_refs": commit["accepted_journal_entry_refs"],
            "accepted_memory_entry_refs": commit["accepted_memory_entry_refs"],
            "pending_approvals": commit["pending_approvals"],
            "review_signal_id": commit["review_signal"]["id"],
        },
        "accepted_state_refs": commit["materialized_snapshot_refs"],
        "recent_change": {
            "id": recent_change["id"],
            "summary": recent_change["summary"],
            "persona_routes": recent_change["candidate_persona_routes"],
        },
        "working_model": {
            "context_package_id": context_package["id"],
            "persona_ref": context_package["persona_context"]["persona_ref"],
            "review_goal": context_package["review_goal"],
            "requires_refresh_before_external_action": context_package["freshness"][
                "requires_refresh_before_external_action"
            ],
            "valid_until": context_package["freshness"]["valid_until"],
        },
        "agent": {
            "activation_id": activation["id"],
            "response_id": response["id"],
            "response_record_type": "agent_response",
            "response_status": response["status"],
            "response_becomes_truth": activation["capture_policy"][
                "response_becomes_truth"
            ],
            "next_review_required": activation["capture_policy"][
                "next_review_required"
            ],
        },
        "evidence_refs": evidence_refs,
        "truth_boundary": (
            "Captured agent responses are artifacts and evidence. They do not "
            "become accepted state unless reviewed and committed later."
        ),
    }
    return summary


def _step_payload(report: JsonObject, name: str) -> JsonObject:
    for step in report["steps"]:
        if step["name"] == name and step["artifact_type"] == "json":
            return load_json(Path(step["artifact_path"]))
    raise OperationalLoopError(f"missing JSON step: {name}")


class OperationalLoopError(ValueError):
    pass
