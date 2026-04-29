from __future__ import annotations

from copy import deepcopy

from state_system.stores import JsonObject


PROTECTED_PATCH_FIELDS = {
    "id",
    "type",
    "primary_family",
    "secondary_families",
    "state_traits",
    "scope",
    "as_of",
    "latest_journal_entry_id",
}


class ProtectedPatchFieldError(ValueError):
    """Raised when a journal patch tries to change materializer-owned fields."""


def materialize_snapshot(snapshot: JsonObject, journal_entry: JsonObject) -> JsonObject:
    result = deepcopy(snapshot)

    for key, value in journal_entry["state_patch"].items():
        if key in PROTECTED_PATCH_FIELDS:
            raise ProtectedPatchFieldError(key)
        result[key] = deepcopy(value)

    result["as_of"] = journal_entry["created_at"]
    result["latest_journal_entry_id"] = journal_entry["id"]
    result["evidence_refs"] = _merge_unique(
        snapshot.get("evidence_refs", []),
        [journal_entry["id"]],
        journal_entry.get("evidence_refs", []),
    )
    return result


def _merge_unique(*groups: list[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group:
            if value in seen:
                continue
            seen.add(value)
            values.append(value)
    return values
