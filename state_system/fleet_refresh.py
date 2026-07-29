from __future__ import annotations

import json
import os
import re
import signal
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from state_system.contracts import JsonObject, load_json, validate_schema
from state_system.entity_current_state import build_entity_current_state_read_model
from state_system.instance_agent_packages import InstanceAgentPackageRuntime
from state_system.instance_preflight import (
    build_instance_preflight_read_model,
    run_instance_preflight,
)
from state_system.instance_source_freshness import (
    build_instance_source_freshness_read_model,
)
from state_system.instance_understanding_surface import (
    build_instance_understanding_surface_read_model,
)
from state_system.package_pressure import (
    load_pressure_registry,
    run_package_pressure,
    validate_pressure_registry,
)
from state_system.stores import StateStoreBundle
from state_system.staleness_runner import parse_instant
from state_system.strategic_staleness import refresh_strategic_staleness_read_model


def run_fleet_refresh(
    manifest: JsonObject,
    *,
    project_root: Path,
    checked_at: str | None = None,
    stale_after: str | None = None,
    output_dir: Path | None = None,
    dry_run: bool = False,
    reviewer: Any | None = None,
) -> JsonObject:
    run_checked_at = checked_at or _now_utc()
    run_stale_after = stale_after or _default_stale_after(
        run_checked_at,
        int(manifest.get("default_ttl_seconds", 3600)),
    )
    instance_results = [
        _refresh_instance(
            instance,
            project_root=project_root,
            checked_at=run_checked_at,
            stale_after=run_stale_after,
            dry_run=dry_run,
            reviewer=reviewer,
        )
        for instance in manifest.get("instances", [])
    ]
    packages = {
        result["package_id"]: load_json(Path(result["package_path"]))
        for result in instance_results
        if result.get("package_path") and Path(result["package_path"]).exists()
    }
    entity_current_state = _refresh_entity_current_state(
        manifest.get("entity_current_state"),
        checked_at=run_checked_at,
        dry_run=dry_run,
    )
    pressure_report = _run_pressure(
        manifest,
        packages=packages,
        project_root=project_root,
        dry_run=dry_run,
    )
    report = {
        "id": f"fleet_refresh_report.{manifest.get('id', 'unknown')}",
        "manifest_id": manifest.get("id"),
        "checked_at": run_checked_at,
        "stale_after": run_stale_after,
        "dry_run": dry_run,
        "ok": all(result["ok"] for result in instance_results)
        and (entity_current_state is None or entity_current_state["status"] in {"planned", "refreshed"})
        and (pressure_report is None or pressure_report["ok"]),
        "instance_count": len(instance_results),
        "instances": instance_results,
        "pressure_report": pressure_report,
        "invariant": {
            "delegated_sources_require_adapter_evidence": True,
            "runner_materializes_raw_source_corpora": False,
            "package_regeneration_is_not_live_access_proof": True,
        },
        "report_age_canary": _evaluate_report_age(
            checked_at=run_checked_at,
            as_of=run_checked_at,
            ttl_seconds=int(manifest.get("default_ttl_seconds", 3600)),
            report_ref="fleet-refresh-report.json",
            exists=True,
        ),
    }
    if entity_current_state is not None:
        report["entity_current_state"] = entity_current_state
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "fleet-refresh-report.json"
        _write_json(report_path, report)
        report["report_path"] = str(report_path)
        report["report_age_canary"]["report_ref"] = str(report_path)
    return report


