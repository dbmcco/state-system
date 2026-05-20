from __future__ import annotations

from state_system.contracts import validate_schema
from state_system.stores import JsonObject, StateStoreBundle


class AgentResponseValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("agent response validation failed")
        self.errors = tuple(errors)


def render_package_for_agent(package: JsonObject) -> str:
    if package.get("package_type") == "instance_agent_package":
        return render_instance_agent_package_for_agent(package)

    lines: list[str] = [
        "State System Agent Package",
        f"Package: {package['id']}",
        f"Type: {package.get('package_type', 'unknown')}",
        f"Created at: {package.get('created_at', 'unknown')}",
        "",
    ]

    persona = package.get("persona_context", {})
    lines.extend(
        [
            f"Persona: {persona.get('persona_ref', 'unknown')}",
            _line("Persona summary", persona.get("summary")),
        ]
    )
    _append_list(lines, "Watched domains", persona.get("watched_domains", []))
    _append_list(lines, "Authority boundaries", persona.get("authority_boundaries", []))

    lines.extend(["", f"Review goal: {package.get('review_goal', '')}", ""])
    _append_recent_changes(lines, package)
    _append_state(lines, package)
    _append_journal(lines, package)
    _append_memory(lines, package)
    _append_evidence(lines, package)
    _append_governance(lines, package)
    _append_relationship_sensitivity(lines, package)
    _append_actions(lines, package)
    _append_excluded_context(lines, package)
    _append_open_questions(lines, package)
    _append_freshness(lines, package)
    _append_do_not(lines)

    return "\n".join(line for line in lines if line is not None).rstrip()


def render_instance_agent_package_for_agent(package: JsonObject) -> str:
    agent = package.get("agent_context", {})
    lines = [
        "State System Instance Agent Package",
        f"Package: {package['id']}",
        f"Instance: {package.get('instance_ref', 'unknown')}",
        f"Entity: {package.get('primary_entity_ref', 'unknown')} ({package.get('entity_kind', 'unknown')})",
        f"Created at: {package.get('created_at', 'unknown')}",
        "",
        f"Agent: {agent.get('agent_ref', 'unknown')}",
        f"Persona: {agent.get('persona_ref', 'unknown')}",
        _line("Agent summary", agent.get("summary")),
        "",
        f"Review goal: {package.get('review_goal', '')}",
        "",
        "Source readiness:",
    ]
    for source in package.get("source_context", {}).get("source_readiness", []):
        lines.append(
            f"- {source.get('connector_ref', 'unknown')}: "
            f"{source.get('understanding_status', 'unknown')} "
            f"(access={source.get('access_status', 'unknown')}, "
            f"freshness={source.get('freshness_status', 'unknown')}, "
            f"index={source.get('index_status', 'unknown')})"
        )
        if source.get("source_module_ref") or source.get("module_mode"):
            lines.append(
                f"  Module: {source.get('source_module_ref', 'unknown')} "
                f"via {source.get('module_registry_ref', 'unknown')} "
                f"(mode={source.get('module_mode', 'unknown')}, "
                f"usable={source.get('usable_access_status', 'unknown')})"
            )
        if source.get("checked_at") or source.get("source_watermark") or source.get("stale_after"):
            lines.append(
                f"  Freshness: checked_at={source.get('checked_at', 'unknown')}, "
                f"watermark={source.get('source_watermark', 'unknown')}, "
                f"stale_after={source.get('stale_after', 'unknown')}"
            )
        _append_inline_list(
            lines,
            "  Contract refs",
            [
                ref
                for ref in (
                    source.get("preflight_contract_ref"),
                    source.get("freshness_contract_ref"),
                    source.get("gap_behavior_ref"),
                )
                if ref
            ],
        )
        if source.get("planned_missing_reason"):
            lines.append(f"  Planned/missing reason: {source['planned_missing_reason']}")
        if source.get("pipeline_dependency"):
            lines.append(f"  Pipeline dependency: {source['pipeline_dependency']}")
        _append_inline_list(lines, "  Index refs", source.get("index_refs", []))
        _append_inline_list(lines, "  Gap refs", source.get("gap_refs", []))
        _append_inline_list(lines, "  Evidence refs", source.get("evidence_refs", []))
        federated = source.get("federated_instance", {})
        if federated:
            lines.append(
                f"  Federated instance: {federated.get('source_instance_ref', 'unknown')} "
                f"({federated.get('status', 'unknown')})"
            )
    lines.append("")

    evidence = package.get("evidence_context", {})
    lines.append("Evidence:")
    _append_list(lines, "Index refs", evidence.get("index_refs", []))
    _append_list(lines, "Evidence refs", evidence.get("evidence_refs", []))
    _append_list(lines, "Federated instance refs", evidence.get("federated_instance_refs", []))
    _append_list(
        lines,
        "Unresolved evidence refs",
        evidence.get("unresolved_evidence_refs", []),
    )
    lines.append("")

    governance = package.get("governance_context", {})
    lines.append("Governance:")
    _append_list(lines, "Governance refs", governance.get("governance_refs", []))
    _append_list(lines, "Constraints", governance.get("constraints", []))
    lines.append(
        f"Protected actions authorized by: {governance.get('protected_action_authorized_by', 'unknown')}"
    )
    lines.append("")

    _append_list(lines, "Available actions", package.get("available_actions", []))
    lines.append("")
    _append_federation_packs(lines, package.get("federation_packs", []))
    lines.append("")
    _append_question_routes(lines, package.get("question_routes", []))
    lines.append("")
    _append_list(lines, "Open questions", package.get("open_questions", []))
    lines.append("")

    freshness = package.get("freshness", {})
    lines.append("Freshness:")
    lines.append(f"- Generated at: {freshness.get('generated_at', 'unknown')}")
    _append_list(lines, "Watermark refs", freshness.get("watermark_refs", []))
    if freshness.get("requires_refresh_before_external_action"):
        lines.append("- Requires refresh before external action.")
    lines.append("")
    _append_do_not(lines)

    return "\n".join(line for line in lines if line is not None).rstrip()


