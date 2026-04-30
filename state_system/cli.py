from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import TextIO

from state_system.contracts import load_json, validate_all_examples
from state_system.runner import SourceEventIngestor
from state_system.stores import JsonObject, StateStoreBundle


COLLECTIONS = {
    "state": "state_objects",
    "source-event": "source_events",
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


def _write_json(stdout: TextIO, payload: JsonObject) -> None:
    json.dump(payload, stdout, indent=2, sort_keys=True)
    stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
