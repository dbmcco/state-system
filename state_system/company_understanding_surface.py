from __future__ import annotations

from state_system.company_capability import build_company_capability_read_model_from_runtime
from state_system.company_preflight import build_company_preflight_read_model
from state_system.contracts import JsonObject
from state_system.source_freshness import build_source_freshness_read_model
from state_system.stores import StateStoreBundle


def build_company_understanding_surface_read_model(
    stores: StateStoreBundle,
) -> JsonObject:
    capability = build_company_capability_read_model_from_runtime(stores)
    preflight = build_company_preflight_read_model(stores)
    freshness = build_source_freshness_read_model(stores)
    generated_at = max(
        (
            value
            for value in [
                capability.get("generated_at", ""),
                preflight.get("generated_at", ""),
                freshness.get("generated_at", ""),
            ]
            if value
        ),
        default="",
    )

    companies = [
        _company_surface(company, preflight, freshness)
        for company in capability.get("companies", [])
    ]

    return {
        "id": "company_understanding_surface_read_model",
        "artifact_type": "json_substrate",
        "generated_at": generated_at,
        "companies": companies,
        "index_refs": sorted(
            {
                manifest["index_ref"]
                for company in companies
                for manifest in company.get("searchable_surfaces", [])
            }
        ),
        "source_gap_refs": [
            gap["gap_ref"]
            for company in companies
            for gap in company.get("source_gaps", [])
        ],
        "invariant": {
            "surface_declares_retrieval_contract": True,
            "surface_executes_retrieval": False,
            "surface_ranks_or_synthesizes": False,
            "preflight_proves_live_access": True,
            "freshness_is_recency_evidence": True,
            "authorizes_execution": False,
            "protected_action_authorized_by": "governance",
        },
    }


def _company_surface(
    company: JsonObject,
    preflight_read_model: JsonObject,
    freshness_read_model: JsonObject,
) -> JsonObject:
    source_readiness = [
        _source_readiness(
            company,
            connector,
            preflight_read_model,
            freshness_read_model,
        )
        for connector in company.get("source_connectors", [])
    ]
    source_gaps = [
        gap
        for source in source_readiness
        for gap in source.get("gaps", [])
    ]
    return {
        "company_ref": company["company_ref"],
        "name": company["name"],
        "primary_agent_refs": company.get("primary_agent_refs", []),
        "oversight_agent_refs": company.get("oversight_agent_refs", []),
        "raw_corpus_refs": company.get("raw_corpus_refs", []),
        "company_memory_refs": company.get("company_memory_refs", []),
        "operating_picture_refs": company.get("operating_picture_refs", []),
        "searchable_surfaces": company.get("index_manifests", []),
        "source_readiness": source_readiness,
        "source_gaps": source_gaps,
    }


def _source_readiness(
    company: JsonObject,
    connector: JsonObject,
    preflight_read_model: JsonObject,
    freshness_read_model: JsonObject,
) -> JsonObject:
    company_ref = company["company_ref"]
    connector_ref = connector["id"]
    source_ref = connector["source_ref"]
    preflight_records = _preflight_records_for_connector(
        preflight_read_model,
        company_ref,
        connector_ref,
    )
    freshness_record = _freshness_record_for_source(
        freshness_read_model,
        company_ref,
        connector_ref,
        source_ref,
    )
    index_manifests = [
        manifest
        for manifest in company.get("index_manifests", [])
        if connector_ref in manifest.get("connector_refs", [])
        or source_ref in manifest.get("source_refs", [])
    ]
    access_status = _access_status(preflight_records)
    freshness_status = freshness_record.get("status", "missing")
    index_status = _index_status(index_manifests)
    gaps = _source_gaps(
        company_ref=company_ref,
        connector_ref=connector_ref,
        source_ref=source_ref,
        access_status=access_status,
        freshness_status=freshness_status,
        index_status=index_status,
    )
    return {
        "connector_ref": connector_ref,
        "connector_type": connector.get("connector_type", ""),
        "source_ref": source_ref,
        "access_status": access_status,
        "freshness_status": freshness_status,
        "index_status": index_status,
        "understanding_status": _understanding_status(
            access_status=access_status,
            freshness_status=freshness_status,
            index_status=index_status,
        ),
        "preflight_records": preflight_records,
        "freshness_record": freshness_record,
        "index_refs": [manifest["index_ref"] for manifest in index_manifests],
        "gaps": gaps,
    }


def _preflight_records_for_connector(
    preflight_read_model: JsonObject,
    company_ref: str,
    connector_ref: str,
) -> list[JsonObject]:
    records = [
        result
        for result in preflight_read_model.get("latest_by_scope_key", {}).values()
        if result.get("company_ref") == company_ref
        and result.get("connector_ref") == connector_ref
    ]
    return sorted(records, key=lambda record: record.get("checked_at", ""), reverse=True)


def _freshness_record_for_source(
    freshness_read_model: JsonObject,
    company_ref: str,
    connector_ref: str,
    source_ref: str,
) -> JsonObject:
    matching = [
        result
        for result in freshness_read_model.get("latest_by_scope_key", {}).values()
        if result.get("company_ref") == company_ref
        and result.get("connector_ref") == connector_ref
        and result.get("source_ref") == source_ref
    ]
    if not matching:
        return {}
    return sorted(matching, key=lambda record: record.get("checked_at", ""), reverse=True)[
        0
    ]


def _access_status(preflight_records: list[JsonObject]) -> str:
    statuses = {record.get("status") for record in preflight_records}
    if "passed" in statuses:
        return "passed"
    if "failed" in statuses:
        return "failed"
    return "missing"


def _index_status(index_manifests: list[JsonObject]) -> str:
    statuses = {manifest.get("status") for manifest in index_manifests}
    if "declared" in statuses:
        return "declared"
    if "planned" in statuses:
        return "planned"
    if "disabled" in statuses:
        return "disabled"
    return "missing"


def _understanding_status(
    *,
    access_status: str,
    freshness_status: str,
    index_status: str,
) -> str:
    if index_status == "declared" and access_status == "passed" and freshness_status == "fresh":
        return "ready"
    if index_status == "declared" and access_status == "passed":
        return "usable_with_freshness_gap"
    if index_status == "declared":
        return "searchable_access_unproven"
    if index_status == "planned":
        return "planned"
    return "gap"


def _source_gaps(
    *,
    company_ref: str,
    connector_ref: str,
    source_ref: str,
    access_status: str,
    freshness_status: str,
    index_status: str,
) -> list[JsonObject]:
    gaps: list[JsonObject] = []
    if access_status != "passed":
        gaps.append(
            _gap(company_ref, connector_ref, source_ref, f"access_{access_status}")
        )
    if freshness_status != "fresh":
        gaps.append(
            _gap(company_ref, connector_ref, source_ref, f"freshness_{freshness_status}")
        )
    if index_status != "declared":
        gaps.append(_gap(company_ref, connector_ref, source_ref, f"index_{index_status}"))
    return gaps


def _gap(
    company_ref: str,
    connector_ref: str,
    source_ref: str,
    reason: str,
) -> JsonObject:
    return {
        "gap_ref": f"gap.{company_ref}.{connector_ref}.{reason}",
        "company_ref": company_ref,
        "connector_ref": connector_ref,
        "source_ref": source_ref,
        "reason": reason,
    }
