# ABOUTME: Pure canonical-claim store diff watcher for human direct edits.
# ABOUTME: Detects add/edit/delete only; semantic reconciliation is reviewer-owned.
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from state_system.stores import JsonObject, StateStoreBundle


CHANGE_ADD = "add"
CHANGE_EDIT = "edit"
CHANGE_DELETE = "delete"
STATUS_UNRECONCILED = "unreconciled"
STATUS_RECONCILED = "reconciled"
STATUS_PENDING_HUMAN_REVIEW = "pending_human_review"
STATUS_FLAGGED = "flagged"


def scan_canon_edits(
    state_root: Path | str,
    *,
    baseline_path: Path | str,
    detected_at: str | None = None,
) -> JsonObject:
    """Detect raw canonical-claim adds/edits/deletes and queue edit items.

    This function is intentionally pure mechanical diffing. It never decides
    whether an edit is a supersession, amendment, retraction, add, or uncertain;
    that judgment belongs to the reviewer in ``canon_reconcile``.

    The persisted baseline includes each claim's content hash and record snapshot.
    The hash map satisfies the cron diff contract, while the retained snapshot is
    required so a vanished claim can emit ``change_type=delete`` with
    ``before=<prior record>`` instead of silently disappearing.
    """
    root = Path(state_root)
    baseline = _load_baseline(Path(baseline_path))
    current = _snapshot_claims(StateStoreBundle(root))
    now = detected_at or _now()
    emitted: list[JsonObject] = []
    store = StateStoreBundle(root).canon_edits
    # Idempotent: a re-scan after a lost/reset baseline must not crash on edits
    # already queued (identical content yields an identical edit id). Skip
    # duplicates so the cron diff is safe to re-run on the same state.
    existing_ids = set(store.list_ids())

    def _queue(edit: JsonObject) -> None:
        if edit["id"] in existing_ids:
            return
        store.create(edit)
        existing_ids.add(edit["id"])
        emitted.append(edit)

    for claim_id in sorted(set(current) - set(baseline)):
        _queue(_edit_record(
            state_root=root,
            detected_at=now,
            change_type=CHANGE_ADD,
            target_claim_id=claim_id,
            before=None,
            after=current[claim_id]["record"],
        ))

    for claim_id in sorted(set(current) & set(baseline)):
        if current[claim_id]["hash"] == baseline[claim_id]["hash"]:
            continue
        _queue(_edit_record(
            state_root=root,
            detected_at=now,
            change_type=CHANGE_EDIT,
            target_claim_id=claim_id,
            before=baseline[claim_id].get("record"),
            after=current[claim_id]["record"],
        ))

    for claim_id in sorted(set(baseline) - set(current)):
        _queue(_edit_record(
            state_root=root,
            detected_at=now,
            change_type=CHANGE_DELETE,
            target_claim_id=claim_id,
            before=baseline[claim_id].get("record"),
            after=None,
        ))

    _write_baseline(Path(baseline_path), current)
    return {
        "ok": True,
        "state_root": str(root),
        "baseline_path": str(Path(baseline_path)),
        "detected_at": now,
        "emitted_count": len(emitted),
        "edits": emitted,
        "invariant": {
            "diff_detection_only": True,
            "semantic_judgment_performed": False,
            "delete_detection_enabled": True,
        },
    }


def pending_canon_edits(stores: StateStoreBundle, *, entity_ref: str | None = None) -> list[JsonObject]:
    edits = [
        deepcopy(edit)
        for edit in stores.canon_edits.replay()
        if edit.get("status") in {STATUS_UNRECONCILED, STATUS_PENDING_HUMAN_REVIEW}
    ]
    if entity_ref is not None:
        edits = [edit for edit in edits if _edit_entity_ref(edit) == entity_ref]
    return sorted(edits, key=lambda edit: (edit.get("detected_at", ""), edit.get("id", "")))


def summarize_canon_edits(stores: StateStoreBundle, *, entity_ref: str | None = None) -> JsonObject:
    pending = pending_canon_edits(stores, entity_ref=entity_ref)
    pending_review = [edit for edit in pending if edit.get("status") == STATUS_PENDING_HUMAN_REVIEW]
    return {
        "unreconciled_count": sum(1 for edit in pending if edit.get("status") == STATUS_UNRECONCILED),
        "pending_human_review_count": len(pending_review),
        "pending_human_review_items": [
            {
                "id": edit.get("id", ""),
                "target_claim_id": edit.get("target_claim_id", ""),
                "change_type": edit.get("change_type", ""),
                "review_reason": edit.get("review_reason"),
            }
            for edit in pending_review[:10]
        ],
    }


def replace_canon_edit(stores: StateStoreBundle, edit: JsonObject) -> None:
    """Replace the current queue item record using the repo's existing update pattern."""
    path = stores.canon_edits.path_for(str(edit["id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(edit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _edit_record(
    *,
    state_root: Path,
    detected_at: str,
    change_type: str,
    target_claim_id: str,
    before: JsonObject | None,
    after: JsonObject | None,
) -> JsonObject:
    digest = hashlib.sha256(
        json.dumps(
            {
                "state_root": str(state_root),
                "detected_at": detected_at,
                "change_type": change_type,
                "target_claim_id": target_claim_id,
                "before": before,
                "after": after,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:12]
    safe_claim_id = target_claim_id.replace("/", ".").replace("\\", ".")
    return {
        "id": f"canon_edit.{safe_claim_id}.{change_type}.{digest}",
        "state_root": str(state_root),
        "detected_at": detected_at,
        "change_type": change_type,
        "target_claim_id": target_claim_id,
        "before": deepcopy(before),
        "after": deepcopy(after),
        "status": STATUS_UNRECONCILED,
        "requires_human_review": False,
        "review_reason": None,
        "reconciliation": None,
        "reconciled_at": None,
    }


def _snapshot_claims(stores: StateStoreBundle) -> dict[str, JsonObject]:
    snapshot: dict[str, JsonObject] = {}
    for claim in stores.canonical_claims.replay():
        claim_id = str(claim.get("id", ""))
        if not claim_id:
            continue
        snapshot[claim_id] = {
            "hash": _content_hash(claim),
            "record": deepcopy(claim),
        }
    return snapshot


def _load_baseline(path: Path) -> dict[str, JsonObject]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object baseline")
    claims = value.get("claims", value)
    if not isinstance(claims, dict):
        raise ValueError(f"{path} claims baseline must be a JSON object")
    normalized: dict[str, JsonObject] = {}
    for claim_id, entry in claims.items():
        if isinstance(entry, str):
            normalized[str(claim_id)] = {"hash": entry, "record": None}
        elif isinstance(entry, dict) and isinstance(entry.get("hash"), str):
            normalized[str(claim_id)] = deepcopy(entry)
    return normalized


def _write_baseline(path: Path, snapshot: dict[str, JsonObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": 1, "claims": snapshot}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _content_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _edit_entity_ref(edit: JsonObject) -> str:
    for key in ("after", "before"):
        value = edit.get(key)
        if isinstance(value, dict):
            return str(value.get("entity_ref", ""))
    return ""


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


__all__ = [
    "CHANGE_ADD",
    "CHANGE_EDIT",
    "CHANGE_DELETE",
    "STATUS_UNRECONCILED",
    "STATUS_RECONCILED",
    "STATUS_PENDING_HUMAN_REVIEW",
    "STATUS_FLAGGED",
    "scan_canon_edits",
    "pending_canon_edits",
    "summarize_canon_edits",
    "replace_canon_edit",
]
