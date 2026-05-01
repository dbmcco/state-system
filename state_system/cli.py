from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import TextIO

from state_system.contracts import load_json, validate_all_examples
from state_system.runtime import (
    build_recent_package,
    build_review_packet_from_source_event,
    commit_model_output,
    index_recent_change,
)
from state_system.runner import SourceEventIngestor
from state_system.source_adapters import git_commit_to_source_event
from state_system.stores import JsonObject, StateStoreBundle


COLLECTIONS = {
    "state": "state_objects",
    "source-event": "source_events",
    "review-packet": "review_packets",
    "journal": "journals",
    "memory": "memory",
    "rollup": "rollups",
    "review-signal": "review_signals",
    "commit": "commits",
    "recent": "recent_changes",
    "package": "context_packages",
}


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    stdout = stdout or sys.stdout
    parser = _parser()
    args = parser.parse_args(argv)
    project_root = Path(args.project_root)
    state_root = Path(args.state_root or args.project_root)
    stores = StateStoreBundle(state_root)

    if args.command == "validate":
        results = validate_all_examples(project_root)
        failures = [result for result in results if not result.ok]
        _write_json(
            stdout,
            {
                "ok": not failures,
                "validated_examples": len(results),
                "failures": [
                    {
                        "path": str(result.path),
                        "schema": result.schema,
                        "errors": list(result.errors),
                    }
                    for result in failures
                ],
            },
        )
        return 0 if not failures else 1

    if args.command == "trigger":
        source_event = load_json(Path(args.source_event))
        schema = load_json(project_root / "schemas" / "source-event.schema.json")
        result = SourceEventIngestor(stores, schema).ingest(source_event)
        _write_json(
            stdout,
            {
                "created": result.created,
                "idempotency_key": result.idempotency_key,
                "source_event_id": result.source_event_id,
                "duplicate_of": result.duplicate_of,
                "duplicate_reason": result.duplicate_reason,
                "watermark_status": result.watermark_status,
                "trigger": result.trigger,
                "evidence_context": result.evidence_context,
            },
        )
        return 0

    if args.command == "git-commit-event":
        event = git_commit_to_source_event(
            load_json(Path(args.commit_metadata)),
            repo_ref=args.repo_ref,
            observed_at=args.observed_at,
            candidate_state_refs=list(args.candidate_state_ref or []),
            governance_refs=list(args.governance_ref or []),
        )
        payload: JsonObject = {"source_event": event}
        if args.ingest:
            schema = load_json(project_root / "schemas" / "source-event.schema.json")
            result = SourceEventIngestor(stores, schema).ingest(event)
            payload["ingested"] = {
                "created": result.created,
                "idempotency_key": result.idempotency_key,
                "source_event_id": result.source_event_id,
                "duplicate_of": result.duplicate_of,
                "duplicate_reason": result.duplicate_reason,
                "watermark_status": result.watermark_status,
                "trigger": result.trigger,
                "evidence_context": result.evidence_context,
            }
        _write_json(stdout, payload)
        return 0

    if args.command == "review":
        packet = build_review_packet_from_source_event(
            stores,
            _runtime_schemas(project_root),
            source_event_id=args.source_event_id,
            packet_id=args.packet_id,
            created_at=args.created_at,
            resolved_evidence=_load_list(args.resolved_evidence),
            unresolved_evidence_refs=list(args.unresolved_evidence_ref or []),
            persona=load_json(Path(args.persona)),
            governance_constraints=_load_list(args.governance_constraints),
        )
        _write_json(stdout, packet)
        return 0

    if args.command == "commit":
        result = commit_model_output(
            stores,
            _runtime_schemas(project_root),
            model_output=load_json(Path(args.model_output)),
            created_at=args.created_at,
            evidence_refs=list(args.evidence_ref or []),
        )
        _write_json(stdout, result)
        return 0

    if args.command == "index-recent":
        entry = index_recent_change(
            stores,
            _runtime_schemas(project_root),
            source_event_id=args.source_event_id,
            commit_id=args.commit_id,
            created_at=args.created_at,
            summary=args.summary,
            routes=_load_list(args.routes),
            opportunity_class_hints=list(args.opportunity_class_hint or []),
            watermark_refs=list(args.watermark_ref or []),
            stale_after=args.stale_after,
            requires_refresh_before_external_action=(
                args.requires_refresh_before_external_action
            ),
        )
        _write_json(stdout, entry)
        return 0

    if args.command == "build-package":
        package = build_recent_package(
            stores,
            _runtime_schemas(project_root),
            persona=load_json(Path(args.persona)),
            package_id=args.package_id,
            created_at=args.created_at,
            review_goal=args.review_goal,
            valid_until=args.valid_until,
        )
        _write_json(stdout, package)
        return 0

    if args.command == "get":
        store = _store(stores, args.collection)
        _write_json(stdout, store.read(args.record_id))
        return 0

    if args.command == "journal":
        entries = [
            entry
            for entry in stores.journals.replay()
            if args.state_object_id is None
            or entry.get("state_object_id") == args.state_object_id
        ]
        _write_json(stdout, {"entries": entries})
        return 0

    if args.command == "memory":
        entries = [
            entry
            for entry in stores.memory.replay()
            if entry.get("agent_ref") == args.agent_ref
        ]
        _write_json(stdout, {"entries": entries})
        return 0

    if args.command == "rollups":
        _write_json(stdout, {"rollup_requests": _rollup_requests(stores)})
        return 0

    if args.command == "recent":
        entries = [
            entry
            for entry in stores.recent_changes.replay()
            if _included_for_persona(entry, args.persona_ref)
        ]
        _write_json(stdout, {"entries": entries})
        return 0

    if args.command == "package":
        _write_json(stdout, stores.context_packages.read(args.package_id))
        return 0

    parser.error(f"unsupported command {args.command}")
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="state")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--state-root")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("validate")

    trigger = subcommands.add_parser("trigger")
    trigger.add_argument("source_event")

    git_commit = subcommands.add_parser("git-commit-event")
    git_commit.add_argument("commit_metadata")
    git_commit.add_argument("--repo-ref", required=True)
    git_commit.add_argument("--observed-at", required=True)
    git_commit.add_argument("--candidate-state-ref", action="append")
    git_commit.add_argument("--governance-ref", action="append")
    git_commit.add_argument("--ingest", action="store_true")

    review = subcommands.add_parser("review")
    review.add_argument("source_event_id")
    review.add_argument("--packet-id", required=True)
    review.add_argument("--created-at", required=True)
    review.add_argument("--persona", required=True)
    review.add_argument("--resolved-evidence", required=True)
    review.add_argument("--governance-constraints", required=True)
    review.add_argument("--unresolved-evidence-ref", action="append")

    commit = subcommands.add_parser("commit")
    commit.add_argument("model_output")
    commit.add_argument("--created-at", required=True)
    commit.add_argument("--evidence-ref", action="append")

    recent_index = subcommands.add_parser("index-recent")
    recent_index.add_argument("source_event_id")
    recent_index.add_argument("commit_id")
    recent_index.add_argument("--created-at", required=True)
    recent_index.add_argument("--summary", required=True)
    recent_index.add_argument("--routes", required=True)
    recent_index.add_argument("--opportunity-class-hint", action="append")
    recent_index.add_argument("--watermark-ref", action="append")
    recent_index.add_argument("--stale-after", required=True)
    recent_index.add_argument(
        "--requires-refresh-before-external-action",
        action="store_true",
    )

    build_package = subcommands.add_parser("build-package")
    build_package.add_argument("persona")
    build_package.add_argument("package_id")
    build_package.add_argument("--created-at", required=True)
    build_package.add_argument("--review-goal", required=True)
    build_package.add_argument("--valid-until", required=True)

    get = subcommands.add_parser("get")
    get.add_argument("collection", choices=sorted(COLLECTIONS))
    get.add_argument("record_id")

    journal = subcommands.add_parser("journal")
    journal.add_argument("state_object_id", nargs="?")

    memory = subcommands.add_parser("memory")
    memory.add_argument("agent_ref")

    subcommands.add_parser("rollups")

    recent = subcommands.add_parser("recent")
    recent.add_argument("persona_ref")

    package = subcommands.add_parser("package")
    package.add_argument("package_id")

    return parser


