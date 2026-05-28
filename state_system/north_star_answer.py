from __future__ import annotations

from typing import Any

from state_system.stores import JsonObject


NORTH_STAR_QUESTIONS = [
    "What is the current state?",
    "Why is that the state?",
    "What changed recently?",
    "What evidence supports it?",
    "What remains uncertain?",
    "Who or what is responsible?",
    "What should happen next?",
    "How does this affect the broader organization?",
]


def build_north_star_answer(
    packages: dict[str, JsonObject],
    *,
    query: str | None = None,
) -> JsonObject:
    package_items = [
        (package_ref, package)
        for package_ref, package in sorted(packages.items())
    ]
    package_values = [package for _, package in package_items]
    source_readiness = [
        _source_summary(package, source)
        for package in package_values
        for source in package.get("source_context", {}).get("source_readiness", [])
    ]
    source_gap_refs = _unique(
        gap_ref
        for package in package_values
        for gap_ref in package.get("source_context", {}).get("source_gap_refs", [])
    )
    unresolved_evidence_refs = _unique(
        ref
        for package in package_values
        for ref in package.get("evidence_context", {}).get("unresolved_evidence_refs", [])
    )
    open_questions = _unique(
        question
        for package in package_values
        for question in package.get("open_questions", [])
    )
    requires_refresh = any(
        package.get("freshness", {}).get("requires_refresh_before_external_action")
        for package in package_values
    )

    return {
        "id": "state_system_north_star_answer",
        "artifact_type": "json_substrate",
        "query": query or "What is the current state?",
        "north_star_questions": list(NORTH_STAR_QUESTIONS),
        "generated_at": _generated_at(package_values),
        "package_refs": [package_ref for package_ref, _ in package_items],
        "answerability": {
            "status": _answerability_status(
                source_readiness,
                source_gap_refs=source_gap_refs,
                unresolved_evidence_refs=unresolved_evidence_refs,
                open_questions=open_questions,
                requires_refresh=requires_refresh,
            ),
            "source_count": len(source_readiness),
            "gap_count": len(source_gap_refs) + len(unresolved_evidence_refs),
        },
        "current_state": [_current_state(package) for package in package_values],
        "why_this_state": {
            "source_readiness": source_readiness,
            "route_contract_refs": _unique(
                route.get("route_contract_ref", "")
                for package in package_values
                for route in package.get("question_routes", [])
            ),
            "answer_contracts": _unique(
                contract
                for package in package_values
                for route in package.get("question_routes", [])
                for contract in route.get("answer_contract", [])
            ),
        },
        "what_changed_recently": {
            "package_created_at": _unique(package.get("created_at", "") for package in package_values),
            "freshness_generated_at": _unique(
                package.get("freshness", {}).get("generated_at", "")
                for package in package_values
            ),
            "watermark_refs": _unique(
                ref
                for package in package_values
                for ref in package.get("freshness", {}).get("watermark_refs", [])
            ),
        },
        "evidence": {
            "index_refs": _unique(
                ref
                for package in package_values
                for ref in package.get("evidence_context", {}).get("index_refs", [])
            ),
            "evidence_refs": _unique(
                ref
                for package in package_values
                for ref in package.get("evidence_context", {}).get("evidence_refs", [])
            ),
            "federated_instance_refs": _unique(
                ref
                for package in package_values
                for ref in package.get("evidence_context", {}).get("federated_instance_refs", [])
            ),
        },
        "uncertainty": {
            "source_gap_refs": source_gap_refs,
            "unresolved_evidence_refs": unresolved_evidence_refs,
            "open_questions": open_questions,
            "not_ready_sources": [
                source
                for source in source_readiness
                if source.get("understanding_status") not in ("ready", "usable")
            ],
        },
        "responsibility": {
            "agent_refs": _unique(
                package.get("agent_context", {}).get("agent_ref", "")
                for package in package_values
            ),
            "persona_refs": _unique(
                package.get("agent_context", {}).get("persona_ref", "")
                for package in package_values
            ),
            "governance_refs": _unique(
                ref
                for package in package_values
                for ref in package.get("governance_context", {}).get("governance_refs", [])
            ),
            "constraints": _unique(
                constraint
                for package in package_values
                for constraint in package.get("governance_context", {}).get("constraints", [])
            ),
            "protected_action_authorized_by": _unique(
                package.get("governance_context", {}).get(
                    "protected_action_authorized_by", ""
                )
                for package in package_values
            ),
            "available_actions": _unique(
                action
                for package in package_values
                for action in package.get("available_actions", [])
            ),
        },
        "next_actions": {
            "requires_refresh_before_external_action": requires_refresh,
            "repair_gap_refs": source_gap_refs + unresolved_evidence_refs,
            "route_required_actions": _unique(
                action
                for package in package_values
                for route in package.get("question_routes", [])
                for action in route.get("required_actions", [])
            ),
        },
        "broader_effects": {
            "federation_packs": [
                _federation_pack_summary(pack)
                for package in package_values
                for pack in package.get("federation_packs", [])
            ],
            "federated_instance_refs": _unique(
                ref
                for package in package_values
                for ref in _package_federated_instance_refs(package)
            ),
            "federated_query_routes": [
                _query_route_summary(route)
                for package in package_values
                for route in package.get("question_routes", [])
                if route.get("federated_query") or route.get("query_route", {}).get("source_instance_ref")
            ],
        },
        "invariant": {
            "ingests_raw_source_data": False,
            "model_owns_synthesis": True,
            "authorizes_execution": False,
            "requires_evidence_refs": True,
            "federated_raw_materialization_forbidden": True,
        },
    }


