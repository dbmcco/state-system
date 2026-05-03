from __future__ import annotations

from state_system.contracts import validate_schema
from state_system.stores import JsonObject, StateStoreBundle


class AgentResponseValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("agent response validation failed")
        self.errors = tuple(errors)


def render_package_for_agent(package: JsonObject) -> str:
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
