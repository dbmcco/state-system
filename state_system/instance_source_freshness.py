from __future__ import annotations

import json
import re

from state_system.contracts import JsonObject
from state_system.stores import StateStoreBundle


def build_instance_source_freshness_read_model(stores: StateStoreBundle) -> JsonObject:
    results = InstanceSourceFreshnessRuntime(stores).list_results()
    return {
        "id": "instance_source_freshness_read_model",
        "artifact_type": "json_substrate",
        "generated_at": max((result["checked_at"] for result in results), default=""),
        "results": results,
        "latest_by_scope_key": _latest_by_scope_key(results),
        "invariant": {
            "freshness_is_recency_evidence": True,
            "preflight_proves_live_access": False,
            "proves_live_access": False,
            "authorizes_execution": False,
            "protected_action_authorized_by": "governance",
        },
    }


class InstanceSourceFreshnessRuntime:
    def __init__(self, stores: StateStoreBundle):
        self.store = stores.instance_source_freshness

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
                result["checked_at"],
            ),
        )


def _normalize_result(result: JsonObject) -> JsonObject:
    record = dict(result)
    record.setdefault("scope_key", _scope_key(record))
    record.setdefault("id", _result_id(record))
    record.setdefault("evidence_refs", [])
    record["freshness_is_recency_evidence"] = True
    record["proves_live_access"] = False
    record["authorizes_execution"] = False
    record["protected_action_authorized_by"] = "governance"
    return record


def _result_id(result: JsonObject) -> str:
    return (
        f"instance_source_freshness.{_slug(result['scope_key'])}."
        f"{_slug(result['checked_at'])}"
    )


def _scope_key(result: JsonObject) -> str:
    return "|".join(
        [
            result["instance_ref"],
            result["connector_ref"],
            result["source_ref"],
        ]
    )


def _latest_by_scope_key(results: list[JsonObject]) -> JsonObject:
    latest: dict[str, JsonObject] = {}
    for result in results:
        previous = latest.get(result["scope_key"])
        if previous is None or result["checked_at"] >= previous["checked_at"]:
            latest[result["scope_key"]] = result
    return latest


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
