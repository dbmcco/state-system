from __future__ import annotations

from pathlib import Path
import json

from state_system.agent_activation import (
    create_agent_activation,
    render_activation_for_agent,
)
from state_system.agent_consumers import capture_agent_response, render_package_for_agent
from state_system.contracts import load_json, validate_schema
from state_system.runtime import (
    build_recent_package,
    build_review_packet_from_source_event,
    commit_model_output,
    index_recent_change,
)
from state_system.reporting import write_trace_report_html
from state_system.runner import SourceEventIngestor
from state_system.stores import JsonObject, StateStoreBundle


SEED_COLLECTIONS = {
    "state": "state_objects",
    "memory": "memory",
    "recent": "recent_changes",
    "package": "context_packages",
    "commit": "commits",
    "source-event": "source_events",
    "agent-activation": "agent_activations",
}


def run_trace_manifest(
    *,
    project_root: Path,
    manifest_path: Path,
    output_dir: Path,
) -> JsonObject:
    output_dir.mkdir(parents=True, exist_ok=True)
    state_root = output_dir / "runtime"
    stores = StateStoreBundle(state_root)
    schemas = _runtime_schemas(project_root)
    manifest = load_json(manifest_path)

    manifest_errors = validate_schema(
        manifest,
        load_json(project_root / "schemas" / "trace-manifest.schema.json"),
    )
    if manifest_errors:
        raise TraceRunnerError(manifest_errors)

    steps: list[JsonObject] = []
    _seed_records(project_root, output_dir, stores, manifest, steps)

    step_number = 2
    source_event_created = None

    if "source_event" in manifest:
        source_event = load_json(project_root / manifest["source_event"]["path"])
        ingest_result = SourceEventIngestor(
            stores,
            schemas["source_event"],
        ).ingest(source_event)
        source_event_created = ingest_result.created
        _write_step(
            steps,
            output_dir,
            _numbered(step_number, "trigger"),
            {
                "created": ingest_result.created,
                "idempotency_key": ingest_result.idempotency_key,
                "source_event_id": ingest_result.source_event_id,
                "duplicate_of": ingest_result.duplicate_of,
                "duplicate_reason": ingest_result.duplicate_reason,
                "watermark_status": ingest_result.watermark_status,
                "trigger": ingest_result.trigger,
                "evidence_context": ingest_result.evidence_context,
            },
        )
        step_number += 1

    if "review" in manifest:
        review = manifest["review"]
        review_packet = build_review_packet_from_source_event(
            stores,
            schemas,
            source_event_id=review["source_event_id"],
            packet_id=review["packet_id"],
            created_at=review["created_at"],
            resolved_evidence=list(review["resolved_evidence"]),
            unresolved_evidence_refs=list(review.get("unresolved_evidence_refs", [])),
            persona=load_json(project_root / review["persona_path"]),
            governance_constraints=list(review["governance_constraints"]),
        )
        _write_step(
            steps,
            output_dir,
            _numbered(step_number, "review-packet"),
            review_packet,
        )
        step_number += 1

    commit_result = None
    if "commit" in manifest:
        commit = manifest["commit"]
        commit_result = commit_model_output(
            stores,
            schemas,
            model_output=load_json(project_root / commit["model_output_path"]),
            created_at=commit["created_at"],
            evidence_refs=list(commit["evidence_refs"]),
        )
        _check_commit_expectations(commit, commit_result)
        _write_step(steps, output_dir, _numbered(step_number, "commit"), commit_result)
        step_number += 1

        if commit_result["materialized_snapshot_refs"]:
            first_snapshot = commit_result["materialized_snapshot_refs"][0]
            updated_state = stores.state_objects.read(first_snapshot)
            _write_step(
                steps,
                output_dir,
                _numbered(step_number, "updated-state"),
                updated_state,
            )
        else:
            _write_step(
                steps,
                output_dir,
                _numbered(step_number, "commit-effects"),
                {
                    "commit_id": commit_result["id"],
                    "commit_status": commit_result["status"],
                    "materialized_snapshot_refs": [],
                    "pending_approvals": list(commit_result["pending_approvals"]),
                    "rejected_proposals": list(commit_result["rejected_proposals"]),
                },
            )
        step_number += 1

    context_package_id = None
    agent_activation_id = None
    if "recent_change" in manifest:
        recent = manifest["recent_change"]
        recent_change = index_recent_change(
            stores,
            schemas,
            source_event_id=recent["source_event_id"],
            commit_id=recent["commit_id"],
            created_at=recent["created_at"],
            summary=recent["summary"],
            routes=list(recent["routes"]),
            opportunity_class_hints=list(recent["opportunity_class_hints"]),
            watermark_refs=list(recent["watermark_refs"]),
            stale_after=recent["stale_after"],
            requires_refresh_before_external_action=recent[
                "requires_refresh_before_external_action"
            ],
        )
        _write_step(
            steps,
            output_dir,
            _numbered(step_number, "recent-change"),
            recent_change,
        )
        step_number += 1

    if "context_package" in manifest:
        package = manifest["context_package"]
        context_package = build_recent_package(
            stores,
            schemas,
            persona=load_json(project_root / package["persona_path"]),
            package_id=package["package_id"],
            created_at=package["created_at"],
            review_goal=package["review_goal"],
            valid_until=package["valid_until"],
        )
        context_package_id = context_package["id"]
        _write_step(
            steps,
            output_dir,
            _numbered(step_number, "maya-package"),
            context_package,
        )
        step_number += 1

    if "render_package" in manifest:
        render_package_id = manifest["render_package"]["package_id"]
        rendered = render_package_for_agent(stores.context_packages.read(render_package_id))
        render_path = output_dir / f"{_numbered(step_number, 'rendered-package')}.txt"
        render_path.write_text(rendered + "\n", encoding="utf-8")
        steps.append(_step("render-package", render_path, "text"))
        context_package_id = context_package_id or render_package_id
        step_number += 1

    if "agent_activation" in manifest:
        activation_spec = manifest["agent_activation"]
        activation = create_agent_activation(
            stores,
            schemas,
            package_id=activation_spec["package_id"],
            consumer_ref=activation_spec["consumer_ref"],
            created_at=activation_spec["created_at"],
            activation_goal=activation_spec["activation_goal"],
            expected_response_type=activation_spec["expected_response_type"],
            activation_id=activation_spec.get("activation_id"),
        )
        agent_activation_id = activation["id"]
        context_package_id = context_package_id or activation["package_id"]
        _write_step(
            steps,
            output_dir,
            _numbered(step_number, "agent-activation"),
            activation,
        )
        step_number += 1

    if "render_activation" in manifest:
        activation_id = (
            manifest["render_activation"].get("activation_id")
            or agent_activation_id
        )
        if activation_id is None:
            raise TraceRunnerError(["render_activation requires an activation id"])
        rendered = render_activation_for_agent(stores, activation_id)
        render_path = output_dir / f"{_numbered(step_number, 'rendered-activation')}.txt"
        render_path.write_text(rendered + "\n", encoding="utf-8")
        steps.append(_step("render-activation", render_path, "text"))
        step_number += 1

    agent_response_id = None
    if "capture_response" in manifest:
        response = manifest["capture_response"]
        response_activation_id = response.get("activation_id") or agent_activation_id
        response_record = capture_agent_response(
            stores,
            schemas,
            package_id=response["package_id"],
            consumer_ref=response["consumer_ref"],
            response_text=response["response_text"],
            created_at=response["created_at"],
            response_id=response.get("response_id"),
            activation_id=response_activation_id,
        )
        agent_response_id = response_record["id"]
        _write_step(
            steps,
            output_dir,
            _numbered(step_number, "agent-response"),
            response_record,
        )

    report: JsonObject = {
        "id": f"report.{manifest['id']}",
        "trace_id": manifest["id"],
        "title": manifest["title"],
        "status": "passed",
        "output_dir": str(output_dir),
        "state_root": str(state_root),
        "steps": steps,
        "validated": {
            "manifest": True,
            "source_event_created": source_event_created,
            "commit_status": commit_result["status"] if commit_result else None,
            "materialized_snapshot_count": (
                len(commit_result["materialized_snapshot_refs"])
                if commit_result
                else 0
            ),
            "pending_approval_count": (
                len(commit_result["pending_approvals"]) if commit_result else 0
            ),
            "context_package_id": context_package_id,
            "agent_activation_id": agent_activation_id,
            "agent_response_id": agent_response_id,
        },
    }
    report_path = output_dir / "trace-report.json"
    _write_json(report_path, report)
    write_trace_report_html(output_dir=output_dir, report=report)
    return report


