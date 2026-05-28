from __future__ import annotations

from state_system.stores import JsonObject


def render_north_star_answer(answer: JsonObject) -> str:
    lines = [
        "North Star Answer",
        f"Query: {answer.get('query', '')}",
        f"Generated at: {answer.get('generated_at', '')}",
        "",
    ]
    answerability = answer.get("answerability", {})
    lines.extend(
        [
            f"Answerability: {answerability.get('status', '')}",
            f"Sources: {answerability.get('source_count', 0)}",
            f"Gaps: {answerability.get('gap_count', 0)}",
            "",
            "Current state",
        ]
    )
    for state in answer.get("current_state", []):
        lines.append(
            "- "
            + " | ".join(
                _present(
                    [
                        state.get("package_ref", ""),
                        state.get("instance_ref", ""),
                        state.get("agent_ref", ""),
                        state.get("review_goal", ""),
                    ]
                )
            )
        )

    lines.extend(["", "Evidence"])
    evidence = answer.get("evidence", {})
    _append_refs(lines, "Index refs", evidence.get("index_refs", []))
    _append_refs(lines, "Evidence refs", evidence.get("evidence_refs", []))
    _append_refs(
        lines,
        "Federated instance refs",
        evidence.get("federated_instance_refs", []),
    )

    uncertainty = answer.get("uncertainty", {})
    lines.extend(["", "Source gaps"])
    _append_refs(lines, "Gap refs", uncertainty.get("source_gap_refs", []))
    _append_refs(
        lines,
        "Unresolved evidence refs",
        uncertainty.get("unresolved_evidence_refs", []),
    )
    _append_refs(lines, "Open questions", uncertainty.get("open_questions", []))

    next_actions = answer.get("next_actions", {})
    lines.extend(
        [
            "",
            "Next actions",
            "- Requires refresh before external action: "
            + _bool(next_actions.get("requires_refresh_before_external_action")),
        ]
    )
    _append_refs(lines, "Repair gap refs", next_actions.get("repair_gap_refs", []))
    _append_refs(
        lines,
        "Route required actions",
        next_actions.get("route_required_actions", []),
    )

    broader_effects = answer.get("broader_effects", {})
    lines.extend(["", "Federated query routes"])
    routes = broader_effects.get("federated_query_routes", [])
    if routes:
        for route in routes:
            lines.extend(
                [
                    f"- Route: {route.get('route_ref', '')}",
                    f"  Source instance: {route.get('source_instance_ref', '')}",
                    f"  Query surface: {route.get('query_surface_ref', '')}",
                    "  Local materialization: "
                    + _bool(route.get("local_materialization")),
                ]
            )
            _append_refs(lines, "  Boundaries", route.get("boundaries", []))
    else:
        lines.append("- none")

    invariant = answer.get("invariant", {})
    lines.extend(
        [
            "",
            "Invariants",
            "- Ingests raw source data: " + _bool(invariant.get("ingests_raw_source_data")),
            "- Authorizes execution: " + _bool(invariant.get("authorizes_execution")),
            "- Federated raw materialization forbidden: "
            + _bool(invariant.get("federated_raw_materialization_forbidden")),
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def validate_render_invariants(answer: JsonObject) -> list[str]:
    errors: list[str] = []
    invariant = answer.get("invariant", {})
    if invariant.get("ingests_raw_source_data") is not False:
        errors.append("invariant.ingests_raw_source_data must be false")
    if invariant.get("authorizes_execution") is not False:
        errors.append("invariant.authorizes_execution must be false")
    if invariant.get("federated_raw_materialization_forbidden") is not True:
        errors.append("invariant.federated_raw_materialization_forbidden must be true")
    for route in answer.get("broader_effects", {}).get("federated_query_routes", []):
        if route.get("local_materialization") is not False:
            route_ref = route.get("route_ref", "<unknown>")
            errors.append(f"{route_ref} local_materialization must be false")
    return errors


def _append_refs(lines: list[str], label: str, values: list[object]) -> None:
    lines.append(f"{label}:")
    if values:
        lines.extend(f"- {value}" for value in values)
    else:
        lines.append("- none")


def _present(values: list[str]) -> list[str]:
    return [value for value in values if value]


def _bool(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "unknown"
