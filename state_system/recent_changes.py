from __future__ import annotations

from copy import deepcopy

from state_system.contracts import validate_schema
from state_system.stores import JsonObject, StateStoreBundle


class RecentChangeValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("recent change validation failed")
        self.errors = tuple(errors)


class RecentChangeIndexer:
    def __init__(self, stores: StateStoreBundle, schemas: dict[str, JsonObject]):
        self.stores = stores
        self.schemas = schemas

    def index_from_source_commit(
        self,
        *,
        source_event: JsonObject,
        commit_result: JsonObject,
        created_at: str,
        summary: str,
        candidate_persona_routes: list[JsonObject],
        opportunity_class_hints: list[str],
        freshness: JsonObject,
    ) -> JsonObject:
        review_signal = commit_result["review_signal"]
        entry = {
            "id": _recent_id(source_event),
            "created_at": created_at,
            "occurred_at": source_event["occurred_at"],
            "observed_at": source_event.get("observed_at"),
            "source_system": source_event["source_system"],
            "source_event": source_event["source_event"],
            "source_event_id": source_event.get("source_event_id"),
            "summary": summary,
            "source_refs": list(source_event["source_refs"]),
            "trigger_refs": [review_signal["trigger_id"]],
            "affected_state_refs": _unique(
                source_event.get("candidate_state_refs", []),
                commit_result.get("materialized_snapshot_refs", []),
                [
                    request["state_object_id"]
                    for request in commit_result.get("queued_rollup_requests", [])
                ],
            ),
            "journal_entry_refs": list(commit_result["accepted_journal_entry_refs"]),
            "commit_refs": [commit_result["id"]],
            "review_signal_refs": [review_signal["id"]],
            "candidate_persona_routes": deepcopy(candidate_persona_routes),
            "opportunity_class_hints": list(opportunity_class_hints),
            "unresolved_follow_up_refs": list(review_signal.get("follow_up_refs", [])),
            "freshness": deepcopy(freshness),
        }
        self._validate(entry)
        self.stores.recent_changes.create(entry)
        return entry

    def index_from_source_event(
        self,
        *,
        source_event: JsonObject,
        created_at: str,
        summary: str,
        candidate_persona_routes: list[JsonObject],
        opportunity_class_hints: list[str],
        freshness: JsonObject,
    ) -> JsonObject:
        entry = {
            "id": _recent_id(source_event),
            "created_at": created_at,
            "occurred_at": source_event["occurred_at"],
            "observed_at": source_event.get("observed_at"),
            "source_system": source_event["source_system"],
            "source_event": source_event["source_event"],
            "source_event_id": source_event.get("source_event_id"),
            "summary": summary,
            "source_refs": list(source_event["source_refs"]),
            "trigger_refs": [_trigger_id(source_event)],
            "affected_state_refs": list(source_event.get("candidate_state_refs", [])),
            "journal_entry_refs": [],
            "commit_refs": [],
            "review_signal_refs": [],
            "candidate_persona_routes": deepcopy(candidate_persona_routes),
            "opportunity_class_hints": list(opportunity_class_hints),
            "unresolved_follow_up_refs": [],
            "freshness": deepcopy(freshness),
        }
        self._validate(entry)
        self.stores.recent_changes.create(entry)
        return entry

    def _validate(self, entry: JsonObject) -> None:
        errors = validate_schema(entry, self.schemas["recent_change"])
        if errors:
            raise RecentChangeValidationError(errors)


def _recent_id(source_event: JsonObject) -> str:
    source_id = source_event["id"]
    if source_id.startswith("source."):
        return f"recent.{source_id[len('source.'):]}"
    return f"recent.{source_id}"


def _trigger_id(source_event: JsonObject) -> str:
    source_id = source_event["id"]
    if source_id.startswith("source."):
        return f"trigger.{source_id[len('source.'):]}"
    return f"trigger.{source_id}"


def _unique(*groups: list[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group:
            if value in seen:
                continue
            seen.add(value)
            values.append(value)
    return values
