from __future__ import annotations

from pathlib import Path

import pytest

from state_system.canon_reconcile import (
    LiveCanonEditReviewer,
    reconcile_edit,
)
from state_system.canonical_claims import CanonicalClaimRuntime
from state_system.model_client import DEFAULT_MODEL_ROUTE, ModelOutputInvalid, PiModelClient
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2026-07-31T00:00:00Z"


def _client(tmp_path, raw_output: str) -> PiModelClient:
    """A PiModelClient whose model call is stubbed to return ``raw_output``."""
    client = PiModelClient(model_route=DEFAULT_MODEL_ROUTE, project_root=ROOT)
    client._call_model = lambda prompt: raw_output  # type: ignore[method-assign]
    return client


def test_review_returns_parsed_valid_edit_judgment(tmp_path):
    raw = (
        '{"edit_item_id": "canon_edit.x.add.1", "action": "add", '
        '"confidence": 0.9, "rationale": "a new priority", '
        '"requires_human_review": false, "resulting_claim": null}'
    )
    judgment = _client(tmp_path, raw).review(
        registry_route="canon-edit-reconcile",
        schema_ref="canon-edit-judgment.v1",
        edit_item={"id": "canon_edit.x.add.1"},
        evidence={},
    )
    assert judgment["action"] == "add"
    assert judgment["requires_human_review"] is False


def test_garbage_model_output_raises_never_fabricates(tmp_path):
    # Boundary: unparseable output must raise, not produce a default judgment.
    with pytest.raises(ModelOutputInvalid):
        _client(tmp_path, "the claim looks fine I guess").review(
            registry_route="canon-edit-reconcile",
            schema_ref="canon-edit-judgment.v1",
            edit_item={"id": "canon_edit.x.add.1"},
            evidence={},
        )


def test_prompt_embeds_schema_ref_and_payload(tmp_path):
    captured: dict[str, str] = {}

    def fake_call(prompt: str) -> str:
        captured["prompt"] = prompt
        return (
            '{"edit_item_id": "e1", "action": "uncertain", "confidence": 0.2, '
            '"rationale": "unsure", "requires_human_review": true, "resulting_claim": null}'
        )

    client = PiModelClient(model_route=DEFAULT_MODEL_ROUTE, project_root=ROOT)
    client._call_model = fake_call  # type: ignore[method-assign]
    client.review(
        registry_route="canon-edit-reconcile",
        schema_ref="canon-edit-judgment.v1",
        edit_item={"id": "e1", "marker": "PAYLOAD_MARKER"},
        evidence={},
    )
    assert "canon-edit-judgment.v1" in captured["prompt"]
    assert "PAYLOAD_MARKER" in captured["prompt"]


def test_anthropic_route_rejected():
    with pytest.raises(ValueError, match="anthropic"):
        PiModelClient(model_route="anthropic/claude-sonnet-4-5", project_root=ROOT)


class _FakeModelClient:
    def __init__(self, judgment: dict) -> None:
        self.judgment = judgment

    def review(self, *, registry_route, schema_ref, **payload) -> dict:
        return dict(self.judgment)


def _claim(**overrides) -> dict:
    claim = {
        "id": "canon.sample.priority",
        "entity_ref": "sampleco",
        "claim_type": "priority",
        "statement": "Validate one narrow workflow before broadening scope.",
        "artifact_ref": None,
        "evidence_refs": [],
        "status": "active",
        "supersedes": None,
        "superseded_by": None,
        "determined_at": "2026-07-01T00:00:00Z",
        "validity": {"window_days": 30, "basis": "calendar", "last_confirmed_at": "2026-07-01T00:00:00Z"},
        "generated_at": "2026-07-01T00:00:00Z",
        "generated_by": "test",
    }
    claim.update(overrides)
    return claim


def _edit(**overrides) -> dict:
    edit = {
        "id": "canon_edit.canon.sample.priority.add.001",
        "state_root": "/tmp/sample",
        "detected_at": "2026-07-30T00:00:00Z",
        "change_type": "add",
        "target_claim_id": "canon.sample.priority",
        "before": None,
        "after": _claim(),
        "status": "unreconciled",
        "requires_human_review": False,
        "review_reason": None,
        "reconciliation": None,
        "reconciled_at": None,
    }
    edit.update(overrides)
    return edit


def test_live_reviewer_uncertain_judgment_holds_without_commit(tmp_path):
    stores = StateStoreBundle(tmp_path)
    edit = _edit()
    stores.canon_edits.create(edit)
    reviewer = LiveCanonEditReviewer(
        model_client=_FakeModelClient(
            {
                "edit_item_id": edit["id"],
                "action": "uncertain",
                "confidence": 0.3,
                "rationale": "cannot tell if this is a new priority",
                "requires_human_review": True,
                "resulting_claim": None,
            }
        )
    )
    result = reconcile_edit(edit, reviewer=reviewer, stores=stores, as_of=AS_OF)
    assert result["status"] == "pending_human_review"
    assert result["committed_canon_change"] is False
    # Nothing was written to the claim store.
    assert list(stores.canonical_claims.replay()) == []


def test_live_reviewer_add_judgment_commits_claim(tmp_path):
    stores = StateStoreBundle(tmp_path)
    edit = _edit()
    stores.canon_edits.create(edit)
    new_claim = _claim(id="canon.sample.priority.v2", statement="Move to onboarding pilots.")
    reviewer = LiveCanonEditReviewer(
        model_client=_FakeModelClient(
            {
                "edit_item_id": edit["id"],
                "action": "add",
                "confidence": 0.85,
                "rationale": "a new declared priority",
                "requires_human_review": False,
                "resulting_claim": new_claim,
            }
        )
    )
    result = reconcile_edit(edit, reviewer=reviewer, stores=stores, as_of=AS_OF)
    assert result["status"] == "reconciled"
    assert result["committed_canon_change"] is True
    ids = [c["id"] for c in stores.canonical_claims.replay()]
    assert "canon.sample.priority.v2" in ids
