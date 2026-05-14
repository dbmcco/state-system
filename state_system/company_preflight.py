from __future__ import annotations

import json
import re

from state_system.contracts import JsonObject
from state_system.stores import StateStoreBundle


def build_company_preflight_read_model(stores: StateStoreBundle) -> JsonObject:
    results = CompanyPreflightRuntime(stores).list_results()
    return {
        "id": "company_preflight_result_read_model",
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


class CompanyPreflightRuntime:
    def __init__(self, stores: StateStoreBundle):
        self.store = stores.company_preflight_results

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


def _result_id(result: JsonObject) -> str:
    return (
        f"preflight_result.{_slug(result['scope_key'])}."
        f"{_slug(result['checked_at'])}"
    )


def _scope_key(result: JsonObject) -> str:
    return "|".join(
        [
            result["preflight_ref"],
            result["company_ref"],
            result.get("connector_ref", ""),
            result.get("tool_ref", ""),
            result.get("action_ref", ""),
            result.get("agent_ref", ""),
            result.get("runner_ref", ""),
        ]
    )


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")


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