def _refresh_entity_current_state(
    config: JsonObject | None,
    *,
    checked_at: str,
    dry_run: bool,
) -> JsonObject | None:
    if config is None:
        return None

    roots = _entity_current_state_roots(config)
    default_output_dir = config.get("output_dir", "entity-current-state")
    refreshed_roots: list[JsonObject] = []
    aggregated_gap_refs: list[str] = []

    for root_config in roots:
        state_root = Path(root_config["state_root"]).expanduser()
        label = root_config["label"]
        output_dir = root_config.get("output_dir") or default_output_dir
        output_path = state_root / output_dir / "entity-current-state-read-model.json"
        root_result: JsonObject = {
            "state_root": str(state_root),
            "label": label,
            "read_model_path": str(output_path),
        }
        if dry_run:
            refreshed_roots.append({**root_result, "status": "planned"})
            continue

        if not state_root.exists():
            gap_ref = f"gap.fleet_ecs.{_slug(label)}.state_root_missing"
            aggregated_gap_refs.append(gap_ref)
            refreshed_roots.append(
                {
                    **root_result,
                    "status": "failed",
                    "error": f"state_root does not exist: {state_root}",
                    "gap_refs": [gap_ref],
                }
            )
            continue

        try:
            read_model = build_entity_current_state_read_model(
                StateStoreBundle(state_root),
                as_of=checked_at,
            )
            _write_json(output_path, read_model)
            refreshed_roots.append({**root_result, "status": "refreshed", "as_of": checked_at})
        except (KeyError, OSError, TypeError, ValueError) as error:
            gap_ref = f"gap.fleet_ecs.{_slug(label)}.projection_failed"
            aggregated_gap_refs.append(gap_ref)
            refreshed_roots.append(
                {
                    **root_result,
                    "status": "failed",
                    "error": str(error),
                    "gap_refs": [gap_ref],
                }
            )

    statuses = {root["status"] for root in refreshed_roots}
    if "failed" in statuses:
        overall_status = "failed"
    elif dry_run or statuses == {"planned"}:
        overall_status = "planned"
    else:
        overall_status = "refreshed"

    result: JsonObject = {
        "status": overall_status,
        "roots": refreshed_roots,
        "gap_refs": sorted(set(aggregated_gap_refs)),
    }

    # Preserve the legacy single-root surface for existing manifests.
    if len(roots) == 1 and "state_root" in config:
        single_root = refreshed_roots[0]
        result["state_root"] = single_root["state_root"]
        result["read_model_path"] = single_root["read_model_path"]
        if single_root.get("as_of"):
            result["as_of"] = single_root["as_of"]

    return result


def _entity_current_state_roots(config: JsonObject) -> list[JsonObject]:
    if "roots" in config:
        return list(config["roots"])
    return [
        {
            "state_root": config["state_root"],
            "label": "default",
        }
    ]


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")

def _refresh_instance(
    config: JsonObject,
    *,
    project_root: Path,
    checked_at: str,
    stale_after: str,
    dry_run: bool,
    reviewer: Any | None = None,
) -> JsonObject:
    state_root = Path(config["state_root"]).expanduser()
    stores = StateStoreBundle(state_root)
    commands = [
        _run_adapter_command(
            command,
            checked_at=checked_at,
            stale_after=stale_after,
            dry_run=dry_run,
        )
        for command in config.get("adapter_commands", [])
    ]
    command_failures = [
        command
        for command in commands
        if command["status"] == "failed" and command.get("required", True)
    ]
    if dry_run:
        return {
            "id": config["id"],
            "state_root": str(state_root),
            "instance_ref": config["instance_ref"],
            "package_id": config["package_id"],
            "ok": not command_failures,
            "status": "planned",
            "adapter_commands": commands,
        }

    if config.get("preflight_mode", "export_only") == "generic_run":
        run_instance_preflight(
            stores,
            instance_ref=config["instance_ref"],
            checked_at=checked_at,
            stale_after=stale_after,
        )

    outputs = config.get("output_dirs", {})
    preflight_path = _write_read_model(
        state_root,
        outputs.get("instance_preflight", "instance-preflight"),
        "instance-preflight-results-read-model.json",
        build_instance_preflight_read_model(stores),
    )
    freshness_path = _write_read_model(
        state_root,
        outputs.get("instance_source_freshness", "instance-source-freshness"),
        "instance-source-freshness-read-model.json",
        build_instance_source_freshness_read_model(stores),
    )
    # Strategic-staleness read model: the per-entity projection agents consume.
    # Reviewer is injected from the caller (CLI, manifest, or test); when None,
    # expired ECS cards are surfaced as explicit awaiting_model_review gaps rather
    # than a healthy-looking empty shell. Code owns load/run/write; the reviewer
    # owns every judgment.
    staleness_path = refresh_strategic_staleness_read_model(
        state_root,
        as_of=parse_instant(checked_at),
        reviewer=reviewer,
    )
    understanding = build_instance_understanding_surface_read_model(stores)
    understanding_path = _write_read_model(
        state_root,
        outputs.get("instance_understanding", "instance-understanding"),
        "instance-understanding-surface-read-model.json",
        understanding,
    )
    package = InstanceAgentPackageRuntime(stores).build(
        {
            "instance_agent_package": load_json(
                project_root / "schemas" / "instance-agent-package.schema.json"
            )
        },
        instance_ref=config["instance_ref"],
        agent_ref=config["agent_ref"],
        persona_ref=config.get("persona_ref"),
        created_at=checked_at,
        review_goal=config.get("review_goal"),
        package_id=config["package_id"],
    )
    package_read_model_path = InstanceAgentPackageRuntime(stores).export(
        state_root / outputs.get("instance_agent_package", "instance-agent-package")
    )
    package_path = (
        state_root
        / "state"
        / "instance-agent-packages"
        / f"{config['package_id']}.json"
    )
    source_counts = _source_counts(package)
    source_gap_refs = package.get("source_context", {}).get("source_gap_refs", [])
    return {
        "id": config["id"],
        "state_root": str(state_root),
        "instance_ref": config["instance_ref"],
        "package_id": config["package_id"],
        "ok": not command_failures,
        "status": "failed" if command_failures else "refreshed",
        "adapter_commands": commands,
        "read_model_paths": {
            "instance_preflight": str(preflight_path),
            "instance_source_freshness": str(freshness_path),
            "instance_understanding": str(understanding_path),
            "instance_agent_package": str(package_read_model_path),
            "strategic_staleness": str(staleness_path),
        },
        "package_path": str(package_path),
        "source_status_counts": source_counts,
        "source_gap_refs": source_gap_refs,
    }


