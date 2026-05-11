from __future__ import annotations

from state_system.contracts import JsonObject


def build_crm_operating_picture_summary(picture: JsonObject) -> JsonObject:
    return {
        "id": f"{picture['id']}.summary",
        "system_of_record_ref": picture["system_of_record_ref"],
        "state_system_role": picture["state_system_role"],
        "relationship_count": len(picture["relationships"]),
        "active_opportunity_count": len(picture["opportunities"]),
        "open_loop_count": len(picture["open_loops"]),
        "recent_change_count": len(picture["recent_changes"]),
        "hidden_sales_scores": _hidden_sales_score_fields(picture),
    }


def _hidden_sales_score_fields(value: object, path: str = "$") -> list[str]:
    fields: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in {"sales_score", "lead_score", "referral_weight"}:
                fields.append(child_path)
            fields.extend(_hidden_sales_score_fields(child, child_path))
    if isinstance(value, list):
        for index, child in enumerate(value):
            fields.extend(_hidden_sales_score_fields(child, f"{path}[{index}]"))
    return fields
