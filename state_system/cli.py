from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import TextIO

from state_system.agent_consumers import (
    capture_agent_response,
    render_package_for_agent,
)
from state_system.agent_activation import (
    create_agent_activation,
    render_activation_for_agent,
)
from state_system.app_integrations import run_app_integration_fixtures
from state_system.company_capability import (
    CompanyCapabilityRuntime,
    build_company_capability_read_model,
    build_company_capability_read_model_from_runtime,
)
from state_system.company_memory import build_company_memory_read_model
from state_system.company_preflight import (
    CompanyPreflightRuntime,
    build_company_preflight_read_model,
)
from state_system.company_understanding_surface import (
    build_company_understanding_surface_read_model,
)
from state_system.interpreted_index import (
    build_interpreted_index_read_model,
    search_interpreted_index,
)
from state_system.contracts import load_json, validate_all_examples, validate_schema
from state_system.heartbeat import run_source_heartbeat
from state_system.instance_capability import (
    InstanceCapabilityRuntime,
    build_instance_capability_read_model,
    build_instance_capability_read_model_from_runtime,
)
from state_system.instance_understanding_surface import (
    build_instance_understanding_surface_read_model,
)
from state_system.mission_records import (
    MissionStoreBundle,
    build_mission_read_model,
    replay_mission_fixture,
)
from state_system.operational_loop import run_operational_loop
from state_system.paia_bootstrap import (
    DEFAULT_PAIA_STATE_ROOT,
    bootstrap_paia_state_system,
)
from state_system.runtime import (
    build_recent_package,
    build_review_packet_from_source_event,
    commit_model_output,
    index_recent_change,
    index_recent_change_from_source_event,
)
from state_system.runtime_seed import seed_repo_runtime
from state_system.runner import SourceEventIngestor
from state_system.reporting import run_report_suite
from state_system.source_adapters import (
    git_commit_metadata_from_repo,
    git_commit_to_source_event,
)
from state_system.source_freshness import (
    SourceFreshnessRuntime,
    build_source_freshness_read_model,
)
from state_system.state_root_migration import migrate_state_root
from state_system.stores import JsonObject, StateStoreBundle
from state_system.trace_runner import run_trace_manifest


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
    "agent-activation": "agent_activations",
    "agent-response": "agent_responses",
    "instance-capability": "instance_capabilities",
    "company-capability": "company_capabilities",
    "company-preflight": "company_preflight_results",
    "source-freshness": "source_freshness",
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

    if args.command == "seed-runtime":
        payload = seed_repo_runtime(
            stores,
            repo_ref=args.repo_ref,
            created_at=args.created_at,
        )
        _write_json(stdout, payload)
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

    if args.command == "git-commit-from-repo":
        metadata = git_commit_metadata_from_repo(Path(args.repo_path), args.commit)
        event = git_commit_to_source_event(
            metadata,
            repo_ref=args.repo_ref,
            observed_at=args.observed_at,
            candidate_state_refs=list(args.candidate_state_ref or []),
            governance_refs=list(args.governance_ref or []),
        )
        payload = {"commit_metadata": metadata, "source_event": event}
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

    if args.command == "index-source-recent":
        entry = index_recent_change_from_source_event(
            stores,
            _runtime_schemas(project_root),
            source_event_id=args.source_event_id,
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

    if args.command == "render-package":
        stdout.write(render_package_for_agent(stores.context_packages.read(args.package_id)))
        stdout.write("\n")
        return 0

    if args.command == "capture-response":
        response_text = Path(args.response_path).read_text(encoding="utf-8")
        record = capture_agent_response(
            stores,
            _runtime_schemas(project_root),
            package_id=args.package_id,
            consumer_ref=args.consumer,
            response_text=response_text,
            created_at=args.created_at,
            response_id=args.response_id,
            activation_id=args.activation_id,
        )
        _write_json(stdout, record)
        return 0

    if args.command == "activate-agent":
        activation = create_agent_activation(
            stores,
            _runtime_schemas(project_root),
            package_id=args.package_id,
            consumer_ref=args.consumer,
            created_at=args.created_at,
            activation_goal=args.activation_goal,
            expected_response_type=args.expected_response_type,
            activation_id=args.activation_id,
        )
        _write_json(stdout, activation)
        return 0

    if args.command == "render-activation":
        stdout.write(render_activation_for_agent(stores, args.activation_id))
        stdout.write("\n")
        return 0

    if args.command == "trace-run":
        output_dir = Path(args.output_dir)
        report = run_trace_manifest(
            project_root=project_root,
            manifest_path=Path(args.trace_manifest),
            output_dir=output_dir,
        )
        _write_json(stdout, report)
        return 0

    if args.command == "app-integrations-run":
        output_dir = Path(args.output_dir)
        report = run_app_integration_fixtures(
            project_root=project_root,
            output_dir=output_dir,
        )
        _write_json(stdout, report)
        return 0 if report["status"] == "passed" else 1

    if args.command == "report-suite-run":
        output_dir = Path(args.output_dir)
        report = run_report_suite(
            project_root=project_root,
            output_dir=output_dir,
        )
        _write_json(stdout, report)
        return 0 if report["status"] == "passed" else 1

    if args.command == "mission-replay":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        mission_stores = MissionStoreBundle(output_dir)
        replay = replay_mission_fixture(Path(args.fixture), mission_stores)
        read_model = build_mission_read_model(
            mission_stores,
            replay["mission_run_id"],
        )
        read_model_path = output_dir / "mission-read-model.json"
        read_model_path.write_text(
            json.dumps(read_model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_json(
            stdout,
            {
                **replay,
                "read_model_path": str(read_model_path),
            },
        )
        return 0

    if args.command == "company-memory-build":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        read_model = build_company_memory_read_model(
            load_json(Path(args.company_memory)),
            load_json(Path(args.crm_operating_picture)),
        )
        read_model_path = output_dir / "company-memory-read-model.json"
        read_model_path.write_text(
            json.dumps(read_model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_json(
            stdout,
            {
                "read_model_id": read_model["id"],
                "read_model_path": str(read_model_path),
            },
        )
        return 0

    if args.command == "company-capability-build":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        read_model = build_company_capability_read_model(
            [load_json(Path(path)) for path in args.company_capability_pack]
        )
        read_model_path = output_dir / "company-capability-read-model.json"
        read_model_path.write_text(
            json.dumps(read_model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_json(
            stdout,
            {
                "read_model_id": read_model["id"],
                "read_model_path": str(read_model_path),
            },
        )
        return 0

    if args.command == "instance-capability-build":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        read_model = build_instance_capability_read_model(
            [load_json(Path(path)) for path in args.instance_capability_pack]
        )
        read_model_path = output_dir / "instance-capability-read-model.json"
        read_model_path.write_text(
            json.dumps(read_model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_json(
            stdout,
            {
                "read_model_id": read_model["id"],
                "read_model_path": str(read_model_path),
            },
        )
        return 0

    if args.command == "instance-capability-seed":
        packs = [load_json(Path(path)) for path in args.instance_capability_pack]
        schema = load_json(
            project_root / "schemas" / "instance-capability-pack.schema.json"
        )
        failures = [
            {"id": pack.get("id"), "errors": list(validate_schema(pack, schema))}
            for pack in packs
        ]
        failures = [failure for failure in failures if failure["errors"]]
        if failures:
            _write_json(stdout, {"ok": False, "failures": failures})
            return 1

        result = InstanceCapabilityRuntime(stores).seed(packs)
        _write_json(stdout, {"ok": True, **result})
        return 0

    if args.command == "instance-capability-read":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        read_model = build_instance_capability_read_model_from_runtime(stores)
        read_model_path = output_dir / "instance-capability-read-model.json"
        read_model_path.write_text(
            json.dumps(read_model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_json(
            stdout,
            {
                "read_model_id": read_model["id"],
                "read_model_path": str(read_model_path),
            },
        )
        return 0

    if args.command == "company-capability-seed":
        packs = [load_json(Path(path)) for path in args.company_capability_pack]
        schema = load_json(
            project_root / "schemas" / "company-capability-pack.schema.json"
        )
        failures = [
            {"id": pack.get("id"), "errors": list(validate_schema(pack, schema))}
            for pack in packs
        ]
        failures = [failure for failure in failures if failure["errors"]]
        if failures:
            _write_json(stdout, {"ok": False, "failures": failures})
            return 1

        result = CompanyCapabilityRuntime(stores).seed(packs)
        _write_json(stdout, {"ok": True, **result})
        return 0

    if args.command == "company-capability-read":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        read_model = build_company_capability_read_model_from_runtime(stores)
        read_model_path = output_dir / "company-capability-read-model.json"
        read_model_path.write_text(
            json.dumps(read_model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_json(
            stdout,
            {
                "read_model_id": read_model["id"],
                "read_model_path": str(read_model_path),
            },
        )
        return 0

    if args.command == "company-preflight-record":
        result = CompanyPreflightRuntime(stores).record(
            _preflight_result_from_args(args)
        )
        schema = load_json(
            project_root / "schemas" / "company-preflight-result.schema.json"
        )
        errors = list(validate_schema(result, schema))
        if errors:
            _write_json(stdout, {"ok": False, "errors": errors})
            return 1
        _write_json(stdout, {"ok": True, "preflight_result": result})
        return 0

    if args.command == "company-preflight-list":
        _write_json(stdout, {"results": CompanyPreflightRuntime(stores).list_results()})
        return 0

    if args.command == "company-preflight-export":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        read_model = build_company_preflight_read_model(stores)
        read_model_path = output_dir / "company-preflight-results-read-model.json"
        read_model_path.write_text(
            json.dumps(read_model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_json(
            stdout,
            {
                "read_model_id": read_model["id"],
                "read_model_path": str(read_model_path),
            },
        )
        return 0

    if args.command == "source-freshness-record":
        result = SourceFreshnessRuntime(stores).record(
            _source_freshness_from_args(args)
        )
        schema = load_json(
            project_root / "schemas" / "source-freshness-record.schema.json"
        )
        errors = list(validate_schema(result, schema))
        if errors:
            _write_json(stdout, {"ok": False, "errors": errors})
            return 1
        _write_json(stdout, {"ok": True, "source_freshness": result})
        return 0

    if args.command == "source-freshness-list":
        _write_json(stdout, {"results": SourceFreshnessRuntime(stores).list_results()})
        return 0

    if args.command == "source-freshness-export":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        read_model = build_source_freshness_read_model(stores)
        read_model_path = output_dir / "source-freshness-read-model.json"
        read_model_path.write_text(
            json.dumps(read_model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_json(
            stdout,
            {
                "read_model_id": read_model["id"],
                "read_model_path": str(read_model_path),
            },
        )
        return 0

    if args.command == "source-heartbeat-run":
        summary = run_source_heartbeat(
            stores,
            company_ref=args.company_ref,
            checked_at=args.checked_at,
            stale_after=args.stale_after,
            output_dir=Path(args.output_dir),
        )
        _write_json(stdout, summary)
        return 0

    if args.command == "company-understanding-surface-read":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        read_model = build_company_understanding_surface_read_model(stores)
        read_model_path = output_dir / "company-understanding-surface-read-model.json"
        read_model_path.write_text(
            json.dumps(read_model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_json(
            stdout,
            {
                "read_model_id": read_model["id"],
                "read_model_path": str(read_model_path),
            },
        )
        return 0

    if args.command == "state-interpreted-index-read":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        read_model = build_interpreted_index_read_model(
            stores,
            company_ref=args.company_ref,
        )
        read_model_path = output_dir / "state-interpreted-index-read-model.json"
        read_model_path.write_text(
            json.dumps(read_model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_json(
            stdout,
            {
                "read_model_id": read_model["id"],
                "read_model_path": str(read_model_path),
            },
        )
        return 0

    if args.command == "state-interpreted-search":
        read_model = build_interpreted_index_read_model(
            stores,
            company_ref=args.company_ref,
        )
        result = search_interpreted_index(
            read_model,
            query=args.query,
            limit=args.limit,
        )
        if args.require_records and not result.get("records"):
            result["ok"] = False
            result["error"] = {
                "code": "state_interpreted_search_no_records",
                "message": "State interpreted search returned no records.",
            }
            _write_json(stdout, result)
            return 1
        _write_json(stdout, result)
        return 0

    if args.command == "instance-understanding-surface-read":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        read_model = build_instance_understanding_surface_read_model(stores)
        read_model_path = output_dir / "instance-understanding-surface-read-model.json"
        read_model_path.write_text(
            json.dumps(read_model, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_json(
            stdout,
            {
                "read_model_id": read_model["id"],
                "read_model_path": str(read_model_path),
            },
        )
        return 0

    if args.command == "state-root-migrate":
        result = migrate_state_root(
            project_root=project_root,
            source_root=Path(args.from_root),
            target_root=Path(args.to_root),
            compat_link=Path(args.compat_link) if args.compat_link else None,
            validate_company_ref=args.validate_company_ref,
            refresh=args.refresh,
            heartbeat_company_ref=args.heartbeat_company_ref,
            heartbeat_checked_at=args.heartbeat_checked_at,
            heartbeat_stale_after=args.heartbeat_stale_after,
        )
        _write_json(stdout, result)
        return 0

    if args.command == "paia-bootstrap-export":
        bootstrap_root = (
            Path(args.state_root) if args.state_root else DEFAULT_PAIA_STATE_ROOT
        )
        result = bootstrap_paia_state_system(project_root, bootstrap_root)
        _write_json(stdout, result)
        return 0

    if args.command == "operational-loop-run":
        summary = run_operational_loop(
            project_root=project_root,
            manifest_path=Path(args.trace_manifest),
            output_dir=Path(args.output_dir),
        )
        _write_json(
            stdout,
            {
                "id": summary["id"],
                "status": summary["status"],
                "summary_path": str(Path(args.output_dir) / "operator-summary.json"),
                "trace_report_path": summary["trace_report_path"],
            },
        )
        return 0 if summary["status"] == "passed" else 1

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

    seed_runtime = subcommands.add_parser("seed-runtime")
    seed_runtime.add_argument("--repo-ref", required=True)
    seed_runtime.add_argument("--created-at", required=True)

    git_commit = subcommands.add_parser("git-commit-event")
    git_commit.add_argument("commit_metadata")
    git_commit.add_argument("--repo-ref", required=True)
    git_commit.add_argument("--observed-at", required=True)
    git_commit.add_argument("--candidate-state-ref", action="append")
    git_commit.add_argument("--governance-ref", action="append")
    git_commit.add_argument("--ingest", action="store_true")

    git_commit_repo = subcommands.add_parser("git-commit-from-repo")
    git_commit_repo.add_argument("repo_path")
    git_commit_repo.add_argument("--commit", default="HEAD")
    git_commit_repo.add_argument("--repo-ref", required=True)
    git_commit_repo.add_argument("--observed-at", required=True)
    git_commit_repo.add_argument("--candidate-state-ref", action="append")
    git_commit_repo.add_argument("--governance-ref", action="append")
    git_commit_repo.add_argument("--ingest", action="store_true")

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

    source_recent_index = subcommands.add_parser("index-source-recent")
    source_recent_index.add_argument("source_event_id")
    source_recent_index.add_argument("--created-at", required=True)
    source_recent_index.add_argument("--summary", required=True)
    source_recent_index.add_argument("--routes", required=True)
    source_recent_index.add_argument("--opportunity-class-hint", action="append")
    source_recent_index.add_argument("--watermark-ref", action="append")
    source_recent_index.add_argument("--stale-after", required=True)
    source_recent_index.add_argument(
        "--requires-refresh-before-external-action",
        action="store_true",
    )

    build_package = subcommands.add_parser("build-package")
    build_package.add_argument("persona")
    build_package.add_argument("package_id")
    build_package.add_argument("--created-at", required=True)
    build_package.add_argument("--review-goal", required=True)
    build_package.add_argument("--valid-until", required=True)

    render_package = subcommands.add_parser("render-package")
    render_package.add_argument("package_id")

    capture_response = subcommands.add_parser("capture-response")
    capture_response.add_argument("package_id")
    capture_response.add_argument("response_path")
    capture_response.add_argument("--consumer", required=True)
    capture_response.add_argument("--created-at", required=True)
    capture_response.add_argument("--response-id")
    capture_response.add_argument("--activation-id")

    activate_agent = subcommands.add_parser("activate-agent")
    activate_agent.add_argument("package_id")
    activate_agent.add_argument("--consumer", required=True)
    activate_agent.add_argument("--created-at", required=True)
    activate_agent.add_argument("--activation-goal", required=True)
    activate_agent.add_argument("--expected-response-type", required=True)
    activate_agent.add_argument("--activation-id")

    render_activation = subcommands.add_parser("render-activation")
    render_activation.add_argument("activation_id")

    trace_run = subcommands.add_parser("trace-run")
    trace_run.add_argument("trace_manifest")
    trace_run.add_argument("--output-dir", required=True)

    app_integrations_run = subcommands.add_parser("app-integrations-run")
    app_integrations_run.add_argument("--output-dir", required=True)

    report_suite_run = subcommands.add_parser("report-suite-run")
    report_suite_run.add_argument("--output-dir", required=True)

    mission_replay = subcommands.add_parser("mission-replay")
    mission_replay.add_argument("fixture")
    mission_replay.add_argument("--output-dir", required=True)

    company_memory = subcommands.add_parser("company-memory-build")
    company_memory.add_argument("company_memory")
    company_memory.add_argument("crm_operating_picture")
    company_memory.add_argument("--output-dir", required=True)

    company_capability = subcommands.add_parser("company-capability-build")
    company_capability.add_argument("company_capability_pack", nargs="+")
    company_capability.add_argument("--output-dir", required=True)

    company_capability_seed = subcommands.add_parser("company-capability-seed")
    company_capability_seed.add_argument("company_capability_pack", nargs="+")

    company_capability_read = subcommands.add_parser("company-capability-read")
    company_capability_read.add_argument("--output-dir", required=True)

    instance_capability = subcommands.add_parser("instance-capability-build")
    instance_capability.add_argument("instance_capability_pack", nargs="+")
    instance_capability.add_argument("--output-dir", required=True)

    instance_capability_seed = subcommands.add_parser("instance-capability-seed")
    instance_capability_seed.add_argument("instance_capability_pack", nargs="+")

    instance_capability_read = subcommands.add_parser("instance-capability-read")
    instance_capability_read.add_argument("--output-dir", required=True)

    preflight_record = subcommands.add_parser("company-preflight-record")
    preflight_record.add_argument("--preflight-ref", required=True)
    preflight_record.add_argument("--company-ref", required=True)
    preflight_record.add_argument("--connector-ref")
    preflight_record.add_argument("--tool-ref")
    preflight_record.add_argument("--action-ref")
    preflight_record.add_argument("--agent-ref")
    preflight_record.add_argument("--runner-ref")
    preflight_record.add_argument(
        "--status",
        choices=["passed", "failed"],
        required=True,
    )
    preflight_record.add_argument("--checked-at", required=True)
    preflight_record.add_argument("--stale-after")
    preflight_record.add_argument("--ttl-seconds", type=int)
    preflight_record.add_argument("--evidence-ref", action="append")
    preflight_record.add_argument("--error-code")
    preflight_record.add_argument("--error-message")
    preflight_record.add_argument("--detail")

    subcommands.add_parser("company-preflight-list")

    preflight_export = subcommands.add_parser("company-preflight-export")
    preflight_export.add_argument("--output-dir", required=True)

    freshness_record = subcommands.add_parser("source-freshness-record")
    freshness_record.add_argument("--company-ref", required=True)
    freshness_record.add_argument("--connector-ref", required=True)
    freshness_record.add_argument("--source-ref", required=True)
    freshness_record.add_argument("--connector-type", required=True)
    freshness_record.add_argument(
        "--status",
        choices=["fresh", "stale", "failed", "unknown"],
        required=True,
    )
    freshness_record.add_argument("--checked-at", required=True)
    freshness_record.add_argument("--source-watermark", required=True)
    freshness_record.add_argument("--stale-after", required=True)
    freshness_record.add_argument("--lag-seconds", type=int)
    freshness_record.add_argument("--evidence-ref", action="append")
    freshness_record.add_argument("--error-code")
    freshness_record.add_argument("--error-message")
    freshness_record.add_argument("--detail")

    subcommands.add_parser("source-freshness-list")

    freshness_export = subcommands.add_parser("source-freshness-export")
    freshness_export.add_argument("--output-dir", required=True)

    source_heartbeat = subcommands.add_parser("source-heartbeat-run")
    source_heartbeat.add_argument("--company-ref")
    source_heartbeat.add_argument("--checked-at", required=True)
    source_heartbeat.add_argument("--stale-after", required=True)
    source_heartbeat.add_argument("--output-dir", required=True)

    understanding_surface = subcommands.add_parser(
        "company-understanding-surface-read"
    )
    understanding_surface.add_argument("--output-dir", required=True)

    interpreted_index = subcommands.add_parser("state-interpreted-index-read")
    interpreted_index.add_argument("--company-ref")
    interpreted_index.add_argument("--output-dir", required=True)

    interpreted_search = subcommands.add_parser("state-interpreted-search")
    interpreted_search.add_argument("--company-ref")
    interpreted_search.add_argument("--query", required=True)
    interpreted_search.add_argument("--limit", type=int, default=10)
    interpreted_search.add_argument("--require-records", action="store_true")

    instance_understanding_surface = subcommands.add_parser(
        "instance-understanding-surface-read"
    )
    instance_understanding_surface.add_argument("--output-dir", required=True)

    migrate = subcommands.add_parser("state-root-migrate")
    migrate.add_argument("--from", dest="from_root", required=True)
    migrate.add_argument("--to", dest="to_root", required=True)
    migrate.add_argument("--compat-link")
    migrate.add_argument("--validate-company-ref")
    migrate.add_argument("--refresh", action="store_true")
    migrate.add_argument("--heartbeat-company-ref")
    migrate.add_argument("--heartbeat-checked-at")
    migrate.add_argument("--heartbeat-stale-after")

    subcommands.add_parser("paia-bootstrap-export")

    operational_loop = subcommands.add_parser("operational-loop-run")
    operational_loop.add_argument("trace_manifest")
    operational_loop.add_argument("--output-dir", required=True)

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


def _preflight_result_from_args(args: argparse.Namespace) -> JsonObject:
    result: JsonObject = {
        "preflight_ref": args.preflight_ref,
        "company_ref": args.company_ref,
        "status": args.status,
        "checked_at": args.checked_at,
        "evidence_refs": list(args.evidence_ref or []),
    }
    for source, target in (
        ("connector_ref", "connector_ref"),
        ("tool_ref", "tool_ref"),
        ("action_ref", "action_ref"),
        ("agent_ref", "agent_ref"),
        ("runner_ref", "runner_ref"),
        ("stale_after", "stale_after"),
        ("ttl_seconds", "ttl_seconds"),
        ("detail", "detail"),
    ):
        value = getattr(args, source)
        if value is not None:
            result[target] = value
    if args.error_code or args.error_message:
        result["error"] = {
            "code": args.error_code or "",
            "message": args.error_message or "",
        }
    return result


def _source_freshness_from_args(args: argparse.Namespace) -> JsonObject:
    result: JsonObject = {
        "company_ref": args.company_ref,
        "connector_ref": args.connector_ref,
        "source_ref": args.source_ref,
        "connector_type": args.connector_type,
        "status": args.status,
        "checked_at": args.checked_at,
        "source_watermark": args.source_watermark,
        "stale_after": args.stale_after,
        "evidence_refs": list(args.evidence_ref or []),
    }
    for source, target in (
        ("lag_seconds", "lag_seconds"),
        ("detail", "detail"),
    ):
        value = getattr(args, source)
        if value is not None:
            result[target] = value
    if args.error_code or args.error_message:
        result["error"] = {
            "code": args.error_code or "",
            "message": args.error_message or "",
        }
    return result


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
        "agent_response": load_json(
            project_root / "schemas" / "agent-response.schema.json"
        ),
        "agent_activation": load_json(
            project_root / "schemas" / "agent-activation.schema.json"
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
