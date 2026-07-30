# ABOUTME: Agent reconciliation loop for raw human canonical-claim edits.
# ABOUTME: Reviewer owns semantic judgment; code owns queue gates and persistence.
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Protocol

from state_system.canon_edit_watcher import (
    STATUS_PENDING_HUMAN_REVIEW,
    STATUS_RECONCILED,
    replace_canon_edit,
)
from state_system.canonical_claims import (
    ACTIVE,
    RETRACTED,
    CanonicalClaimRuntime,
    build_canonical_claims_read_model,
    supersede,
    validate_canonical_claim,
)
from state_system.contracts import JsonObject, load_json
from state_system.stores import RecordNotFoundError, StateStoreBundle


ACTIONS = ("supersede", "amend", "retract", "add", "uncertain")


class MissingCanonEditJudgmentError(KeyError):
    def __init__(self, edit_id: str):
        super().__init__(f"no recorded canon edit judgment for {edit_id}")
        self.edit_id = edit_id


class CanonEditReviewer(Protocol):
    """Semantic reviewer boundary for raw canonical-claim edits.

    The reviewer/model owns every judgment: whether a raw edit is a supersede,
    amend, retraction, add, and whether it is uncertain. Code must not infer the
    action from content shape, regexes, confidence thresholds, or heuristics.
    """

    def judge_edit(self, edit_item: JsonObject, evidence: JsonObject) -> JsonObject:
        ...


class RecordedCanonEditReviewer:
    """Replay recorded edit judgments keyed by unreconciled edit id."""

    def __init__(self, judgments_by_edit_id: dict[str, JsonObject]):
        self.judgments_by_edit_id = {
            key: deepcopy(value) for key, value in judgments_by_edit_id.items()
        }

    @classmethod
    def from_examples(cls, path: Path) -> "RecordedCanonEditReviewer":
        judgments: dict[str, JsonObject] = {}
        for file_path in sorted(path.rglob("*.json")):
            judgment = load_json(file_path)
            _validate_judgment_shape(judgment, source=str(file_path))
            judgments[str(judgment["edit_item_id"])] = judgment
        return cls(judgments)

    def judge_edit(self, edit_item: JsonObject, evidence: JsonObject) -> JsonObject:
        edit_id = str(edit_item["id"])
        if edit_id not in self.judgments_by_edit_id:
            raise MissingCanonEditJudgmentError(edit_id)
        return deepcopy(self.judgments_by_edit_id[edit_id])


class LiveCanonEditReviewer:
    """Production hook for an injected semantic model client.

    A missing model client is explicitly unsupported. Code never substitutes a
    heuristic judgment or threshold to decide the meaning of a human edit.
    """

    def __init__(
        self,
        *,
        registry_route: str = "canon-edit-reconcile",
        model_client: object | None = None,
    ):
        self.registry_route = registry_route
        self.model_client = model_client

    def judge_edit(self, edit_item: JsonObject, evidence: JsonObject) -> JsonObject:
        if self.model_client is None:
            raise NotImplementedError(
                "Live canon edit reconciliation requires an injected model_client. "
                f"Resolve route '{self.registry_route}' through the central registry, "
                "call the model with the edit item and assembled evidence, and validate "
                "its output. Use the recorded reviewer for dry-runs."
            )
        return self.model_client.review(
            registry_route=self.registry_route,
            edit_item=edit_item,
            evidence=evidence,
            schema_ref="canon-edit-judgment.v1",
        )