def _run_adapter_command(
    command: JsonObject,
    *,
    checked_at: str,
    stale_after: str,
    dry_run: bool,
) -> JsonObject:
    result = {
        "id": command["id"],
        "required": command.get("required", True),
        "argv": command.get("argv", []),
        "cwd": command.get("cwd", ""),
    }
    if dry_run:
        return {**result, "status": "planned"}
    process: subprocess.Popen[str] | None = None
    try:
        env = {
            **os.environ,
            "STATE_SYSTEM_FLEET_CHECKED_AT": checked_at,
            "STATE_SYSTEM_FLEET_STALE_AFTER": stale_after,
            "STATE_SYSTEM_FLEET_COMMAND_ID": command["id"],
        }
        process = subprocess.Popen(
            command["argv"],
            cwd=command.get("cwd") or None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )
        stdout, stderr = process.communicate(
            timeout=int(command.get("timeout_seconds", 300))
        )
    except subprocess.TimeoutExpired as error:
        if process is not None:
            _terminate_process_group(process)
        return {**result, "status": "failed", "error": str(error)}
    except OSError as error:
        return {**result, "status": "failed", "error": str(error)}
    return {
        **result,
        "status": "passed" if process.returncode == 0 else "failed",
        "returncode": process.returncode,
        "stdout": stdout[-4000:],
        "stderr": stderr[-4000:],
    }


def _terminate_process_group(process: subprocess.Popen[str]) -> None:
    """Stop a timed-out adapter and every descendant it started."""
    for pid in _descendant_pids(process.pid):
        _signal_process(pid, signal.SIGTERM)
    _signal_process_group(process.pid, signal.SIGTERM)

    try:
        process.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        pass

    for pid in _descendant_pids(process.pid):
        _signal_process(pid, signal.SIGKILL)
    _signal_process_group(process.pid, signal.SIGKILL)
    try:
        process.kill()
    except ProcessLookupError:
        pass
    process.communicate()


def _descendant_pids(root_pid: int) -> list[int]:
    completed = subprocess.run(
        ["ps", "-axo", "pid=,ppid="],
        check=False,
        capture_output=True,
        text=True,
    )
    children: dict[int, list[int]] = {}
    for line in completed.stdout.splitlines():
        fields = line.split()
        if len(fields) != 2:
            continue
        pid, parent_pid = (int(value) for value in fields)
        children.setdefault(parent_pid, []).append(pid)

    descendants: list[int] = []
    pending = [root_pid]
    while pending:
        parent_pid = pending.pop()
        for child_pid in children.get(parent_pid, []):
            descendants.append(child_pid)
            pending.append(child_pid)
    return descendants