class TraceRunnerError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("trace manifest validation failed")
        self.errors = tuple(errors)


def _seed_records(
    project_root: Path,
    output_dir: Path,
    stores: StateStoreBundle,
    manifest: JsonObject,
    steps: list[JsonObject],
) -> None:
    seeded: list[JsonObject] = []
    for seed in manifest["seed_records"]:
        collection = seed["collection"]
        store = getattr(stores, SEED_COLLECTIONS[collection])
        record = load_json(project_root / seed["path"])
        store.create(record)
        seeded.append(
            {
                "collection": collection,
                "path": seed["path"],
                "record_id": record["id"],
            }
        )
    path = output_dir / "01-seed-records.json"
    _write_json(path, {"records": seeded})
    steps.append(
        {
            "name": "seed-records",
            "status": "passed",
            "artifact_type": "json",
            "artifact_path": str(path),
            "record_count": len(seeded),
        }
    )


def _write_step(
    steps: list[JsonObject],
    output_dir: Path,
    stem: str,
    payload: JsonObject,
) -> None:
    path = output_dir / f"{stem}.json"
    _write_json(path, payload)
    steps.append(_step(stem.split("-", 1)[1], path, "json", payload.get("id")))


def _step(
    name: str,
    path: Path,
    artifact_type: str,
    record_id: str | None = None,
) -> JsonObject:
    step: JsonObject = {
        "name": name,
        "status": "passed",
        "artifact_type": artifact_type,
        "artifact_path": str(path),
    }
    if record_id:
        step["record_id"] = record_id
    return step


