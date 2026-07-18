from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Mapping


JsonObject = dict[str, Any]
Clock = Callable[[], datetime]
PROTOCOL_VERSION = "state-system.v1"
GENESIS_HASH = "0" * 64
ENTRY_RETENTION = timedelta(days=400)
CHECKPOINT_RETENTION = timedelta(days=365 * 7)
_REF_RE = re.compile(r"^[a-z][a-z0-9+.-]*:[^\s]+$")


class LedgerError(ValueError):
    """Base class for audit ledger failures."""


class LedgerConflictError(LedgerError):
    """An idempotency, request, or correlation key was reused differently."""


class LedgerTamperError(LedgerError):
    """The persisted JSONL ledger failed its hash-chain verification."""


_CONTEXT_FIELDS = frozenset(
    {
        "protocol_version",
        "decision",
        "reason",
        "route_ref",
        "decided_at",
        "expires_at",
        "evidence_refs",
        "gap_refs",
        "freshness",
        "package_ref",
        "package_hash",
        "action_ref",
        "requires_refresh_before_external_action",
    }
)
_FRESHNESS_FIELDS = frozenset(
    {
        "protocol_version",
        "status",
        "basis",
        "observed_at",
        "expires_at",
        "stale_after_seconds",
        "coverage_status",
        "evidence_refs",
        "status_reason",
    }
)
_GAP_FIELDS = frozenset(
    {
        "protocol_version",
        "acknowledgement_ref",
        "gap_ref",
        "request_id",
        "idempotency_key",
        "retention_class",
        "retain_until",
        "redaction_policy",
        "acknowledged_by_ref",
        "acknowledged_at",
        "reason",
        "scope",
    }
)