def reconcile_edit(
    edit_item: JsonObject,
    *,
    reviewer: CanonEditReviewer,
    stores: StateStoreBundle,
    as_of: str,
    claim_schema: JsonObject | None = None,
) -> JsonObject:
    """Reconcile one raw edit using a reviewer-owned semantic judgment.

    MODEL-MEDIATED BOUNDARY: reviewer output declares both the action and whether
    human review is required. Code only gates declared ``uncertain``/review flags,
    stamps provenance, validates persistence shape through runtimes, and enforces
    supersession/retraction mechanics. A low confidence value alone never blocks
    commit; no code path infers uncertainty from a confidence threshold.
    """
    evidence = assemble_edit_evidence(edit_item, stores=stores, as_of=as_of)
    judgment = reviewer.judge_edit(edit_item, evidence)
    _validate_judgment_shape(judgment)
    action = str(judgment["action"])
    requires_human_review = bool(judgment.get("requires_human_review", False))

    if action == "uncertain" or requires_human_review:
        held = deepcopy(edit_item)
        held["status"] = STATUS_PENDING_HUMAN_REVIEW
        held["requires_human_review"] = True
        held["review_reason"] = str(judgment.get("rationale", ""))
        held["reconciliation"] = _reconciliation_payload(judgment, None)
        held["reconciled_at"] = None
        replace_canon_edit(stores, held)
        return {
            "ok": True,
            "status": STATUS_PENDING_HUMAN_REVIEW,
            "edit": held,
            "committed_canon_change": False,
            "evidence": evidence,
            "judgment": judgment,
            "invariant": _boundary_invariant(),
        }

    resulting_claim = _claim_for_action(action, judgment, edit_item, as_of=as_of)
    resulting_claim = _stamp_provenance(resulting_claim, edit_item)
    commit_result = _commit_claim_action(
        action, resulting_claim, edit_item, stores, claim_schema=claim_schema
    )

    if commit_result.get("held"):
        # Invalid reviewer-produced claim: hold for human review rather than
        # persist malformed canon. Code owns this gate; the reviewer is not
        # re-consulted (a schema failure is structural, not semantic).
        held = deepcopy(edit_item)
        held["status"] = STATUS_PENDING_HUMAN_REVIEW
        held["requires_human_review"] = True
        held["review_reason"] = (
            f"{commit_result.get('hold_reason', 'invalid')}: "
            f"{commit_result.get('validation_errors', [])}"
        )
        held["reconciliation"] = _reconciliation_payload(judgment, None)
        held["reconciled_at"] = None
        replace_canon_edit(stores, held)
        return {
            "ok": True,
            "status": STATUS_PENDING_HUMAN_REVIEW,
            "edit": held,
            "committed_canon_change": False,
            "evidence": evidence,
            "judgment": judgment,
            "hold_reason": commit_result.get("hold_reason"),
            "validation_errors": commit_result.get("validation_errors", []),
            "invariant": _boundary_invariant(),
        }

    reconciled = deepcopy(edit_item)
    reconciled["status"] = STATUS_RECONCILED
    reconciled["requires_human_review"] = False
    reconciled["review_reason"] = None
    reconciled["reconciliation"] = _reconciliation_payload(
        judgment, str(commit_result.get("resulting_claim_id", resulting_claim.get("id")))
    )
    reconciled["reconciled_at"] = as_of
    replace_canon_edit(stores, reconciled)
    return {
        "ok": True,
        "status": STATUS_RECONCILED,
        "edit": reconciled,
        "committed_canon_change": True,
        "commit": commit_result,
        "evidence": evidence,
        "judgment": judgment,
        "invariant": _boundary_invariant(),
    }


def reconcile_unreconciled_edits(
    *,
    reviewer: CanonEditReviewer,
    stores: StateStoreBundle,
    as_of: str,
    claim_schema: JsonObject | None = None,
) -> JsonObject:
    results = []
    for edit in stores.canon_edits.replay():
        if edit.get("status") != "unreconciled":
            continue
        results.append(
            reconcile_edit(
                edit, reviewer=reviewer, stores=stores, as_of=as_of,
                claim_schema=claim_schema,
            )
        )
    return {
        "ok": True,
        "as_of": as_of,
        "reviewed_count": len(results),
        "results": results,
        "invariant": _boundary_invariant(),
    }


def assemble_edit_evidence(edit_item: JsonObject, *, stores: StateStoreBundle, as_of: str) -> JsonObject:
    entity_ref = _edit_entity_ref(edit_item)
    read_model = build_canonical_claims_read_model(stores, as_of=as_of)
    current_claims = [
        claim
        for claim in read_model["active_claims"]
        if entity_ref == "" or claim.get("entity_ref", "") == entity_ref
    ]
    return {
        "edit_item_id": edit_item.get("id"),
        "change_type": edit_item.get("change_type"),
        "target_claim_id": edit_item.get("target_claim_id"),
        "before": deepcopy(edit_item.get("before")),
        "after": deepcopy(edit_item.get("after")),
        "entity_ref": entity_ref,
        "current_canon": current_claims,
        "invariant": {
            "code_assembled_evidence_only": True,
            "semantic_judgment_performed": False,
        },
    }


def _commit_claim_action(
    action: str,
    resulting_claim: JsonObject,
    edit_item: JsonObject,
    stores: StateStoreBundle,
    *,
    claim_schema: JsonObject | None = None,
) -> JsonObject:
    # Code owns the schema gate: validate the reviewer-produced claim before it
    # is persisted. Invalid model output is held for human review rather than
    # committed (the model owns the judgment; code owns structural integrity).
    if claim_schema is not None:
        errors = validate_canonical_claim(resulting_claim, claim_schema)
        if errors:
            return {
                "action": action,
                "held": True,
                "hold_reason": "invalid_resulting_claim",
                "validation_errors": errors,
            }
    runtime = CanonicalClaimRuntime(stores)
    if action == "supersede":
        old_id = str(resulting_claim.get("supersedes") or edit_item["target_claim_id"])
        # Use the baseline prior snapshot so the superseded marker records what
        # was actually replaced, not the live (already-human-edited) record.
        prior = (
            edit_item.get("before")
            if isinstance(edit_item.get("before"), dict)
            else None
        )
        result = supersede(old_id, resulting_claim, stores, prior_record=prior)
        return {
            "action": action,
            "resulting_claim_id": result["active_claim"]["id"],
            "superseded_claim_id": old_id,
        }
    if action == "add":
        record = runtime.record(resulting_claim)
        return {"action": action, "resulting_claim_id": record["id"]}
    if action == "amend":
        _replace_claim(stores, resulting_claim)
        return {"action": action, "resulting_claim_id": resulting_claim["id"]}
    if action == "retract":
        runtime.record(resulting_claim)
        return {
            "action": action,
            "resulting_claim_id": resulting_claim["id"],
            "retracted_claim_id": edit_item["target_claim_id"],
        }
    raise ValueError(f"unsupported canon edit action: {action}")


