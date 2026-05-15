from __future__ import annotations

import json
from pathlib import Path

from state_system.company_capability import CompanyCapabilityRuntime
from state_system.contracts import JsonObject
from state_system.source_freshness import (
    SourceFreshnessRuntime,
    build_source_freshness_read_model,
)
from state_system.stores import StateStoreBundle


DELEGATED_CONNECTOR_TYPES = {
    "folio",
    "gws_drive",
    "gws_account",
    "linear",
    "msgvault",
    "repo",
    "crm",
    "docs",
}


def run_source_heartbeat(
    stores: StateStoreBundle,
    *,
    company_ref: str | None,
    checked_at: str,
    stale_after: str,
    output_dir: Path,
) -> JsonObject:
    companies = _selected_companies(stores, company_ref)
    runtime = SourceFreshnessRuntime(stores)
    records: list[JsonObject] = []

    for company in companies:
        for connector in company["source_connectors"]:
            record = _freshness_record_for_connector(
                company_ref=company["company_ref"],
                connector=connector,
                checked_at=checked_at,
                stale_after=stale_after,
            )
            records.append(runtime.record(record))

    read_model = build_source_freshness_read_model(stores)
    read_model_path = output_dir / "source-freshness-read-model.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    read_model_path.write_text(
        json.dumps(read_model, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {
        "id": f"source_heartbeat.{company_ref or 'all'}",
        "company_ref": company_ref,
        "checked_at": checked_at,
        "stale_after": stale_after,
        "recorded": len(records),
        "status_counts": _status_counts(records),
        "read_model_id": read_model["id"],
        "read_model_path": str(read_model_path),
        "records": records,
        "invariant": {
            "state_system_orchestrates_heartbeat": True,
            "local_path_checked_directly": True,
            "credentialed_connectors_are_delegated": True,
            "ingests_raw_source_data": False,
        },
    }


def _selected_companies(
    stores: StateStoreBundle,
    company_ref: str | None,
) -> list[JsonObject]:
    runtime = CompanyCapabilityRuntime(stores)
    if company_ref:
        return [runtime.read_company(company_ref)]
    return runtime.list_packs()


def _freshness_record_for_connector(
    *,
    company_ref: str,
    connector: JsonObject,
    checked_at: str,
    stale_after: str,
) -> JsonObject:
    connector_type = connector["connector_type"]
    if connector_type == "local_path":
        return _local_path_record(company_ref, connector, checked_at, stale_after)
    if connector_type in DELEGATED_CONNECTOR_TYPES:
        return _delegated_record(company_ref, connector, checked_at, stale_after)
    return _unsupported_record(company_ref, connector, checked_at, stale_after)


def _local_path_record(
    company_ref: str,
    connector: JsonObject,
    checked_at: str,
    stale_after: str,
) -> JsonObject:
    source_ref = connector["source_ref"]
    path = Path(source_ref.removeprefix("local:")).expanduser()
    base = _base_record(company_ref, connector, checked_at, stale_after)
    if path.exists():
        stat = path.stat()
        return {
            **base,
            "status": "fresh",
            "source_watermark": f"local.mtime_ns:{stat.st_mtime_ns}",
            "lag_seconds": 0,
            "evidence_refs": [f"state-system:heartbeat:local_path:{connector['id']}"],
            "detail": f"State System directly checked local path metadata for {path}.",
        }
    return {
        **base,
        "status": "failed",
        "source_watermark": "local.path_missing",
        "evidence_refs": [f"state-system:heartbeat:local_path:{connector['id']}"],
        "error": {
            "code": "path_missing",
            "message": f"Local path does not exist: {path}",
        },
        "detail": "State System directly checked local path metadata.",
    }


def _delegated_record(
    company_ref: str,
    connector: JsonObject,
    checked_at: str,
    stale_after: str,
) -> JsonObject:
    return {
        **_base_record(company_ref, connector, checked_at, stale_after),
        "status": "unknown",
        "source_watermark": "delegated:not_checked",
        "evidence_refs": [f"state-system:heartbeat:delegated:{connector['id']}"],
        "error": {
            "code": "delegated_connector",
            "message": (
                f"{connector['connector_type']} freshness requires an external "
                "connector adapter."
            ),
        },
        "detail": (
            "State System orchestrated heartbeat and recorded the adapter "
            "boundary; no credentialed source call was made."
        ),
    }


def _unsupported_record(
    company_ref: str,
    connector: JsonObject,
    checked_at: str,
    stale_after: str,
) -> JsonObject:
    return {
        **_base_record(company_ref, connector, checked_at, stale_after),
        "status": "unknown",
        "source_watermark": "unsupported:not_checked",
        "evidence_refs": [f"state-system:heartbeat:unsupported:{connector['id']}"],
        "error": {
            "code": "unsupported_connector",
            "message": f"No heartbeat adapter for {connector['connector_type']}.",
        },
        "detail": "State System has no direct or delegated heartbeat adapter yet.",
    }


def _base_record(
    company_ref: str,
    connector: JsonObject,
    checked_at: str,
    stale_after: str,
) -> JsonObject:
    return {
        "company_ref": company_ref,
        "connector_ref": connector["id"],
        "source_ref": connector["source_ref"],
        "connector_type": connector["connector_type"],
        "checked_at": checked_at,
        "stale_after": stale_after,
    }


def _status_counts(records: list[JsonObject]) -> JsonObject:
    counts: dict[str, int] = {}
    for record in records:
        status = record["status"]
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))
