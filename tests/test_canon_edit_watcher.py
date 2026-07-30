from __future__ import annotations

from copy import deepcopy

from state_system.canon_edit_watcher import scan_canon_edits
from state_system.canonical_claims import CanonicalClaimRuntime
from state_system.stores import StateStoreBundle


AS_OF = "2026-07-31T00:00:00Z"


def _claim(**overrides) -> dict:
    claim = {
        "id": "canon.sample.priority",
        "entity_ref": "sampleco",
        "claim_type": "priority",
        "statement": "SampleCo should validate one narrow workflow before broadening scope.",
        "artifact_ref": None,
        "evidence_refs": ["memory:canonical-priority-note"],
        "status": "active",
        "supersedes": None,
        "superseded_by": None,
        "determined_at": "2026-07-01T00:00:00Z",
        "validity": {
            "window_days": 30,
            "basis": "calendar",
            "last_confirmed_at": "2026-07-01T00:00:00Z",
        },
        "generated_at": "2026-07-01T00:05:00Z",
        "generated_by": "test",
    }
    claim.update(overrides)
    return claim


def test_scan_canon_edits_detects_add_edit_and_delete(tmp_path):
    stores = StateStoreBundle(tmp_path)
    runtime = CanonicalClaimRuntime(stores)
    runtime.record(_claim(id="canon.sample.deleted"))
    unchanged = runtime.record(_claim(id="canon.sample.unchanged"))
    edited = runtime.record(_claim(id="canon.sample.edited"))
    baseline_path = tmp_path / "baseline" / "canon-claims.json"

    initial = scan_canon_edits(tmp_path, baseline_path=baseline_path, detected_at=AS_OF)
    assert initial["emitted_count"] == 3

    edited_after = deepcopy(edited)
    edited_after["statement"] = "SampleCo should validate two narrow workflows."
    stores.canonical_claims.path_for("canon.sample.edited").write_text(
        __import__("json").dumps(edited_after, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    stores.canonical_claims.path_for("canon.sample.deleted").unlink()
    runtime.record(_claim(id="canon.sample.added"))

    result = scan_canon_edits(
        tmp_path,
        baseline_path=baseline_path,
        detected_at="2026-08-01T00:00:00Z",
    )

    changes = {edit["target_claim_id"]: edit for edit in result["edits"]}
    assert result["emitted_count"] == 3
    assert changes["canon.sample.added"]["change_type"] == "add"
    assert changes["canon.sample.added"]["before"] is None
    assert changes["canon.sample.edited"]["change_type"] == "edit"
    assert changes["canon.sample.edited"]["before"]["statement"] == edited["statement"]
    assert changes["canon.sample.deleted"]["change_type"] == "delete"
    assert changes["canon.sample.deleted"]["before"]["id"] == "canon.sample.deleted"
    assert changes["canon.sample.deleted"]["after"] is None
    assert unchanged["id"] not in changes
