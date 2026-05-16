from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from state_system.company_understanding_surface import (
    build_company_understanding_surface_read_model,
)
from state_system.contracts import JsonObject
from state_system.stores import StateStoreBundle


def build_interpreted_index_read_model(
    stores: StateStoreBundle,
    *,
    company_ref: str | None = None,
) -> JsonObject:
    surface = build_company_understanding_surface_read_model(stores)
    companies = [
        company
        for company in surface.get("companies", [])
        if company_ref is None or company.get("company_ref") == company_ref
    ]
    records = [
        record
        for company in companies
        for record in _company_records(company)
    ]
    return {
        "id": "state_system_interpreted_index_read_model",
        "artifact_type": "json_substrate",
        "generated_at": _generated_at(surface),
        "company_refs": [company["company_ref"] for company in companies],
        "records": records,
        "record_refs": [record["record_ref"] for record in records],
        "invariant": {
            "index_over_state_system_records": True,
            "ingests_raw_source_data": False,
            "search_executes_retrieval": True,
            "search_ranks_records": True,
            "model_owns_synthesis": True,
            "authorizes_execution": False,
        },
    }


def search_interpreted_index(
    read_model: JsonObject,
    *,
    query: str,
    limit: int = 10,
) -> JsonObject:
    query_tokens = _tokens(query)
    scored = [
        (_score(query_tokens, record), record)
        for record in read_model.get("records", [])
    ]
    matches = [
        record
        for score, record in sorted(
            scored,
            key=lambda item: (-item[0], item[1].get("record_ref", "")),
        )
        if score > 0
    ][: max(1, limit)]
    return {
        "id": "state_system_interpreted_search_result",
        "artifact_type": "json_substrate",
        "generated_at": _generated_at(read_model),
        "query": query,
        "company_refs": read_model.get("company_refs", []),
        "records": matches,
        "record_refs": [record["record_ref"] for record in matches],
        "invariant": {
            "retrieval_only": True,
            "model_owns_synthesis": True,
            "ingests_raw_source_data": False,
            "authorizes_execution": False,
        },
    }


def _company_records(company: JsonObject) -> list[JsonObject]:
    company_ref = company["company_ref"]
    records: list[JsonObject] = [
        _record(
            company_ref=company_ref,
            record_kind="company_operating_context",
            record_ref=f"company_context.{company_ref}",
            title=f"{company['name']} operating context",
            text=" ".join(
                [
                    company["name"],
                    company_ref,
                    "company memory",
                    " ".join(company.get("company_memory_refs", [])),
                    "operating picture",
                    " ".join(company.get("operating_picture_refs", [])),
                    "corpus",
                    " ".join(company.get("raw_corpus_refs", [])),
                ]
            ),
            evidence_refs=[],
            source_refs=company.get("raw_corpus_refs", []),
        )
    ]

    records.extend(_source_readiness_records(company))
    records.extend(_source_gap_records(company))
    records.extend(_searchable_surface_records(company))
    return records


def _source_readiness_records(company: JsonObject) -> list[JsonObject]:
    company_ref = company["company_ref"]
    records = []
    for source in company.get("source_readiness", []):
        connector_ref = source.get("connector_ref", "")
        records.append(
            _record(
                company_ref=company_ref,
                record_kind="source_readiness",
                record_ref=f"source_readiness.{company_ref}.{connector_ref}",
                title=f"{connector_ref} readiness",
                text=" ".join(
                    [
                        connector_ref,
                        source.get("connector_type", ""),
                        source.get("source_ref", ""),
                        f"access {source.get('access_status', '')}",
                        f"freshness {source.get('freshness_status', '')}",
                        f"index {source.get('index_status', '')}",
                        f"understanding {source.get('understanding_status', '')}",
                        " ".join(source.get("index_refs", [])),
                    ]
                ),
                evidence_refs=_evidence_refs_from_source(source),
                source_refs=[source.get("source_ref", "")],
            )
        )
    return records


def _source_gap_records(company: JsonObject) -> list[JsonObject]:
    company_ref = company["company_ref"]
    return [
        _record(
            company_ref=company_ref,
            record_kind="source_gap",
            record_ref=gap.get("gap_ref", ""),
            title=f"{gap.get('connector_ref', '')} {gap.get('reason', '')}",
            text=" ".join(
                [
                    gap.get("connector_ref", ""),
                    gap.get("source_ref", ""),
                    gap.get("reason", ""),
                    "source gap planned missing stale failed unknown",
                ]
            ),
            evidence_refs=[],
            source_refs=[gap.get("source_ref", "")],
        )
        for gap in company.get("source_gaps", [])
    ]


def _searchable_surface_records(company: JsonObject) -> list[JsonObject]:
    company_ref = company["company_ref"]
    records = []
    for surface in company.get("searchable_surfaces", []):
        records.append(
            _record(
                company_ref=company_ref,
                record_kind="searchable_surface",
                record_ref=f"searchable_surface.{surface.get('index_ref', '')}",
                title=surface.get("index_ref", ""),
                text=" ".join(
                    [
                        surface.get("index_ref", ""),
                        surface.get("status", ""),
                        surface.get("scope", ""),
                        surface.get("backend", ""),
                        " ".join(surface.get("record_kinds", [])),
                        " ".join(surface.get("source_refs", [])),
                        " ".join(surface.get("connector_refs", [])),
                        str(surface.get("query_surface", {}).get("tool_ref", "")),
                        str(surface.get("notes", "")),
                    ]
                ),
                evidence_refs=[],
                source_refs=surface.get("source_refs", []),
            )
        )
    return records


def _record(
    *,
    company_ref: str,
    record_kind: str,
    record_ref: str,
    title: str,
    text: str,
    evidence_refs: list[str],
    source_refs: list[str],
) -> JsonObject:
    return {
        "record_ref": record_ref,
        "company_ref": company_ref,
        "record_kind": record_kind,
        "title": title,
        "text": " ".join(text.split()),
        "evidence_refs": [ref for ref in evidence_refs if ref],
        "source_refs": [ref for ref in source_refs if ref],
    }


def _evidence_refs_from_source(source: JsonObject) -> list[str]:
    refs: list[str] = []
    for preflight in source.get("preflight_records", []):
        refs.extend(preflight.get("evidence_refs", []))
    refs.extend(source.get("freshness_record", {}).get("evidence_refs", []))
    return refs


def _score(query_tokens: list[str], record: JsonObject) -> int:
    if not query_tokens:
        return 0
    record_tokens = Counter(_tokens(_record_search_text(record)))
    return sum(record_tokens[token] for token in query_tokens)


def _record_search_text(record: JsonObject) -> str:
    return " ".join(
        [
            record.get("record_ref", ""),
            record.get("record_kind", ""),
            record.get("title", ""),
            record.get("text", ""),
        ]
    )


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", value.casefold())


def _generated_at(read_model: JsonObject) -> str:
    return str(
        read_model.get("generated_at")
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
