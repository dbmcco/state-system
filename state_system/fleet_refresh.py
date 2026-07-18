from __future__ import annotations

import json
import os
import signal
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from state_system.contracts import JsonObject, load_json, validate_schema
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
        )
        for instance in manifest.get("instances", [])
    ]
    packages = {
        result["package_id"]: load_json(Path(result["package_path"]))
        for result in instance_results
        if result.get("package_path") and Path(result["package_path"]).exists()
    }
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
        and (pressure_report is None or pressure_report["ok"]),
        "instance_count": len(instance_results),
        "instances": instance_results,
        "pressure_report": pressure_report,
        "invariant": {
            "delegated_sources_require_adapter_evidence": True,
            "runner_materializes_raw_source_corpora": False,
            "package_regeneration_is_not_live_access_proof": True,
        },
    }
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "fleet-refresh-report.json"
        _write_json(report_path, report)
        report["report_path"] = str(report_path)
    return report


def _refresh_instance(
    config: JsonObject,
    *,
    project_root: Path,
    checked_at: str,
    stale_after: str,
    dry_run: bool,
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
    # Reviewer is None until a live reviewer is wired; until then this writes
    # an honest empty read model so the file exists for consumers without any
    # fabricated judgment. Code owns load/run/write; the reviewer owns judgment.
    staleness_path = refresh_strategic_staleness_read_model(
        state_root,
        as_of=parse_instant(checked_at),
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


def validate_fleet_refresh_manifest(manifest: JsonObject, schema: JsonObject) -> list[str]:
    return validate_schema(manifest, schema)