def _store(stores: StateStoreBundle, collection: str):
    return getattr(stores, COLLECTIONS[collection])


def _included_for_persona(entry: JsonObject, persona_ref: str) -> bool:
    for route in entry["candidate_persona_routes"]:
        if route["persona_ref"] == persona_ref:
            return bool(route["included"])
    return False


def _rollup_requests(stores: StateStoreBundle) -> list[JsonObject]:
    requests: list[JsonObject] = []
    for commit in stores.commits.replay():
        requests.extend(commit.get("queued_rollup_requests", []))
    for journal in stores.journals.replay():
        requests.extend(journal.get("rollup_requests", []))
    return requests


def _runtime_schemas(project_root: Path) -> dict[str, JsonObject]:
    return {
        "review_packet": load_json(
            project_root / "schemas" / "model-review-packet.schema.json"
        ),
        "model_output": load_json(
            project_root / "schemas" / "model-proposal-output.schema.json"
        ),
        "journal": load_json(
            project_root / "schemas" / "state-journal-entry.schema.json"
        ),
        "memory": load_json(
            project_root / "schemas" / "agent-memory-entry.schema.json"
        ),
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
    }


def _load_list(path: str) -> list[JsonObject]:
    json_path = Path(path)
    with json_path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, list):
        raise ValueError(f"{path} must contain a JSON list")
    return value


def _write_json(stdout: TextIO, payload: JsonObject) -> None:
    json.dump(payload, stdout, indent=2, sort_keys=True)
    stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
