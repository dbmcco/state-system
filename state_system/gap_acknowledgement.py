from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
from typing import Any

from state_system.audit_ledger import ENTRY_RETENTION, JsonObject, StateAuditLedger, _iso, _timestamp


class GapAcknowledgementLedger:
    """Non-authorizing facade for durable gap acknowledgements."""

    def __init__(self, ledger: StateAuditLedger):
        self.ledger = ledger

    def acknowledge_gap(
        self,
        gap_ref: str,
        *,
        request_id: str,
        idempotency_key: str,
        acknowledged_by_ref: str,
        reason: str,
        scope: str | None = None,
        acknowledged_at: datetime | None = None,
        redaction_policy: str = "hash_only",
        retention_class: str = "audit",
        retain_until: datetime | str | None = None,
        correlation_id: str | None = None,
    ) -> JsonObject:
        now = _timestamp(acknowledged_at, self.ledger._now())
        acknowledgement_ref = _acknowledgement_ref(request_id, gap_ref)
        payload: JsonObject = {
            "protocol_version": "state-system.v1",
            "acknowledgement_ref": acknowledgement_ref,
            "gap_ref": gap_ref,
            "request_id": request_id,
            "idempotency_key": idempotency_key,
            "retention_class": retention_class,
            "retain_until": _iso(
                _timestamp(retain_until, now + ENTRY_RETENTION)
                if retain_until is not None
                else now + ENTRY_RETENTION
            ),
            "redaction_policy": redaction_policy,
            "acknowledged_by_ref": acknowledged_by_ref,
            "acknowledged_at": _iso(now),
            "reason": reason,
        }
        if scope is not None:
            payload["scope"] = scope
        record = self.ledger.append_gap_acknowledgement(
            payload,
            request_id=request_id,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            actor_ref=acknowledged_by_ref,
        )
        # This marker is intentionally outside the canonical acknowledgement;
        # acknowledging a gap never changes freshness or grants an effect token.
        result = dict(record)
        result["authorizes"] = False
        return result

    def acknowledgements(self) -> list[JsonObject]:
        return [
            record
            for record in self.ledger.entries()
            if record["event_type"] == "gap_acknowledgement"
        ]


def acknowledge_gap(
    ledger: StateAuditLedger,
    *,
    gap_ref: str,
    request_id: str,
    idempotency_key: str,
    acknowledged_by_ref: str,
    reason: str,
    scope: str | None = None,
    acknowledged_at: datetime | None = None,
    redaction_policy: str = "hash_only",
    retention_class: str = "audit",
    retain_until: datetime | str | None = None,
    correlation_id: str | None = None,
) -> JsonObject:
    return GapAcknowledgementLedger(ledger).acknowledge_gap(
        gap_ref,
        request_id=request_id,
        idempotency_key=idempotency_key,
        acknowledged_by_ref=acknowledged_by_ref,
        reason=reason,
        scope=scope,
        acknowledged_at=acknowledged_at,
        redaction_policy=redaction_policy,
        retention_class=retention_class,
        retain_until=retain_until,
        correlation_id=correlation_id,
    )


def _acknowledgement_ref(request_id: str, gap_ref: str) -> str:
    digest = hashlib.sha256(f"{request_id}:{gap_ref}".encode("utf-8")).hexdigest()[:24]
    return f"ack:{digest}"
