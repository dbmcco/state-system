from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from state_system.contracts import validate_schema
from state_system.stores import JsonObject, StateStoreBundle


class SourceEventValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("source event validation failed")
        self.errors = tuple(errors)


@dataclass(frozen=True)
class SourceEventIngestionResult:
    created: bool
    idempotency_key: str
    source_event_id: str
    trigger: JsonObject | None
    evidence_context: JsonObject
    duplicate_of: str | None = None
    duplicate_reason: str | None = None
    watermark_status: str = "unknown"


class SourceEventIngestor:
    def __init__(self, stores: StateStoreBundle, source_event_schema: JsonObject):
        self.stores = stores
        self.source_event_schema = source_event_schema

    def ingest(self, source_event: JsonObject) -> SourceEventIngestionResult:
        errors = validate_schema(source_event, self.source_event_schema)
        if errors:
            raise SourceEventValidationError(errors)

        idempotency_key = _idempotency_key(source_event)
        existing, duplicate_reason = self._find_duplicate(source_event)
        watermark_status = self._watermark_status(source_event)
        evidence_context = _evidence_context(source_event, watermark_status)
        if existing is not None:
            self._record_duplicate(source_event, existing, duplicate_reason, watermark_status)
            return SourceEventIngestionResult(
                created=False,
                idempotency_key=idempotency_key,
                source_event_id=_source_event_id(source_event),
                trigger=None,
                evidence_context=evidence_context,
                duplicate_of=existing["id"],
                duplicate_reason=duplicate_reason,
                watermark_status=watermark_status,
            )

        self.stores.source_events.create(_record_with_watermark(source_event, watermark_status))
        trigger = _trigger_from_source_event(source_event)
        return SourceEventIngestionResult(
            created=True,
            idempotency_key=idempotency_key,
            source_event_id=_source_event_id(source_event),
            trigger=trigger,
            evidence_context=evidence_context,
            watermark_status=watermark_status,
        )

    def _find_duplicate(self, source_event: JsonObject) -> tuple[JsonObject | None, str | None]:
        identities = _dedupe_identities(source_event)
        for record in self.stores.source_events.replay():
            record_identities = _dedupe_identities(record)
            for reason in (
                "idempotency_key",
                "source_event_id",
                "semantic_fingerprint",
                "field_transition",
            ):
                if (
                    identities.get(reason)
                    and identities.get(reason) == record_identities.get(reason)
                ):
                    return record, reason
        return None, None

    def _record_duplicate(
        self,
        source_event: JsonObject,
        existing: JsonObject,
        duplicate_reason: str | None,
        watermark_status: str,
    ) -> None:
        if source_event["id"] == existing["id"]:
            return
        if source_event["id"] in self.stores.source_events.list_ids():
            return

        duplicate = _record_with_watermark(source_event, watermark_status)
        duplicate["duplicate_of_ref"] = existing["id"]
        duplicate["duplicate_reason"] = duplicate_reason
        duplicate["idempotency"] = deepcopy(source_event["idempotency"])
        duplicate["idempotency"]["duplicate_of_ref"] = existing["id"]
        self.stores.source_events.create(duplicate)

    def _watermark_status(self, source_event: JsonObject) -> str:
        watermark = _source_watermark(source_event)
        if watermark is None:
            return "unknown"

        source_system = source_event.get("source_system")
        prior_watermarks = [
            prior
            for record in self.stores.source_events.replay()
            if record.get("source_system") == source_system
            for prior in [_source_watermark(record)]
            if prior is not None
        ]
        if prior_watermarks and watermark < max(prior_watermarks):
            return "out_of_order"
        return "in_order"


def _trigger_from_source_event(source_event: JsonObject) -> JsonObject:
    payload = {
        "source_system": source_event["source_system"],
        "source_event": source_event["source_event"],
    }
    for key in ("source_event_id", "change", "sync_context"):
        if key in source_event:
            payload[key] = deepcopy(source_event[key])

    trigger: JsonObject = {
        "id": _trigger_id(source_event),
        "source": "tool_result",
        "created_at": source_event["observed_at"],
        "actor_ref": source_event["actor_ref"],
        "summary": source_event["summary"],
        "payload": payload,
        "evidence_refs": list(source_event["source_refs"]),
        "candidate_state_refs": list(source_event.get("candidate_state_refs", [])),
        "candidate_memory_refs": [],
        "governance_refs": list(source_event.get("governance_refs", [])),
    }
    return trigger


def _evidence_context(source_event: JsonObject, watermark_status: str) -> JsonObject:
    event = _record_with_watermark(source_event, watermark_status)
    return {
        "source_event": event,
        "source_refs": list(source_event["source_refs"]),
    }


def _trigger_id(source_event: JsonObject) -> str:
    source_id = str(source_event["id"])
    if source_id.startswith("source."):
        return f"trigger.{source_id[len('source.'):]}"
    return f"trigger.{source_id}"


def _source_event_id(source_event: JsonObject) -> str:
    return str(source_event.get("source_event_id") or source_event["id"])


def _idempotency_key(source_event: JsonObject) -> str:
    return str(source_event["idempotency"]["key"])


def _dedupe_identities(source_event: JsonObject) -> dict[str, str]:
    identities = {"idempotency_key": _idempotency_key(source_event)}
    source_event_id = source_event.get("source_event_id")
    if isinstance(source_event_id, str) and source_event_id:
        identities["source_event_id"] = source_event_id

    semantic_fingerprint = source_event.get("idempotency", {}).get(
        "semantic_fingerprint"
    )
    if isinstance(semantic_fingerprint, str) and semantic_fingerprint:
        identities["semantic_fingerprint"] = semantic_fingerprint

    field_transition = _field_transition_identity(source_event)
    if field_transition is not None:
        identities["field_transition"] = field_transition

    return identities


def _field_transition_identity(source_event: JsonObject) -> str | None:
    change = source_event.get("change")
    if not isinstance(change, dict):
        return None
    required = ("object_ref", "field", "old_value", "new_value")
    if not all(key in change for key in required):
        return None
    return ":".join(
        [
            str(source_event.get("source_system", "")),
            str(change["object_ref"]),
            str(change["field"]),
            str(change["old_value"]),
            str(change["new_value"]),
        ]
    )


def _source_watermark(source_event: JsonObject) -> str | None:
    sync_context = source_event.get("sync_context")
    if not isinstance(sync_context, dict):
        return None
    watermark = sync_context.get("source_watermark")
    if not isinstance(watermark, str) or not watermark:
        return None
    return watermark


def _record_with_watermark(source_event: JsonObject, watermark_status: str) -> JsonObject:
    record = deepcopy(source_event)
    if watermark_status != "unknown":
        record["watermark_status"] = watermark_status
    return record
