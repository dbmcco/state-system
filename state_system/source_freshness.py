from __future__ import annotations

import json
import re

from state_system.contracts import JsonObject
from state_system.stores import StateStoreBundle


def build_source_freshness_read_model(stores: StateStoreBundle) -> JsonObject:
    results = SourceFreshnessRuntime(stores).list_results()
    return {
        "id": "source_freshness_read_model",
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


class SourceFreshnessRuntime:
    def __init__(self, stores: StateStoreBundle):
        self.store = stores.source_freshness

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
                result["company_ref"],
                result["connector_ref"],
                result["source_ref"],
                result["checked_at"],
            ),
        )


def _normalize_result(result: JsonObject) -> JsonObject:
    record = dict(result)
    _validate_freshness_contract(record)
    record.setdefault("scope_key", _scope_key(record))
    record.setdefault("id", _result_id(record))
    record.setdefault("evidence_refs", [])
    record["freshness_is_recency_evidence"] = True
    record["proves_live_access"] = False
    record["authorizes_execution"] = False
    record["protected_action_authorized_by"] = "governance"
    return record


def _validate_freshness_contract(record: JsonObject) -> None:
    required = [
        "company_ref",
        "connector_ref",
        "source_ref",
        "connector_type",
        "status",
        "checked_at",
        "source_watermark",
        "stale_after",
        "watermark_basis",
        "status_reason",
    ]
    missing = [field for field in required if not record.get(field)]
    if missing:
        raise ValueError(
            "source freshness record missing required freshness contract "
            f"field(s): {', '.join(missing)}"
        )

    status = record["status"]
    basis = record["watermark_basis"]
    if status not in {"fresh", "stale", "failed", "unknown"}:
        raise ValueError(f"invalid freshness status: {status}")
    if basis not in {
        "source_content",
        "source_event",
        "source_index",
        "derived_index",
        "package_generation",
        "probe_only",
        "declared_gap",
    }:
        raise ValueError(f"invalid watermark_basis: {basis}")

    if status == "fresh" and basis in {
        "probe_only",
        "package_generation",
        "declared_gap",
    }:
        raise ValueError(f"fresh cannot be proven by {basis}")

    if basis in {"source_content", "source_event"} and not any(
        record.get(field)
        for field in [
            "latest_source_event_at",
            "latest_source_modified_at",
            "latest_decision_updated_at",
        ]
    ):
        raise ValueError(
            "source_content/source_event freshness requires a typed source "
            "timestamp such as latest_source_event_at or latest_source_modified_at"
        )

    if basis in {"source_index", "derived_index"} and not record.get(
        "latest_indexed_at"
    ):
        raise ValueError("source_index/derived_index freshness requires latest_indexed_at")

    if basis == "package_generation":
        if not record.get("latest_indexed_at"):
            raise ValueError("package_generation freshness requires generated_at/latest_indexed_at")
        if "generated_at" not in str(record.get("source_watermark", "")):
            raise ValueError("package_generation watermark must include generated_at")

    if basis == "probe_only":
        proof_text = " ".join(
            [
                str(record.get("source_watermark", "")),
                str(record.get("status_reason", "")),
            ]
        ).lower()
        if "unproven" not in proof_text and "not prove" not in proof_text:
            raise ValueError(
                "probe_only freshness must explicitly state that source/corpus "
                "freshness is unproven"
            )

    if basis == "declared_gap" and status == "fresh":
        raise ValueError("declared_gap cannot be fresh")


def _result_id(result: JsonObject) -> str:
    return (
        f"source_freshness.{_slug(result['scope_key'])}."
        f"{_slug(result['checked_at'])}"
    )


def _scope_key(result: JsonObject) -> str:
    return "|".join(
        [
            result["company_ref"],
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
