from __future__ import annotations

from pathlib import Path

from state_system.contracts import JsonObject, load_json, validate_schema


class InstanceFederationPackValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("instance federation pack validation failed")
        self.errors = tuple(errors)


def load_instance_federation_pack_registry(path: Path) -> JsonObject:
    return load_json(path)


def validate_instance_federation_pack_registry(
    registry: JsonObject,
    schema: JsonObject,
) -> None:
    errors = validate_schema(registry, schema)
    errors.extend(_semantic_errors(registry))
    if errors:
        raise InstanceFederationPackValidationError(errors)


def render_instance_federation_pack_registry(registry: JsonObject) -> str:
    lines = [
        "State System Instance Federation Packs",
        f"Registry: {registry.get('id', 'unknown')}",
        f"Generated at: {registry.get('generated_at', 'unknown')}",
        "",
    ]
    for pack in registry.get("packs", []):
        materialization = pack.get("materialization_policy", {})
        freshness = pack.get("freshness_policy", {})
        lines.extend(
            [
                f"- {pack.get('id', 'unknown')}: {pack.get('status', 'unknown')}",
                f"  Mode: {pack.get('federation_mode', 'unknown')}",
                f"  Local: {pack.get('local_instance_ref', 'unknown')}",
                f"  Remote: {', '.join(pack.get('remote_instance_refs', [])) or 'unknown'}",
                f"  Local materialization: {materialization.get('local_materialization', 'unknown')}",
                f"  Raw corpus policy: {materialization.get('raw_remote_corpus_policy', '')}",
                f"  Freshness: {freshness.get('freshness_status', 'unknown')} "
                f"checked_at={freshness.get('checked_at', '')} "
                f"watermark={freshness.get('source_watermark', '')}",
            ]
        )
        _append_inline_list(lines, "  Routes", pack.get("route_refs", []))
        _append_inline_list(lines, "  Query surfaces", pack.get("query_surface_refs", []))
        _append_inline_list(lines, "  Tool actions", pack.get("tool_action_refs", []))
        _append_inline_list(lines, "  Source modules", pack.get("source_module_refs", []))
        _append_inline_list(lines, "  Gap refs", freshness.get("gap_refs", []))
        subject_note_policy = pack.get("subject_note_policy", {})
        if subject_note_policy:
            lines.append(
                f"  Subject notes: applies={subject_note_policy.get('applies', 'unknown')} "
                f"policy={subject_note_policy.get('policy', '')}"
            )
        repair = pack.get("repair_policy", {})
        if repair:
            lines.append(f"  Repair owner: {repair.get('owner', 'unknown')}")
            lines.append(f"  When unavailable: {repair.get('when_unavailable', '')}")
            lines.append(f"  When stale: {repair.get('when_stale', '')}")
    return "\n".join(lines).rstrip()


def _semantic_errors(registry: JsonObject) -> list[str]:
    errors: list[str] = []
    for index, pack in enumerate(registry.get("packs", [])):
        path = f"$.packs[{index}]"
        materialization = pack.get("materialization_policy", {})
        invariant = pack.get("invariant", {})
        if materialization.get("local_materialization") is True:
            allowed = set(materialization.get("allowed_artifact_types", []))
            if "raw_corpus" in allowed or "raw_remote_corpus" in allowed:
                errors.append(f"{path}: raw remote corpus cannot be materialized")
        if invariant.get("pack_does_not_copy_raw_remote_data") is not True:
            errors.append(f"{path}: pack must prohibit raw remote data copies")
    return errors


def _append_inline_list(lines: list[str], label: str, values: list[str]) -> None:
    if values:
        lines.append(f"{label}: {', '.join(values)}")