def _append_question_routes(lines: list[str], routes: list[JsonObject]) -> None:
    lines.append("Question routes:")
    if not routes:
        lines.extend(["- None included.", ""])
        return
    for route in routes:
        lines.append(f"- {route.get('id', 'unknown')}: {route.get('intent', '')}")
        if route.get("route_contract_ref"):
            lines.append(f"  Route contract: {route['route_contract_ref']}")
        _append_inline_list(lines, "  Applies to", route.get("applies_to", []))
        _append_route_coverage(lines, route.get("required_source_coverage", []))
        _append_route_module_modes(lines, route.get("module_modes", []))
        _append_inline_list(lines, "  Source order", route.get("source_order", []))
        _append_inline_list(lines, "  Tool refs", route.get("tool_refs", []))
        _append_inline_list(lines, "  Tool action refs", route.get("tool_action_refs", []))
        _append_inline_list(lines, "  Required tools", route.get("required_tools", []))
        _append_inline_list(lines, "  Optional tools", route.get("optional_tools", []))
        _append_inline_list(
            lines,
            "  Optional external context tools",
            route.get("optional_external_context_tools", []),
        )
        _append_inline_list(lines, "  Capability refs", route.get("capability_refs", []))
        federated_query = route.get("federated_query", {})
        if federated_query:
            lines.append(
                f"  Federated query: {federated_query.get('query_surface_ref', 'unknown')} "
                f"from {federated_query.get('source_instance_ref', 'unknown')}"
            )
            lines.append(
                f"  Federated local materialization: {federated_query.get('local_materialization', 'unknown')}"
            )
            _append_inline_list(
                lines,
                "  Federated boundaries",
                federated_query.get("boundaries", []),
            )
        query_route = route.get("query_route", {})
        if query_route:
            lines.append(
                f"  Query route: {query_route.get('query_surface_ref', 'unknown')} "
                f"({query_route.get('status', 'unknown')})"
            )
            if "source_instance_ref" in query_route:
                lines.append(
                    f"  Source instance: {query_route.get('source_instance_ref', 'unknown')}"
                )
            lines.append(
                f"  Local materialization: {query_route.get('local_materialization', 'unknown')}"
            )
            _append_inline_list(lines, "  Boundaries", query_route.get("boundaries", []))
        _append_inline_list(lines, "  Required actions", route.get("required_actions", []))
        _append_inline_list(lines, "  Answer contract", route.get("answer_contract", []))
        answer_policy = route.get("answer_contract_policy", {})
        if answer_policy:
            lines.append(
                "  Answer policy: "
                f"evidence_refs={answer_policy.get('requires_evidence_refs', 'unknown')}, "
                f"freshness_summary={answer_policy.get('requires_source_freshness_summary', 'unknown')}, "
                f"separate_evidence={answer_policy.get('direct_evidence_vs_interpretation', 'unknown')}"
            )
            _append_inline_list(
                lines,
                "  Subject note policy",
                answer_policy.get("subject_note_policy", []),
            )
        fallback_policy = route.get("fallback_policy", {})
        if fallback_policy:
            lines.append(
                f"  Fallback policy: {fallback_policy.get('policy', '')}"
            )
            if fallback_policy.get("repair_gate"):
                lines.append(f"  Repair gate: {fallback_policy['repair_gate']}")
            if fallback_policy.get("external_context_rule"):
                lines.append(
                    f"  External context rule: {fallback_policy['external_context_rule']}"
                )
            _append_inline_list(
                lines,
                "  Fallback tool refs",
                fallback_policy.get("fallback_tool_refs", []),
            )
        gap_behavior = route.get("gap_behavior", {})
        if gap_behavior:
            lines.append(
                "  Gap behavior: "
                f"missing={gap_behavior.get('when_required_source_missing', '')}; "
                f"stale={gap_behavior.get('when_source_stale', '')}"
            )
            _append_inline_list(
                lines,
                "  Route gap refs",
                gap_behavior.get("relevant_gap_refs", []),
            )


