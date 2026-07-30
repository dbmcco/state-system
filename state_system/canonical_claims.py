# ABOUTME: Canonical claim substrate — append-only store, supersession markers,
# ABOUTME: and deterministic reevaluation-window arithmetic for agent consumers.
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from state_system.contracts import JsonObject, validate_schema
from state_system.stores import StateStoreBundle


ACTIVE = "active"
SUPERSEDED = "superseded"
RETRACTED = "retracted"
CURRENT = "current"
DUE_FOR_RECONFIRMATION = "due_for_reconfirmation"
OVERDUE = "overdue"


class CanonicalClaimRuntime:
    """Append-only writer/reader for canonical claims.

    Claim content is model/human authored. This runtime owns only mechanical
    persistence. Supersession is represented by the new active claim pointing at
    the prior claim via ``supersedes`` plus an append-only superseded-state
    marker for consumers that need an explicit inactive directive.
    """

    def __init__(self, stores: StateStoreBundle):
        self.store = stores.canonical_claims

    def record(self, claim: JsonObject) -> JsonObject:
        record = _normalize_claim(claim)
        self.store.create(record)
        return record

    def read(self, claim_id: str) -> JsonObject:
        return self.store.read(claim_id)

    def list_records(self) -> list[JsonObject]:
        return sorted(
            self.store.replay(),
            key=lambda claim: (
                claim.get("entity_ref", ""),
                claim.get("determined_at", ""),
                claim.get("id", ""),
            ),
        )


def validate_canonical_claim(record: JsonObject, schema: JsonObject) -> list[str]:
    """Validate a canonical claim using the shared schema helper."""
    return list(validate_schema(record, schema))


def supersede(
    old_id: str, new_record: JsonObject, stores: StateStoreBundle
) -> JsonObject:
    """Append a new active claim and an append-only superseded marker.

    The prior raw record is not destructively rewritten. The marker records the
    inactive state with ``status=superseded`` and ``superseded_by=<new_id>`` so
    agent-facing surfaces can name the superseder while retaining history.
    """
    runtime = CanonicalClaimRuntime(stores)
    old_record = runtime.read(old_id)
    active_record = _normalize_claim(new_record)
    active_record["status"] = ACTIVE
    active_record["supersedes"] = old_id
    active_record.setdefault("superseded_by", None)
    runtime.store.create(active_record)

    marker = deepcopy(old_record)
    marker["id"] = _superseded_marker_id(old_id, active_record["id"])
    marker["status"] = SUPERSEDED
    marker["supersedes"] = old_id
    marker["superseded_by"] = active_record["id"]
    marker["generated_at"] = active_record.get(
        "generated_at", marker.get("generated_at", "")
    )
    marker["generated_by"] = active_record.get(
        "generated_by", marker.get("generated_by", "")
    )
    runtime.store.create(marker)

    return {
        "active_claim": active_record,
        "superseded_claim": marker,
    }


def derive_reevaluation(claim: JsonObject, *, as_of: str) -> JsonObject:
    """Compute the agent-facing reevaluation directive for one claim.

    This is PURE code-owned arithmetic over declared timestamps and windows. It
    never attempts to decide whether the claim still holds semantically.
    """
    validity = (
        claim.get("validity", {}) if isinstance(claim.get("validity"), dict) else {}
    )
    window_days = int(validity.get("window_days", 0))
    basis = str(validity.get("basis", ""))
    determined_at = str(claim.get("determined_at", ""))
    last_confirmed_at = str(validity.get("last_confirmed_at", ""))
    reconfirm_by = _zulu(_parse_instant(determined_at) + timedelta(days=window_days))
    age_days = max(0, (_parse_instant(as_of) - _parse_instant(determined_at)).days)
    status = str(claim.get("status", ACTIVE))

    if status != ACTIVE:
        superseder = str(
            claim.get("superseded_by") or claim.get("supersedes") or "unknown"
        )
        return {
            "reevaluation_status": status,
            "determined_at": determined_at,
            "age_days": age_days,
            "window_days": window_days,
            "basis": basis,
            "last_confirmed_at": last_confirmed_at,
            "reconfirm_by": reconfirm_by,
            "agent_directive": (
                f"This claim is {status}; superseder: {superseder}. "
                "Do not rely on it as current canon without reviewing the replacement."
            ),
        }

    if age_days <= window_days:
        reevaluation_status = CURRENT
        status_words = "current for"
    elif age_days <= window_days * 2:
        reevaluation_status = DUE_FOR_RECONFIRMATION
        status_words = "due for"
    else:
        reevaluation_status = OVERDUE
        status_words = "overdue for"

    return {
        "reevaluation_status": reevaluation_status,
        "determined_at": determined_at,
        "age_days": age_days,
        "window_days": window_days,
        "basis": basis,
        "last_confirmed_at": last_confirmed_at,
        "reconfirm_by": reconfirm_by,
        "agent_directive": (
            f"This was determined {age_days} days ago (window {window_days}d) "
            f"and is {status_words} reconfirmation before relying on it."
        ),
    }


