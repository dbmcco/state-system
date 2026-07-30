from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from state_system.canonical_claim_review import (
    MissingCanonicalClaimJudgmentError,
    RecordedCanonicalClaimReviewer,
    assemble_claim_evidence,
)
from state_system.canonical_claims import (
    CanonicalClaimRuntime,
    build_canonical_claims_read_model,
    derive_reevaluation,
    supersede,
    validate_canonical_claim,
)
from state_system.contracts import load_json
from state_system.stores import StateStoreBundle


AS_OF = "2026-07-31T00:00:00Z"


def _schema() -> dict:
    return load_json(Path("schemas/canonical-claim.schema.json"))


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


def test_canonical_claim_schema_validation_accepts_valid_claim():
    assert validate_canonical_claim(_claim(), _schema()) == []


@pytest.mark.parametrize(
    "mutator, expected",
    [
        (lambda claim: claim.update({"claim_type": "guess"}), "$.claim_type"),
        (lambda claim: claim.pop("statement"), "missing required key statement"),
        (lambda claim: claim.update({"status": "stale"}), "$.status"),
    ],
)
def test_canonical_claim_schema_validation_rejects_bad_records(mutator, expected):
    claim = _claim()
    mutator(claim)

    errors = validate_canonical_claim(claim, _schema())

    assert any(expected in error for error in errors)


@pytest.mark.parametrize(
    "determined_at, expected_status, expected_age",
    [
        ("2026-07-02T00:00:00Z", "current", 29),
        ("2026-06-30T00:00:00Z", "due_for_reconfirmation", 31),
        ("2026-05-30T00:00:00Z", "overdue", 62),
    ],
)
def test_derive_reevaluation_uses_window_arithmetic(determined_at, expected_status, expected_age):
    claim = _claim(determined_at=determined_at)
    claim["validity"] = {
        "window_days": 30,
        "basis": "calendar",
        "last_confirmed_at": determined_at,
    }

    result = derive_reevaluation(claim, as_of=AS_OF)

    assert result["reevaluation_status"] == expected_status
    assert result["age_days"] == expected_age
    assert result["window_days"] == 30
    assert result["reconfirm_by"].endswith("T00:00:00Z")
    assert "before relying on it" in result["agent_directive"]


def test_derive_reevaluation_for_inactive_claim_names_superseder():
    result = derive_reevaluation(
        _claim(status="superseded", superseded_by="canon.sample.priority.v2"),
        as_of=AS_OF,
    )

    assert result["reevaluation_status"] == "superseded"
    assert "canon.sample.priority.v2" in result["agent_directive"]


def test_supersede_writes_new_active_claim_and_append_only_superseded_marker(tmp_path):
    stores = StateStoreBundle(tmp_path)
    runtime = CanonicalClaimRuntime(stores)
    old_claim = runtime.record(_claim())
    new_claim = _claim(
        id="canon.sample.priority.v2",
        statement="SampleCo should move from workflow validation to onboarding pilots.",
        determined_at="2026-07-20T00:00:00Z",
        generated_at="2026-07-20T00:05:00Z",
    )

    result = supersede(old_claim["id"], new_claim, stores)

    assert result["active_claim"]["status"] == "active"
    assert result["active_claim"]["supersedes"] == old_claim["id"]
    assert result["superseded_claim"]["status"] == "superseded"
    assert result["superseded_claim"]["superseded_by"] == "canon.sample.priority.v2"
    assert runtime.read(old_claim["id"])["status"] == "active"
    read_model = build_canonical_claims_read_model(stores, as_of=AS_OF)
    active_ids = [claim["id"] for claim in read_model["active_claims"]]
    assert active_ids == ["canon.sample.priority.v2"]
    assert old_claim["id"] in read_model["superseded_claim_refs"]


def test_derive_reevaluation_uses_last_confirmed_at_when_present():
    # Determined months ago (would be overdue by determined_at alone) but
    # reconfirmed recently: reevaluation must track the confirmation, not the
    # original determination, so a reconfirmed claim reads as current.
    claim = _claim(determined_at="2026-04-01T00:00:00Z")
    claim["validity"] = {
        "window_days": 30,
        "basis": "calendar",
        "last_confirmed_at": "2026-07-20T00:00:00Z",
    }
    result = derive_reevaluation(claim, as_of=AS_OF)
    assert result["reevaluation_status"] == "current"
    # age is measured from last_confirmed_at (11 days), not determined_at (121 days)
    assert result["age_days"] == 11
    assert result["reconfirm_by"].startswith("2026-08-19")