def _write_json(path: Path, payload: JsonObject) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _check_commit_expectations(expectations: JsonObject, commit_result: JsonObject) -> None:
    expected_status = expectations.get("expected_status")
    if expected_status and commit_result["status"] != expected_status:
        raise TraceRunnerError(
            [f"commit status {commit_result['status']} != expected {expected_status}"]
        )

    expected_snapshots = expectations.get("expected_materialized_snapshot_count")
    if (
        expected_snapshots is not None
        and len(commit_result["materialized_snapshot_refs"]) != expected_snapshots
    ):
        raise TraceRunnerError(
            [
                "materialized snapshot count "
                f"{len(commit_result['materialized_snapshot_refs'])} != "
                f"expected {expected_snapshots}"
            ]
        )

    expected_pending = expectations.get("expected_pending_approval_count")
    if expected_pending is not None and len(commit_result["pending_approvals"]) != expected_pending:
        raise TraceRunnerError(
            [
                "pending approval count "
                f"{len(commit_result['pending_approvals'])} != expected {expected_pending}"
            ]
        )


def _numbered(step_number: int, name: str) -> str:
    return f"{step_number:02d}-{name}"


def _runtime_schemas(project_root: Path) -> dict[str, JsonObject]:
    return {
        "source_event": load_json(
            project_root / "schemas" / "source-event.schema.json"
        ),
        "review_packet": load_json(
            project_root / "schemas" / "model-review-packet.schema.json"
        ),
        "model_output": load_json(
            project_root / "schemas" / "model-proposal-output.schema.json"
        ),
        "journal": load_json(
            project_root / "schemas" / "state-journal-entry.schema.json"
        ),
        "memory": load_json(project_root / "schemas" / "agent-memory-entry.schema.json"),
        "state": load_json(project_root / "schemas" / "state-object.schema.json"),
        "commit": load_json(project_root / "schemas" / "commit-result.schema.json"),
        "review_signal": load_json(
            project_root / "schemas" / "review-signal.schema.json"
        ),
        "recent_change": load_json(
            project_root / "schemas" / "recent-change-entry.schema.json"
        ),
        "context_package": load_json(
            project_root / "schemas" / "context-package.schema.json"
        ),
        "agent_response": load_json(
            project_root / "schemas" / "agent-response.schema.json"
        ),
        "agent_activation": load_json(
            project_root / "schemas" / "agent-activation.schema.json"
        ),
    }
