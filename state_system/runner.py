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


class SourceEventIngestor:
    def __init__(self, stores: StateStoreBundle, source_event_schema: JsonObject):
        self.stores = stores
        self.source_event_schema = source_event_schema

    def ingest(self, source_event: JsonObject) -> SourceEventIngestionResult:
        errors = validate_schema(source_event, self.source_event_schema)
        if errors:
            raise SourceEventValidationError(errors)

        idempotency_key = _idempotency_key(source_event)
        existing = self._find_existing_by_idempotency_key(idempotency_key)
        evidence_context = _evidence_context(source_event)
        if existing is not None:
            return SourceEventIngestionResult(
                created=False,
                idempotency_key=idempotency_key,
                source_event_id=_source_event_id(source_event),
                trigger=None,
                evidence_context=evidence_context,
                duplicate_of=existing["id"],
            )

        self.stores.source_events.create(source_event)
        trigger = _trigger_from_source_event(source_event)
        return SourceEventIngestionResult(
            created=True,
            idempotency_key=idempotency_key,
            source_event_id=_source_event_id(source_event),
            trigger=trigger,
            evidence_context=evidence_context,
        )

    def _find_existing_by_idempotency_key(self, idempotency_key: str) -> JsonObject | None:
        for record in self.stores.source_events.replay():
            if _idempotency_key(record) == idempotency_key:
                return record
        return None


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


def _evidence_context(source_event: JsonObject) -> JsonObject:
    return {
        "source_event": deepcopy(source_event),
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