def _append_federation_packs(lines: list[str], packs: list[JsonObject]) -> None:
    lines.append("Federation packs:")
    if not packs:
        lines.append("- None included.")
        return
    for pack in packs:
        materialization = pack.get("materialization_policy", {})
        freshness = pack.get("freshness_policy", {})
        lines.append(f"- {pack.get('id', 'unknown')}: {pack.get('status', 'unknown')}")
        lines.append(f"  Mode: {pack.get('federation_mode', 'unknown')}")
        _append_inline_list(lines, "  Remote instances", pack.get("remote_instance_refs", []))
        _append_inline_list(lines, "  Routes", pack.get("route_refs", []))
        _append_inline_list(lines, "  Tool action refs", pack.get("tool_action_refs", []))
        lines.append(
            f"  Local materialization: {materialization.get('local_materialization', 'unknown')}"
        )
        if materialization.get("raw_remote_corpus_policy"):
            lines.append(
                f"  Raw corpus policy: {materialization['raw_remote_corpus_policy']}"
            )
        lines.append(
            f"  Federation freshness: {freshness.get('freshness_status', 'unknown')} "
            f"checked_at={freshness.get('checked_at', '')} "
            f"watermark={freshness.get('source_watermark', '')}"
        )
        _append_inline_list(lines, "  Federation gap refs", freshness.get("gap_refs", []))
        subject_note_policy = pack.get("subject_note_policy", {})
        if subject_note_policy:
            lines.append(
                f"  Subject note policy: applies={subject_note_policy.get('applies', 'unknown')}; "
                f"{subject_note_policy.get('policy', '')}"
            )


def _append_route_coverage(lines: list[str], coverage: list[JsonObject]) -> None:
    if not coverage:
        return
    lines.append("  Required source coverage:")
    for item in coverage:
        connectors = ", ".join(item.get("connector_refs", [])) or "none"
        modules = ", ".join(item.get("source_module_refs", [])) or "none"
        lines.append(
            f"    - {item.get('coverage_ref', 'coverage')}: "
            f"{item.get('minimum_status', 'unknown')} "
            f"(connectors={connectors}; modules={modules})"
        )


def _append_route_module_modes(lines: list[str], modes: list[JsonObject]) -> None:
    if not modes:
        return
    lines.append("  Module modes:")
    for mode in modes:
        lines.append(
            f"    - {mode.get('source_module_ref', 'unknown')}: "
            f"{mode.get('mode', 'unknown')}"
        )