def test_supersede_uses_prior_record_snapshot_for_marker(tmp_path):
    # In the scan/reconcile flow the live store has already been edited before
    # supersession, so the marker must use the baseline prior snapshot passed in,
    # not whatever the live store currently holds.
    stores = StateStoreBundle(tmp_path)
    runtime = CanonicalClaimRuntime(stores)
    old_claim = runtime.record(_claim(statement="LIVE STORE STATEMENT"))
    baseline_prior = deepcopy(old_claim)
    baseline_prior["statement"] = "BASELINE SNAPSHOT"
    new_claim = _claim(
        id="canon.sample.priority.v2",
        determined_at="2026-07-20T00:00:00Z",
        generated_at="2026-07-20T00:05:00Z",
    )
    result = supersede(old_claim["id"], new_claim, stores, prior_record=baseline_prior)
    # The superseded marker records the baseline prior, not the live record.
    assert result["superseded_claim"]["statement"] == "BASELINE SNAPSHOT"


def test_recorded_canonical_claim_reviewer_replays_recorded_judgment(tmp_path):
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "canonical-claim-judgment-sample.json").write_text(
        """
        {
          "claim_id": "canon.sample.priority",
          "judgment": "still_holds",
          "rationale": "Recorded model judgment.",
          "confidence": 0.9,
          "newer_evidence_refs": [],
          "reviewed_at": "2026-07-15T00:00:00Z"
        }
        """,
        encoding="utf-8",
    )
    reviewer = RecordedCanonicalClaimReviewer.from_examples(examples)

    judgment = reviewer.review(_claim(), {"evidence_refs": []})

    assert judgment["judgment"] == "still_holds"
    with pytest.raises(MissingCanonicalClaimJudgmentError):
        reviewer.review(_claim(id="canon.sample.unrecorded"), {})


def test_assemble_claim_evidence_gathers_refs_without_judgment(tmp_path):
    stores = StateStoreBundle(tmp_path)
    stores.memory.create(
        {
            "id": "canonical-priority-note",
            "summary": "The priority was declared by an operator.",
        }
    )
    claim = _claim(
        artifact_ref="memory:canonical-priority-note",
        evidence_refs=["memory:canonical-priority-note", "memory:missing"],
    )

    evidence = assemble_claim_evidence(claim, stores)

    assert evidence["claim_id"] == claim["id"]
    assert [item["ref"] for item in evidence["resolved_evidence"]] == [
        "memory:canonical-priority-note"
    ]
    assert evidence["unresolved_evidence_refs"] == ["memory:missing"]
    assert evidence["artifact"]["resolution_status"] == "resolved"
    assert evidence["invariant"]["semantic_judgment_performed"] is False


def test_build_canonical_claims_read_model_attaches_reevaluation(tmp_path):
    stores = StateStoreBundle(tmp_path)
    runtime = CanonicalClaimRuntime(stores)
    runtime.record(_claim(id="canon.sample.current", determined_at="2026-07-10T00:00:00Z"))
    due_claim = _claim(id="canon.sample.due", determined_at="2026-06-15T00:00:00Z")
    due_claim["validity"] = deepcopy(due_claim["validity"])
    due_claim["validity"]["last_confirmed_at"] = "2026-06-15T00:00:00Z"
    runtime.record(due_claim)
    runtime.record(_claim(id="canon.sample.retracted", status="retracted"))

    read_model = build_canonical_claims_read_model(stores, as_of=AS_OF)

    assert [claim["id"] for claim in read_model["active_claims"]] == [
        "canon.sample.current",
        "canon.sample.due",
    ]
    statuses = {
        claim["id"]: claim["reevaluation"]["reevaluation_status"]
        for claim in read_model["active_claims"]
    }
    assert statuses == {
        "canon.sample.current": "current",
        "canon.sample.due": "due_for_reconfirmation",
    }
    assert read_model["counts_by_reevaluation_status"] == {
        "current": 1,
        "due_for_reconfirmation": 1,
    }