@dataclass
class StateAuditLedger:
    """Append-only, redacted, hash-chained State System decision ledger.

    Only ``StateContextDecision`` and ``GapAcknowledgement`` payloads are
    accepted.  External effect receipts deliberately have no append method.
    """

    path: Path
    clock: Clock | None = None

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        if self.clock is None:
            self.clock = lambda: datetime.now(UTC)

    def append_context_decision(
        self,
        decision: Mapping[str, Any],
        *,
        request_id: str,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        actor_ref: str = "actor:state-system",
        redaction_policy: str = "hash_only",
        retention_class: str = "audit",
        retain_until: datetime | str | None = None,
    ) -> JsonObject:
        payload = _canonical_context(decision)
        occurred_at = _timestamp(payload.get("decided_at"), self._now())
        return self._append(
            event_type="state_context_decision",
            payload=payload,
            request_id=request_id,
            idempotency_key=idempotency_key or f"request:{request_id}",
            correlation_id=correlation_id,
            actor_ref=actor_ref,
            redaction_policy=redaction_policy,
            retention_class=retention_class,
            retain_until=retain_until,
            occurred_at=occurred_at,
        )

    def append_gap_acknowledgement(
        self,
        acknowledgement: Mapping[str, Any],
        *,
        request_id: str | None = None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        actor_ref: str | None = None,
        redaction_policy: str | None = None,
        retention_class: str | None = None,
        retain_until: datetime | str | None = None,
    ) -> JsonObject:
        payload = _canonical_gap(acknowledgement)
        request_id = request_id or _required_string(payload, "request_id")
        idempotency_key = idempotency_key or _required_string(payload, "idempotency_key")
        actor_ref = actor_ref or _required_string(payload, "acknowledged_by_ref")
        policy = redaction_policy or str(payload["redaction_policy"])
        klass = retention_class or str(payload["retention_class"])
        return self._append(
            event_type="gap_acknowledgement",
            payload=payload,
            request_id=request_id,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            actor_ref=actor_ref,
            redaction_policy=policy,
            retention_class=klass,
            retain_until=retain_until or payload["retain_until"],
            occurred_at=_timestamp(payload["acknowledged_at"], self._now()),
        )

    def entries(self) -> list[JsonObject]:
        return [record for record in self._read_records() if record["record_type"] == "entry"]

    def checkpoints(self) -> list[JsonObject]:
        return [
            record
            for record in self._read_records()
            if record["record_type"] == "chain_head_checkpoint"
        ]

    def verify(self) -> bool:
        records = self._read_records()
        anchors = {GENESIS_HASH}
        for record in records:
            if record["record_type"] == "chain_head_checkpoint":
                if record.get("checkpoint_hash") != _checkpoint_hash(record):
                    raise LedgerTamperError("chain checkpoint hash mismatch")
                chain_head = record.get("chain_head_hash")
                if not isinstance(chain_head, str) or not re.fullmatch(r"[0-9a-f]{64}", chain_head):
                    raise LedgerTamperError("invalid chain checkpoint head")
                anchors.add(chain_head)

        expected = GENESIS_HASH
        seen_entry = False
        for record in records:
            if record["record_type"] != "entry":
                continue
            previous = record.get("previous_hash")
            if not isinstance(previous, str):
                raise LedgerTamperError("entry is missing previous_hash")
            if not seen_entry:
                if previous not in anchors:
                    raise LedgerTamperError("entry does not connect to a chain head")
                seen_entry = True
            elif previous != expected:
                raise LedgerTamperError("hash chain link mismatch")
            if record.get("entry_hash") != _entry_hash(record):
                raise LedgerTamperError("entry hash mismatch")
            expected = record["entry_hash"]
        return True

    verify_chain = verify

    def prune(self, *, now: datetime | None = None) -> JsonObject:
        """Drop entries older than 400 days and retain a seven-year chain anchor."""
        records = self._read_records()
        self.verify()
        current = _timestamp(now, self._now()) if now is not None else self._now()
        cutoff = current - ENTRY_RETENTION
        entries = [record for record in records if record["record_type"] == "entry"]
        old_entries = [
            record
            for record in entries
            if _timestamp(record["occurred_at"], current) < cutoff
        ]
        checkpoints = [
            record
            for record in records
            if record["record_type"] == "chain_head_checkpoint"
            and _timestamp(record["retain_until"], current) >= current
        ]
        expired_checkpoints = sum(
            1
            for record in records
            if record["record_type"] == "chain_head_checkpoint"
            and _timestamp(record["retain_until"], current) < current
        )

        if old_entries:
            chain_head = old_entries[-1]["entry_hash"] if old_entries else GENESIS_HASH
            checkpoint = {
                "record_type": "chain_head_checkpoint",
                "chain_head_hash": chain_head,
                "checkpointed_at": _iso(current),
                "retain_until": _iso(current + CHECKPOINT_RETENTION),
            }
            checkpoint["checkpoint_hash"] = _checkpoint_hash(checkpoint)
            if not any(
                item["chain_head_hash"] == chain_head for item in checkpoints
            ):
                checkpoints.append(checkpoint)

        retained_entries = [
            record
            for record in entries
            if record not in old_entries
        ]
        if old_entries or expired_checkpoints:
            self._rewrite(checkpoints + retained_entries)

        return {
            "pruned_entries": len(old_entries),
            "expired_checkpoints": expired_checkpoints,
            "cutoff": _iso(cutoff),
            "checkpoint_retention_days": CHECKPOINT_RETENTION.days,
        }

    def _append(
        self,
        *,
        event_type: str,
        payload: JsonObject,
        request_id: str,
        idempotency_key: str,
        correlation_id: str | None,
        actor_ref: str,
        redaction_policy: str,
        retention_class: str,
        retain_until: datetime | str | None,
        occurred_at: datetime,
    ) -> JsonObject:
        if event_type not in {"state_context_decision", "gap_acknowledgement"}:
            raise LedgerError("only StateContextDecision and GapAcknowledgement may be recorded")
        _validate_string(request_id, "request_id")
        _validate_string(idempotency_key, "idempotency_key")
        _validate_ref(actor_ref, "actor_ref")
        if correlation_id is not None:
            _validate_string(correlation_id, "correlation_id")
        if redaction_policy not in {"none", "bounded", "hash_only"}:
            raise LedgerError(f"invalid redaction policy: {redaction_policy}")
        if retention_class not in {"ephemeral", "operational", "audit"}:
            raise LedgerError(f"invalid retention class: {retention_class}")

        payload = _redact_payload(payload, event_type, redaction_policy)
        current = self._now()
        retain = _timestamp(retain_until, current) if retain_until is not None else current + ENTRY_RETENTION
        records = self._read_records()
        self.verify()
        for existing in records:
            if existing["record_type"] != "entry":
                continue
            if any(
                value is not None
                and existing.get(key) == value
                for key, value in (
                    ("request_id", request_id),
                    ("correlation_id", correlation_id),
                    ("idempotency_key", idempotency_key),
                )
            ):
                if _same_request(existing, event_type, payload, actor_ref):
                    return existing
                raise LedgerConflictError("request, correlation, or idempotency key was reused")

        previous_hash = _chain_head(records)
        record: JsonObject = {
            "record_type": "entry",
            "event_type": event_type,
            "payload": payload,
            "entry_ref": _entry_ref(event_type, request_id),
            "request_id": request_id,
            "correlation_id": correlation_id,
            "idempotency_key": idempotency_key,
            "actor_ref": actor_ref,
            "retention_class": retention_class,
            "retain_until": _iso(retain),
            "redaction_policy": redaction_policy,
            "occurred_at": _iso(occurred_at),
            "previous_hash": previous_hash,
        }
        record["entry_hash"] = _entry_hash(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(_json(record) + "\n")
        return record

    def _read_records(self) -> list[JsonObject]:
        if not self.path.exists():
            return []
        records: list[JsonObject] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise LedgerTamperError(f"invalid JSON at line {line_number}") from exc
                if not isinstance(value, dict) or value.get("record_type") not in {
                    "entry",
                    "chain_head_checkpoint",
                }:
                    raise LedgerTamperError(f"invalid ledger record at line {line_number}")
                records.append(value)
        return records

    def _rewrite(self, records: list[JsonObject]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            for record in records:
                handle.write(_json(record) + "\n")
        temporary.replace(self.path)

    def _now(self) -> datetime:
        assert self.clock is not None
        return _timestamp(self.clock(), datetime.now(UTC))


def _canonical_context(value: Mapping[str, Any]) -> JsonObject:
    payload = _mapping(value)
    result = {key: payload[key] for key in _CONTEXT_FIELDS if key in payload}
    result.setdefault("protocol_version", PROTOCOL_VERSION)
    if result["protocol_version"] != PROTOCOL_VERSION:
        raise LedgerError("unsupported StateContextDecision protocol_version")
    for required in ("decision", "reason", "route_ref", "decided_at"):
        if required not in result:
            raise LedgerError(f"StateContextDecision missing {required}")
    if result["decision"] not in {"include", "omit", "degrade", "deny"}:
        raise LedgerError("invalid StateContextDecision decision")
    _validate_ref(str(result["route_ref"]), "route_ref")
    _timestamp(result["decided_at"], datetime.now(UTC))
    for field in ("package_ref", "package_hash", "action_ref"):
        if result.get(field) is not None:
            _validate_ref(str(result[field]), field)
    if not isinstance(result["reason"], str) or not result["reason"]:
        raise LedgerError("StateContextDecision reason must be a non-empty string")
    return result


def _canonical_gap(value: Mapping[str, Any]) -> JsonObject:
    payload = _mapping(value)
    result = {key: payload[key] for key in _GAP_FIELDS if key in payload}
    result.setdefault("protocol_version", PROTOCOL_VERSION)
    if result["protocol_version"] != PROTOCOL_VERSION:
        raise LedgerError("unsupported GapAcknowledgement protocol_version")
    for required in (
        "acknowledgement_ref",
        "gap_ref",
        "request_id",
        "idempotency_key",
        "retention_class",
        "retain_until",
        "redaction_policy",
        "acknowledged_by_ref",
        "acknowledged_at",
        "reason",
    ):
        if required not in result:
            raise LedgerError(f"GapAcknowledgement missing {required}")
    for field in ("acknowledgement_ref", "gap_ref", "acknowledged_by_ref"):
        _validate_ref(str(result[field]), field)
    if result.get("scope") is not None:
        _validate_ref(str(result["scope"]), "scope")
    if result["retention_class"] not in {"ephemeral", "operational", "audit"}:
        raise LedgerError("invalid GapAcknowledgement retention_class")
    if result["redaction_policy"] not in {"none", "bounded", "hash_only"}:
        raise LedgerError("invalid GapAcknowledgement redaction_policy")
    return result


def _redact_payload(payload: JsonObject, event_type: str, policy: str) -> JsonObject:
    result = dict(payload)
    # Reasons are free text and may accidentally contain private message/corpus
    # data. Store only a deterministic digest marker, regardless of policy.
    if isinstance(result.get("reason"), str):
        result["reason"] = _redacted_text(result["reason"])
    if event_type == "gap_acknowledgement":
        result["redaction_policy"] = policy
    if isinstance(result.get("freshness"), dict):
        result["freshness"] = {
            key: value
            for key, value in result["freshness"].items()
            if key in _FRESHNESS_FIELDS
        }
        if isinstance(result["freshness"].get("status_reason"), str):
            result["freshness"]["status_reason"] = _redacted_text(
                result["freshness"]["status_reason"]
            )
    return result


def _redacted_text(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"[redacted:sha256:{digest}]"


def _same_request(existing: JsonObject, event_type: str, payload: JsonObject, actor_ref: str) -> bool:
    return (
        existing.get("event_type") == event_type
        and existing.get("payload") == payload
        and existing.get("actor_ref") == actor_ref
    )


def _entry_hash(record: JsonObject) -> str:
    unsigned = {key: value for key, value in record.items() if key != "entry_hash"}
    return hashlib.sha256(_json(unsigned).encode("utf-8")).hexdigest()


def _checkpoint_hash(record: JsonObject) -> str:
    unsigned = {key: value for key, value in record.items() if key != "checkpoint_hash"}
    return hashlib.sha256(_json(unsigned).encode("utf-8")).hexdigest()


def _chain_head(records: list[JsonObject]) -> str:
    entries = [record for record in records if record["record_type"] == "entry"]
    if entries:
        return str(entries[-1]["entry_hash"])
    checkpoints = [
        record for record in records if record["record_type"] == "chain_head_checkpoint"
    ]
    return str(checkpoints[-1]["chain_head_hash"]) if checkpoints else GENESIS_HASH


def _entry_ref(event_type: str, request_id: str) -> str:
    digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:24]
    return f"audit:{event_type}:{digest}"


def _mapping(value: Mapping[str, Any]) -> JsonObject:
    if not isinstance(value, Mapping):
        raise LedgerError("ledger payload must be an object")
    return dict(value)


def _required_string(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise LedgerError(f"{field} must be a non-empty string")
    return result


def _validate_string(value: str, field: str) -> None:
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        raise LedgerError(f"{field} must be a non-empty non-whitespace string")


def _validate_ref(value: str, field: str) -> None:
    if not isinstance(value, str) or not _REF_RE.fullmatch(value):
        raise LedgerError(f"{field} must be a State System reference")


def _timestamp(value: datetime | str | None, fallback: datetime) -> datetime:
    if value is None:
        result = fallback
    elif isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise LedgerError(f"invalid timestamp: {value}") from exc
    else:
        raise LedgerError("timestamp must be datetime or ISO string")
    if result.tzinfo is None:
        result = result.replace(tzinfo=UTC)
    return result.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _json(value: JsonObject) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