def _signal_process(pid: int, sig: signal.Signals) -> None:
    try:
        os.kill(pid, sig)
    except (PermissionError, ProcessLookupError):
        pass


def _signal_process_group(pid: int, sig: signal.Signals) -> None:
    try:
        os.killpg(pid, sig)
    except (PermissionError, ProcessLookupError):
        pass


def _run_pressure(
    manifest: JsonObject,
    *,
    packages: dict[str, JsonObject],
    project_root: Path,
    dry_run: bool,
) -> JsonObject | None:
    pressure = manifest.get("pressure")
    if not pressure or dry_run:
        return None
    registry_path = Path(pressure["registry"])
    if not registry_path.is_absolute():
        registry_path = project_root / registry_path
    for package_id, path in pressure.get("packages", {}).items():
        packages[package_id] = load_json(Path(path).expanduser())
    registry = load_pressure_registry(registry_path)
    validate_pressure_registry(
        registry,
        load_json(project_root / "schemas" / "package-pressure-question.schema.json"),
    )
    return run_package_pressure(
        registry,
        packages,
        include_planned=bool(pressure.get("include_planned", False)),
    )


def _write_read_model(
    state_root: Path,
    output_dir: str,
    filename: str,
    payload: JsonObject,
) -> Path:
    path = state_root / output_dir / filename
    _write_json(path, payload)
    return path


