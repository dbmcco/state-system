# ABOUTME: Canonical claim drift-review boundary: code assembles evidence, model judges.
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Protocol

from state_system.contracts import JsonObject, load_json, validate_schema
from state_system.stores import RecordNotFoundError, StateStoreBundle


JUDGMENT_SCHEMA: JsonObject = {
    "type": "object",
    "required": [
        "claim_id",
        "judgment",
        "rationale",
        "confidence",
        "newer_evidence_refs",
        "reviewed_at",
    ],
    "properties": {
        "claim_id": {"type": "string"},
        "judgment": {
            "type": "string",
            "enum": ["still_holds", "drifted", "superseded", "uncertain"],
        },
        "rationale": {"type": "string"},
        "confidence": {"type": "number"},
        "newer_evidence_refs": {"type": "array", "items": {"type": "string"}},
        "reviewed_at": {"type": "string"},
    },
}


class MissingCanonicalClaimJudgmentError(KeyError):
    def __init__(self, claim_id: str):
        super().__init__(f"no recorded canonical claim judgment for {claim_id}")
        self.claim_id = claim_id


class CanonicalClaimReviewer(Protocol):
    """Semantic reviewer boundary for canonical claims.

    Implementations receive code-assembled evidence and return a model-owned
    judgment. Code must not infer whether a claim still holds.
    """

    def review(self, claim: JsonObject, evidence: JsonObject) -> JsonObject:
        ...


class RecordedCanonicalClaimReviewer:
    """Replay recorded canonical claim judgments keyed by claim id."""

    def __init__(self, judgments_by_claim_id: dict[str, JsonObject]):
        self.judgments_by_claim_id = {
            key: deepcopy(value) for key, value in judgments_by_claim_id.items()
        }

    @classmethod
    def from_examples(cls, path: Path) -> "RecordedCanonicalClaimReviewer":
        judgments: dict[str, JsonObject] = {}
        for file_path in sorted(path.rglob("canonical-claim-judgment-*.json")):
            judgment = load_json(file_path)
            errors = list(validate_schema(judgment, JUDGMENT_SCHEMA))
            if errors:
                raise ValueError(
                    f"{file_path} is not a valid canonical claim judgment: {errors}"
                )
            judgments[str(judgment["claim_id"])] = judgment
        return cls(judgments)

    def review(self, claim: JsonObject, evidence: JsonObject) -> JsonObject:
        claim_id = str(claim["id"])
        if claim_id not in self.judgments_by_claim_id:
            raise MissingCanonicalClaimJudgmentError(claim_id)
        return deepcopy(self.judgments_by_claim_id[claim_id])


class LiveCanonicalClaimReviewer:
    """Production hook for an injected semantic model client.

    The supported live path is an injected ``model_client`` implementing
    ``review(registry_route=..., claim=..., evidence=..., schema_ref=...)``. A
    missing client is explicitly unsupported; code never substitutes a heuristic
    judgment.
    """

    def __init__(
        self,
        *,
        registry_route: str = "canonical-claim-review",
        model_client: object | None = None,
    ):
        self.registry_route = registry_route
        self.model_client = model_client

    def review(self, claim: JsonObject, evidence: JsonObject) -> JsonObject:
        if self.model_client is None:
            raise NotImplementedError(
                "Live canonical claim review requires an injected model_client. "
                f"Resolve route '{self.registry_route}' through the central registry, "
                "call the model with the claim and assembled evidence, and validate "
                "its output against canonical-claim-judgment.schema.json. Use the "
                "recorded reviewer for dry-runs."
            )
        return self.model_client.review(
            registry_route=self.registry_route,
            claim=claim,
            evidence=evidence,
            schema_ref="canonical-claim-judgment.schema.json",
        )


def assemble_claim_evidence(claim: JsonObject, stores: StateStoreBundle) -> JsonObject:
    """Gather the refs a reviewer needs without judging claim validity."""
    refs = list(claim.get("evidence_refs", []))
    resolved_refs: list[JsonObject] = []
    unresolved_refs: list[str] = []
    for ref in refs:
        resolved = _resolve_store_ref(str(ref), stores)
        if resolved is None:
            unresolved_refs.append(str(ref))
        else:
            resolved_refs.append(resolved)

    artifact_ref = claim.get("artifact_ref")
    artifact: JsonObject | None = None
    if artifact_ref:
        artifact = {
            "ref": artifact_ref,
            "resolved": _resolve_store_ref(str(artifact_ref), stores),
        }
        if artifact["resolved"] is None:
            artifact["resolution_status"] = "unresolved"
        else:
            artifact["resolution_status"] = "resolved"

    return {
        "claim_id": claim.get("id"),
        "claim_statement": claim.get("statement"),
        "claim_type": claim.get("claim_type"),
        "entity_ref": claim.get("entity_ref", ""),
        "evidence_refs": refs,
        "resolved_evidence": resolved_refs,
        "unresolved_evidence_refs": unresolved_refs,
        "artifact_ref": artifact_ref,
        "artifact": artifact,
        "invariant": {
            "code_assembled_evidence_only": True,
            "semantic_judgment_performed": False,
        },
    }


def _resolve_store_ref(ref: str, stores: StateStoreBundle) -> JsonObject | None:
    if ":" not in ref:
        return None
    collection, record_id = ref.split(":", 1)
    if not collection or not record_id:
        return None
    store = getattr(stores, collection, None)
    if store is None:
        return None
    try:
        return {"ref": ref, "record": store.read(record_id)}
    except (RecordNotFoundError, ValueError):
        return None


__all__ = [
    "JUDGMENT_SCHEMA",
    "MissingCanonicalClaimJudgmentError",
    "CanonicalClaimReviewer",
    "RecordedCanonicalClaimReviewer",
    "LiveCanonicalClaimReviewer",
    "assemble_claim_evidence",
]
