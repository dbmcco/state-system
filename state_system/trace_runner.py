from __future__ import annotations

from pathlib import Path
import json

from state_system.agent_consumers import capture_agent_response, render_package_for_agent
from state_system.contracts import load_json, validate_schema
from state_system.runtime import (
    build_recent_package,
    build_review_packet_from_source_event,
    commit_model_output,
    index_recent_change,
)
from state_system.runner import SourceEventIngestor
from state_system.stores import JsonObject, StateStoreBundle


SEED_COLLECTIONS = {
    "state": "state_objects",
    "memory": "memory",
    "recent": "recent_changes",
    "package": "context_packages",
    "commit": "commits",
    "source-event": "source_events",
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

    source_event = load_json(project_root / manifest["source_event"]["path"])
    ingest_result = SourceEventIngestor(
        stores,
        schemas["source_event"],
    ).ingest(source_event)
    _write_step(
        steps,
        output_dir,
        "02-trigger",
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
    _write_step(steps, output_dir, "03-review-packet", review_packet)

    commit = manifest["commit"]
    commit_result = commit_model_output(
        stores,
        schemas,
        model_output=load_json(project_root / commit["model_output_path"]),
        created_at=commit["created_at"],
        evidence_refs=list(commit["evidence_refs"]),
    )
    _write_step(steps, output_dir, "04-commit", commit_result)

    first_snapshot = commit_result["materialized_snapshot_refs"][0]
    updated_state = stores.state_objects.read(first_snapshot)
    _write_step(steps, output_dir, "05-updated-state", updated_state)

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
    _write_step(steps, output_dir, "06-recent-change", recent_change)

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
    _write_step(steps, output_dir, "07-laura-package", context_package)

    rendered = render_package_for_agent(
        stores.context_packages.read(manifest["render_package"]["package_id"])
    )
    render_path = output_dir / "08-rendered-package.txt"
    render_path.write_text(rendered + "\n", encoding="utf-8")
    steps.append(_step("render-package", render_path, "text"))

    response = manifest["capture_response"]
    response_record = capture_agent_response(
        stores,
        schemas,
        package_id=response["package_id"],
        consumer_ref=response["consumer_ref"],
        response_text=response["response_text"],
        created_at=response["created_at"],
        response_id=response.get("response_id"),
    )
    _write_step(steps, output_dir, "09-agent-response", response_record)

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
            "source_event_created": ingest_result.created,
            "commit_status": commit_result["status"],
            "context_package_id": context_package["id"],
            "agent_response_id": response_record["id"],
        },
    }
    report_path = output_dir / "trace-report.json"
    _write_json(report_path, report)
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
    }