def capture_agent_response(
    stores: StateStoreBundle,
    schemas: dict[str, JsonObject],
    *,
    package_id: str,
    consumer_ref: str,
    response_text: str,
    created_at: str,
    response_id: str | None = None,
    activation_id: str | None = None,
    evidence_refs: list[str] | None = None,
) -> JsonObject:
    package = stores.context_packages.read(package_id)
    refs = list(evidence_refs) if evidence_refs is not None else _package_evidence_refs(package)
    if activation_id and activation_id not in refs:
        refs = [activation_id, *refs]
    record = {
        "id": response_id
        or _default_response_id(
            package_id=package_id,
            consumer_ref=consumer_ref,
            created_at=created_at,
        ),
        "package_id": package_id,
        "consumer_ref": consumer_ref,
        "created_at": created_at,
        "response_text": response_text,
        "evidence_refs": refs,
        "status": "captured",
        "extraction_status": "not_extracted",
        "proposed_effect_refs": [],
    }
    if activation_id:
        record["activation_id"] = activation_id
    errors = validate_schema(record, schemas["agent_response"])
    if errors:
        raise AgentResponseValidationError(errors)
    stores.agent_responses.create(record)
    return record


def _append_recent_changes(lines: list[str], package: JsonObject) -> None:
    entries = package.get("recent_change_context", {}).get("entries", [])
    lines.append("Recent changes:")
    if not entries:
        lines.extend(["- None included.", ""])
        return
    for entry in entries:
        route = entry.get("persona_route", {})
        lines.append(f"- {entry.get('id', 'unknown')}: {entry.get('summary', '')}")
        lines.append(f"  Relevance: {route.get('relevance_tier', 'unknown')}")
        lines.append(f"  Why relevant: {route.get('routing_reason', '')}")
        _append_inline_list(lines, "  Source refs", entry.get("source_refs", []))
        _append_inline_list(
            lines,
            "  Affected state",
            entry.get("affected_state_refs", []),
        )
    lines.append("")


def _append_state(lines: list[str], package: JsonObject) -> None:
    snapshots = package.get("state_context", {}).get("snapshots", [])
    lines.append("Current state:")
    if not snapshots:
        lines.extend(["- None included.", ""])
        return
    for snapshot in snapshots:
        lines.append(
            f"- {snapshot.get('id', 'unknown')}: "
            f"{snapshot.get('summary', snapshot.get('name', ''))}"
        )
        if snapshot.get("status"):
            lines.append(f"  Status: {snapshot['status']}")
        if snapshot.get("uncertainties"):
            _append_inline_list(lines, "  Uncertainties", snapshot["uncertainties"])
    lines.append("")


def _append_journal(lines: list[str], package: JsonObject) -> None:
    entries = package.get("journal_context", {}).get("recent_entries", [])
    lines.append("Journal:")
    if not entries:
        lines.extend(["- None included.", ""])
        return
    for entry in entries:
        lines.append(
            f"- {entry.get('id', 'unknown')}: "
            f"{entry.get('summary', entry.get('change_summary', ''))}"
        )
    lines.append("")


def _append_memory(lines: list[str], package: JsonObject) -> None:
    entries = package.get("memory_context", {}).get("entries", [])
    lines.append("Memory:")
    if not entries:
        lines.extend(["- None included.", ""])
        return
    for entry in entries:
        lines.append(
            f"- {entry.get('id', 'unknown')}: "
            f"{entry.get('summary', entry.get('memory', ''))}"
        )
    lines.append("")


def _append_evidence(lines: list[str], package: JsonObject) -> None:
    evidence = package.get("evidence_context", {})
    lines.append("Evidence:")
    _append_list(lines, "Evidence refs", evidence.get("evidence_refs", []))
    resolved = evidence.get("resolved_evidence", [])
    if resolved:
        lines.append("Resolved evidence:")
        for item in resolved:
            lines.append(f"- {item.get('ref', 'unknown')}: {item.get('summary', '')}")
    _append_list(
        lines,
        "Unresolved evidence refs",
        evidence.get("unresolved_evidence_refs", []),
    )
    lines.append("")