def _claim_for_action(action: str, judgment: JsonObject, edit_item: JsonObject, *, as_of: str) -> JsonObject:
    claim = judgment.get("resulting_claim")
    if isinstance(claim, dict):
        result = deepcopy(claim)
    elif action == "retract":
        before = edit_item.get("before")
        if not isinstance(before, dict):
            raise ValueError("retract judgments require a before snapshot or resulting_claim")
        result = deepcopy(before)
        result["id"] = f"{edit_item['target_claim_id']}.retracted-at.{_compact_time(as_of)}"
        result["status"] = RETRACTED
        result["supersedes"] = edit_item["target_claim_id"]
        result["superseded_by"] = None
        result["generated_at"] = as_of
        result["generated_by"] = "canon-edit-reconcile"
    else:
        raise ValueError(f"{action} judgments require resulting_claim")

    if action in {"supersede", "add", "amend"}:
        result.setdefault("status", ACTIVE)
    if action == "supersede":
        result["status"] = ACTIVE
        result.setdefault("supersedes", edit_item["target_claim_id"])
    if action == "retract":
        result["status"] = RETRACTED
        result.setdefault("supersedes", edit_item["target_claim_id"])
    return result


def _stamp_provenance(claim: JsonObject, edit_item: JsonObject) -> JsonObject:
    record = deepcopy(claim)
    provenance = dict(record.get("provenance", {})) if isinstance(record.get("provenance"), dict) else {}
    provenance.update(
        {
            "origin": "human_edit",
            "structured_by": "agent",
            "edit_item_id": edit_item.get("id", ""),
            "change_type": edit_item.get("change_type", ""),
        }
    )
    record["provenance"] = provenance
    return record


def _replace_claim(stores: StateStoreBundle, claim: JsonObject) -> None:
    try:
        stores.canonical_claims.read(str(claim["id"]))
    except RecordNotFoundError:
        raise ValueError(f"amend target claim does not exist: {claim['id']}") from None
    path = stores.canonical_claims.path_for(str(claim["id"]))
    path.write_text(json.dumps(claim, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _reconciliation_payload(judgment: JsonObject, resulting_claim_id: str | None) -> JsonObject:
    return {
        "action": judgment["action"],
        "resulting_claim_id": resulting_claim_id,
        "provenance": {"origin": "human_edit", "structured_by": "agent"},
        "confidence": judgment["confidence"],
        "rationale": judgment["rationale"],
    }


def _validate_judgment_shape(judgment: JsonObject, *, source: str = "judgment") -> None:
    required = ["edit_item_id", "action", "confidence", "rationale", "requires_human_review"]
    missing = [name for name in required if name not in judgment]
    if missing:
        raise ValueError(f"{source} missing required canon edit judgment fields: {missing}")
    if judgment["action"] not in ACTIONS:
        raise ValueError(f"{source} action must be one of {ACTIONS}")
    if not isinstance(judgment["requires_human_review"], bool):
        raise ValueError(f"{source} requires_human_review must be boolean")
    if not isinstance(judgment["confidence"], int | float):
        raise ValueError(f"{source} confidence must be numeric")
    if not isinstance(judgment["rationale"], str):
        raise ValueError(f"{source} rationale must be string")


def _edit_entity_ref(edit_item: JsonObject) -> str:
    for key in ("after", "before"):
        value = edit_item.get(key)
        if isinstance(value, dict):
            return str(value.get("entity_ref", ""))
    return ""


def _compact_time(value: str) -> str:
    return value.replace(":", "").replace("-", "").replace(".", "").replace("Z", "z")


def _boundary_invariant() -> JsonObject:
    return {
        "reviewer_declares_action": True,
        "reviewer_declares_uncertainty": True,
        "code_infers_uncertainty_from_confidence_threshold": False,
        "code_infers_supersede_vs_amend": False,
    }


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


__all__ = [
    "ACTIONS",
    "MissingCanonEditJudgmentError",
    "CanonEditReviewer",
    "RecordedCanonEditReviewer",
    "LiveCanonEditReviewer",
    "reconcile_edit",
    "reconcile_unreconciled_edits",
    "assemble_edit_evidence",
]