def build_canonical_claims_read_model(
    stores: StateStoreBundle, *, as_of: str
) -> JsonObject:
    """Build the agent/consumer read model for active canonical claims."""
    records = CanonicalClaimRuntime(stores).list_records()
    superseded_source_ids = _superseded_source_ids(records)
    retracted_source_ids = _retracted_source_ids(records)
    inactive_source_ids = superseded_source_ids | retracted_source_ids
    active_claims: list[JsonObject] = []

    for record in records:
        record_id = str(record.get("id", ""))
        if record.get("status") != ACTIVE:
            continue
        if record_id in inactive_source_ids:
            continue
        claim = deepcopy(record)
        claim["reevaluation"] = derive_reevaluation(claim, as_of=as_of)
        active_claims.append(claim)

    active_claims.sort(
        key=lambda claim: (
            claim.get("entity_ref", ""),
            claim.get("claim_type", ""),
            claim.get("id", ""),
        )
    )
    counts = Counter(
        claim["reevaluation"]["reevaluation_status"] for claim in active_claims
    )
    return {
        "id": "canonical_claims_read_model",
        "artifact_type": "json_substrate",
        "generated_at": as_of,
        "as_of": as_of,
        "active_claims": active_claims,
        "counts_by_reevaluation_status": dict(sorted(counts.items())),
        "superseded_claim_refs": sorted(superseded_source_ids),
        "retracted_claim_refs": sorted(
            retracted_source_ids
            | {
                str(record.get("id", ""))
                for record in records
                if record.get("status") == RETRACTED and not record.get("supersedes")
            }
        ),
        "invariant": {
            "reevaluation_is_window_arithmetic": True,
            "semantic_drift_judgment_is_model_owned": True,
            "code_classifies_whether_claim_still_holds": False,
            "authorizes_execution": False,
        },
    }


def _normalize_claim(claim: JsonObject) -> JsonObject:
    record = deepcopy(claim)
    record.setdefault("entity_ref", "")
    record.setdefault("artifact_ref", None)
    record.setdefault("evidence_refs", [])
    record.setdefault("status", ACTIVE)
    record.setdefault("supersedes", None)
    record.setdefault("superseded_by", None)
    return record


def _superseded_source_ids(records: list[JsonObject]) -> set[str]:
    ids = {
        str(record["supersedes"])
        for record in records
        if record.get("supersedes") and record.get("status") == ACTIVE
    }
    ids.update(
        str(record["supersedes"])
        for record in records
        if record.get("status") == SUPERSEDED and record.get("supersedes")
    )
    return ids


def _retracted_source_ids(records: list[JsonObject]) -> set[str]:
    return {
        str(record["supersedes"])
        for record in records
        if record.get("status") == RETRACTED and record.get("supersedes")
    }


def _superseded_marker_id(old_id: str, new_id: str) -> str:
    return f"{old_id}.superseded-by.{new_id}"


def _parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _zulu(moment: datetime) -> str:
    return (
        moment.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


__all__ = [
    "CanonicalClaimRuntime",
    "validate_canonical_claim",
    "supersede",
    "derive_reevaluation",
    "build_canonical_claims_read_model",
]