def _append_governance(lines: list[str], package: JsonObject) -> None:
    constraints = package.get("governance_context", {}).get("constraints", [])
    lines.append("Governance:")
    if not constraints:
        lines.extend(["- None included.", ""])
        return
    for constraint in constraints:
        approval = (
            "approval required"
            if constraint.get("approval_required")
            else "no approval flag"
        )
        lines.append(
            f"- {constraint.get('id', 'unknown')}: "
            f"{constraint.get('summary', '')} ({approval})"
        )
    lines.append("")


def _append_relationship_sensitivity(lines: list[str], package: JsonObject) -> None:
    sensitivity = package.get("relationship_sensitivity", {})
    lines.append("Relationship sensitivity:")
    lines.append(
        f"- Level: {sensitivity.get('level', 'unknown')}. "
        f"{sensitivity.get('summary', '')}"
    )
    _append_list(lines, "Redactions", sensitivity.get("redactions", []))
    lines.append("")


def _append_actions(lines: list[str], package: JsonObject) -> None:
    actions = package.get("available_actions", [])
    lines.append("Available actions:")
    if not actions:
        lines.extend(["- None included.", ""])
        return
    for action in actions:
        approval = (
            "requires approval"
            if action.get("approval_required")
            else "no approval required"
        )
        lines.append(
            f"- {action.get('id', 'unknown')}: {action.get('summary', '')} "
            f"({approval})"
        )
    lines.append("")


def _append_excluded_context(lines: list[str], package: JsonObject) -> None:
    excluded = package.get("excluded_context_summary", [])
    lines.append("Excluded context:")
    if not excluded:
        lines.extend(["- None recorded.", ""])
        return
    for item in excluded:
        lines.append(
            f"- {item.get('recent_change_ref', item.get('id', 'unknown'))}: "
            f"{item.get('summary', '')}"
        )
    lines.append("")


def _append_open_questions(lines: list[str], package: JsonObject) -> None:
    _append_list(lines, "Open questions", package.get("open_questions", []))
    lines.append("")


def _append_freshness(lines: list[str], package: JsonObject) -> None:
    freshness = package.get("freshness", {})
    lines.append("Freshness:")
    lines.append(f"- Valid until: {freshness.get('valid_until', 'unknown')}")
    _append_list(lines, "Watermark refs", freshness.get("watermark_refs", []))
    _append_list(lines, "Stale if refs change", freshness.get("stale_if_refs_change", []))
    if freshness.get("requires_refresh_before_external_action"):
        lines.append("- Requires refresh before external action.")
    lines.append("")


def _append_do_not(lines: list[str]) -> None:
    lines.extend(
        [
            "Do not:",
            "- Treat this package as permission to take external action.",
            "- Publish, commit, or promise anything that governance marks approval-gated.",
            "- Ignore unresolved evidence refs or freshness requirements.",
        ]
    )


def _append_list(lines: list[str], title: str, values: list[object]) -> None:
    lines.append(f"{title}:")
    if not values:
        lines.append("- None.")
        return
    for value in values:
        lines.append(f"- {_format_value(value)}")


def _append_inline_list(lines: list[str], title: str, values: list[object]) -> None:
    if values:
        lines.append(f"{title}: {', '.join(_format_value(value) for value in values)}")


def _line(title: str, value: object) -> str:
    return f"{title}: {_format_value(value)}"


def _format_value(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("summary") or value.get("id") or value)
    return str(value)


def _package_evidence_refs(package: JsonObject) -> list[str]:
    evidence = [package["id"]]
    evidence.extend(package.get("evidence_context", {}).get("evidence_refs", []))
    evidence.extend(package.get("freshness", {}).get("watermark_refs", []))
    return _unique(evidence)


def _default_response_id(*, package_id: str, consumer_ref: str, created_at: str) -> str:
    timestamp = (
        created_at.replace("-", "")
        .replace(":", "")
        .replace(".", "")
        .replace("+", "")
    )
    return f"response.{package_id}.{consumer_ref}.{timestamp}"


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