def _write_json(path: Path, payload: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source_counts(package: JsonObject) -> JsonObject:
    counts: dict[str, int] = {}
    for source in package.get("source_context", {}).get("source_readiness", []):
        key = "|".join(
            [
                source.get("access_status", "unknown"),
                source.get("freshness_status", "unknown"),
                source.get("understanding_status", "unknown"),
            ]
        )
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def _default_stale_after(checked_at: str, ttl_seconds: int) -> str:
    parsed = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
    return (parsed + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z")


def _derive_report_ttl(report: JsonObject, checked_at: object) -> int:
    """Best-effort TTL (seconds) for a fleet-refresh report read from disk.

    Prefer the report's own stale_after window (checked_at + ttl) so a consumer
    evaluates the same freshness contract the producer declared; fall back to a
    declared ttl field, then a sane default. Used by the report-age canary
    consumer which has no manifest in scope.
    """
    stale_after = report.get("stale_after")
    if isinstance(stale_after, str) and isinstance(checked_at, str):
        try:
            window = (
                parse_instant(stale_after) - parse_instant(checked_at)
            ).total_seconds()
            if window > 0:
                return int(window)
        except (ValueError, TypeError):
            pass
    for key in ("ttl_seconds", "default_ttl_seconds"):
        value = report.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
    return 3600


def _evaluate_report_age(
    *,
    checked_at: object,
    as_of: str,
    ttl_seconds: int,
    report_ref: object,
    exists: bool,
    unreadable: bool = False,
) -> JsonObject:
    """Pure freshness arithmetic for a fleet-refresh report.

    A report is fresh while ``checked_at`` is within ``ttl_seconds`` of
    ``as_of``; over-age, missing, unreadable, or undated reports fail. This is
    the core of the report-age canary: a self-referential field embedded at
    generation time can never be stale (it compares checked_at to a stale_after
    derived from the same checked_at), so it cannot detect a dead producer.
    Evaluating against an independent ``as_of`` (real wall-clock time, supplied
    by a consumer) is what makes the canary able to catch a launchd job whose
    report has frozen while time kept advancing.
    """
    result: JsonObject = {
        "checked_against": as_of,
        "ttl_seconds": ttl_seconds,
        "report_ref": str(report_ref),
        "exists": exists,
    }
    if not exists:
        return {**result, "status": "fail", "reason": "missing"}
    if unreadable:
        return {**result, "status": "fail", "reason": "unreadable"}
    if not isinstance(checked_at, str) or not checked_at:
        return {**result, "status": "fail", "reason": "missing_checked_at"}
    try:
        age_seconds = (parse_instant(as_of) - parse_instant(checked_at)).total_seconds()
    except (ValueError, TypeError):
        return {
            **result,
            "report_checked_at": checked_at,
            "status": "fail",
            "reason": "invalid_checked_at",
        }
    over_age = age_seconds > ttl_seconds
    return {
        **result,
        "report_checked_at": checked_at,
        "age_seconds": age_seconds,
        "status": "fail" if over_age else "pass",
        "reason": "over_age" if over_age else "fresh",
    }


def check_fleet_refresh_report_age(
    report_path: Path | str,
    *,
    as_of: str | None = None,
    ttl_seconds: int | None = None,
) -> JsonObject:
    """Consumer canary: evaluate a fleet-refresh report's age against real time.

    A live launchd job regenerates the fleet-refresh report on a fixed cadence.
    If the job dies, the report's ``checked_at`` freezes while wall-clock time
    keeps advancing. This reads the report from disk and compares its
    ``checked_at`` to ``as_of`` (default now); over-age, missing, or unreadable
    reports fail. An external watchdog (cron, a launchd probe, an agent loop)
    calls this and alerts on ``status == "fail"``.
    """
    path = Path(report_path)
    as_of_iso = as_of or _now_utc()
    if not path.exists():
        return _evaluate_report_age(
            checked_at=None,
            as_of=as_of_iso,
            ttl_seconds=ttl_seconds or 3600,
            report_ref=path,
            exists=False,
        )
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _evaluate_report_age(
            checked_at=None,
            as_of=as_of_iso,
            ttl_seconds=ttl_seconds or 3600,
            report_ref=path,
            exists=True,
            unreadable=True,
        )
    checked_at = report.get("checked_at")
    ttl = ttl_seconds if ttl_seconds is not None else _derive_report_ttl(report, checked_at)
    return _evaluate_report_age(
        checked_at=checked_at,
        as_of=as_of_iso,
        ttl_seconds=ttl,
        report_ref=path,
        exists=True,
    )


def validate_fleet_refresh_manifest(manifest: JsonObject, schema: JsonObject) -> list[str]:
    errors = validate_schema(manifest, schema)
    errors.extend(_validate_entity_current_state(manifest.get("entity_current_state")))
    return errors


_ECS_ROOT_FIELDS = {"state_root", "label", "output_dir"}


def _validate_entity_current_state(ecs: object) -> list[str]:
    """Enforce the entity_current_state oneOf the repo validator cannot.

    ``validate_schema`` checks type/required/enum only; it does not enforce
    oneOf branching, nested required keys, minItems, or additionalProperties.
    Invalid ECS shapes (empty roots, missing labels, unknown keys) would
    otherwise validate then crash or silently no-op at refresh time. This makes
    those failures fail at validation instead.
    """
    if ecs is None:
        return []
    if not isinstance(ecs, dict):
        return ["entity_current_state must be null, a single-root, or a multi-root object"]

    extra_top = set(ecs) - {"state_root", "output_dir", "roots"}
    if extra_top:
        return [
            f"entity_current_state has unknown keys: {sorted(extra_top)}; "
            "allowed: state_root, output_dir, roots"
        ]

    has_single = "state_root" in ecs
    has_multi = "roots" in ecs
    if has_single and has_multi:
        return [
            "entity_current_state is ambiguous: provide either state_root (single-root) "
            "or roots (multi-root), not both"
        ]
    if not has_single and not has_multi:
        return [
            "entity_current_state object must declare state_root (single-root) "
            "or roots (multi-root)"
        ]

    if has_single:
        if not str(ecs.get("state_root") or "").strip():
            return ["entity_current_state.state_root must be a non-empty string"]
        return []

    roots = ecs.get("roots")
    if not isinstance(roots, list) or not roots:
        return ["entity_current_state.roots must be a non-empty array"]
    errors: list[str] = []
    for index, root in enumerate(roots):
        if not isinstance(root, dict):
            errors.append(f"entity_current_state.roots[{index}] must be an object")
            continue
        missing = [key for key in ("state_root", "label") if not str(root.get(key) or "").strip()]
        if missing:
            errors.append(
                f"entity_current_state.roots[{index}] missing required non-empty: {missing}"
            )
        unknown = set(root) - _ECS_ROOT_FIELDS
        if unknown:
            errors.append(
                f"entity_current_state.roots[{index}] has unknown keys: {sorted(unknown)}; "
                f"allowed: {sorted(_ECS_ROOT_FIELDS)}"
            )
    return errors
