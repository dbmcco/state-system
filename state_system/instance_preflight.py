from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import urllib.error
import urllib.request

from state_system.contracts import JsonObject
from state_system.stores import StateStoreBundle

MSGVAULT_HEALTH_URL = "http://127.0.0.1:8080/health"
FOLIO_ROOT = Path("/Users/braydon/projects/experiments/folio")
RELATIONSHIP_SUBSTRATE_ROOT = Path(
    "/Users/braydon/projects/experiments/relationship-substrate"
)


def build_instance_preflight_read_model(stores: StateStoreBundle) -> JsonObject:
    results = InstancePreflightRuntime(stores).list_results()
    return {
        "id": "instance_preflight_result_read_model",
        "artifact_type": "json_substrate",
        "generated_at": max((result["checked_at"] for result in results), default=""),
        "results": results,
        "latest_by_scope_key": _latest_by_scope_key(results),
        "latest_by_preflight_ref": _latest_by_preflight_ref(results),
        "invariant": {
            "preflight_results_are_live_access_evidence": True,
            "authorizes_execution": False,
            "protected_action_authorized_by": "governance",
        },
    }


def run_instance_connector_preflight(
    stores: StateStoreBundle,
    instance_capability_pack: JsonObject,
    *,
    checked_at: str,
    stale_after: str,
    allow_network: bool = True,
    msgvault_health_url: str = MSGVAULT_HEALTH_URL,
) -> JsonObject:
    runtime = InstancePreflightRuntime(stores)
    records = [
        runtime.record(
            _connector_preflight_result(
                instance_capability_pack,
                connector,
                checked_at=checked_at,
                stale_after=stale_after,
                allow_network=allow_network,
                msgvault_health_url=msgvault_health_url,
            )
        )
        for connector in instance_capability_pack.get("source_connectors", [])
    ]
    return {
        "id": f"instance_preflight_run.{_slug(instance_capability_pack['instance_ref'])}.{_slug(checked_at)}",
        "instance_ref": instance_capability_pack["instance_ref"],
        "checked_at": checked_at,
        "stale_after": stale_after,
        "records": records,
        "invariant": {
            "mutates_source_systems": False,
            "copies_raw_corpora": False,
            "authorizes_execution": False,
        },
    }


