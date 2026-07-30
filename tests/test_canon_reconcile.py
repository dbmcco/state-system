from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from state_system.api_surface import dispatch
from state_system.canon_reconcile import RecordedCanonEditReviewer, reconcile_edit
from state_system.canonical_claims import CanonicalClaimRuntime, build_canonical_claims_read_model
from state_system.context_packages import ContextPackager
from state_system.contracts import load_json
from state_system.stores import StateStoreBundle


ROOT = Path(__file__).resolve().parents[1]
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


def _edit(**overrides) -> dict:
    edit = {
        "id": "canon_edit.canon.sample.priority.edit.001",
        "state_root": "/tmp/sample-state",
        "detected_at": "2026-07-30T00:00:00Z",
        "change_type": "edit",
        "target_claim_id": "canon.sample.priority",
        "before": _claim(),
        "after": _claim(statement="SampleCo should move to onboarding pilots."),
        "status": "unreconciled",
        "requires_human_review": False,
        "review_reason": None,
        "reconciliation": None,
        "reconciled_at": None,
    }
    edit.update(overrides)
    return edit


def _reviewer(tmp_path, judgment: dict) -> RecordedCanonEditReviewer:
    examples = tmp_path / "judgments"
    examples.mkdir()
    (examples / "recorded-canon-edit-judgment.json").write_text(
        __import__("json").dumps(judgment, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return RecordedCanonEditReviewer.from_examples(examples)


def test_reconcile_supersede_commits_claim_and_marks_edit_reconciled_with_provenance(tmp_path):
    stores = StateStoreBundle(tmp_path)
    old_claim = CanonicalClaimRuntime(stores).record(_claim())
    edit = _edit(before=old_claim)
    stores.canon_edits.create(edit)
    new_claim = _claim(
        id="canon.sample.priority.v2",
        statement="SampleCo should move to onboarding pilots.",
        determined_at="2026-07-30T00:00:00Z",
        generated_at="2026-07-30T00:01:00Z",
    )
    reviewer = _reviewer(
        tmp_path,
        {
            "edit_item_id": edit["id"],
            "action": "supersede",
            "resulting_claim": new_claim,
            "confidence": 0.81,
            "rationale": "The human edit changes the active priority meaning.",
            "requires_human_review": False,
        },
    )

    result = reconcile_edit(edit, reviewer=reviewer, stores=stores, as_of=AS_OF)

    assert result["status"] == "reconciled"
    read_model = build_canonical_claims_read_model(stores, as_of=AS_OF)
    assert [claim["id"] for claim in read_model["active_claims"]] == [
        "canon.sample.priority.v2"
    ]
    assert "canon.sample.priority" in read_model["superseded_claim_refs"]
    active_claim = stores.canonical_claims.read("canon.sample.priority.v2")
    assert active_claim["provenance"]["origin"] == "human_edit"
    assert active_claim["provenance"]["structured_by"] == "agent"
    stored_edit = stores.canon_edits.read(edit["id"])
    assert stored_edit["status"] == "reconciled"
    assert stored_edit["reconciliation"]["action"] == "supersede"


def test_reconcile_uncertain_holds_without_committing_canon_change(tmp_path):
    stores = StateStoreBundle(tmp_path)
    old_claim = CanonicalClaimRuntime(stores).record(_claim())
    edit = _edit(before=old_claim)
    stores.canon_edits.create(edit)
    reviewer = _reviewer(
        tmp_path,
        {
            "edit_item_id": edit["id"],
            "action": "uncertain",
            "resulting_claim": None,
            "confidence": 0.2,
            "rationale": "The edit could be a typo or a canon-changing priority shift.",
            "requires_human_review": True,
        },
    )

    result = reconcile_edit(edit, reviewer=reviewer, stores=stores, as_of=AS_OF)

    assert result["committed_canon_change"] is False
    assert [claim["id"] for claim in build_canonical_claims_read_model(stores, as_of=AS_OF)["active_claims"]] == [old_claim["id"]]
    stored_edit = stores.canon_edits.read(edit["id"])
    assert stored_edit["status"] == "pending_human_review"
    assert stored_edit["requires_human_review"] is True
    assert stored_edit["review_reason"] == "The edit could be a typo or a canon-changing priority shift."


def test_low_confidence_declared_supersede_still_commits_because_code_does_not_infer_uncertainty(tmp_path):
    stores = StateStoreBundle(tmp_path)
    old_claim = CanonicalClaimRuntime(stores).record(_claim())
    edit = _edit(id="canon_edit.canon.sample.priority.edit.low-confidence", before=old_claim)
    stores.canon_edits.create(edit)
    reviewer = _reviewer(
        tmp_path,
        {
            "edit_item_id": edit["id"],
            "action": "supersede",
            "resulting_claim": _claim(
                id="canon.sample.priority.low-confidence.v2",
                statement="SampleCo should prioritize onboarding pilots.",
                determined_at="2026-07-30T00:00:00Z",
                generated_at="2026-07-30T00:01:00Z",
            ),
            "confidence": 0.01,
            "rationale": "Low confidence is not uncertainty unless the reviewer declares uncertainty.",
            "requires_human_review": False,
        },
    )

    result = reconcile_edit(edit, reviewer=reviewer, stores=stores, as_of=AS_OF)

    assert result["committed_canon_change"] is True
    assert result["invariant"]["code_infers_uncertainty_from_confidence_threshold"] is False
    assert stores.canon_edits.read(edit["id"])["status"] == "reconciled"


def test_canon_api_operation_returns_reevaluation_and_pending_counts(tmp_path):
    stores = StateStoreBundle(tmp_path)
    CanonicalClaimRuntime(stores).record(_claim())
    stores.canon_edits.create(
        _edit(
            id="canon_edit.canon.sample.priority.pending.001",
            status="pending_human_review",
            requires_human_review=True,
            review_reason="Agent is unsure whether this is an amendment or supersession.",
        )
    )

    response = dispatch(
        "canon",
        project_root=ROOT,
        state_root=tmp_path,
        scope="entity:sampleco",
        arguments={"as_of": AS_OF},
    )

    assert response["status"] == "ok"
    data = response["data"]
    assert data["active_claims"][0]["reevaluation"]["reevaluation_status"] == "current"
    assert data["canon_edit_queue"]["pending_human_review_count"] == 1


def test_context_package_includes_canonical_claims_block_for_agent_chat(tmp_path):
    stores = StateStoreBundle(tmp_path)
    CanonicalClaimRuntime(stores).record(_claim())
    stores.canon_edits.create(
        _edit(
            id="canon_edit.canon.sample.priority.pending.002",
            status="pending_human_review",
            requires_human_review=True,
            review_reason="Needs chat judgment.",
        )
    )
    stores.recent_changes.create(load_json(ROOT / "examples" / "recent-linear-southern-abrasives-won.json"))
    schemas = {"context_package": load_json(ROOT / "schemas" / "context-package.schema.json")}

    package = ContextPackager(stores, schemas).build_recent_change_package(
        persona=load_json(ROOT / "examples" / "maya-persona.json"),
        package_id="context.maya.canon-chat",
        created_at=AS_OF,
        review_goal="Review canon-aware context.",
        valid_until="2026-08-01T00:00:00Z",
    )

    assert "canonical_claims" in package
    assert package["canonical_claims"]["active_claims"][0]["id"] == "canon.sample.priority"
    assert package["canonical_claims"]["pending_human_review_count"] == 1
    assert "chat" in package["canonical_claims"]["agent_chat_directive"]


def test_reconcile_holds_invalid_reviewer_claim_for_human_review(tmp_path):
    # Code owns the schema gate: a reviewer-produced claim that fails canonical-
    # claim schema validation is held for human review, never persisted as canon.
    stores = StateStoreBundle(tmp_path)
    old_claim = CanonicalClaimRuntime(stores).record(_claim())
    edit = _edit(before=deepcopy(old_claim))
    stores.canon_edits.create(edit)
    invalid_judgment = {
        "edit_item_id": edit["id"],
        "action": "supersede",
        "confidence": 0.8,
        "rationale": "framing changed",
        "requires_human_review": False,
        "resulting_claim": {
            "id": "canon.sample.priority.v2",
            "entity_ref": "sampleco",
            "claim_type": "priority",
            # missing required statement/determined_at/validity/status/generated_at
        },
    }
    reviewer = _reviewer(tmp_path, invalid_judgment)
    schema = load_json(ROOT / "schemas" / "canonical-claim.schema.json")
    result = reconcile_edit(
        edit, reviewer=reviewer, stores=stores, as_of=AS_OF, claim_schema=schema
    )
    assert result["status"] == "pending_human_review"
    assert result["committed_canon_change"] is False
    assert result["edit"]["requires_human_review"] is True
    # The original active claim is unchanged — no supersession was committed.
    read_model = build_canonical_claims_read_model(stores, as_of=AS_OF)
    assert [c["id"] for c in read_model["active_claims"]] == ["canon.sample.priority"]