def _current_state(package: JsonObject) -> JsonObject:
    agent = package.get("agent_context", {})
    return {
        "package_ref": package.get("id", ""),
        "package_type": package.get("package_type", ""),
        "created_at": package.get("created_at", ""),
        "instance_ref": package.get("instance_ref", ""),
        "primary_entity_ref": package.get("primary_entity_ref", ""),
        "entity_kind": package.get("entity_kind", ""),
        "agent_ref": agent.get("agent_ref", ""),
        "persona_ref": agent.get("persona_ref", ""),
        "review_goal": package.get("review_goal", ""),
    }


def _source_summary(package: JsonObject, source: JsonObject) -> JsonObject:
    return {
        "package_ref": package.get("id", ""),
        "connector_ref": source.get("connector_ref", ""),
        "connector_type": source.get("connector_type", ""),
        "source_ref": source.get("source_ref", ""),
        "access_status": source.get("access_status", ""),
        "freshness_status": source.get("freshness_status", ""),
        "index_status": source.get("index_status", ""),
        "understanding_status": source.get("understanding_status", ""),
        "index_refs": list(source.get("index_refs", [])),
        "gap_refs": list(source.get("gap_refs", [])),
        "evidence_refs": list(source.get("evidence_refs", [])),
    }


def _federation_pack_summary(pack: JsonObject) -> JsonObject:
    materialization = pack.get("materialization_policy", {})
    return {
        "id": pack.get("id", ""),
        "federation_mode": pack.get("federation_mode", ""),
        "remote_instance_refs": list(pack.get("remote_instance_refs", [])),
        "local_materialization": materialization.get("local_materialization"),
    }


def _query_route_summary(route: JsonObject) -> JsonObject:
    query_route = route.get("federated_query") or route.get("query_route", {})
    return {
        "route_ref": route.get("id", ""),
        "source_instance_ref": query_route.get("source_instance_ref", ""),
        "query_surface_ref": query_route.get("query_surface_ref", ""),
        "local_materialization": query_route.get("local_materialization"),
        "boundaries": list(query_route.get("boundaries", [])),
    }


def _package_federated_instance_refs(package: JsonObject) -> list[str]:
    refs = list(package.get("evidence_context", {}).get("federated_instance_refs", []))
    for pack in package.get("federation_packs", []):
        refs.extend(pack.get("remote_instance_refs", []))
    return refs


def _answerability_status(
    source_readiness: list[JsonObject],
    *,
    source_gap_refs: list[str],
    unresolved_evidence_refs: list[str],
    open_questions: list[str],
    requires_refresh: bool,
) -> str:
    if not source_readiness:
        return "not_ready"
    if source_gap_refs or unresolved_evidence_refs or open_questions or requires_refresh:
        return "usable_with_gaps"
    if all(source.get("understanding_status") == "ready" for source in source_readiness):
        return "ready"
    if any(
        source.get("understanding_status", "").startswith("usable")
        for source in source_readiness
    ):
        return "usable_with_gaps"
    return "not_ready"


def _generated_at(packages: list[JsonObject]) -> str:
    for package in packages:
        generated_at = package.get("freshness", {}).get("generated_at")
        if generated_at:
            return str(generated_at)
    for package in packages:
        created_at = package.get("created_at")
        if created_at:
            return str(created_at)
    return "unknown"


def _unique(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