class InstancePreflightRuntime:
    def __init__(self, stores: StateStoreBundle):
        self.store = stores.instance_preflight_results

    def record(self, result: JsonObject) -> JsonObject:
        record = _normalize_result(result)
        path = self.store.path_for(record["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return record

    def read(self, record_id: str) -> JsonObject:
        return self.store.read(record_id)

    def list_results(self) -> list[JsonObject]:
        return sorted(
            self.store.replay(),
            key=lambda result: (
                result["instance_ref"],
                result["connector_ref"],
                result["source_ref"],
                result["preflight_ref"],
                result.get("agent_ref") or "",
                result.get("runner_ref") or "",
                result["checked_at"],
            ),
        )


def _normalize_result(result: JsonObject) -> JsonObject:
    record = dict(result)
    record.setdefault("scope_key", _scope_key(record))
    record.setdefault("id", _result_id(record))
    record.setdefault("evidence_refs", [])
    record["proves_live_access"] = record["status"] == "passed"
    record["authorizes_execution"] = False
    record["protected_action_authorized_by"] = "governance"
    return record


def _connector_preflight_result(
    instance_capability_pack: JsonObject,
    connector: JsonObject,
    *,
    checked_at: str,
    stale_after: str,
    allow_network: bool,
    msgvault_health_url: str,
) -> JsonObject:
    status, detail, evidence_refs = _probe_connector(
        connector,
        allow_network=allow_network,
        msgvault_health_url=msgvault_health_url,
    )
    return {
        "preflight_ref": _preflight_ref(
            instance_capability_pack["instance_ref"],
            connector["id"],
        ),
        "instance_ref": instance_capability_pack["instance_ref"],
        "connector_ref": connector["id"],
        "source_ref": connector["source_ref"],
        "connector_type": connector.get("connector_type", ""),
        "status": status,
        "checked_at": checked_at,
        "stale_after": stale_after,
        "evidence_refs": evidence_refs,
        "detail": detail,
    }


def _probe_connector(
    connector: JsonObject,
    *,
    allow_network: bool,
    msgvault_health_url: str,
) -> tuple[str, str, list[str]]:
    connector_type = connector.get("connector_type", "")
    source_ref = connector.get("source_ref", "")

    if connector_type == "local_path":
        return _probe_path(_path_from_local_source(source_ref), "local_path")
    if connector_type == "relationship_substrate":
        return _probe_path(RELATIONSHIP_SUBSTRATE_ROOT, "relationship_substrate")
    if connector_type == "folio":
        return _probe_path(FOLIO_ROOT, "folio_root")
    if connector_type == "msgvault":
        return _probe_msgvault(allow_network, msgvault_health_url)
    if connector_type == "paia_workboard":
        return _probe_executable("wg", "paia_workboard_cli")
    if connector_type == "agentmem":
        return _probe_agentmem()
    if connector_type == "state_system_instance":
        return (
            "planned",
            "no_safe_probe_declared: state_system_instance root resolution belongs to federation task",
            [],
        )
    return (
        "planned",
        f"no_safe_probe_declared: unsupported connector_type {connector_type}",
        [],
    )


def _probe_path(path: Path, label: str) -> tuple[str, str, list[str]]:
    if path.exists():
        return "passed", f"{label} exists: {path}", [f"local-path:{path}"]
    return "failed", f"{label} missing: {path}", [f"local-path:{path}"]


def _probe_executable(command: str, label: str) -> tuple[str, str, list[str]]:
    path = shutil.which(command)
    if path:
        return "passed", f"{label} executable found: {path}", [f"executable:{command}"]
    return "planned", f"no_safe_probe_declared: {label} executable not found", []


def _probe_agentmem() -> tuple[str, str, list[str]]:
    home = os.environ.get("AGENTMEM_HOME")
    if home:
        return _probe_path(Path(home), "agentmem_home")
    return "planned", "no_safe_probe_declared: AGENTMEM_HOME is not set", []


def _probe_msgvault(
    allow_network: bool,
    health_url: str,
) -> tuple[str, str, list[str]]:
    if not allow_network:
        return "planned", "no_safe_probe_declared: network probes disabled", []
    request = urllib.request.Request(health_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=1) as response:
            status = getattr(response, "status", 0)
    except (OSError, urllib.error.URLError) as exc:
        return "failed", f"msgvault health check failed: {exc}", [health_url]
    if 200 <= status < 300:
        return "passed", f"msgvault health check passed: {health_url}", [health_url]
    return "failed", f"msgvault health check returned HTTP {status}", [health_url]


def _path_from_local_source(source_ref: str) -> Path:
    prefix = "local:"
    if source_ref.startswith(prefix):
        return Path(source_ref[len(prefix) :])
    return Path(source_ref)


def _preflight_ref(instance_ref: str, connector_ref: str) -> str:
    return f"preflight.{_slug(instance_ref)}.{_slug(connector_ref)}"


def _result_id(result: JsonObject) -> str:
    return (
        f"instance_preflight_result.{_slug(result['scope_key'])}."
        f"{_slug(result['checked_at'])}"
    )


def _scope_key(result: JsonObject) -> str:
    return "|".join(
        [
            result["instance_ref"],
            result["connector_ref"],
            result["source_ref"],
            result["preflight_ref"],
            result.get("tool_ref", ""),
            result.get("action_ref", ""),
            result.get("agent_ref", ""),
            result.get("runner_ref", ""),
        ]
    )


def _latest_by_preflight_ref(results: list[JsonObject]) -> JsonObject:
    latest: dict[str, JsonObject] = {}
    for result in results:
        previous = latest.get(result["preflight_ref"])
        if previous is None or result["checked_at"] >= previous["checked_at"]:
            latest[result["preflight_ref"]] = result
    return latest


def _latest_by_scope_key(results: list[JsonObject]) -> JsonObject:
    latest: dict[str, JsonObject] = {}
    for result in results:
        previous = latest.get(result["scope_key"])
        if previous is None or result["checked_at"] >= previous["checked_at"]:
            latest[result["scope_key"]] = result
    return latest


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
